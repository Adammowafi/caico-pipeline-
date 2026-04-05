"""Interactive review/approval loop for generated images."""
from __future__ import annotations

from pathlib import Path

from models import GenerationResult


def review_product_batch(
    product_id: str,
    results: list[GenerationResult],
    pause: bool = True,
) -> str:
    """
    Show results for a product and optionally pause for approval.

    Args:
        product_id: The product being reviewed
        results: Results for this product
        pause: Whether to wait for user input

    Returns:
        "approve", "skip", or "regenerate"
    """
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    print(f"\n{'='*60}")
    print(f"  Product: {product_id}")
    print(f"  Generated: {len(successful)} images | Failed: {len(failed)}")
    print(f"{'='*60}")

    if successful:
        print(f"\n  ✓ Saved to:")
        for r in successful:
            print(f"    {r.output_path}")

    if failed:
        print(f"\n  ✗ Failed:")
        for r in failed:
            print(f"    {r.job.reference.id} v{r.job.variant}: {r.error}")

    if not pause:
        return "approve"

    print(f"\n  Open the output folder to review images.")
    print(f"  [a]pprove and continue | [s]kip | [r]egenerate | [q]uit")

    while True:
        try:
            choice = input("  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return "skip"

        if choice in ("a", "approve", "y", "yes", ""):
            return "approve"
        elif choice in ("s", "skip", "n", "no"):
            return "skip"
        elif choice in ("r", "regenerate", "redo"):
            return "regenerate"
        elif choice in ("q", "quit", "exit"):
            print("  Stopping pipeline.")
            raise KeyboardInterrupt
        else:
            print("  Please enter: a(pprove), s(kip), r(egenerate), or q(uit)")
