"""Configuration loader for the image generation pipeline."""

import os
import sys
from pathlib import Path
from typing import Any

import yaml

from models import Product, Reference


def load_yaml(path: Path) -> dict:
    """Load a YAML file and return its contents."""
    if not path.exists():
        print(f"Error: Config file not found: {path}")
        sys.exit(1)
    with open(path) as f:
        return yaml.safe_load(f) or {}


class PipelineConfig:
    """Loads and validates all pipeline configuration."""

    def __init__(self, brand_dir: Path):
        """
        Args:
            brand_dir: Path to the brand directory (e.g. ~/story-unheard/caico-cotton/)
        """
        self.brand_dir = brand_dir.resolve()
        self.pipeline_yaml = self.brand_dir / "pipeline.yaml"

        # Load master config
        raw = load_yaml(self.pipeline_yaml)

        # API settings
        api = raw.get("api", {})
        self.api_key = os.environ.get(api.get("key_env_var", "GOOGLE_GENAI_API_KEY"), "")
        self.model = api.get("model", "gemini-3-pro-image-preview")
        self.fallback_model = api.get("fallback_model", "gemini-3.1-flash-image-preview")
        self.max_retries = api.get("max_retries", 3)
        self.retry_delay = api.get("retry_delay_seconds", 5)
        self.rate_limit_rpm = api.get("rate_limit_rpm", 10)

        # Generation settings
        gen = raw.get("generation", {})
        self.image_size = gen.get("image_size", "4K")
        self.variants_per_scene = gen.get("variants_per_scene", 2)

        # Paths (relative to brand_dir)
        paths = raw.get("paths", {})
        self.products_dir = self._resolve(paths.get("products_dir", "images/products"))
        self.references_dir = self._resolve(paths.get("references_dir", "images/references"))
        self.outputs_dir = self._resolve(paths.get("outputs_dir", "images/outputs"))
        self.products_config = self._resolve(paths.get("products_config", "products.yaml"))
        self.references_config = self._resolve(paths.get("references_config", "references.yaml"))
        self.templates_dir = self._resolve(paths.get("templates_dir", "prompt_templates"))

        # Review settings
        review = raw.get("review", {})
        self.pause_for_approval = review.get("pause_for_approval", True)

        # Brand settings (for prompt templates)
        brand = raw.get("brand", {})
        self.brand_name = brand.get("name", "Caico Cotton")
        self.brand_tagline = brand.get("tagline", "100% Organic Egyptian Cotton")
        self.style_keywords = brand.get("style_keywords", [])

    def _resolve(self, relative: str) -> Path:
        """Resolve a path relative to the brand directory."""
        return (self.brand_dir / relative).resolve()

    @property
    def style_keywords_formatted(self) -> str:
        return ", ".join(self.style_keywords)

    def load_products(self) -> list[Product]:
        """Load product catalogue from YAML."""
        raw = load_yaml(self.products_config)
        products = []
        for p in raw.get("products", []):
            product = Product(
                id=p["id"],
                name=p["name"],
                colour=p["colour"],
                colour_description=p.get("colour_description", p["colour"]),
                product_type=p["product_type"],
                subtype=p.get("subtype"),
                sleeve=p.get("sleeve"),
                image=p["image"],
                age_ranges=p.get("age_ranges", []),
                key_details=p.get("key_details", []),
                fabric_description=p.get("fabric_description", "organic Egyptian cotton"),
                family=p.get("family", p["id"].rsplit("-", 1)[0]),
                category=p.get("category", "full"),
            )
            # Validate image exists
            img_path = self.products_dir / product.image
            if not img_path.exists():
                print(f"Warning: Product image not found: {img_path}")
            products.append(product)
        return products

    def load_references(self) -> list[Reference]:
        """Load reference image catalogue from YAML."""
        raw = load_yaml(self.references_config)
        references = []
        for r in raw.get("references", []):
            ref = Reference(
                id=r["id"],
                image=r["image"],
                scene=r["scene"],
                scene_description=r.get("scene_description", ""),
                child_age_group=r.get("child_age_group", "infant"),
                child_age_months=str(r.get("child_age_months", "0-12")),
                pose=r.get("pose", ""),
                lighting=r.get("lighting", ""),
                mood=r.get("mood", ""),
                tags=r.get("tags", []),
            )
            # Validate image exists
            img_path = self.references_dir / ref.image
            if not img_path.exists():
                print(f"Warning: Reference image not found: {img_path}")
            references.append(ref)
        return references

    def validate(self) -> list[str]:
        """Check config is valid. Returns list of errors (empty = OK)."""
        errors = []
        if not self.api_key:
            errors.append(
                f"No API key found. Set the GOOGLE_GENAI_API_KEY environment variable "
                f"or configure api.key_env_var in pipeline.yaml"
            )
        if not self.products_dir.exists():
            errors.append(f"Products directory not found: {self.products_dir}")
        if not self.references_dir.exists():
            errors.append(f"References directory not found: {self.references_dir}")
        if not self.products_config.exists():
            errors.append(f"Products config not found: {self.products_config}")
        if not self.references_config.exists():
            errors.append(f"References config not found: {self.references_config}")
        if not self.templates_dir.exists():
            errors.append(f"Templates directory not found: {self.templates_dir}")
        return errors
