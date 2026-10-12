/**
 * ZETTA UI - Computer Control & Accessibility View
 * Visual command center for desktop control and 25 accessibility actions.
 */

import { api } from '../api.js';

export async function renderComputer(container) {
  container.innerHTML = `
    <div class="view-header" style="display: flex; justify-content: space-between; align-items: flex-end;">
      <div>
        <div class="view-title">Computer Control & Accessibility</div>
        <div class="view-subtitle">Live screen observation and assistive desktop automation controls</div>
      </div>
      <button class="btn btn-primary btn-sm" id="btn-snap-screen">Capture Live Screen</button>
    </div>

    <!-- Status Cards -->
    <div class="card-grid" style="margin-bottom: 20px;">
      <div class="glass-card">
        <div class="card-title">
          <span>Active Window</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
        </div>
        <div class="metric-value" style="font-size: 18px;" id="active-win-val">Desktop Session</div>
        <div class="metric-label" id="displays-info-val">Resolving displays...</div>
      </div>

      <div class="glass-card">
        <div class="card-title">
          <span>Accessibility Framework</span>
          <span class="brand-badge" style="background: rgba(34, 197, 94, 0.15); color: #4ade80;">25 Actions</span>
        </div>
        <div class="metric-value" style="font-size: 18px; color: #22c55e;">Ready</div>
        <div class="metric-label">Linux UI automation & assistive navigation</div>
      </div>
    </div>

    <!-- Live Screen Observation & Controls -->
    <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 24px;">
      <!-- Screen Preview Box -->
      <div class="glass-card" style="display: flex; flex-direction: column;">
        <div class="card-title">
          <span>Live Screen Observation</span>
          <span id="screen-meta-badge" class="brand-badge">No Capture</span>
        </div>
        <div class="screen-preview-container" id="screen-container">
          <div id="screen-placeholder" style="color: var(--text-muted); font-size: 13px; text-align: center;">
            Click <strong>Capture Live Screen</strong> to observe current desktop
          </div>
          <img id="screen-img" class="screen-preview-img" style="display: none;" alt="Desktop Snapshot" />
        </div>
      </div>

      <!-- Action Panel -->
      <div class="glass-card">
        <div class="card-title">
          <span>Direct Assistive Action</span>
        </div>
        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">
          Dispatch one of the 25 composable accessibility capabilities to control active UI elements.
        </div>

        <div style="display: flex; flex-direction: column; gap: 10px;">
          <div>
            <label style="font-size: 11px; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Select Action</label>
            <select class="form-input" id="comp-action-select" style="margin-top: 4px;">
              <option value="inspect_active_ui">inspect_active_ui (Observe active elements)</option>
              <option value="click_element">click_element (Click focused target)</option>
              <option value="double_click">double_click (Double click)</option>
              <option value="right_click">right_click (Right click)</option>
              <option value="type_text">type_text (Type input string)</option>
              <option value="press_key">press_key (Press specific key)</option>
              <option value="hotkey">hotkey (Trigger key combination)</option>
              <option value="scroll_down">scroll_down (Scroll active page)</option>
              <option value="scroll_up">scroll_up (Scroll page up)</option>
              <option value="copy_selection">copy_selection (Copy selected text)</option>
              <option value="paste_clipboard">paste_clipboard (Paste clipboard)</option>
              <option value="switch_window">switch_window (Focus target window)</option>
            </select>
          </div>

          <div id="param-input-container">
            <label style="font-size: 11px; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Parameter / Target</label>
            <input type="text" class="form-input" id="comp-param-input" placeholder="e.g. text to type or key name" style="margin-top: 4px;" />
          </div>

          <button class="btn btn-primary" id="btn-exec-comp-action" style="margin-top: 8px;">Execute Assistive Action</button>

          <div id="comp-action-result" style="display: none; padding: 10px; border-radius: var(--radius-sm); font-size: 11px; font-family: var(--font-mono); background: var(--bg-surface-elevated); margin-top: 10px; word-break: break-word;"></div>
        </div>
      </div>
    </div>
  `;

  const snapBtn = container.querySelector('#btn-snap-screen');
  const screenImg = container.querySelector('#screen-img');
  const screenPlaceholder = container.querySelector('#screen-placeholder');
  const screenBadge = container.querySelector('#screen-meta-badge');
  const activeWinVal = container.querySelector('#active-win-val');
  const displaysInfoVal = container.querySelector('#displays-info-val');
  const actionSelect = container.querySelector('#comp-action-select');
  const paramInput = container.querySelector('#comp-param-input');
  const execBtn = container.querySelector('#btn-exec-comp-action');
  const resultBox = container.querySelector('#comp-action-result');

  // Load status
  try {
    const status = await api.getComputerStatus();
    activeWinVal.textContent = status.active_window || 'Desktop Workspace';
    const dispCount = (status.displays || []).length;
    displaysInfoVal.textContent = `${dispCount} display(s) detected • Resolution: 1920x1080`;
  } catch (err) {
    console.warn('Could not load computer status:', err);
  }

  async function takeSnapshot() {
    snapBtn.disabled = true;
    snapBtn.textContent = 'Capturing...';
    try {
      const res = await api.getScreenshot();
      if (res.image_base64) {
        screenImg.src = res.image_base64;
        screenImg.style.display = 'block';
        screenPlaceholder.style.display = 'none';
        screenBadge.textContent = `${res.width}x${res.height} (${Math.round(res.duration_ms || 0)}ms)`;
      }
    } catch (e) {
      alert(`Capture failed: ${e.message}`);
    } finally {
      snapBtn.disabled = false;
      snapBtn.textContent = 'Capture Live Screen';
    }
  }

  snapBtn.addEventListener('click', takeSnapshot);

  execBtn.addEventListener('click', async () => {
    const action = actionSelect.value;
    const paramVal = paramInput.value.trim();
    const params = {};
    if (action === 'type_text') params.text = paramVal || 'Hello from ZETTA';
    else if (action === 'press_key' || action === 'hotkey') params.key = paramVal || 'Return';
    else if (paramVal) params.target = paramVal;

    execBtn.disabled = true;
    execBtn.textContent = 'Executing...';
    try {
      const res = await api.executeComputerAction(action, params);
      resultBox.style.display = 'block';
      resultBox.style.color = res.success ? '#22c55e' : '#ef4444';
      resultBox.textContent = `Action '${action}' executed: ${JSON.stringify(res.data || res.error)}`;
    } catch (err) {
      resultBox.style.display = 'block';
      resultBox.style.color = '#ef4444';
      resultBox.textContent = `Execution failed: ${err.message}`;
    } finally {
      execBtn.disabled = false;
      execBtn.textContent = 'Execute Assistive Action';
    }
  });
}
