#!/usr/bin/env python3
"""
Caico Cotton Image Generation Pipeline

Usage:
    python generate.py                                  # All products × all matched references
    python generate.py --family crossover-bodysuit      # All colours of crossover bodysuit
    python generate.py --product leggings-alabaster     # One specific product
    python generate.py --aspect 4:5                     # Instagram/Etsy portrait ratio
    python generate.py --dry-run                        # Preview prompts, no API calls
    python generate.py --model flash                    # Use cheaper Nano Banana 2
    python generate.py --no-review                      # Skip approval pauses
    python generate.py --variants 3                     # 3 variants per combo
    python generate.py --no-shuffle                     # Don't shuffle references across colours
    python generate.py --today                          # Use references from today/ subfolder
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from collections import defaultdict
from pathlib import Path

from config import PipelineConfig
from matcher import match_products_to_references
from prompts import get_template_for_product, render_prompt
from api_client import GeminiImageClient
from output_manager import OutputManager
from review import review_product_batch
from models import GenerationResult
from grid import build_from_manifest
from costs import get_cost_per_image, save_session_cost, print_cost_summary


MODEL_ALIASES = {
    "pro": "gemini-3-pro-image-preview",
    "flash": "gemini-3.1-flash-image-preview",
}

ASPECT_PRESETS = {
    "square": "1:1",
    "instagram": "4:5",
    "story": "9:16",
    "hero": "16:9",
    "etsy": "4:5",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Caico Cotton Image Generation Pipeline"
    )
    parser.add_argument(
        "--brand-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent.parent / "caico-cotton",
        help="Path to the brand directory",
    )
    parser.add_argument(
        "--product",
        type=str,
        default=None,
        help="Generate for a specific product ID only",
    )
    parser.add_argument(
        "--family",
        type=str,
        default=None,
        help="Generate for a product family (all colours), e.g. 'crossover-bodysuit'",
    )
    parser.add_argument(
        "--scene",
        type=str,
        default=None,
        help="Filter references by scene tag",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        choices=["pro", "flash"],
        help="Model: 'pro' (Nano Banana Pro) or 'flash' (Nano Banana 2)",
    )
    parser.add_argument(
        "--variants",
        type=int,
        default=None,
        help="Number of variants per product+reference combo",
    )
    parser.add_argument(
        "--aspect",
        type=str,
        default=None,
        help="Aspect ratio: '4:5' (instagram/etsy), '9:16' (stories), '16:9' (hero), '1:1' (square), or preset name",
    )
    parser.add_argument(
        "--template",
        type=str,
        default=None,
        help="Force a specific prompt template (overrides auto-selection by category)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview matches and prompts without calling the API",
    )
    parser.add_argument(
        "--no-review",
        action="store_true",
        help="Skip the approval pause between products",
    )
    parser.add_argument(
        "--no-shuffle",
        action="store_true",
        help="Don't shuffle references across colour variants",
    )
    parser.add_argument(
        "--today",
        action="store_true",
        help="Use references from the 'today' subfolder instead of the main references folder",
    )
    return parser.parse_args()


def setup_today_references(config):
    """
    If --today is used, look for images in references/today/ and auto-create
    a temporary references config from them.
    """
    today_dir = config.references_dir / "today"
    if not today_dir.exists():
        today_dir.mkdir(parents=True)
        print(f"Created today folder: {today_dir}")
        print(f"Drop reference images in there and run again.")
        sys.exit(0)

    # Find all images in today/
    image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.avif'}
    images = [f for f in today_dir.iterdir()
              if f.suffix.lower() in image_extensions]

    if not images:
        print(f"No images found in: {today_dir}")
        print(f"Drop reference images in there and run again.")
        sys.exit(0)

    # Auto-generate reference entries from filenames
    from models import Reference
    references = []
    for i, img in enumerate(sorted(images)):
        ref_id = f"today-{i+1:02d}"
        references.append(Reference(
            id=ref_id,
            image=f"today/{img.name}",
            scene="lifestyle",
            scene_description="lifestyle scene matching the reference photo",
            child_age_group="infant",
            child_age_months="0-18",
            pose="natural pose matching the reference photo",
            lighting="natural lighting matching the reference photo",
            mood="warm, natural",
            tags=["today"],
        ))
        print(f"  Found: {img.name} → {ref_id}")

    return references


def estimate_cost(num_images, model):
    costs = {
        "gemini-3-pro-image-preview": 0.134,
        "gemini-3.1-flash-image-preview": 0.045,
    }
    return num_images * costs.get(model, 0.10)


def list_families(products):
    """Show available product families."""
    families = defaultdict(list)
    for p in products:
        if p.family:
            families[p.family].append(p.colour)
    print("\nAvailable product families:")
    for fam, colours in sorted(families.items()):
        print(f"  {fam}: {', '.join(colours)}")
    print()


def main():
    args = parse_args()

    # Load config
    print(f"Loading config from: {args.brand_dir}")
    config = PipelineConfig(args.brand_dir)

    # Override model
    if args.model:
        config.model = MODEL_ALIASES.get(args.model, args.model)

    # Override variants
    if args.variants:
        config.variants_per_scene = args.variants

    # Resolve aspect ratio
    aspect_ratio = None
    if args.aspect:
        aspect_ratio = ASPECT_PRESETS.get(args.aspect, args.aspect)

    # Validate
    errors = config.validate()
    if not args.dry_run and errors:
        non_api = [e for e in errors if "API key" not in e]
        api_errors = [e for e in errors if "API key" in e]
        if non_api:
            print("Configuration errors:")
            for e in non_api:
                print(f"  ✗ {e}")
            sys.exit(1)
        if api_errors:
            print("Configuration errors:")
            for e in api_errors:
                print(f"  ✗ {e}")
            sys.exit(1)
    elif args.dry_run:
        non_api = [e for e in errors if "API key" not in e]
        if non_api:
            print("Configuration errors:")
            for e in non_api:
                print(f"  ✗ {e}")
            sys.exit(1)

    # Load products
    products = config.load_products()

    # Load references (from today folder or main config)
    if args.today:
        references = setup_today_references(config)
        print(f"Using {len(references)} references from today/ folder")
    else:
        references = config.load_references()

    print(f"Loaded {len(products)} products, {len(references)} references")

    # Show families if no filter specified
    if not args.product and not args.family:
        list_families(products)

    # Match products to references
    jobs = match_products_to_references(
        products=products,
        references=references,
        variants_per_scene=config.variants_per_scene,
        product_filter=args.product,
        family_filter=args.family,
        scene_filter=args.scene,
        shuffle_colours=not args.no_shuffle,
    )

    if not jobs:
        print("No matching jobs found. Check product/reference age ranges.")
        sys.exit(0)

    # Render prompts — auto-select template by product category
    for job in jobs:
        if args.template:
            from prompts import load_template
            template = load_template(config.templates_dir, args.template)
        else:
            template = get_template_for_product(config.templates_dir, job.product)

        # Get variation hints if set by matcher
        pose_var = getattr(job, '_pose_variation', None)
        framing_var = getattr(job, '_framing_variation', None)

        prompt, system_instruction = render_prompt(
            template=template,
            product=job.product,
            reference=job.reference,
            brand_name=config.brand_name,
            brand_tagline=config.brand_tagline,
            style_keywords_formatted=config.style_keywords_formatted,
            pose_variation=pose_var,
            framing_variation=framing_var,
        )
        job.prompt = prompt
        job.system_instruction = system_instruction

    # Group by product
    jobs_by_product = defaultdict(list)
    for job in jobs:
        jobs_by_product[job.product.id].append(job)

    # Summary
    cost = estimate_cost(len(jobs), config.model)
    print(f"\n{'='*60}")
    print(f"  Pipeline Summary")
    print(f"{'='*60}")
    print(f"  Model:      {config.model}")
    print(f"  Resolution: {config.image_size}")
    if aspect_ratio:
        print(f"  Aspect:     {aspect_ratio}")
    print(f"  Products:   {len(jobs_by_product)}")
    print(f"  References: {len(references)}")
    print(f"  Total jobs: {len(jobs)} images")
    print(f"  Est. cost:  ${cost:.2f}")
    if not args.no_shuffle and args.family:
        print(f"  Shuffle:    ON (each colour gets different reference)")
    print(f"{'='*60}\n")

    # Dry run
    if args.dry_run:
        print("DRY RUN — showing prompts for each job:\n")
        for product_id, product_jobs in jobs_by_product.items():
            product = product_jobs[0].product
            print(f"\n{'─'*60}")
            print(f"Product: {product_id} ({product.colour})")
            print(f"  Family: {product.family} | Category: {product.category}")
            print(f"  Template: {'bottom' if product.category == 'bottom' else 'lifestyle'}")
            print(f"  Matched to {len(product_jobs)} generation jobs:")
            for job in product_jobs:
                pose_var = getattr(job, '_pose_variation', 'default')
                print(f"\n  → {job.reference.id} (v{job.variant})")
                print(f"    Scene: {job.reference.scene_description[:80]}...")
                print(f"    Pose variation: {pose_var[:60]}...")
                print(f"    Prompt preview: {job.prompt[:150]}...")
        print(f"\n{'─'*60}")
        print(f"\nDry run complete. {len(jobs)} images would be generated.")
        return

    # Confirm
    try:
        confirm = input(f"Proceed with generating {len(jobs)} images? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        return
    if confirm not in ("y", "yes"):
        print("Aborted.")
        return

    # Initialize
    client = GeminiImageClient(
        api_key=config.api_key,
        model=config.model,
        image_size=config.image_size,
        aspect_ratio=aspect_ratio,
        max_retries=config.max_retries,
        retry_delay=config.retry_delay,
        rate_limit_rpm=config.rate_limit_rpm,
    )
    output = OutputManager(config.outputs_dir)

    # Generate
    total = len(jobs)
    completed = 0

    for product_id, product_jobs in jobs_by_product.items():
        product_results = []

        for job in product_jobs:
            completed += 1
            template_used = "bottom" if job.product.category == "bottom" else "lifestyle"
            print(f"\n[{completed}/{total}] {job.product.id} × {job.reference.id} (v{job.variant}) [{template_used}]")

            product_image = config.products_dir / job.product.image
            reference_image = config.references_dir / job.reference.image

            if not product_image.exists():
                result = GenerationResult(
                    job=job, success=False, error=f"Product image not found: {product_image}"
                )
                output.record_result(result)
                product_results.append(result)
                continue

            if not reference_image.exists():
                result = GenerationResult(
                    job=job, success=False, error=f"Reference image not found: {reference_image}"
                )
                output.record_result(result)
                product_results.append(result)
                continue

            image_bytes = client.generate(
                product_image_path=product_image,
                reference_image_path=reference_image,
                prompt=job.prompt,
                system_instruction=job.system_instruction,
            )

            if image_bytes:
                output_path = output.save_image(image_bytes, job)
                result = GenerationResult(
                    job=job, success=True, output_path=output_path,
                    model_used=config.model, prompt_used=job.prompt,
                )
                print(f"  ✓ Saved: {output_path}")
            else:
                result = GenerationResult(
                    job=job, success=False, error="No image returned",
                    model_used=config.model, prompt_used=job.prompt,
                )
                print(f"  ✗ Failed")

            output.record_result(result)
            product_results.append(result)

        # Review
        if not args.no_review and config.pause_for_approval:
            action = review_product_batch(
                product_id=product_id,
                results=product_results,
                pause=True,
            )
            if action == "regenerate":
                print(f"  Regenerating {product_id}...")
                for job in product_jobs:
                    image_bytes = client.generate(
                        product_image_path=config.products_dir / job.product.image,
                        reference_image_path=config.references_dir / job.reference.image,
                        prompt=job.prompt,
                        system_instruction=job.system_instruction,
                    )
                    if image_bytes:
                        output_path = output.save_image(image_bytes, job)
                        result = GenerationResult(
                            job=job, success=True, output_path=output_path,
                            model_used=config.model, prompt_used=job.prompt,
                        )
                        output.record_result(result)
                        print(f"  ✓ Saved: {output_path}")

    # Manifest
    manifest_path = output.write_manifest()
    summary = output.get_summary()

    # Cost tracking
    actual_cost = summary["successful"] * get_cost_per_image(config.model)
    save_session_cost(
        brand_dir=config.brand_dir,
        model=config.model,
        num_images=summary["total"],
        num_successful=summary["successful"],
        cost=actual_cost,
    )

    # Contact sheet
    print("\nGenerating contact sheet...")
    grid_path = build_from_manifest(output.batch_dir)

    print(f"\n{'='*60}")
    print(f"  Pipeline Complete!")
    print(f"{'='*60}")
    print(f"  Total:      {summary['total']} images")
    print(f"  Successful: {summary['successful']}")
    print(f"  Failed:     {summary['failed']}")
    print(f"  Session:    ${actual_cost:.2f}")
    print(f"  Output:     {summary['output_dir']}")
    print(f"  Manifest:   {manifest_path}")
    if grid_path:
        print(f"  Grid:       {grid_path}")
    print_cost_summary(config.brand_dir)
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
