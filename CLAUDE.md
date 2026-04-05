# Story Unheard — Claude Code Project

## Quick Start
Read BUSINESS_BRIEF.md and SESSION_LOG.md for full context.

## What This Is
Image generation pipeline for Caico Cotton (baby clothing brand). Takes product flatlay photos + reference lifestyle images and generates photorealistic lifestyle product photography using Google's Gemini API.

## Owner
Adam Mowafi (adam@mo4network.com) — runs two brands under Story Unheard LTD:
- **Caico Cotton** — organic Egyptian cotton baby/kids clothing (pipeline built)
- **BekyaBekya** — Egyptian artisan homeware (pipeline planned, not built)

## How To Work With Adam
- Copy-paste ready outputs, not explanations
- He explores before committing — don't assume he wants to execute immediately
- His wife handles creative direction and uses the web UI
- Warehouse files are source of truth for stock, not Shopify

## Key Commands
```bash
# Start the web UI (wife's workflow)
cd ~/story-unheard/shared/pipeline
export GOOGLE_GENAI_API_KEY="AIzaSyALUzLCnK0SGN5m096I6GxLbPRp5A6n7uI"
python3 web.py
# Opens at http://localhost:5050

# CLI usage
python3 generate.py --family crossover-bodysuit --no-review
python3 generate.py --product leggings-alabaster --aspect 4:5 --no-review
python3 generate.py --dry-run
```

## Key Files
- `caico-cotton/products.yaml` — 38 products with garment details
- `caico-cotton/references.yaml` — reference lifestyle images
- `caico-cotton/prompt_templates/` — lifestyle.yaml + bottom.yaml
- `shared/pipeline/generate.py` — CLI entry point
- `shared/pipeline/web.py` — Web UI (port 5050)

## Not Yet Built
- BekyaBekya pipeline (homeware — pottery, glassware, alabaster)
- Outfit pairing (top + bottom combos)
- Wife's laptop setup (needs AirDrop + setup-new-mac.sh)
- Full Shopify product sync
- Google Drive sync between Macs
