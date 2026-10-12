/**
 * ZETTA UI - Agent Center View
 * Distinguishes Registered Fleet from Specialized / Composite Agents.
 */

import { api } from '../api.js';

export async function renderAgents(container) {
  container.innerHTML = `
    <div class="view-header" style="display: flex; justify-content: space-between; align-items: flex-end;">
      <div>
        <div class="view-title">Agent Center</div>
        <div class="view-subtitle">Architecture overview of base worker fleet and specialized autonomous agents</div>
      </div>
      <button class="btn btn-secondary btn-sm" id="btn-refresh-agents">Refresh Fleet</button>
    </div>

    <!-- Section 1: Base Worker Fleet -->
    <div style="margin-bottom: 30px;">
      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 14px;">
        <h3 style="font-size: 15px; font-weight: 700; color: #fff;">Registered Worker Fleet</h3>
        <span class="brand-badge" style="background: rgba(34, 197, 94, 0.15); color: #4ade80; border-color: rgba(34, 197, 94, 0.3);">Permanent Core</span>
      </div>
      <div class="card-grid" id="fleet-agents-grid">
        <div style="color: var(--text-muted); font-size: 12px;">Loading fleet agents...</div>
      </div>
    </div>

    <!-- Section 2: Specialized / Composite Capabilities -->
    <div>
      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 14px;">
        <h3 style="font-size: 15px; font-weight: 700; color: #fff;">Specialized / Composite Agents</h3>
        <span class="brand-badge" style="background: rgba(168, 85, 247, 0.15); color: #c084fc; border-color: rgba(168, 85, 247, 0.3);">On-Demand Execution</span>
      </div>
      <div class="card-grid" id="specialized-agents-grid">
        <div style="color: var(--text-muted); font-size: 12px;">Loading specialized agents...</div>
      </div>
    </div>
  `;

  const fleetGrid = container.querySelector('#fleet-agents-grid');
  const specGrid = container.querySelector('#specialized-agents-grid');
  const refreshBtn = container.querySelector('#btn-refresh-agents');

  async function loadData() {
    try {
      const data = await api.getAgents();
      const fleet = data.fleet || data.registered_fleet || [];
      const specialized = data.specialized || data.specialized_agents || [];

      fleetGrid.innerHTML = fleet.map((a) => `
        <div class="glass-card">
          <div class="card-title">
            <span style="font-size: 15px; font-weight: 700; color: #fff;">${a.name}</span>
            <span class="status-dot"></span>
          </div>
          <div style="font-size: 12px; color: #60a5fa; margin-bottom: 6px; font-weight: 600;">
            ${(a.capabilities || []).join(', ').toUpperCase() || 'CORE FLEET'}
          </div>
          <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px; line-height: 1.5;">
            ${a.description || 'Active worker agent ready for autonomous execution.'}
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-subtle); padding-top: 10px; font-size: 11px;">
            <span style="color: var(--text-muted);">Permission: <strong style="color: var(--text-primary);">${a.required_permission || 'LOW'}</strong></span>
            <span class="brand-badge" style="background: rgba(34, 197, 94, 0.1); color: #4ade80;">Active</span>
          </div>
        </div>
      `).join('');

      specGrid.innerHTML = specialized.map((s) => `
        <div class="glass-card" style="border-left: 3px solid #a855f7;">
          <div class="card-title">
            <span style="font-size: 15px; font-weight: 700; color: #fff;">${s.name}</span>
            <span class="brand-badge" style="background: rgba(168, 85, 247, 0.2); color: #c084fc;">On-Demand</span>
          </div>
          <div style="font-size: 12px; color: #c084fc; margin-bottom: 6px; font-weight: 600;">
            ${s.type}
          </div>
          <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px; line-height: 1.5;">
            ${s.description}
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-subtle); padding-top: 10px; font-size: 11px;">
            <span style="color: var(--text-muted);">Required: <strong style="color: #f87171;">${s.required_permission}</strong></span>
            <span style="color: var(--text-muted);">Capabilities: <strong>${(s.capabilities || []).length}</strong></span>
          </div>
        </div>
      `).join('');
    } catch (err) {
      fleetGrid.innerHTML = `<div style="color: #ef4444; font-size: 12px;">Failed to load agents: ${err.message}</div>`;
    }
  }

  refreshBtn.addEventListener('click', loadData);
  loadData();
}
