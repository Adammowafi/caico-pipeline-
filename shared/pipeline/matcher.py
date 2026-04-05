"""Product-to-reference matching with colour shuffle logic."""
from __future__ import annotations

import random
from collections import defaultdict
from typing import List, Optional

from models import Product, Reference, GenerationJob, POSE_VARIATIONS, FRAMING_VARIATIONS


def ranges_overlap(a: tuple, b: tuple) -> bool:
    """Check if two numeric ranges overlap."""
    return a[0] < b[1] and b[0] < a[1]


def overlap_score(a: tuple, b: tuple) -> float:
    """Calculate overlap as a fraction of the reference range."""
    overlap_start = max(a[0], b[0])
    overlap_end = min(a[1], b[1])
    overlap = max(0, overlap_end - overlap_start)
    ref_span = max(1, b[1] - b[0])
    return overlap / ref_span


def match_products_to_references(
    products: List[Product],
    references: List[Reference],
    variants_per_scene: int = 2,
    product_filter: Optional[str] = None,
    family_filter: Optional[str] = None,
    scene_filter: Optional[str] = None,
    shuffle_colours: bool = True,
) -> List[GenerationJob]:
    """
    Match products to age-appropriate references with colour shuffling.

    When shuffle_colours is True and a product family has multiple colours,
    each colour gets a DIFFERENT reference so the images don't look
    computer-generated (identical scene, different colour = obvious AI).

    Args:
        products: All available products
        references: All available reference images
        variants_per_scene: How many variants per product+reference combo
        product_filter: Optional product ID to filter to
        family_filter: Optional family name to filter to (runs all colours)
        scene_filter: Optional scene tag to filter references
        shuffle_colours: Distribute references across colour variants

    Returns:
        List of GenerationJob objects
    """
    # Apply filters
    if product_filter:
        products = [p for p in products if p.id == product_filter]
        if not products:
            print(f"No product found with ID: {product_filter}")
            return []

    if family_filter:
        products = [p for p in products if p.family == family_filter]
        if not products:
            print(f"No products found in family: {family_filter}")
            return []

    if scene_filter:
        references = [r for r in references if scene_filter in r.tags or r.scene == scene_filter]
        if not references:
            print(f"No references found with scene/tag: {scene_filter}")
            return []

    if not shuffle_colours:
        # Simple mode: every product gets every matching reference
        return _match_simple(products, references, variants_per_scene)

    # Group products by family
    families = defaultdict(list)
    standalone = []
    for p in products:
        if p.family:
            families[p.family].append(p)
        else:
            standalone.append(p)

    jobs = []

    # For each family, shuffle references across colour variants
    for family_name, family_products in families.items():
        # Find references that match ANY product in the family (age-wise)
        family_month_range = (
            min(p.month_range[0] for p in family_products),
            max(p.month_range[1] for p in family_products),
        )
        matching_refs = []
        for ref in references:
            if ranges_overlap(family_month_range, ref.month_range):
                score = overlap_score(family_month_range, ref.month_range)
                matching_refs.append((ref, score))

        matching_refs.sort(key=lambda x: x[1], reverse=True)
        matched_refs = [r for r, _ in matching_refs]

        if not matched_refs:
            continue

        # Distribute references across colours
        # If 3 colours and 2 references: colour1→ref1, colour2→ref2, colour3→ref1 (with variation)
        num_colours = len(family_products)
        num_refs = len(matched_refs)

        for colour_idx, product in enumerate(family_products):
            # Pick which reference(s) this colour gets
            # Rotate through references so each colour gets a different one
            ref_idx = colour_idx % num_refs
            ref = matched_refs[ref_idx]

            # Pick pose/framing variation based on colour index
            pose_var = POSE_VARIATIONS[colour_idx % len(POSE_VARIATIONS)]
            framing_var = FRAMING_VARIATIONS[colour_idx % len(FRAMING_VARIATIONS)]

            for variant in range(1, variants_per_scene + 1):
                job = GenerationJob(
                    product=product,
                    reference=ref,
                    variant=variant,
                )
                # Store variation hints for prompt rendering
                job._pose_variation = pose_var
                job._framing_variation = framing_var
                jobs.append(job)

    # Standalone products (no family) get simple matching
    jobs.extend(_match_simple(standalone, references, variants_per_scene))

    return jobs


def _match_simple(
    products: List[Product],
    references: List[Reference],
    variants_per_scene: int,
) -> List[GenerationJob]:
    """Simple matching: each product gets all age-appropriate references."""
    jobs = []
    for product in products:
        product_months = product.month_range
        matched_refs = []

        for ref in references:
            ref_months = ref.month_range
            if ranges_overlap(product_months, ref_months):
                score = overlap_score(product_months, ref_months)
                matched_refs.append((ref, score))

        matched_refs.sort(key=lambda x: x[1], reverse=True)

        for ref, _score in matched_refs:
            for variant in range(1, variants_per_scene + 1):
                jobs.append(GenerationJob(
                    product=product,
                    reference=ref,
                    variant=variant,
                ))

    return jobs
