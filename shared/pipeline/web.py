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

        .regen-btn { background: #a0522d; color: white; border: none; padding: 10px 20px; border-radius: 6px; font-size: 14px; cursor: pointer; margin-top: 12px; margin-left: 8px; }
        .regen-btn:hover { background: #7d3f22; }
        .regen-btn:disabled { background: #ccc; cursor: not-allowed; }

        .flag-btn { background: #f5f1ea; color: #7a5a14; border: 1px solid #e0d5bd; padding: 4px 9px; border-radius: 4px; font-size: 11px; cursor: pointer; margin-right: 6px; }
        .flag-btn:hover { background: #ede4d0; }
        .flag-btn.flagged { background: #c24f3e; color: white; border-color: #a03a2c; }
        .flag-btn.flagged:hover { background: #a03a2c; }

        .output-card.is-fixed { border: 2px solid #2a7d4a; }
        .fixed-badge { background: #2a7d4a; color: white; font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 3px; letter-spacing: 0.4px; }

        .flag-panel { padding: 12px; background: #fbf7ef; border-top: 1px solid #ecdfbf; display: none; }
        .flag-panel.open { display: block; }
        .flag-panel h4 { font-size: 12px; color: #7a5a14; margin-bottom: 8px; font-weight: 600; }
        .flag-panel label { display: block; font-size: 12px; margin: 4px 0; color: #444; cursor: pointer; }
        .flag-panel label input { margin-right: 6px; vertical-align: middle; }
        .flag-panel textarea { width: 100%; margin-top: 8px; padding: 6px; font-size: 12px; border: 1px solid #ddd; border-radius: 4px; font-family: inherit; resize: vertical; min-height: 48px; }
        .flag-panel .actions { margin-top: 8px; display: flex; gap: 6px; }
        .flag-panel .save-btn { background: #8b6914; color: white; border: none; padding: 5px 12px; border-radius: 4px; font-size: 11px; cursor: pointer; }
        .flag-panel .clear-btn { background: #eee; color: #555; border: none; padding: 5px 12px; border-radius: 4px; font-size: 11px; cursor: pointer; }

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
                    <label>Child age (matches stock size)</label><br>
                    <select id="child-age">
                        <option value="">Auto (full product range)</option>
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
            <button class="regen-btn" id="regen-btn" onclick="regenerateFlagged()" style="display:none;">Regenerate flagged (<span id="flag-count">0</span>)</button>
            <div class="output-grid" id="output-grid"></div>
        </div>
    </div>

    <script>
        let products = [];
        let families = {};
        let references = [];
        let selectedFamily = null;
        let selectedProducts = new Set();

        const ISSUE_OPTIONS = [
            {code: 'wrong-colour', label: 'Wrong colour'},
            {code: 'design-altered', label: 'Design / details altered'},
            {code: 'label-visible', label: 'Label or logo visible on front'},
            {code: 'wrong-wrap', label: 'Wrap / overlap direction reversed'},
            {code: 'extra-pattern', label: 'Extra pattern or print added'},
            {code: 'face-too-similar', label: 'Face too similar to reference'},
            {code: 'wrong-age', label: 'Wrong age / size of child'},
            {code: 'scene-off-reference', label: 'Scene too far from reference'},
        ];

        function escapeHtml(s) {
            return String(s || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
        }

        function buildOutputCard(img) {
            const flag = img.flag || null;
            const flagged = !!flag;
            const card = document.createElement('div');
            card.className = 'output-card' + (img.is_fixed ? ' is-fixed' : '');
            card.dataset.rel = img.rel;

            const label = img.is_fixed
                ? '<span class="fixed-badge">CORRECTED</span> ' + escapeHtml(img.product) + ' · ' + escapeHtml(img.reference)
                : escapeHtml(img.product) + ' · ' + escapeHtml(img.reference);

            let checkboxesHtml = '';
            ISSUE_OPTIONS.forEach(opt => {
                const checked = flag && flag.issues && flag.issues.includes(opt.code) ? 'checked' : '';
                checkboxesHtml += '<label><input type="checkbox" value="' + opt.code + '" ' + checked + '>' + opt.label + '</label>';
            });

            const noteVal = flag && flag.note ? escapeHtml(flag.note) : '';

            card.innerHTML =
                '<img src="/output-image/' + img.path + '">' +
                '<div class="info"><span class="label">' + label + '</span>' +
                '<div>' +
                    '<button class="flag-btn ' + (flagged ? 'flagged' : '') + '" onclick="toggleFlagPanel(this)">' + (flagged ? 'Flagged' : 'Flag issue') + '</button>' +
                    '<a class="dl-btn" href="/output-image/' + img.path + '" download="' + img.product + '_' + img.reference + '.png">Download</a>' +
                '</div></div>' +
                '<div class="flag-panel">' +
                    '<h4>What needs fixing?</h4>' +
                    checkboxesHtml +
                    '<textarea placeholder="Optional note (e.g. sleeves should be shorter, logo should be embossed not printed)">' + noteVal + '</textarea>' +
                    '<div class="actions">' +
                        '<button class="save-btn" onclick="saveFlag(this)">Save flag</button>' +
                        '<button class="clear-btn" onclick="clearFlag(this)">Clear</button>' +
                    '</div>' +
                '</div>';
            return card;
        }

        function toggleFlagPanel(btn) {
            const card = btn.closest('.output-card');
            const panel = card.querySelector('.flag-panel');
            panel.classList.toggle('open');
        }

        async function saveFlag(btn) {
            const card = btn.closest('.output-card');
            const panel = card.querySelector('.flag-panel');
            const issues = Array.from(panel.querySelectorAll('input[type=checkbox]:checked')).map(c => c.value);
            const note = panel.querySelector('textarea').value.trim();

            const resp = await fetch('/api/flag', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({rel: card.dataset.rel, issues, note}),
            });
            const data = await resp.json();
            if (data.success) {
                const flagBtn = card.querySelector('.flag-btn');
                if (data.flag) {
                    flagBtn.classList.add('flagged');
                    flagBtn.textContent = 'Flagged';
                } else {
                    flagBtn.classList.remove('flagged');
                    flagBtn.textContent = 'Flag issue';
                }
                panel.classList.remove('open');
                refreshFlagCount();
            }
        }

        async function clearFlag(btn) {
            const card = btn.closest('.output-card');
            const panel = card.querySelector('.flag-panel');
            panel.querySelectorAll('input[type=checkbox]').forEach(c => c.checked = false);
            panel.querySelector('textarea').value = '';
            await fetch('/api/flag', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({rel: card.dataset.rel, issues: [], note: ''}),
            });
            const flagBtn = card.querySelector('.flag-btn');
            flagBtn.classList.remove('flagged');
            flagBtn.textContent = 'Flag issue';
            panel.classList.remove('open');
            refreshFlagCount();
        }

        async function refreshFlagCount() {
            const resp = await fetch('/api/flags');
            const data = await resp.json();
            const count = Object.keys(data.flags || {}).length;
            const btn = document.getElementById('regen-btn');
            document.getElementById('flag-count').textContent = count;
            btn.style.display = count > 0 ? 'inline-block' : 'none';
        }

        async function regenerateFlagged() {
            const btn = document.getElementById('regen-btn');
            btn.disabled = true;
            btn.textContent = 'Regenerating...';

            const log = document.getElementById('log');
            const progress = document.getElementById('progress');
            const progressBar = document.getElementById('progress-bar');
            log.style.display = 'block';
            progress.style.display = 'block';
            log.textContent = '';

            const body = {
                aspect: document.getElementById('aspect').value,
                model: document.getElementById('model').value,
                child_age: document.getElementById('child-age').value,
            };

            const resp = await fetch('/api/regenerate-flagged', {
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
                            if (msg.image_path) {
                                const card = buildOutputCard({
                                    path: msg.image_path, product: msg.product, reference: msg.reference,
                                    rel: msg.image_path.split('/').slice(1).join('/'),
                                    is_fixed: true, flag: null,
                                });
                                // Place the corrected image directly after its original for easy comparison
                                const originalCard = document.querySelector('[data-rel="' + msg.original_rel + '"]');
                                if (originalCard && originalCard.parentNode) {
                                    originalCard.insertAdjacentElement('afterend', card);
                                    const fb = originalCard.querySelector('.flag-btn');
                                    fb.classList.remove('flagged');
                                    fb.textContent = 'Flag issue';
                                } else {
                                    document.getElementById('output-grid').prepend(card);
                                }
                            }
                        } else if (msg.type === 'complete') {
                            log.textContent += '\\n' + msg.message + '\\n';
                        } else if (msg.type === 'error') {
                            log.textContent += '\\n' + msg.message + '\\n';
                        }
                    } catch(e) {}
                }
            }

            btn.disabled = false;
            refreshFlagCount();
            loadCost();
        }

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
            renderAgeOptions();
            updateEstimate();
        }

        // Size ordering used to sort the age dropdown (matches SIZE_TO_MONTHS in models.py)
        const SIZE_ORDER = ["NB", "NB-3M", "0-3M", "1-3M", "3-6M", "6-9M", "9-12M", "6-12M", "12-18M", "12-18", "18-24M", "2-3Y", "3-4Y", "4-5Y", "5-6Y", "6-7Y"];

        function renderAgeOptions() {
            const select = document.getElementById('child-age');
            const prevValue = select.value;

            // Gather age ranges from selected products (union)
            const available = new Set();
            products.forEach(p => {
                if (selectedProducts.has(p.id) && p.age_ranges) {
                    p.age_ranges.forEach(a => available.add(a));
                }
            });

            // Sort by canonical size order
            const sorted = Array.from(available).sort((a, b) => {
                const ai = SIZE_ORDER.indexOf(a);
                const bi = SIZE_ORDER.indexOf(b);
                return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
            });

            // Rebuild options
            select.innerHTML = '<option value="">Auto (full product range)</option>';
            sorted.forEach(size => {
                const opt = document.createElement('option');
                opt.value = size;
                opt.textContent = size;
                select.appendChild(opt);
            });

            // Preserve prior selection if still valid
            if (sorted.includes(prevValue)) select.value = prevValue;
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
                    renderAgeOptions();
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
                                const card = buildOutputCard({
                                    path: msg.image_path, product: msg.product, reference: msg.reference,
                                    rel: msg.image_path.split('/').slice(1).join('/'),
                                    is_fixed: false, flag: null,
                                });
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
                grid.appendChild(buildOutputCard(img));
            });
            refreshFlagCount();
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
             "category": p.category, "image": p.image, "age_ranges": p.age_ranges}
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


def _latest_batch_dir():
    """Return the most recent batch directory (by name / date), or None."""
    outputs_dir = BRAND_DIR / "images" / "outputs"
    if not outputs_dir.exists():
        return None
    batches = sorted([d for d in outputs_dir.iterdir() if d.is_dir()], reverse=True)
    return batches[0] if batches else None


def _load_flags(batch_dir):
    """Load flags.json for a batch dir; returns {} if missing."""
    flags_path = batch_dir / "flags.json"
    if not flags_path.exists():
        return {}
    try:
        with open(flags_path) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_flags(batch_dir, flags):
    """Persist flags dict to batch_dir/flags.json."""
    batch_dir.mkdir(parents=True, exist_ok=True)
    with open(batch_dir / "flags.json", "w") as f:
        json.dump(flags, f, indent=2)


@app.route("/api/outputs")
def api_outputs():
    images = []
    batch = _latest_batch_dir()

    if batch:
        flags = _load_flags(batch)
        for product_dir in sorted(batch.iterdir()):
            if not product_dir.is_dir():
                continue
            for img in sorted(product_dir.glob("*.png")):
                rel = f"{product_dir.name}/{img.name}"
                is_fixed = "_fixed" in img.stem
                images.append({
                    "path": f"{batch.name}/{rel}",
                    "product": product_dir.name,
                    "reference": img.stem,
                    "rel": rel,
                    "is_fixed": is_fixed,
                    "flag": flags.get(rel),
                })

    return jsonify({"images": images})


@app.route("/api/flag", methods=["POST"])
def api_flag():
    """Save or update a flag for an output image."""
    batch = _latest_batch_dir()
    if not batch:
        return jsonify({"success": False, "error": "No batch found"}), 404

    data = request.json or {}
    rel = data.get("rel", "").strip()
    issues = data.get("issues", [])
    note = data.get("note", "").strip()

    if not rel:
        return jsonify({"success": False, "error": "Missing image path"}), 400

    flags = _load_flags(batch)

    if not issues and not note:
        # Empty flag = unflag
        flags.pop(rel, None)
    else:
        flags[rel] = {
            "issues": issues,
            "note": note,
            "flagged_at": datetime.now().isoformat(),
        }

    _save_flags(batch, flags)
    return jsonify({"success": True, "flag": flags.get(rel)})


@app.route("/api/flags")
def api_flags():
    batch = _latest_batch_dir()
    if not batch:
        return jsonify({"flags": {}})
    return jsonify({"flags": _load_flags(batch)})


# Map of issue codes → corrective instructions appended to the regen prompt
ISSUE_CORRECTIONS = {
    "wrong-colour": "The previous attempt has the WRONG colour. Match the flatlay's colour exactly — do not shift, tint, or alter the hue.",
    "design-altered": "The previous attempt altered the garment's design or construction. Reproduce the flatlay EXACTLY — same seams, same panels, same cut, same details.",
    "label-visible": "The previous attempt shows a label, tag, or logo on the FRONT of the garment. All labels must be hidden on the back neckline and not visible.",
    "wrong-wrap": "The previous attempt has the wrap/crossover direction reversed. The overlap direction MUST match the flatlay exactly — do not mirror or flip it.",
    "extra-pattern": "The previous attempt added a pattern or print that is not on the flatlay. The garment must be plain/solid unless the flatlay clearly shows a print.",
    "face-too-similar": "The previous attempt's child looks too similar to the reference photo. Generate a COMPLETELY DIFFERENT child — different features, different hair, different skin tone.",
    "wrong-age": "The previous attempt shows a child of the wrong age. Match the age specified in the prompt precisely — look at proportions, head-to-body ratio, and facial maturity.",
    "scene-off-reference": "The previous attempt drifted too far from the reference scene. The setting, background, props, colour palette, and mood must match the reference photo closely.",
}


def _build_corrections_block(flag: dict) -> str:
    """Assemble a corrections instruction block from issue codes + freeform note."""
    lines = ["CORRECTIONS TO APPLY (the previous attempt failed for these specific reasons — fix every one):"]
    for code in flag.get("issues", []) or []:
        text = ISSUE_CORRECTIONS.get(code)
        if text:
            lines.append(f"- {text}")
    note = (flag.get("note") or "").strip()
    if note:
        lines.append(f"- Additional correction: {note}")
    return "\n".join(lines) + "\n"


def _next_fixed_path(batch_dir, product_id: str, reference_id: str, variant: int):
    """Pick a `_fixed.png` filename that doesn't already exist, returning (abs_path, rel_path)."""
    product_dir = batch_dir / product_id
    product_dir.mkdir(parents=True, exist_ok=True)
    base = f"{reference_id}_v{variant}_fixed"
    candidate = product_dir / f"{base}.png"
    i = 2
    while candidate.exists():
        candidate = product_dir / f"{base}{i}.png"
        i += 1
    rel = f"{product_id}/{candidate.name}"
    return candidate, rel


@app.route("/api/regenerate-flagged", methods=["POST"])
def api_regenerate_flagged():
    """Regenerate all flagged images with their corrections, saving new files alongside."""
    from config import PipelineConfig
    from prompts import get_template_for_product, render_prompt
    from api_client import GeminiImageClient
    from models import GenerationJob, SIZE_TO_DESCRIPTION

    batch = _latest_batch_dir()
    if not batch:
        return jsonify({"error": "No batch found"}), 404

    flags = _load_flags(batch)
    if not flags:
        return jsonify({"error": "No flags to regenerate"}), 400

    MODEL_MAP = {"pro": "gemini-3-pro-image-preview", "flash": "gemini-3.1-flash-image-preview"}
    data = request.json or {}
    aspect = data.get("aspect", "") or None
    model_name = MODEL_MAP.get(data.get("model", "pro"), "gemini-3-pro-image-preview")
    child_age = data.get("child_age", "")
    child_age_description = SIZE_TO_DESCRIPTION.get(child_age, "")

    def generate_stream():
        try:
            config = PipelineConfig(BRAND_DIR)
            config.model = model_name

            products_by_id = {p.id: p for p in config.load_products()}
            refs_by_id = {r.id: r for r in config.load_references()}

            api_key = config.api_key or os.environ.get("GOOGLE_GENAI_API_KEY", "")
            if not api_key:
                yield json.dumps({"type": "error", "message": "API key not set."}) + "\n"
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

            items = list(flags.items())
            total = len(items)
            yield json.dumps({"type": "progress", "completed": 0, "total": total, "message": f"Regenerating {total} flagged images..."}) + "\n"

            for i, (rel_path, flag) in enumerate(items):
                # rel_path is like "muslin-dress/upload-001_v1.png"
                try:
                    product_id, filename = rel_path.split("/", 1)
                except ValueError:
                    yield json.dumps({"type": "progress", "completed": i+1, "total": total, "message": f"✗ skipped {rel_path} (bad path)"}) + "\n"
                    continue

                # Parse reference_id and variant from filename
                stem = Path(filename).stem
                # Strip any _fixed[N] suffix to get back to the original ref/variant
                base_stem = stem.split("_fixed")[0]
                if "_v" not in base_stem:
                    yield json.dumps({"type": "progress", "completed": i+1, "total": total, "message": f"✗ skipped {rel_path} (no variant)"}) + "\n"
                    continue
                reference_id, _, variant_str = base_stem.rpartition("_v")
                try:
                    variant = int(variant_str)
                except ValueError:
                    variant = 1

                product = products_by_id.get(product_id)
                reference = refs_by_id.get(reference_id)
                if not product or not reference:
                    yield json.dumps({"type": "progress", "completed": i+1, "total": total, "message": f"✗ {rel_path} — product or reference no longer exists"}) + "\n"
                    continue

                previous_image = batch / product_id / filename
                if not previous_image.exists():
                    yield json.dumps({"type": "progress", "completed": i+1, "total": total, "message": f"✗ {rel_path} — previous image missing"}) + "\n"
                    continue

                template = get_template_for_product(config.templates_dir, product)
                prompt, sys_instr = render_prompt(
                    template=template, product=product, reference=reference,
                    brand_name=config.brand_name, brand_tagline=config.brand_tagline,
                    style_keywords_formatted=config.style_keywords_formatted,
                    child_age_override=child_age_description if child_age_description else None,
                )

                corrections = _build_corrections_block(flag)

                product_image = config.products_dir / product.image
                reference_image = config.references_dir / reference.image

                image_bytes = client.generate(
                    product_image_path=product_image,
                    reference_image_path=reference_image,
                    prompt=prompt,
                    system_instruction=sys_instr,
                    previous_image_path=previous_image,
                    corrections_block=corrections,
                )

                if image_bytes:
                    out_path, out_rel = _next_fixed_path(batch, product_id, reference_id, variant)
                    with open(out_path, "wb") as f:
                        f.write(image_bytes)

                    # Clear the flag now that it's been addressed
                    flags.pop(rel_path, None)
                    _save_flags(batch, flags)

                    yield json.dumps({
                        "type": "progress", "completed": i+1, "total": total,
                        "message": f"✓ fixed {product_id} × {reference_id}",
                        "image_path": f"{batch.name}/{out_rel}",
                        "product": product_id,
                        "reference": reference_id,
                        "original_rel": rel_path,
                    }) + "\n"
                else:
                    yield json.dumps({"type": "progress", "completed": i+1, "total": total, "message": f"✗ {rel_path} — regen failed"}) + "\n"

            yield json.dumps({"type": "complete", "message": "Regeneration complete"}) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "message": f"Error: {str(e)}"}) + "\n"

    return app.response_class(
        generate_stream(),
        mimetype="text/plain",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


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
            "child_age_months": "0-72",
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

    from models import SIZE_TO_DESCRIPTION

    data = request.json
    family = data.get("family")
    product_ids = data.get("product_ids", [])
    aspect = data.get("aspect", "") or None
    variants = data.get("variants", 1)
    model_name = MODEL_MAP.get(data.get("model", "pro"), "gemini-3-pro-image-preview")
    child_age = data.get("child_age", "")
    # child_age is now a stock size like "3-4Y" — look up the prompt description
    child_age_description = SIZE_TO_DESCRIPTION.get(child_age, "")

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
