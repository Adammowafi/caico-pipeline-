"""Generate a comparison contact sheet from a batch of generated images."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont


def build_contact_sheet(
    batch_dir: Path,
    columns: int = 4,
    thumb_width: int = 512,
    padding: int = 20,
    label_height: int = 40,
    output_name: str = "contact_sheet.jpg",
) -> Optional[Path]:
    """
    Build a contact sheet grid from all generated images in a batch directory.

    Args:
        batch_dir: Path to the date-stamped batch folder (e.g. outputs/2026-04-05/)
        columns: Number of columns in the grid
        thumb_width: Width of each thumbnail
        padding: Pixels between thumbnails
        label_height: Height reserved for text label below each thumbnail
        output_name: Filename for the contact sheet

    Returns:
        Path to the saved contact sheet, or None if no images found
    """
    # Find all generated images
    images = []
    for product_dir in sorted(batch_dir.iterdir()):
        if not product_dir.is_dir():
            continue
        for img_path in sorted(product_dir.glob("*.png")):
            product_id = product_dir.name
            ref_name = img_path.stem  # e.g. "sitting-baby-cream-01_v1"
            images.append({
                "path": img_path,
                "label": f"{product_id}\n{ref_name}",
                "product": product_id,
            })

    if not images:
        print("No images found in batch directory.")
        return None

    # Calculate grid dimensions
    num_images = len(images)
    rows = (num_images + columns - 1) // columns
    thumb_height = thumb_width  # assume square-ish thumbnails

    cell_width = thumb_width + padding
    cell_height = thumb_height + label_height + padding

    grid_width = columns * cell_width + padding
    grid_height = rows * cell_height + padding

    # Create canvas
    canvas = Image.new("RGB", (grid_width, grid_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    # Try to load a nice font, fall back to default
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 11)
    except (OSError, IOError):
        font = ImageFont.load_default()
        font_small = font

    # Place thumbnails
    for idx, img_info in enumerate(images):
        row = idx // columns
        col = idx % columns

        x = padding + col * cell_width
        y = padding + row * cell_height

        # Load and resize image
        try:
            img = Image.open(img_info["path"])
            img.thumbnail((thumb_width, thumb_height), Image.LANCZOS)

            # Center the thumbnail if it's not exactly the right size
            offset_x = x + (thumb_width - img.width) // 2
            offset_y = y + (thumb_height - img.height) // 2
            canvas.paste(img, (offset_x, offset_y))
        except Exception as e:
            # Draw a placeholder
            draw.rectangle([x, y, x + thumb_width, y + thumb_height], outline=(200, 200, 200))
            draw.text((x + 10, y + thumb_height // 2), f"Error: {e}", fill=(255, 0, 0), font=font_small)

        # Draw label
        label_y = y + thumb_height + 4
        lines = img_info["label"].split("\n")
        draw.text((x + 4, label_y), lines[0], fill=(40, 40, 40), font=font)
        if len(lines) > 1:
            draw.text((x + 4, label_y + 16), lines[1], fill=(120, 120, 120), font=font_small)

    # Save
    output_path = batch_dir / output_name
    canvas.save(output_path, "JPEG", quality=90)
    print(f"Contact sheet saved: {output_path}")
    print(f"  {num_images} images in {rows}×{columns} grid ({grid_width}×{grid_height}px)")
    return output_path


def build_from_manifest(batch_dir: Path, **kwargs) -> Optional[Path]:
    """Build contact sheet using manifest data for richer labels."""
    manifest_path = batch_dir / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        successful = manifest.get("successful", 0)
        failed = manifest.get("failed", 0)
        print(f"Batch: {successful} successful, {failed} failed")

    return build_contact_sheet(batch_dir, **kwargs)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python grid.py <batch_dir>")
        print("  e.g. python grid.py ../../caico-cotton/images/outputs/2026-04-05")
        sys.exit(1)

    batch_path = Path(sys.argv[1]).resolve()
    if not batch_path.exists():
        print(f"Directory not found: {batch_path}")
        sys.exit(1)

    build_from_manifest(batch_path)
