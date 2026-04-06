#!/usr/bin/env python3
"""
Simple web UI for the Caico Cotton image generation pipeline.
Run: python web.py
Open: http://localhost:5000
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template_string, request, jsonify, send_from_directory

from config import PipelineConfig
from costs import load_cost_history

# Paths
BRAND_DIR = Path(__file__).resolve().parent.parent.parent / "caico-cotton"
PIPELINE_DIR = Path(__file__).resolve().parent

app = Flask(__name__)

# Track running jobs
running_job = {"active": False, "log": [], "progress": 0, "total": 0}


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Caico Cotton — Image Pipeline</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #faf9f7; color: #333; }

        .header { background: #fff; border-bottom: 1px solid #e8e4df; padding: 20px 40px; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { font-size: 22px; font-weight: 600; color: #2c2c2c; }
        .header .cost { font-size: 14px; color: #888; }

        .container { max-width: 1200px; margin: 0 auto; padding: 30px 40px; }

        .section { background: #fff; border: 1px solid #e8e4df; border-radius: 12px; padding: 24px; margin-bottom: 24px; }
        .section h2 { font-size: 16px; font-weight: 600; margin-bottom: 16px; color: #555; }

        .product-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }
        .product-card { border: 2px solid #e8e4df; border-radius: 8px; padding: 8px; cursor: pointer; transition: all 0.2s; text-align: center; }
        .product-card:hover { border-color: #c4a882; }
        .product-card.selected { border-color: #8b6914; background: #fdf6ec; }
        .product-card img { width: 100%; height: 100px; object-fit: contain; border-radius: 4px; margin-bottom: 6px; }
        .product-card .name { font-size: 11px; font-weight: 600; color: #444; }
        .product-card .colour { font-size: 10px; color: #888; }

        .ref-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
        .ref-card { border: 2px solid #e8e4df; border-radius: 8px; padding: 8px; cursor: pointer; transition: all 0.2s; }
        .ref-card:hover { border-color: #c4a882; }
        .ref-card.selected { border-color: #8b6914; background: #fdf6ec; }
        .ref-card img { width: 100%; height: 120px; object-fit: cover; border-radius: 4px; margin-bottom: 6px; }
        .ref-card .name { font-size: 11px; color: #444; text-align: center; }

        .controls { display: flex; gap: 16px; align-items: center; flex-wrap: wrap; }
        .controls select, .controls input { padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
        .controls label { font-size: 13px; color: #666; }

        .generate-btn { background: #8b6914; color: white; border: none; padding: 14px 32px; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; transition: background 0.2s; }
        .generate-btn:hover { background: #725811; }
        .generate-btn:disabled { background: #ccc; cursor: not-allowed; }

        .progress { background: #f0ebe4; border-radius: 8px; height: 8px; margin-top: 12px; overflow: hidden; display: none; }
        .progress-bar { background: #8b6914; height: 100%; width: 0%; transition: width 0.3s; border-radius: 8px; }

        .log { font-family: 'SF Mono', Monaco, monospace; font-size: 12px; background: #1e1e1e; color: #d4d4d4; padding: 16px; border-radius: 8px; max-height: 200px; overflow-y: auto; margin-top: 12px; display: none; white-space: pre-wrap; }

        .output-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 16px; margin-top: 16px; }
        .output-card { border: 1px solid #e8e4df; border-radius: 8px; overflow: hidden; background: #fff; }
        .output-card img { width: 100%; height: auto; }
        .output-card .info { padding: 8px 12px; font-size: 12px; color: #666; display: flex; justify-content: space-between; align-items: center; }
        .output-card .info .label { flex: 1; }

        .dl-btn { background: #8b6914; color: white; border: none; padding: 5px 10px; border-radius: 4px; font-size: 11px; cursor: pointer; text-decoration: none; }
        .dl-btn:hover { background: #725811; }

        .dl-all-btn { background: #555; color: white; border: none; padding: 10px 20px; border-radius: 6px; font-size: 14px; cursor: pointer; margin-top: 12px; }
        .dl-all-btn:hover { background: #333; }

        .family-chips { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
        .family-chip { padding: 6px 14px; border: 1px solid #ddd; border-radius: 20px; font-size: 12px; cursor: pointer; transition: all 0.2s; }
        .family-chip:hover { border-color: #c4a882; }
        .family-chip.selected { background: #8b6914; color: white; border-color: #8b6914; }

        .drop-zone { border: 2px dashed #ccc; border-radius: 12px; padding: 32px; text-align: center; cursor: pointer; transition: all 0.2s; margin-bottom: 16px; }
        .drop-zone:hover, .drop-zone.dragover { border-color: #8b6914; background: #fdf6ec; }
        .drop-zone .icon { font-size: 32px; margin-bottom: 8px; }
        .drop-zone .text { font-size: 14px; color: #888; }
        .drop-zone .subtext { font-size: 12px; color: #aaa; margin-top: 4px; }
        .drop-zone input[type="file"] { display: none; }

        .ref-card .delete-btn { position: absolute; top: 4px; right: 4px; background: rgba(0,0,0,0.5); color: white; border: none; border-radius: 50%; width: 22px; height: 22px; font-size: 12px; cursor: pointer; display: none; line-height: 22px; text-align: center; }
        .ref-card:hover .delete-btn { display: block; }
        .ref-card { position: relative; }

        .uploading { opacity: 0.5; pointer-events: none; }
        .upload-spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid #ccc; border-top-color: #8b6914; border-radius: 50%; animation: spin 0.6s linear infinite; margin-right: 6px; vertical-align: middle; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="header">
        <h1>Caico Cotton — Image Pipeline</h1>
        <div class="cost" id="cost-summary">Loading...</div>
    </div>

    <div class="container">
        <!-- Product Families -->
        <div class="section">
            <h2>1. Select Product Family</h2>
            <div class="family-chips" id="family-chips"></div>
            <div class="product-grid" id="product-grid"></div>
        </div>

        <!-- References -->
        <div class="section">
            <h2>2. Reference Images</h2>
            <div class="drop-zone" id="drop-zone" onclick="document.getElementById('file-input').click()">
                <div class="icon">+</div>
                <div class="text">Drag & drop reference images here</div>
                <div class="subtext">or click to browse — JPG, PNG, WEBP</div>
                <input type="file" id="file-input" multiple accept="image/*">
            </div>
            <div id="upload-status"></div>
            <div class="ref-grid" id="ref-grid"></div>
        </div>

        <!-- Settings -->
        <div class="section">
            <h2>3. Settings</h2>
            <div class="controls">
                <div>
                    <label>Where is this for?</label><br>
                    <select id="aspect">
                        <option value="">Shopify / Website (Square 1:1)</option>
                        <option value="4:5">Instagram Feed / Etsy (Portrait 4:5)</option>
                        <option value="9:16">Instagram Stories / Reels / TikTok (Vertical 9:16)</option>
                        <option value="16:9">Website Hero Banner / Facebook Cover (Wide 16:9)</option>
                        <option value="4:3">Etsy Landscape (4:3)</option>
                    </select>
                </div>
                <div>
                    <label>How many options per image?</label><br>
                    <select id="variants">
                        <option value="1">1 — single shot</option>
                        <option value="2">2 — pick the best</option>
                        <option value="3">3 — more to choose from</option>
                    </select>
                </div>
                <div>
                    <label>Child age</label><br>
                    <select id="child-age">
                        <option value="">Auto (match product sizes)</option>
                        <option value="newborn">Newborn (0-3 months)</option>
                        <option value="baby-small">Small baby (3-6 months)</option>
                        <option value="baby">Baby (6-12 months)</option>
                        <option value="toddler-young">Young toddler (12-18 months)</option>
                        <option value="toddler">Toddler (18-24 months)</option>
                        <option value="child-small">Small child (2-3 years)</option>
                        <option value="child">Child (3-5 years)</option>
                        <option value="child-older">Older child (5-7 years)</option>
                    </select>
                </div>
                <div>
                    <label>Model</label><br>
                    <select id="model">
                        <option value="pro">Nano Banana Pro ($0.13/img)</option>
                        <option value="flash">Nano Banana Flash ($0.045/img)</option>
                    </select>
                </div>
            </div>
        </div>

        <!-- Generate -->
        <div class="section">
            <button class="generate-btn" id="generate-btn" onclick="generate()">Generate Images</button>
            <span id="estimate" style="margin-left: 16px; font-size: 14px; color: #888;"></span>
            <div class="progress" id="progress"><div class="progress-bar" id="progress-bar"></div></div>
            <div class="log" id="log"></div>
        </div>

        <!-- Outputs -->
        <div class="section" id="outputs-section" style="display: none;">
            <h2>Generated Images</h2>
            <button class="dl-all-btn" onclick="downloadAll()">Download All as ZIP</button>
            <div class="output-grid" id="output-grid"></div>
        </div>
    </div>

    <script>
        let products = [];
        let families = {};
        let references = [];
        let selectedFamily = null;
        let selectedProducts = new Set();

        async function loadData() {
            const resp = await fetch('/api/data');
            const data = await resp.json();
            products = data.products;
            references = data.references;
            families = {};

            products.forEach(p => {
                if (!families[p.family]) families[p.family] = [];
                families[p.family].push(p);
            });

            renderFamilies();
            renderReferences();
            loadCost();
            loadOutputs();
        }

        function renderFamilies() {
            const container = document.getElementById('family-chips');
            container.innerHTML = '';
            Object.keys(families).sort().forEach(fam => {
                const chip = document.createElement('div');
                chip.className = 'family-chip' + (fam === selectedFamily ? ' selected' : '');
                chip.textContent = fam.replace(/-/g, ' ') + ' (' + families[fam].length + ')';
                chip.onclick = () => { selectFamily(fam); };
                container.appendChild(chip);
            });
        }

        function selectFamily(fam) {
            selectedFamily = fam === selectedFamily ? null : fam;
            selectedProducts = new Set();
            if (selectedFamily) {
                families[selectedFamily].forEach(p => selectedProducts.add(p.id));
            }
            renderFamilies();
            renderProducts();
            updateEstimate();
        }

        function renderProducts() {
            const container = document.getElementById('product-grid');
            container.innerHTML = '';
            const displayProducts = selectedFamily ? families[selectedFamily] : products;

            displayProducts.forEach(p => {
                const card = document.createElement('div');
                card.className = 'product-card' + (selectedProducts.has(p.id) ? ' selected' : '');
                card.innerHTML = '<img src="/product-image/' + p.image + '" onerror="this.style.display=\\'none\\'"><div class="name">' + p.name + '</div><div class="colour">' + p.colour + '</div>';
                card.onclick = () => {
                    if (selectedProducts.has(p.id)) selectedProducts.delete(p.id);
                    else selectedProducts.add(p.id);
                    renderProducts();
                    updateEstimate();
                };
                container.appendChild(card);
            });
        }

        function renderReferences() {
            const container = document.getElementById('ref-grid');
            container.innerHTML = '';
            references.forEach(r => {
                const card = document.createElement('div');
                card.className = 'ref-card selected';
                card.innerHTML = '<img src="/ref-image/' + r.image + '" onerror="this.style.display=\\'none\\'"><button class="delete-btn" onclick="event.stopPropagation(); deleteRef(\\'' + r.id + '\\')">x</button><div class="name">' + r.id + '</div>';
                container.appendChild(card);
            });
        }

        // Drag and drop
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file-input');

        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
        dropZone.addEventListener('dragleave', () => { dropZone.classList.remove('dragover'); });
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            handleFiles(e.dataTransfer.files);
        });
        fileInput.addEventListener('change', (e) => { handleFiles(e.target.files); fileInput.value = ''; });

        async function handleFiles(files) {
            const status = document.getElementById('upload-status');
            status.innerHTML = '<span class="upload-spinner"></span> Uploading ' + files.length + ' image(s)...';

            const formData = new FormData();
            for (const file of files) {
                formData.append('files', file);
            }

            try {
                const resp = await fetch('/api/upload-references', { method: 'POST', body: formData });
                const data = await resp.json();
                if (data.success) {
                    status.innerHTML = '<span style="color: #2a7d2a;">Uploaded ' + data.count + ' reference(s)</span>';
                    setTimeout(() => { status.innerHTML = ''; }, 3000);
                    // Reload references
                    const dataResp = await fetch('/api/data');
                    const newData = await dataResp.json();
                    references = newData.references;
                    renderReferences();
                    updateEstimate();
                } else {
                    status.innerHTML = '<span style="color: red;">Upload failed: ' + data.error + '</span>';
                }
            } catch(e) {
                status.innerHTML = '<span style="color: red;">Upload error: ' + e.message + '</span>';
            }
        }

        async function deleteRef(refId) {
            const resp = await fetch('/api/delete-reference/' + refId, { method: 'DELETE' });
            const data = await resp.json();
            if (data.success) {
                const dataResp = await fetch('/api/data');
                const newData = await dataResp.json();
                references = newData.references;
                renderReferences();
                updateEstimate();
            }
        }

        function updateEstimate() {
            const variants = parseInt(document.getElementById('variants').value) || 1;
            const model = document.getElementById('model').value;
            const costPerImage = model === 'flash' ? 0.045 : 0.134;
            const numImages = selectedProducts.size * references.length * variants;
            const cost = (numImages * costPerImage).toFixed(2);
            document.getElementById('estimate').textContent = numImages + ' images · ~$' + cost;
        }

        async function generate() {
            if (selectedProducts.size === 0) { alert('Select at least one product'); return; }

            const btn = document.getElementById('generate-btn');
            btn.disabled = true;
            btn.textContent = 'Generating...';

            const progress = document.getElementById('progress');
            const progressBar = document.getElementById('progress-bar');
            const log = document.getElementById('log');
            progress.style.display = 'block';
            log.style.display = 'block';
            log.textContent = '';
            document.getElementById('output-grid').innerHTML = '';
            document.getElementById('outputs-section').style.display = 'none';

            const body = {
                product_ids: Array.from(selectedProducts),
                family: selectedFamily,
                aspect: document.getElementById('aspect').value,
                variants: parseInt(document.getElementById('variants').value) || 1,
                model: document.getElementById('model').value,
                child_age: document.getElementById('child-age').value,
            };

            const resp = await fetch('/api/generate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(body),
            });

            const reader = resp.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const {value, done} = await reader.read();
                if (done) break;
                const text = decoder.decode(value);
                const lines = text.split('\\n').filter(l => l.trim());

                for (const line of lines) {
                    try {
                        const msg = JSON.parse(line);
                        if (msg.type === 'progress') {
                            progressBar.style.width = ((msg.completed / msg.total) * 100) + '%';
                            log.textContent += msg.message + '\\n';
                            log.scrollTop = log.scrollHeight;
                            // Show image immediately if path included
                            if (msg.image_path) {
                                const section = document.getElementById('outputs-section');
                                const grid = document.getElementById('output-grid');
                                section.style.display = 'block';
                                const card = document.createElement('div');
                                card.className = 'output-card';
                                card.innerHTML = '<img src="/output-image/' + msg.image_path + '">' +
                                    '<div class="info"><span class="label">' + msg.product + ' · ' + msg.reference + '</span>' +
                                    '<a class="dl-btn" href="/output-image/' + msg.image_path + '" download="' + msg.product + '_' + msg.reference + '.png">Download</a></div>';
                                grid.prepend(card);
                            }
                        } else if (msg.type === 'complete') {
                            log.textContent += '\\n✅ ' + msg.message + '\\n';
                        } else if (msg.type === 'error') {
                            log.textContent += '\\n❌ ' + msg.message + '\\n';
                        }
                    } catch(e) {}
                }
            }

            btn.disabled = false;
            btn.textContent = 'Generate Images';
            loadCost();
        }

        async function loadCost() {
            const resp = await fetch('/api/costs');
            const data = await resp.json();
            document.getElementById('cost-summary').textContent =
                'Today: $' + data.today_cost.toFixed(2) + ' · Month: $' + data.month_cost.toFixed(2) + ' · All time: $' + data.total_cost.toFixed(2);
        }

        async function loadOutputs() {
            const resp = await fetch('/api/outputs');
            const data = await resp.json();
            const section = document.getElementById('outputs-section');
            const grid = document.getElementById('output-grid');

            if (data.images.length === 0) { section.style.display = 'none'; return; }
            section.style.display = 'block';
            grid.innerHTML = '';

            data.images.forEach(img => {
                const card = document.createElement('div');
                card.className = 'output-card';
                card.innerHTML = '<img src="/output-image/' + img.path + '">' +
                    '<div class="info"><span class="label">' + img.product + ' · ' + img.reference + '</span>' +
                    '<a class="dl-btn" href="/output-image/' + img.path + '" download="' + img.product + '_' + img.reference + '.png">Download</a></div>';
                grid.appendChild(card);
            });
        }

        async function downloadAll() {
            const btn = document.querySelector('.dl-all-btn');
            btn.textContent = 'Zipping...';
            btn.disabled = true;

            try {
                const resp = await fetch('/api/download-all');
                const blob = await resp.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'caico-images-' + new Date().toISOString().split('T')[0] + '.zip';
                a.click();
                URL.revokeObjectURL(url);
            } catch(e) {
                alert('Download failed: ' + e.message);
            }

            btn.textContent = 'Download All as ZIP';
            btn.disabled = false;
        }

        document.getElementById('variants').addEventListener('change', updateEstimate);
        document.getElementById('model').addEventListener('change', updateEstimate);

        loadData();
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/data")
def api_data():
    config = PipelineConfig(BRAND_DIR)
    products = config.load_products()
    references = config.load_references()

    return jsonify({
        "products": [
            {"id": p.id, "name": p.name, "colour": p.colour, "family": p.family,
             "category": p.category, "image": p.image}
            for p in products
        ],
        "references": [
            {"id": r.id, "image": r.image, "scene": r.scene}
            for r in references
        ],
    })


@app.route("/api/costs")
def api_costs():
    history = load_cost_history(BRAND_DIR)
    now = datetime.now()
    today_cost = 0.0
    month_cost = 0.0

    for s in history.get("sessions", []):
        d = datetime.fromisoformat(s["date"])
        if d.date() == now.date():
            today_cost += s["cost_usd"]
        if d.year == now.year and d.month == now.month:
            month_cost += s["cost_usd"]

    return jsonify({
        "today_cost": today_cost,
        "month_cost": month_cost,
        "total_cost": history.get("total_cost", 0.0),
    })


@app.route("/api/outputs")
def api_outputs():
    outputs_dir = BRAND_DIR / "images" / "outputs"
    images = []

    # Get the latest batch
    batches = sorted([d for d in outputs_dir.iterdir() if d.is_dir()], reverse=True)
    if batches:
        batch = batches[0]
        for product_dir in sorted(batch.iterdir()):
            if not product_dir.is_dir():
                continue
            for img in sorted(product_dir.glob("*.png")):
                images.append({
                    "path": f"{batch.name}/{product_dir.name}/{img.name}",
                    "product": product_dir.name,
                    "reference": img.stem,
                })

    return jsonify({"images": images})


@app.route("/api/upload-references", methods=["POST"])
def api_upload_references():
    """Handle drag-and-drop reference image uploads."""
    config = PipelineConfig(BRAND_DIR)
    refs_dir = config.references_dir
    refs_config_path = config.references_config

    files = request.files.getlist("files")
    if not files:
        return jsonify({"success": False, "error": "No files uploaded"})

    # Load existing references
    import yaml
    with open(refs_config_path) as f:
        refs_yaml = yaml.safe_load(f) or {}
    existing_refs = refs_yaml.get("references", [])
    existing_ids = {r["id"] for r in existing_refs}

    # Count existing uploaded refs to generate unique IDs
    upload_count = sum(1 for r in existing_refs if r["id"].startswith("upload-"))

    added = []
    for file in files:
        if not file.filename:
            continue

        # Generate a clean filename and ID
        ext = Path(file.filename).suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".avif"}:
            continue

        upload_count += 1
        ref_id = f"upload-{upload_count:03d}"

        # Save with clean name
        clean_filename = f"{ref_id}{ext}"
        save_path = refs_dir / clean_filename
        file.save(str(save_path))

        # Convert avif to jpg if needed (Gemini API might not support avif)
        if ext == ".avif":
            try:
                from PIL import Image as PILImage
                img = PILImage.open(save_path)
                jpg_path = refs_dir / f"{ref_id}.jpg"
                img.convert("RGB").save(str(jpg_path), quality=95)
                save_path.unlink()
                clean_filename = f"{ref_id}.jpg"
            except Exception:
                pass  # keep the avif if conversion fails

        # Add to references config with sensible defaults
        new_ref = {
            "id": ref_id,
            "image": clean_filename,
            "scene": "lifestyle",
            "scene_description": "lifestyle scene matching the reference photo",
            "child_age_group": "infant",
            "child_age_months": "0-18",
            "pose": "natural pose matching the reference photo",
            "lighting": "natural lighting matching the reference photo",
            "mood": "warm, natural",
            "tags": ["uploaded"],
        }
        existing_refs.append(new_ref)
        added.append(ref_id)

    # Save updated references.yaml
    refs_yaml["references"] = existing_refs
    with open(refs_config_path, "w") as f:
        yaml.dump(refs_yaml, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return jsonify({"success": True, "count": len(added), "ids": added})


@app.route("/api/delete-reference/<ref_id>", methods=["DELETE"])
def api_delete_reference(ref_id):
    """Remove a reference image and its config entry."""
    config = PipelineConfig(BRAND_DIR)
    refs_dir = config.references_dir
    refs_config_path = config.references_config

    import yaml
    with open(refs_config_path) as f:
        refs_yaml = yaml.safe_load(f) or {}

    existing_refs = refs_yaml.get("references", [])

    # Find and remove
    removed = None
    new_refs = []
    for r in existing_refs:
        if r["id"] == ref_id:
            removed = r
        else:
            new_refs.append(r)

    if not removed:
        return jsonify({"success": False, "error": "Reference not found"})

    # Delete the image file
    img_path = refs_dir / removed["image"]
    if img_path.exists():
        img_path.unlink()

    # Save updated config
    refs_yaml["references"] = new_refs
    with open(refs_config_path, "w") as f:
        yaml.dump(refs_yaml, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return jsonify({"success": True})


@app.route("/api/download-all")
def api_download_all():
    """Download all images from the latest batch as a ZIP."""
    import zipfile
    import io

    outputs_dir = BRAND_DIR / "images" / "outputs"
    batches = sorted([d for d in outputs_dir.iterdir() if d.is_dir()], reverse=True)

    if not batches:
        return jsonify({"error": "No images to download"}), 404

    batch = batches[0]
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for product_dir in sorted(batch.iterdir()):
            if not product_dir.is_dir():
                continue
            for img in sorted(product_dir.glob("*.png")):
                arcname = f"{product_dir.name}/{img.name}"
                zf.write(img, arcname)

    zip_buffer.seek(0)
    return app.response_class(
        zip_buffer.getvalue(),
        mimetype="application/zip",
        headers={"Content-Disposition": f"attachment; filename=caico-images-{batch.name}.zip"},
    )


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """Run the pipeline directly in-process (no subprocess)."""
    from collections import defaultdict
    from config import PipelineConfig
    from matcher import match_products_to_references
    from prompts import get_template_for_product, render_prompt
    from api_client import GeminiImageClient
    from output_manager import OutputManager
    from models import GenerationResult
    from grid import build_from_manifest
    from costs import get_cost_per_image, save_session_cost

    MODEL_MAP = {"pro": "gemini-3-pro-image-preview", "flash": "gemini-3.1-flash-image-preview"}

    AGE_DESCRIPTIONS = {
        "newborn": "newborn baby (approximately 0-3 months old)",
        "baby-small": "small baby (approximately 3-6 months old)",
        "baby": "baby (approximately 6-12 months old)",
        "toddler-young": "young toddler (approximately 12-18 months old)",
        "toddler": "toddler (approximately 18-24 months old)",
        "child-small": "small child (approximately 2-3 years old)",
        "child": "young child (approximately 3-5 years old)",
        "child-older": "child (approximately 5-7 years old)",
    }

    data = request.json
    family = data.get("family")
    product_ids = data.get("product_ids", [])
    aspect = data.get("aspect", "") or None
    variants = data.get("variants", 1)
    model_name = MODEL_MAP.get(data.get("model", "pro"), "gemini-3-pro-image-preview")
    child_age = data.get("child_age", "")
    child_age_description = AGE_DESCRIPTIONS.get(child_age, "")

    def generate_stream():
        try:
            config = PipelineConfig(BRAND_DIR)
            config.model = model_name
            config.variants_per_scene = variants

            products = config.load_products()
            references = config.load_references()

            # Filter to only the products the user actually selected
            if product_ids:
                products = [p for p in products if p.id in product_ids]

            if not products:
                yield json.dumps({"type": "error", "message": "No products selected"}) + "\n"
                return

            jobs = match_products_to_references(
                products=products,
                references=references,
                variants_per_scene=variants,
                shuffle_colours=True,
            )

            if not jobs:
                yield json.dumps({"type": "error", "message": "No matching jobs found"}) + "\n"
                return

            # Render prompts
            for job in jobs:
                template = get_template_for_product(config.templates_dir, job.product)
                pose_var = getattr(job, '_pose_variation', None)
                framing_var = getattr(job, '_framing_variation', None)

                prompt, sys_instr = render_prompt(
                    template=template, product=job.product, reference=job.reference,
                    brand_name=config.brand_name, brand_tagline=config.brand_tagline,
                    style_keywords_formatted=config.style_keywords_formatted,
                    pose_variation=pose_var, framing_variation=framing_var,
                    child_age_override=child_age_description if child_age_description else None,
                )
                job.prompt = prompt
                job.system_instruction = sys_instr

            total = len(jobs)
            yield json.dumps({"type": "progress", "completed": 0, "total": total, "message": f"Starting {total} images..."}) + "\n"

            # Use env var directly as fallback (Railway sets it at runtime)
            api_key = config.api_key or os.environ.get("GOOGLE_GENAI_API_KEY", "")
            if not api_key:
                yield json.dumps({"type": "error", "message": "API key not set. Add GOOGLE_GENAI_API_KEY in Railway Variables."}) + "\n"
                return

            client = GeminiImageClient(
                api_key=api_key,
                model=config.model,
                image_size=config.image_size,
                aspect_ratio=aspect,
                max_retries=config.max_retries,
                retry_delay=config.retry_delay,
                rate_limit_rpm=config.rate_limit_rpm,
            )
            output = OutputManager(config.outputs_dir)

            for i, job in enumerate(jobs):
                product_image = config.products_dir / job.product.image
                reference_image = config.references_dir / job.reference.image

                if not product_image.exists() or not reference_image.exists():
                    result = GenerationResult(job=job, success=False, error="Image file not found")
                    output.record_result(result)
                    yield json.dumps({"type": "progress", "completed": i+1, "total": total, "message": f"✗ {job.product.id} — image not found"}) + "\n"
                    continue

                image_bytes = client.generate(
                    product_image_path=product_image,
                    reference_image_path=reference_image,
                    prompt=job.prompt,
                    system_instruction=job.system_instruction,
                )

                if image_bytes:
                    output_path = output.save_image(image_bytes, job)
                    result = GenerationResult(job=job, success=True, output_path=output_path, model_used=config.model, prompt_used=job.prompt)
                    output.record_result(result)
                    # Include image path so frontend can show it immediately
                    rel_path = f"{output.batch_date}/{job.product.id}/{job.reference.id}_v{job.variant}.png"
                    yield json.dumps({
                        "type": "progress", "completed": i+1, "total": total,
                        "message": f"✓ {job.product.id} × {job.reference.id}",
                        "image_path": rel_path,
                        "product": job.product.id,
                        "reference": job.reference.id,
                    }) + "\n"
                else:
                    result = GenerationResult(job=job, success=False, error="No image returned", model_used=config.model, prompt_used=job.prompt)
                    output.record_result(result)
                    yield json.dumps({"type": "progress", "completed": i+1, "total": total, "message": f"✗ {job.product.id} — generation failed"}) + "\n"

            # Save manifest + grid + costs
            output.write_manifest()
            try:
                build_from_manifest(output.batch_dir)
            except Exception:
                pass

            summary = output.get_summary()
            actual_cost = summary["successful"] * get_cost_per_image(config.model)
            save_session_cost(BRAND_DIR, config.model, summary["total"], summary["successful"], actual_cost)

            yield json.dumps({"type": "complete", "message": f"Done! {summary['successful']}/{summary['total']} images generated. Cost: ${actual_cost:.2f}"}) + "\n"

        except Exception as e:
            yield json.dumps({"type": "error", "message": f"Error: {str(e)}"}) + "\n"

    return app.response_class(
        generate_stream(),
        mimetype="text/plain",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@app.route("/product-image/<path:filename>")
def product_image(filename):
    return send_from_directory(BRAND_DIR / "images" / "products", filename)


@app.route("/ref-image/<path:filename>")
def ref_image(filename):
    return send_from_directory(BRAND_DIR / "images" / "references", filename)


@app.route("/output-image/<path:filename>")
def output_image(filename):
    return send_from_directory(BRAND_DIR / "images" / "outputs", filename)


if __name__ == "__main__":
    # Check API key
    if not os.environ.get("GOOGLE_GENAI_API_KEY"):
        print("Warning: GOOGLE_GENAI_API_KEY not set. Set it before generating.")
        print("  export GOOGLE_GENAI_API_KEY='your-key'")

    port = int(os.environ.get("PORT", 5050))
    print(f"\n  Caico Cotton Image Pipeline")
    print(f"  Open: http://localhost:{port}")
    print(f"  Brand dir: {BRAND_DIR}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
