/**
 * ZETTA AI EMPLOYEE — Core Frontend Application Controller
 * Orchestrates navigation, WebSocket event stream, global modals, and view lifecycle.
 */

import { api } from './api.js';
import { wsClient } from './ws.js';
import { store } from './state.js';

// Import Modular Views
import { renderHome } from './views/home.js';
import { renderChat } from './views/chat.js';
import { renderAgents } from './views/agents.js';
import { renderTasks } from './views/tasks.js';
import { renderComputer } from './views/computer.js';
import { renderBrowser } from './views/browser.js';
import { renderVision } from './views/vision.js';
import { renderVoice } from './views/voice.js';
import { renderMemory } from './views/memory.js';
import { renderSkills } from './views/skills.js';
import { renderDocuments } from './views/documents.js';
import { renderSettings } from './views/settings.js';

const viewRenderers = {
  home: renderHome,
  chat: renderChat,
  agents: renderAgents,
  tasks: renderTasks,
  computer: renderComputer,
  browser: renderBrowser,
  vision: renderVision,
  voice: renderVoice,
  memory: renderMemory,
  skills: renderSkills,
  documents: renderDocuments,
  settings: renderSettings,
};

let activeConfirmation = null;
let currentActiveView = null;

// Initialize Application
async function initApp() {
  console.log('[ZETTA] Initializing desktop console...');

  // Setup Navigation listeners
  setupNavigation();

  // Setup Activity Drawer toggle
  setupDrawer();

  // Setup Confirmation Modal actions
  setupConfirmationModal();

  // Connect WebSocket Event Stream
  setupWebSocket();

  // Periodic status poll (every 15s)
  updateStatusTelemetry();
  setInterval(updateStatusTelemetry, 15000);

  // Check pending confirmations immediately
  checkPendingConfirmations();

  // Load initial view
  switchView('home', true);
}

function setupNavigation() {
  const navItems = document.querySelectorAll('#sidebar-nav .nav-item');
  navItems.forEach((item) => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const view = item.getAttribute('data-view');
      if (view) {
        store.setActiveView(view);
      }
    });
  });

  // Subscribe specifically to explicit view transitions (decoupled from general events)
  store.subscribeView((newView) => {
    switchView(newView);
  });
}

function switchView(viewName, force = false) {
  if (!force && currentActiveView === viewName) {
    return;
  }
  currentActiveView = viewName;

  const navItems = document.querySelectorAll('#sidebar-nav .nav-item');
  navItems.forEach((item) => {
    if (item.getAttribute('data-view') === viewName) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });

  const views = document.querySelectorAll('.workspace-view');
  views.forEach((v) => v.classList.remove('active'));

  const targetContainer = document.getElementById(`view-${viewName}`);
  if (targetContainer) {
    targetContainer.classList.add('active');
    const renderer = viewRenderers[viewName];
    if (renderer) {
      renderer(targetContainer);
    }
  }
}

function setupDrawer() {
  const toggleBtn = document.getElementById('btn-toggle-drawer');
  const drawer = document.getElementById('context-drawer');
  const clearBtn = document.getElementById('btn-quick-clear-events');
  const snapBtn = document.getElementById('btn-quick-screenshot');

  toggleBtn?.addEventListener('click', () => {
    drawer.style.display = drawer.style.display === 'none' ? 'flex' : 'none';
  });

  clearBtn?.addEventListener('click', () => {
    const list = document.getElementById('activity-list');
    if (list) {
      list.innerHTML = `<div style="color: var(--text-muted); font-size: 12px; text-align: center; margin-top: 30px;">Activity history cleared.</div>`;
    }
    const counter = document.getElementById('event-counter');
    if (counter) counter.textContent = '0 events';
  });

  snapBtn?.addEventListener('click', async () => {
    try {
      await api.captureScreen();
      store.setActiveView('vision');
    } catch (e) {
      alert(`Snap failed: ${e.message}`);
    }
  });
}

