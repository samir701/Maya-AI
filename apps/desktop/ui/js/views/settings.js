/**
 * ZETTA UI - Settings & Persona Configuration View
 */

import { api } from '../api.js';

export async function renderSettings(container) {
  container.innerHTML = `
    <div class="view-header" style="display: flex; justify-content: space-between; align-items: flex-end;">
      <div>
        <div class="view-title">System Settings & Personas</div>
        <div class="view-subtitle">Runtime parameters, behavioral personas, security policies, and subsystem configurations</div>
      </div>
      <button class="btn btn-secondary btn-sm" id="btn-refresh-settings">Reload</button>
    </div>

    <!-- Persona Switcher -->
    <div class="glass-card" style="margin-bottom: 24px; border-left: 3px solid #a855f7;">
      <div class="card-title">
        <span>Operating Persona Configuration</span>
        <span class="brand-badge" id="active-persona-badge">Loading...</span>
      </div>
      <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 14px;">
        Switch ZETTA's tone, formality, verbosity, and proactiveness profile.
      </div>
      <div id="personas-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px;">
        <div style="color: var(--text-muted); font-size: 12px;">Loading personas...</div>
      </div>
    </div>

    <!-- Two-Column Settings Grid -->
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
      <!-- AI & LLM Provider -->
      <div class="glass-card">
        <div class="card-title">
          <span>AI Inference & LLM Model</span>
        </div>
        <div style="display: flex; flex-direction: column; gap: 10px; font-size: 12px;" id="ai-settings-list">
          <div style="color: var(--text-muted);">Loading AI config...</div>
        </div>
      </div>

      <!-- Security Policies -->
      <div class="glass-card">
        <div class="card-title">
          <span>Security & Confirmation Policies</span>
        </div>
        <div style="display: flex; flex-direction: column; gap: 10px; font-size: 12px;" id="security-settings-list">
          <div style="color: var(--text-muted);">Loading Security config...</div>
        </div>
      </div>
    </div>
  `;

  const personaBadge = container.querySelector('#active-persona-badge');
  const personasGrid = container.querySelector('#personas-grid');
  const aiList = container.querySelector('#ai-settings-list');
  const secList = container.querySelector('#security-settings-list');
  const refreshBtn = container.querySelector('#btn-refresh-settings');

  async function loadConfig() {
    try {
      const [settings, personasData] = await Promise.all([
        api.getSettings(),
        api.getPersonas(),
      ]);

      const activePersonaType = settings.active_persona?.type || 'default';
      personaBadge.textContent = settings.active_persona?.name || 'Default';

      // Render Personas
      personasGrid.innerHTML = (personasData.personas || []).map((p) => {
        const isActive = p.type === activePersonaType;
        return `
          <div style="padding: 14px; background: var(--bg-surface-elevated); border: 1px solid ${isActive ? '#a855f7' : 'var(--border-subtle)'}; border-radius: var(--radius-sm); display: flex; flex-direction: column; gap: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <strong style="color: #fff; font-size: 14px;">${p.name}</strong>
              ${isActive ? '<span class="brand-badge" style="background: rgba(168,85,247,0.2); color: #c084fc;">Active</span>' : ''}
            </div>
            <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.4;">${p.description}</div>
            <div style="font-size: 11px; color: var(--text-muted);">Style: ${p.communication_style}</div>
            ${!isActive ? `<button class="btn btn-secondary btn-sm btn-switch-persona" data-type="${p.type}" style="margin-top: 4px;">Switch to ${p.name}</button>` : ''}
          </div>
        `;
      }).join('');

      // Render AI settings
      const ai = settings.ai || {};
      aiList.innerHTML = `
        <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--border-subtle);">
          <span style="color: var(--text-muted);">Provider</span>
          <strong style="color: #fff;">${ai.default_provider}</strong>
        </div>
        <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--border-subtle);">
          <span style="color: var(--text-muted);">Default Model</span>
          <strong style="color: #60a5fa;">${ai.default_model}</strong>
        </div>
        <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--border-subtle);">
          <span style="color: var(--text-muted);">Groq API Key</span>
          <span style="font-family: var(--font-mono); color: ${ai.has_groq_key ? '#4ade80' : 'var(--text-muted)'};">${ai.groq_key_masked || 'Not Configured'}</span>
        </div>
        <div style="display: flex; justify-content: space-between; padding: 6px 0;">
          <span style="color: var(--text-muted);">OpenAI API Key</span>
          <span style="font-family: var(--font-mono); color: ${ai.has_openai_key ? '#4ade80' : 'var(--text-muted)'};">${ai.openai_key_masked || 'Not Configured'}</span>
        </div>
      `;

      // Render Security settings
      const sec = settings.security || {};
      secList.innerHTML = `
        <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--border-subtle);">
          <span style="color: var(--text-muted);">Confirmation Threshold</span>
          <span class="brand-badge" style="background: rgba(239,68,68,0.2); color: #f87171;">${sec.confirmation_threshold}</span>
        </div>
        <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--border-subtle);">
          <span style="color: var(--text-muted);">Sandbox Isolation</span>
          <strong style="color: ${sec.sandbox_enabled ? '#4ade80' : '#f87171'};">${sec.sandbox_enabled ? 'Enforced' : 'Disabled'}</strong>
        </div>
        <div style="display: flex; justify-content: space-between; padding: 6px 0;">
          <span style="color: var(--text-muted);">Security Audit Logging</span>
          <strong style="color: #4ade80;">Active (SQLite)</strong>
        </div>
      `;

      // Attach persona switchers
      personasGrid.querySelectorAll('.btn-switch-persona').forEach((btn) => {
        btn.addEventListener('click', async () => {
          const type = btn.getAttribute('data-type');
          try {
            await api.switchPersona(type);
            loadConfig();
          } catch (e) {
            alert(`Failed to switch persona: ${e.message}`);
          }
        });
      });
    } catch (err) {
      console.error('Failed to load settings:', err);
    }
  }

  refreshBtn.addEventListener('click', loadConfig);
  loadConfig();
}
