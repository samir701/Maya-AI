/**
 * ZETTA UI - Command Center View
 * Provides intelligent, real-time overview of the AI Employee.
 */

import { api } from '../api.js';
import { store } from '../state.js';

export async function renderHome(container) {
  let status = store.get().systemStatus;
  try {
    const liveStatus = await api.getSystemStatus();
    store.set({ systemStatus: liveStatus });
    status = liveStatus;
  } catch (err) {
    console.warn('Using cached status for Home view:', err);
  }

  const activeTask = status.active_task;
  const activeTaskHtml = activeTask
    ? `
      <div style="margin-top: 12px; padding: 14px; background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.2); border-radius: var(--radius-sm);">
        <div style="font-weight: 600; color: #60a5fa; font-size: 14px;">${activeTask.name || 'Autonomous Task'}</div>
        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">Status: <span style="color: #22c55e;">${activeTask.status}</span></div>
        <div style="margin-top: 8px; background: rgba(255, 255, 255, 0.06); height: 6px; border-radius: 3px; overflow: hidden;">
          <div style="background: #3b82f6; height: 100%; width: 70%; animation: pulse-dot 2s infinite ease-in-out;"></div>
        </div>
      </div>
    `
    : `
      <div style="margin-top: 12px; font-size: 13px; color: var(--text-muted);">
        No autonomous tasks running. ZETTA is idle and awaiting your command.
      </div>
    `;

  container.innerHTML = `
    <div class="view-header">
      <div class="view-title">Command Center</div>
      <div class="view-subtitle">Live operating overview and telemetry for ZETTA AI Employee</div>
    </div>

    <div class="card-grid">
      <!-- Status Card -->
      <div class="glass-card">
        <div class="card-title">
          <span>Employee Status</span>
          <span class="status-dot pulsing"></span>
        </div>
        <div class="metric-value" style="color: #22c55e;">${status.state || 'ONLINE'}</div>
        <div class="metric-label">Operational on Ubuntu Linux (Env: ${status.environment || 'production'})</div>
      </div>

      <!-- Active Agent -->
      <div class="glass-card">
        <div class="card-title">
          <span>Primary Active Agent</span>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
        </div>
        <div class="metric-value" style="font-size: 20px;">${status.active_agent || 'GeneralAssistantAgent'}</div>
        <div class="metric-label">${status.registered_agents_count || 6} base worker agents registered</div>
      </div>

      <!-- Active Persona -->
      <div class="glass-card">
        <div class="card-title">
          <span>Operating Persona</span>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#a855f7" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
        </div>
        <div class="metric-value" style="font-size: 20px;">${status.active_persona || 'ZETTA Default'}</div>
        <div class="metric-label">Profile: ${status.persona_type || 'default'}</div>
      </div>

      <!-- Memory Context -->
      <div class="glass-card">
        <div class="card-title">
          <span>Memory Footprint</span>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#06b6d4" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
        </div>
        <div class="metric-value">${status.memory_count !== undefined ? status.memory_count : 'Ready'}</div>
        <div class="metric-label">Persistent SQLite + Semantic Vector Memory</div>
      </div>
    </div>

    <!-- Active Task & Direct Control Section -->
    <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 24px;">
      <div class="glass-card">
        <div class="card-title">
          <span>Current Task Execution</span>
          <span class="brand-badge">${status.active_tasks_count || 0} active</span>
        </div>
        ${activeTaskHtml}
      </div>

      <div class="glass-card">
        <div class="card-title">
          <span>Quick Actions</span>
        </div>
        <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 12px;">
          <button class="btn btn-secondary btn-sm" id="btn-quick-new-chat" style="justify-content: flex-start;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            Direct Message ZETTA
          </button>
          <button class="btn btn-secondary btn-sm" id="btn-quick-take-snap" style="justify-content: flex-start;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
            Capture Screen Snapshot
          </button>
          <button class="btn btn-secondary btn-sm" id="btn-quick-browse" style="justify-content: flex-start;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/></svg>
            Inspect Browser State
          </button>
        </div>
      </div>
    </div>

    <!-- Subsystem Health Diagnostic -->
    <div class="glass-card">
      <div class="card-title">
        <span>Subsystem Operational Telemetry</span>
        <button class="btn btn-secondary btn-sm" id="btn-refresh-health">Refresh Diagnostics</button>
      </div>
      <div id="home-health-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; margin-top: 14px;">
        <div style="font-size: 12px; color: var(--text-muted);">Loading health telemetry...</div>
      </div>
    </div>
  `;

  // Attach quick action listeners
  container.querySelector('#btn-quick-new-chat')?.addEventListener('click', () => {
    store.setActiveView('chat');
  });

  container.querySelector('#btn-quick-take-snap')?.addEventListener('click', async () => {
    try {
      await api.captureScreen();
      store.setActiveView('vision');
    } catch (e) {
      alert(`Capture failed: ${e.message}`);
    }
  });

  container.querySelector('#btn-quick-browse')?.addEventListener('click', () => {
    store.setActiveView('browser');
  });

  const refreshHealthBtn = container.querySelector('#btn-refresh-health');
  refreshHealthBtn?.addEventListener('click', () => loadHealthTelemetry(container));

  loadHealthTelemetry(container);
}

async function loadHealthTelemetry(container) {
  const grid = container.querySelector('#home-health-grid');
  if (!grid) return;

  try {
    const health = await api.getHealth();
    const checks = health.checks || {};
    grid.innerHTML = Object.entries(checks)
      .map(([name, val]) => {
        const isOk = val.status === 'OK';
        const color = isOk ? '#22c55e' : '#ef4444';
        return `
          <div style="padding: 10px 12px; background: var(--bg-surface-elevated); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <span style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 700;">${name.replace(/_/g, ' ')}</span>
              <span style="font-size: 10px; font-weight: 700; color: ${color};">${val.status}</span>
            </div>
            <div style="font-size: 11px; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
              ${val.provider || val.version || val.environment || 'Operational'}
            </div>
          </div>
        `;
      })
      .join('');
  } catch (err) {
    grid.innerHTML = `<div style="color: #ef4444; font-size: 12px;">Failed to load health telemetry: ${err.message}</div>`;
  }
}
