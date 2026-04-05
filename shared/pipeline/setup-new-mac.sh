#!/bin/bash
# One-time setup for Caico Cotton Image Pipeline on a new Mac
# Run this once: bash setup-new-mac.sh

echo ""
echo "  ✨ Caico Cotton Pipeline — Setup"
echo "  ─────────────────────────────────"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "  ❌ Python 3 not found. Install it from python.org first."
    exit 1
fi
echo "  ✓ Python 3 found: $(python3 --version)"

# Install dependencies
echo "  Installing dependencies..."
pip3 install google-genai pyyaml Pillow rich flask 2>&1 | tail -1
echo "  ✓ Dependencies installed"

# Verify
echo ""
echo "  ✓ Setup complete!"
echo ""
echo "  To use the pipeline:"
echo "  1. Double-click 'Caico Pipeline' on the Desktop"
echo "  2. Or run: cd ~/story-unheard/shared/pipeline && python3 web.py"
echo "  3. Open http://localhost:5050 in Chrome"
echo ""
