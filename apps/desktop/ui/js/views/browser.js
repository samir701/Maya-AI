/**
 * ZETTA UI - Browser Center View
 * Web automation and navigation workspace powered by BrowserManager.
 */

import { api } from '../api.js';

export async function renderBrowser(container) {
  container.innerHTML = `
    <div class="view-header" style="display: flex; justify-content: space-between; align-items: flex-end;">
      <div>
        <div class="view-title">Browser Center</div>
        <div class="view-subtitle">Autonomous web navigation, DOM element interaction, and session management</div>
      </div>
      <div style="display: flex; gap: 8px;">
        <button class="btn btn-secondary btn-sm" id="btn-refresh-browser">Refresh Status</button>
        <button class="btn btn-primary btn-sm" id="btn-launch-browser">Launch Browser Session</button>
      </div>
    </div>

    <!-- Browser Telemetry Card -->
    <div class="card-grid" style="margin-bottom: 20px;">
      <div class="glass-card">
        <div class="card-title">
          <span>Browser Session Status</span>
          <span class="status-dot" id="browser-status-dot"></span>
        </div>
        <div class="metric-value" style="font-size: 20px;" id="browser-state-val">Checking...</div>
        <div class="metric-label" id="browser-provider-val">Playwright / BrowserManager</div>
      </div>

      <div class="glass-card">
        <div class="card-title">
          <span>Installed Engine</span>
          <span class="brand-badge">Linux Ready</span>
        </div>
        <div class="metric-value" style="font-size: 20px;" id="browser-engine-val">Google Chrome / Chromium</div>
        <div class="metric-label">Headless & Visual Automation Supported</div>
      </div>
    </div>

    <!-- Navigation & Interaction Controls -->
    <div class="glass-card" style="margin-bottom: 20px;">
      <div class="card-title">
        <span>Address Bar & Navigation</span>
      </div>
      <form id="browser-nav-form" style="display: flex; gap: 10px; margin-top: 10px;">
        <input type="url" class="form-input" id="browser-url-input" placeholder="Enter target URL (e.g. https://news.ycombinator.com)..." required />
        <button type="submit" class="btn btn-primary" id="btn-navigate">Navigate</button>
      </form>
    </div>

    <!-- Interactive Web Element Actions -->
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
      <!-- Click Element -->
      <div class="glass-card">
        <div class="card-title">
          <span>Click Selector / Element</span>
        </div>
        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 10px;">
          Click a button, link, or element using CSS selector or text description.
        </div>
        <div style="display: flex; gap: 8px;">
          <input type="text" class="form-input" id="browser-click-target" placeholder="e.g. button#submit or text='Login'" />
          <button class="btn btn-secondary" id="btn-browser-click">Click</button>
        </div>
      </div>

      <!-- Type into Element -->
      <div class="glass-card">
        <div class="card-title">
          <span>Type into Input</span>
        </div>
        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 10px;">
          Type text or search query into target form field.
        </div>
        <div style="display: flex; flex-direction: column; gap: 8px;">
          <input type="text" class="form-input" id="browser-type-target" placeholder="Selector: e.g. input[name='q']" />
          <div style="display: flex; gap: 8px;">
            <input type="text" class="form-input" id="browser-type-text" placeholder="Text to type..." />
            <button class="btn btn-secondary" id="btn-browser-type">Type</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Interaction Log -->
    <div id="browser-action-output" style="margin-top: 20px; display: none;" class="glass-card">
      <div class="card-title">
        <span>Operation Result</span>
      </div>
      <div id="browser-log-content" style="font-family: var(--font-mono); font-size: 12px; color: #4ade80;"></div>
    </div>
  `;

  const statusDot = container.querySelector('#browser-status-dot');
  const stateVal = container.querySelector('#browser-state-val');
  const providerVal = container.querySelector('#browser-provider-val');
  const refreshBtn = container.querySelector('#btn-refresh-browser');
  const launchBtn = container.querySelector('#btn-launch-browser');
  const navForm = container.querySelector('#browser-nav-form');
  const urlInput = container.querySelector('#browser-url-input');
  const outputCard = container.querySelector('#browser-action-output');
  const logContent = container.querySelector('#browser-log-content');

  async function updateStatus() {
    try {
      const st = await api.getBrowserStatus();
      const isOpen = st.is_open || false;
      stateVal.textContent = isOpen ? 'Active Session' : 'Ready (Idle)';
      stateVal.style.color = isOpen ? '#22c55e' : '#60a5fa';
      providerVal.textContent = `Provider: ${st.provider || 'BrowserManager'} • Available: ${st.is_available}`;
      statusDot.style.background = isOpen ? '#22c55e' : '#3b82f6';
    } catch (err) {
      stateVal.textContent = 'Degraded';
      stateVal.style.color = '#ef4444';
      providerVal.textContent = err.message;
    }
  }

  launchBtn.addEventListener('click', async () => {
    launchBtn.disabled = true;
    launchBtn.textContent = 'Launching...';
    try {
      const res = await api.launchBrowser(true);
      outputCard.style.display = 'block';
      logContent.textContent = `Browser launched successfully. Session ID: ${res.session_id}`;
      updateStatus();
    } catch (e) {
      alert(`Launch failed: ${e.message}`);
    } finally {
      launchBtn.disabled = false;
      launchBtn.textContent = 'Launch Browser Session';
    }
  });

  navForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const url = urlInput.value.trim();
    if (!url) return;

    outputCard.style.display = 'block';
    logContent.textContent = `Navigating to ${url}...`;
    try {
      const res = await api.browserNavigate(url);
      logContent.textContent = `Navigation successful: ${res.status || 'OK'}. URL: ${url}`;
      updateStatus();
    } catch (err) {
      logContent.style.color = '#ef4444';
      logContent.textContent = `Navigation failed: ${err.message}`;
    }
  });

  container.querySelector('#btn-browser-click').addEventListener('click', async () => {
    const target = container.querySelector('#browser-click-target').value.trim();
    if (!target) return alert('Enter target selector or element text');

    try {
      const res = await api.browserClick(target);
      outputCard.style.display = 'block';
      logContent.style.color = '#4ade80';
      logContent.textContent = `Clicked element '${target}': ${res.status || 'Success'}`;
    } catch (e) {
      outputCard.style.display = 'block';
      logContent.style.color = '#ef4444';
      logContent.textContent = `Click failed: ${e.message}`;
    }
  });

  container.querySelector('#btn-browser-type').addEventListener('click', async () => {
    const target = container.querySelector('#browser-type-target').value.trim();
    const text = container.querySelector('#browser-type-text').value.trim();
    if (!target || !text) return alert('Enter both selector and text');

    try {
      const res = await api.browserType(target, text);
      outputCard.style.display = 'block';
      logContent.style.color = '#4ade80';
      logContent.textContent = `Typed '${text}' into '${target}': ${res.status || 'Success'}`;
    } catch (e) {
      outputCard.style.display = 'block';
      logContent.style.color = '#ef4444';
      logContent.textContent = `Typing failed: ${e.message}`;
    }
  });

  refreshBtn.addEventListener('click', updateStatus);
  updateStatus();
}
