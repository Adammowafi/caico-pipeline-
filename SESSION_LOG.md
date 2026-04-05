# Session Log — 5 April 2026

## What Was Built

### Caico Cotton Image Generation Pipeline
A complete system that takes product flatlay photos + reference lifestyle images and generates photorealistic lifestyle product photography using Google's Gemini API (Nano Banana Pro).

### Components Built
1. **CLI Pipeline** (`shared/pipeline/generate.py`) — command-line tool for batch image generation
2. **Web UI** (`shared/pipeline/web.py`) — browser-based interface at localhost:5050 for wife to use
3. **Desktop Launcher** (`~/Desktop/Caico Pipeline.command`) — double-click to start
4. **38 products** catalogued with accurate garment details from flatlay inspection + Shopify export
5. **Prompt templates** — lifestyle (full garments) + bottom (leggings/pants paired with plain white top)
6. **Age matching** — auto-matches products to age-appropriate reference images
7. **Colour shuffle** — each colour variant gets different pose/framing so images don't look AI-generated
8. **Contact sheet** — auto-generates a grid of all outputs for quick review
9. **Cost tracking** — tracks API spend per session, daily, monthly

### Key Decisions Made
- **Gemini API** (Nano Banana Pro) via google-genai SDK, not browser automation
- **YAML configs** for products and references (human-readable)
- **Auto template selection** — bottoms use a different prompt that pairs with a plain white top
- **Pose/framing variations** per colour to avoid identical-looking outputs
- **Label fix** — prompts explicitly say no labels/tags visible on front of garments
- **Port 5050** — port 5000 blocked by AirPlay on Mac
- **Web UI drag-and-drop** for reference images — auto-saves to references folder + updates YAML

### API Key
- Google AI Studio key is set in the launcher script and used by the pipeline
- Adam's account: adam@mo4network.com

### What's NOT Built Yet
- **BekyaBekya pipeline** — same architecture but different templates (homeware not babywear), different matching logic (product type not age), needs its own prompt templates for pottery/glassware/alabaster in home settings
- **Google Drive sync** — Drive desktop app not installed, using local files for now
- **Wife's laptop setup** — need to AirDrop the story-unheard folder + run setup-new-mac.sh
- **Full Shopify-synced products.yaml** — current YAML has 38 products from flatlays, Shopify export saved but not fully integrated (has ~60 SKUs including Cotton Bloom prints, pyjama sets, muslin dress, etc.)
- **Outfit pairing** — combining top + bottom flatlays into one generation (e.g. bodysuit + leggings together)
- **Favourite/reject workflow** — marking good/bad outputs to learn which combos work
- **A/B prompt testing** — comparing different prompt templates side by side

### CLI Usage
```bash
cd ~/story-unheard/shared/pipeline
export GOOGLE_GENAI_API_KEY="your-key"

python3 generate.py --family crossover-bodysuit --no-review    # all colours
python3 generate.py --product leggings-alabaster --no-review   # one product
python3 generate.py --family leggings --aspect 4:5 --no-review # Instagram ratio
python3 generate.py --model flash --no-review                  # cheaper model
python3 generate.py --dry-run                                  # preview only
python3 generate.py --today --no-review                        # use today/ references
```

### Web UI Usage
1. Double-click "Caico Pipeline" on Desktop (or run `python3 web.py`)
2. Opens at http://localhost:5050
3. Drag-drop reference images into the browser
4. Click product family → pick settings → Generate
5. Review outputs in browser + full-res files in images/outputs/

### Wife's Workflow (Current)
Her old process: manually pick flatlay → find reference → write prompt in ChatGPT → paste into AI Studio → re-prompt when wrong → tweak face → repeat per product (hours per image)

New process: drag references into browser → click product family → hit Generate → review grid → done (minutes for a full colour range)

### File Structure
```
~/story-unheard/
├── BUSINESS_BRIEF.md
├── SESSION_LOG.md              ← this file
├── caico-cotton/
│   ├── pipeline.yaml
│   ├── products.yaml           ← 38 products
│   ├── references.yaml
│   ├── shopify-export.csv
│   ├── cost_history.json
│   ├── prompt_templates/
│   │   ├── lifestyle.yaml
│   │   └── bottom.yaml
│   └── images/
│       ├── products/           ← 39 flatlay photos
│       ├── references/         ← lifestyle reference photos
│       └── outputs/            ← generated images + contact sheets
├── bekyabekya/                 ← empty, ready for future
│   ├── images/
│   ├── prompts/
│   └── exports/
└── shared/
    ├── pipeline/
    │   ├── generate.py         ← CLI
    │   ├── web.py              ← Web UI (port 5050)
    │   ├── models.py
    │   ├── config.py
    │   ├── matcher.py
    │   ├── prompts.py
    │   ├── api_client.py
    │   ├── output_manager.py
    │   ├── grid.py
    │   ├── costs.py
    │   ├── review.py
    │   ├── requirements.txt
    │   └── setup-new-mac.sh
    └── warehouse-reports/
```

### For Next Session
To get any new Claude Code session up to speed, say:
"Read ~/story-unheard/BUSINESS_BRIEF.md and ~/story-unheard/SESSION_LOG.md"