function setupConfirmationModal() {
  const modal = document.getElementById('confirmation-modal');
  const approveBtn = document.getElementById('btn-confirm-approve');
  const cancelBtn = document.getElementById('btn-confirm-cancel');

  approveBtn?.addEventListener('click', async () => {
    if (!activeConfirmation) return;
    try {
      await api.resolveConfirmation(activeConfirmation.id, true, 'User approved from desktop UI modal');
      modal.classList.remove('open');
      activeConfirmation = null;
    } catch (err) {
      alert(`Approval error: ${err.message}`);
    }
  });

  cancelBtn?.addEventListener('click', async () => {
    if (!activeConfirmation) return;
    try {
      await api.resolveConfirmation(activeConfirmation.id, false, 'User rejected from desktop UI modal');
      modal.classList.remove('open');
      activeConfirmation = null;
    } catch (err) {
      alert(`Rejection error: ${err.message}`);
    }
  });
}

function showConfirmationModal(item) {
  activeConfirmation = item;
  const modal = document.getElementById('confirmation-modal');
  const title = document.getElementById('confirm-action-title');
  const desc = document.getElementById('confirm-action-desc');
  const badge = document.getElementById('confirm-permission-badge');

  if (title) title.textContent = `Confirm: ${item.action || 'High-Risk Operation'}`;
  if (desc) desc.textContent = item.description || 'This operation requires your explicit authorization.';
  if (badge) badge.textContent = item.required_permission || 'HIGH';

  modal?.classList.add('open');
}

async function checkPendingConfirmations() {
  try {
    const res = await api.getConfirmations();
    const pending = res.pending || [];
    if (pending.length > 0 && !activeConfirmation) {
      showConfirmationModal(pending[0]);
    }
  } catch (err) {
    // Backend may not have any
  }
}

function setupWebSocket() {
  wsClient.connect();

  wsClient.subscribeAll((event) => {
    store.addActivityEvent(event);
    renderActivityEvent(event);

    // If confirmation event, open modal immediately
    if (event.event_type === 'CONFIRMATION_REQUESTED' || event.event_type === 'USER_CONFIRMATION_REQUIRED') {
      const payload = event.payload || {};
      showConfirmationModal({
        id: payload.confirmation_id || 'manual-confirm',
        action: payload.action || 'High Risk Action',
        description: payload.description || 'Approval required',
        required_permission: payload.required_permission || 'HIGH',
      });
    }
  });
}

function renderActivityEvent(event) {
  const list = document.getElementById('activity-list');
  const counter = document.getElementById('event-counter');
  if (!list) return;

  const card = document.createElement('div');
  card.className = 'activity-event-card';
  const timeStr = new Date().toTimeString().slice(0, 8);
  const typeStr = event.event_type || 'EVENT';

  card.innerHTML = `
    <span class="event-time">${timeStr}</span>
    <div class="event-type">${typeStr}</div>
    <div class="event-details">${formatPayload(event.payload)}</div>
  `;

  list.insertBefore(card, list.firstChild);
  if (counter) {
    const count = list.querySelectorAll('.activity-event-card').length;
    counter.textContent = `${count} events`;
  }
}

function formatPayload(payload) {
  if (!payload || typeof payload !== 'object') return '';
  const parts = [];
  for (const [k, v] of Object.entries(payload)) {
    if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') {
      parts.push(`${k}: ${v}`);
    }
  }
  return parts.slice(0, 3).join(' • ') || JSON.stringify(payload);
}

async function updateStatusTelemetry() {
  try {
    const st = await api.getSystemStatus();
    store.set({ systemStatus: st });

    const statusText = document.getElementById('status-text');
    const personaLabel = document.getElementById('active-persona-label');
    if (statusText) statusText.textContent = `ZETTA ${st.state || 'ONLINE'}`;
    if (personaLabel) personaLabel.textContent = st.active_persona || 'Default';
  } catch (err) {
    const statusText = document.getElementById('status-text');
    if (statusText) statusText.textContent = 'ZETTA Offline';
  }
}

// Start application when DOM is ready
document.addEventListener('DOMContentLoaded', initApp);
