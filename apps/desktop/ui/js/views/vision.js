/**
 * ZETTA UI - Vision & OCR Center View
 * Multimodal screen observation, OCR, and element detection.
 */

import { api } from '../api.js';

export async function renderVision(container) {
  container.innerHTML = `
    <div class="view-header" style="display: flex; justify-content: space-between; align-items: flex-end;">
      <div>
        <div class="view-title">Vision & OCR Workspace</div>
        <div class="view-subtitle">Multimodal screen analysis, text recognition, and UI element detection</div>
      </div>
      <div style="display: flex; gap: 8px;">
        <button class="btn btn-secondary btn-sm" id="btn-run-ocr">Run OCR</button>
        <button class="btn btn-secondary btn-sm" id="btn-detect-ui">Detect UI Elements</button>
        <button class="btn btn-primary btn-sm" id="btn-capture-vision">Capture Screen</button>
      </div>
    </div>

    <!-- Main Workspace Layout -->
    <div style="display: grid; grid-template-columns: 3fr 2fr; gap: 20px;">
      <!-- Left: Screen Image Canvas/Preview -->
      <div class="glass-card" style="display: flex; flex-direction: column;">
        <div class="card-title">
          <span>Screen Snapshot</span>
          <span class="brand-badge" id="vision-meta-badge">Ready</span>
        </div>
        <div class="screen-preview-container" id="vision-preview-container">
          <div id="vision-placeholder" style="color: var(--text-muted); font-size: 13px; text-align: center;">
            Click <strong>Capture Screen</strong> to analyze desktop
          </div>
          <img id="vision-img" class="screen-preview-img" style="display: none;" alt="Vision Snapshot" />
        </div>
      </div>

      <!-- Right: OCR and Detection Findings -->
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <!-- OCR Results -->
        <div class="glass-card">
          <div class="card-title">
            <span>OCR Extracted Text</span>
            <span class="brand-badge" id="ocr-badge">Idle</span>
          </div>
          <div id="ocr-text-output" style="max-height: 200px; overflow-y: auto; font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary); white-space: pre-wrap; background: var(--bg-surface-elevated); padding: 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
            Run OCR to extract visible text from the captured screen.
          </div>
        </div>

        <!-- UI Elements Detected -->
        <div class="glass-card" style="flex: 1;">
          <div class="card-title">
            <span>Detected UI Elements</span>
            <span class="brand-badge" id="elements-count-badge">0 items</span>
          </div>
          <div id="ui-elements-list" style="max-height: 240px; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; margin-top: 8px;">
            <div style="color: var(--text-muted); font-size: 12px;">Run UI Detection to locate interactive controls.</div>
          </div>
        </div>
      </div>
    </div>
  `;

  const captureBtn = container.querySelector('#btn-capture-vision');
  const ocrBtn = container.querySelector('#btn-run-ocr');
  const detectBtn = container.querySelector('#btn-detect-ui');
  const visionImg = container.querySelector('#vision-img');
  const placeholder = container.querySelector('#vision-placeholder');
  const metaBadge = container.querySelector('#vision-meta-badge');
  const ocrBadge = container.querySelector('#ocr-badge');
  const ocrOutput = container.querySelector('#ocr-text-output');
  const elBadge = container.querySelector('#elements-count-badge');
  const elementsList = container.querySelector('#ui-elements-list');

  captureBtn.addEventListener('click', async () => {
    captureBtn.disabled = true;
    captureBtn.textContent = 'Capturing...';
    try {
      const res = await api.captureScreen();
      if (res.capture?.image_data_url) {
        visionImg.src = res.capture.image_data_url;
        visionImg.style.display = 'block';
        placeholder.style.display = 'none';
        metaBadge.textContent = `${res.capture.width}x${res.capture.height}`;
      }
    } catch (e) {
      alert(`Capture failed: ${e.message}`);
    } finally {
      captureBtn.disabled = false;
      captureBtn.textContent = 'Capture Screen';
    }
  });

  ocrBtn.addEventListener('click', async () => {
    ocrBtn.disabled = true;
    ocrBtn.textContent = 'Processing OCR...';
    try {
      const res = await api.runOcr();
      ocrBadge.textContent = `Confidence: ${(res.confidence * 100).toFixed(0)}%`;
      ocrOutput.textContent = res.text || '(No text detected)';
    } catch (e) {
      ocrOutput.textContent = `OCR failed: ${e.message}`;
    } finally {
      ocrBtn.disabled = false;
      ocrBtn.textContent = 'Run OCR';
    }
  });

  detectBtn.addEventListener('click', async () => {
    detectBtn.disabled = true;
    detectBtn.textContent = 'Detecting UI...';
    try {
      const res = await api.detectUi();
      const elements = res.elements || [];
      elBadge.textContent = `${elements.length} elements`;
      elementsList.innerHTML = elements.map((el, i) => `
        <div style="padding: 6px 10px; background: var(--bg-surface-elevated); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); font-size: 11px; display: flex; justify-content: space-between;">
          <span style="font-weight: 600; color: #60a5fa;">#${i + 1} ${el.element_type || 'Control'}</span>
          <span style="color: var(--text-muted); font-family: var(--font-mono);">${el.text || el.label || 'interactive'}</span>
        </div>
      `).join('');
    } catch (e) {
      elementsList.innerHTML = `<div style="color: #ef4444; font-size: 12px;">Detection failed: ${e.message}</div>`;
    } finally {
      detectBtn.disabled = false;
      detectBtn.textContent = 'Detect UI Elements';
    }
  });
}
