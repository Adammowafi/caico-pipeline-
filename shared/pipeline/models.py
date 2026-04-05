"""Data models for the Caico Cotton image generation pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class AgeGroup(Enum):
    NEWBORN = "newborn"      # 0-3 months
    INFANT = "infant"        # 3-12 months
    TODDLER = "toddler"     # 12-36 months
    CHILD = "child"          # 3-6 years


# Size range to month range mapping
SIZE_TO_MONTHS = {
    "NB": (0, 1),
    "NB-3M": (0, 3),
    "0-3M": (0, 3),
    "1-3M": (1, 3),
    "3-6M": (3, 6),
    "6-9M": (6, 9),
    "9-12M": (9, 12),
    "6-12M": (6, 12),
    "12-18M": (12, 18),
    "12-18": (12, 18),
    "18-24M": (18, 24),
    "2-3Y": (24, 36),
    "3-4Y": (36, 48),
    "4-5Y": (48, 60),
    "5-6Y": (60, 72),
    "6-7Y": (72, 84),
    "ONE SIZE": (0, 12),
    "One Size": (0, 12),
}

# Prompt variation modifiers — shuffled per colour to avoid identical scenes
POSE_VARIATIONS = [
    "looking directly at the camera with a gentle expression",
    "looking slightly to the left with a curious expression",
    "looking down at their hands with a peaceful expression",
    "looking slightly to the right with a happy expression",
    "looking up with wide eyes and a slight smile",
]

FRAMING_VARIATIONS = [
    "full body shot showing the complete outfit from head to toe",
    "three-quarter shot from the waist up, garment details clearly visible",
    "close-up shot emphasising the fabric texture and garment construction",
    "medium shot with the child slightly off-centre, natural composition",
    "slightly elevated angle looking down, showing the full garment layout",
]


@dataclass
class Product:
    """A Caico Cotton product with its flatlay image and metadata."""
    id: str
    name: str
    colour: str
    colour_description: str
    product_type: str
    subtype: Optional[str]
    sleeve: Optional[str]
    image: str  # filename in products dir
    age_ranges: list[str]
    key_details: list[str]
    fabric_description: str
    family: str = ""           # groups colour variants, e.g. "crossover-bodysuit"
    category: str = "full"     # "top", "bottom", "full", "accessory" — determines prompt template

    @property
    def month_range(self) -> tuple[int, int]:
        """Get the full month range this product covers across all sizes."""
        if not self.age_ranges:
            return (0, 72)  # default to all ages
        min_month = min(SIZE_TO_MONTHS.get(s, (0, 72))[0] for s in self.age_ranges)
        max_month = max(SIZE_TO_MONTHS.get(s, (0, 72))[1] for s in self.age_ranges)
        return (min_month, max_month)

    @property
    def key_details_formatted(self) -> str:
        """Join key details into a prompt-friendly string."""
        return "; ".join(self.key_details)

    @property
    def age_description(self) -> str:
        """Human-readable age range for prompts."""
        min_m, max_m = self.month_range
        if max_m <= 3:
            return "newborn (0-3 months)"
        elif max_m <= 12:
            return f"{min_m}-{max_m} month old baby"
        elif max_m <= 24:
            return f"{min_m}-{max_m} month old toddler"
        else:
            min_y = min_m // 12
            max_y = max_m // 12
            return f"{min_y}-{max_y} year old child"


@dataclass
class Reference:
    """A reference lifestyle image with scene metadata."""
    id: str
    image: str  # filename in references dir
    scene: str
    scene_description: str
    child_age_group: str  # newborn | infant | toddler | child
    child_age_months: str  # e.g. "0-3" or "18-36"
    pose: str
    lighting: str
    mood: str
    tags: list[str] = field(default_factory=list)

    @property
    def month_range(self) -> tuple[int, int]:
        """Parse the child_age_months string into a numeric range."""
        if "-" in self.child_age_months:
            parts = self.child_age_months.split("-")
            return (int(parts[0]), int(parts[1]))
        else:
            m = int(self.child_age_months)
            return (m, m + 3)  # assume 3 month window for single values

    @property
    def child_age_description(self) -> str:
        """Human-readable age for prompts."""
        group = self.child_age_group
        months = self.child_age_months
        if group == "newborn":
            return f"newborn baby (approximately {months} months old)"
        elif group == "infant":
            return f"baby (approximately {months} months old)"
        elif group == "toddler":
            return f"toddler (approximately {months} months old)"
        else:
            return f"young child (approximately {months} months old)"


@dataclass
class GenerationJob:
    """A matched product + reference pair ready for generation."""
    product: Product
    reference: Reference
    prompt: str = ""
    system_instruction: str = ""
    variant: int = 1

    @property
    def job_id(self) -> str:
        return f"{self.product.id}__{self.reference.id}__v{self.variant}"


@dataclass
class GenerationResult:
    """Result of a single image generation attempt."""
    job: GenerationJob
    success: bool
    output_path: Optional[Path] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    model_used: str = ""
    prompt_used: str = ""

    def to_dict(self) -> dict:
        """Serialize for manifest.json."""
        return {
            "job_id": self.job.job_id,
            "product_id": self.job.product.id,
            "reference_id": self.job.reference.id,
            "variant": self.job.variant,
            "success": self.success,
            "output_path": str(self.output_path) if self.output_path else None,
            "error": self.error,
            "timestamp": self.timestamp,
            "model_used": self.model_used,
            "prompt_used": self.prompt_used,
        }
