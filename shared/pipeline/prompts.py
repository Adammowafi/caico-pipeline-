"""Prompt template engine with category-aware template selection and variation support."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from models import Product, Reference, GenerationJob


# Map product category to template name
CATEGORY_TEMPLATE_MAP = {
    "full": "lifestyle",       # bodysuits, jumpsuits, rompers — covers whole body
    "top": "lifestyle",        # tees, blouses — top only, but similar prompt
    "bottom": "bottom",        # leggings, pants, bloomers — needs special handling
    "accessory": "lifestyle",  # bibs, bonnets — use standard template
}


def load_template(templates_dir: Path, template_name: str = "lifestyle") -> dict:
    """Load a prompt template YAML file."""
    path = templates_dir / f"{template_name}.yaml"
    if not path.exists():
        # Fall back to lifestyle template
        path = templates_dir / "lifestyle.yaml"
        if not path.exists():
            raise FileNotFoundError(f"No prompt templates found in: {templates_dir}")
    with open(path) as f:
        return yaml.safe_load(f)


def get_template_for_product(templates_dir: Path, product: Product) -> dict:
    """Auto-select the right template based on product category."""
    template_name = CATEGORY_TEMPLATE_MAP.get(product.category, "lifestyle")
    return load_template(templates_dir, template_name)


def render_prompt(
    template: dict,
    product: Product,
    reference: Reference,
    brand_name: str = "Caico Cotton",
    brand_tagline: str = "100% Organic Egyptian Cotton",
    style_keywords_formatted: str = "",
    pose_variation: Optional[str] = None,
    framing_variation: Optional[str] = None,
    child_age_override: Optional[str] = None,
) -> tuple:
    """
    Render a prompt template with product and reference metadata.

    Args:
        template: The loaded YAML template
        product: Product with metadata
        reference: Reference image with metadata
        pose_variation: Optional override for child pose (for colour shuffling)
        framing_variation: Optional override for framing/composition

    Returns:
        Tuple of (prompt, system_instruction)
    """
    # Build the variable map
    variables = {
        # Brand
        "brand_name": brand_name,
        "brand_tagline": brand_tagline,
        "style_keywords_formatted": style_keywords_formatted,
        # Product
        "product_name": product.name,
        "product_type": product.product_type,
        "product_subtype": product.subtype or product.product_type,
        "colour": product.colour,
        "colour_description": product.colour_description,
        "fabric_description": product.fabric_description,
        "key_details_formatted": product.key_details_formatted,
        "sleeve": product.sleeve or "sleeveless",
        "product_age_description": product.age_description,
        # Reference
        "scene": reference.scene,
        "scene_description": reference.scene_description,
        "child_age_group": reference.child_age_group,
        "child_age_description": child_age_override or reference.child_age_description,
        "pose": pose_variation or reference.pose,
        "lighting": reference.lighting,
        "mood": reference.mood,
        # Variations
        "pose_variation": pose_variation or reference.pose,
        "framing_variation": framing_variation or "full body shot showing the complete outfit",
    }

    # Render
    prompt = template.get("prompt", "").format_map(variables)
    system_instruction = template.get("system_instruction", "").format_map(variables)

    return prompt, system_instruction
