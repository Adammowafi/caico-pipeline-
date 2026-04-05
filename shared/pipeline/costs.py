"""Cost tracking for API usage."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional


COST_PER_IMAGE = {
    "gemini-3-pro-image-preview": 0.134,
    "gemini-3.1-flash-image-preview": 0.045,
}

COST_FILE = "cost_history.json"


def get_cost_per_image(model: str) -> float:
    return COST_PER_IMAGE.get(model, 0.10)


def load_cost_history(brand_dir: Path) -> dict:
    """Load cost history from the brand directory."""
    path = brand_dir / COST_FILE
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"sessions": [], "total_images": 0, "total_cost": 0.0}


def save_session_cost(
    brand_dir: Path,
    model: str,
    num_images: int,
    num_successful: int,
    cost: float,
):
    """Record a generation session's cost."""
    history = load_cost_history(brand_dir)

    session = {
        "date": datetime.now().isoformat(),
        "model": model,
        "images_attempted": num_images,
        "images_successful": num_successful,
        "cost_usd": round(cost, 4),
    }

    history["sessions"].append(session)
    history["total_images"] += num_successful
    history["total_cost"] = round(history["total_cost"] + cost, 4)

    path = brand_dir / COST_FILE
    with open(path, "w") as f:
        json.dump(history, f, indent=2)


def print_cost_summary(brand_dir: Path):
    """Print a summary of costs."""
    history = load_cost_history(brand_dir)

    if not history["sessions"]:
        print("No cost history yet.")
        return

    # This month
    now = datetime.now()
    month_cost = 0.0
    month_images = 0
    today_cost = 0.0
    today_images = 0

    for s in history["sessions"]:
        session_date = datetime.fromisoformat(s["date"])
        if session_date.year == now.year and session_date.month == now.month:
            month_cost += s["cost_usd"]
            month_images += s["images_successful"]
        if session_date.date() == now.date():
            today_cost += s["cost_usd"]
            today_images += s["images_successful"]

    print(f"\n  Cost Summary")
    print(f"  {'─'*40}")
    print(f"  Today:      {today_images} images  ${today_cost:.2f}")
    print(f"  This month: {month_images} images  ${month_cost:.2f}")
    print(f"  All time:   {history['total_images']} images  ${history['total_cost']:.2f}")
    print(f"  {'─'*40}")
