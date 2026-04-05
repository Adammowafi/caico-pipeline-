"""Output file management — saving images, organizing folders, writing manifests."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from models import GenerationJob, GenerationResult


class OutputManager:
    """Manages output file organization and manifest tracking."""

    def __init__(self, outputs_dir: Path, batch_date: Optional[str] = None):
        self.outputs_dir = outputs_dir
        self.batch_date = batch_date or datetime.now().strftime("%Y-%m-%d")
        self.batch_dir = outputs_dir / self.batch_date
        self.results: list[GenerationResult] = []

    def ensure_dirs(self, product_id: str) -> Path:
        """Create output directories and return the product output folder."""
        product_dir = self.batch_dir / product_id
        product_dir.mkdir(parents=True, exist_ok=True)
        return product_dir

    def save_image(self, image_bytes: bytes, job: GenerationJob) -> Path:
        """Save generated image bytes to the correct location."""
        product_dir = self.ensure_dirs(job.product.id)
        filename = f"{job.reference.id}_v{job.variant}.png"
        output_path = product_dir / filename
        with open(output_path, "wb") as f:
            f.write(image_bytes)
        return output_path

    def record_result(self, result: GenerationResult):
        """Add a result to the manifest."""
        self.results.append(result)

    def write_manifest(self):
        """Write the full manifest.json for this batch."""
        self.batch_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = self.batch_dir / "manifest.json"

        manifest = {
            "batch_date": self.batch_date,
            "generated_at": datetime.now().isoformat(),
            "total_jobs": len(self.results),
            "successful": sum(1 for r in self.results if r.success),
            "failed": sum(1 for r in self.results if not r.success),
            "results": [r.to_dict() for r in self.results],
        }

        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        return manifest_path

    def get_summary(self) -> dict:
        """Get a summary of results so far."""
        return {
            "total": len(self.results),
            "successful": sum(1 for r in self.results if r.success),
            "failed": sum(1 for r in self.results if not r.success),
            "output_dir": str(self.batch_dir),
        }
