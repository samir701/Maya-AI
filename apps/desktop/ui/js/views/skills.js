/**
 * ZETTA UI - Skills & Plugins Catalog View
 */

import { api } from '../api.js';

export async function renderSkills(container) {
  container.innerHTML = `
    <div class="view-header" style="display: flex; justify-content: space-between; align-items: flex-end;">
      <div>
        <div class="view-title">Skills & Plugins Catalog</div>
        <div class="view-subtitle">Reusable workflow capabilities and modular plugin extensions</div>
      </div>
      <button class="btn btn-secondary btn-sm" id="btn-refresh-skills">Refresh Catalog</button>
    </div>

    <!-- Plugins Section -->
    <div style="margin-bottom: 30px;">
      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 14px;">
        <h3 style="font-size: 15px; font-weight: 700; color: #fff;">Installed Plugins</h3>
        <span class="brand-badge" id="plugins-count-badge">0 plugins</span>
      </div>
      <div class="card-grid" id="plugins-grid">
        <div style="color: var(--text-muted); font-size: 12px;">Loading plugins...</div>
      </div>
    </div>

    <!-- Skills Section -->
    <div>
      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 14px;">
        <h3 style="font-size: 15px; font-weight: 700; color: #fff;">Registered Skills</h3>
        <span class="brand-badge" id="skills-count-badge">0 skills</span>
      </div>
      <div class="card-grid" id="skills-grid">
        <div style="color: var(--text-muted); font-size: 12px;">Loading skills...</div>
      </div>
    </div>
  `;

  const pluginsGrid = container.querySelector('#plugins-grid');
  const skillsGrid = container.querySelector('#skills-grid');
  const pluginsBadge = container.querySelector('#plugins-count-badge');
  const skillsBadge = container.querySelector('#skills-count-badge');
  const refreshBtn = container.querySelector('#btn-refresh-skills');

  async function loadData() {
    try {
      const [skillsData, pluginsData] = await Promise.all([
        api.getSkills(),
        api.getPlugins(),
      ]);

      const skills = skillsData.skills || [];
      const plugins = pluginsData.plugins || [];

      pluginsBadge.textContent = `${plugins.length} plugins`;
      skillsBadge.textContent = `${skills.length} skills`;

      if (plugins.length === 0) {
        pluginsGrid.innerHTML = `<div style="color: var(--text-muted); font-size: 13px;">No third-party plugins installed in current environment.</div>`;
      } else {
        pluginsGrid.innerHTML = plugins.map((p) => {
          const isEnabled = p.status === 'ENABLED';
          return `
            <div class="glass-card">
              <div class="card-title">
                <span style="font-size: 15px; font-weight: 700; color: #fff;">${p.name}</span>
                <span class="brand-badge" style="background: ${isEnabled ? 'rgba(34,197,94,0.15)' : 'rgba(255,255,255,0.06)'}; color: ${isEnabled ? '#4ade80' : 'var(--text-muted)'};">${p.status}</span>
              </div>
              <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px; line-height: 1.5;">
                ${p.description || 'Extension bundle adding tools, agents, and skills.'}
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-subtle); padding-top: 10px; font-size: 11px;">
                <span style="color: var(--text-muted);">v${p.version || '1.0.0'} • By ${p.author || 'ZETTA'}</span>
                <button class="btn btn-secondary btn-sm btn-toggle-plugin" data-name="${p.name}" data-enabled="${isEnabled}">
                  ${isEnabled ? 'Disable' : 'Enable'}
                </button>
              </div>
            </div>
          `;
        }).join('');
      }

      if (skills.length === 0) {
        skillsGrid.innerHTML = `<div style="color: var(--text-muted); font-size: 13px;">No reusable skills registered.</div>`;
      } else {
        skillsGrid.innerHTML = skills.map((s) => `
          <div class="glass-card">
            <div class="card-title">
              <span style="font-size: 15px; font-weight: 700; color: #fff;">${s.name}</span>
              <span class="brand-badge" style="background: rgba(59,130,246,0.15); color: #60a5fa;">v${s.version || '1.0.0'}</span>
            </div>
            <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px; line-height: 1.5;">
              ${s.description || 'Specialized workflow skill.'}
            </div>
            <div style="border-top: 1px solid var(--border-subtle); padding-top: 8px; font-size: 11px; color: var(--text-muted);">
              <div>Inputs: <strong style="color: var(--text-primary);">${(s.inputs || []).join(', ') || 'none'}</strong></div>
              <div style="margin-top: 2px;">Outputs: <strong style="color: var(--text-primary);">${(s.outputs || []).join(', ') || 'none'}</strong></div>
            </div>
          </div>
        `).join('');
      }

      // Attach plugin toggle
      pluginsGrid.querySelectorAll('.btn-toggle-plugin').forEach((btn) => {
        btn.addEventListener('click', async () => {
          const name = btn.getAttribute('data-name');
          const current = btn.getAttribute('data-enabled') === 'true';
          try {
            await api.togglePlugin(name, !current);
            loadData();
          } catch (e) {
            alert(`Toggle failed: ${e.message}`);
          }
        });
      });
    } catch (err) {
      pluginsGrid.innerHTML = `<div style="color: #ef4444; font-size: 12px;">Failed to load catalog: ${err.message}</div>`;
    }
  }

  refreshBtn.addEventListener('click', loadData);
  loadData();
}
