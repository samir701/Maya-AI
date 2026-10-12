/**
 * ZETTA UI - Memory Explorer View
 * Semantic and persistent memory browser across Short-Term, Long-Term, and Episodic stores.
 */

import { api } from '../api.js';

export async function renderMemory(container) {
  container.innerHTML = `
    <div class="view-header" style="display: flex; justify-content: space-between; align-items: flex-end;">
      <div>
        <div class="view-title">Memory Explorer</div>
        <div class="view-subtitle">Inspect episodic records, long-term facts, preferences, and semantic vector associations</div>
      </div>
      <button class="btn btn-primary btn-sm" id="btn-show-add-memory">+ Store Memory</button>
    </div>

    <!-- Search & Filter Bar -->
    <div class="glass-card" style="margin-bottom: 20px; padding: 14px 20px;">
      <div style="display: flex; gap: 12px; align-items: center;">
        <input type="text" class="form-input" id="memory-search-input" placeholder="Search memories semantically (e.g. 'coding preferences', 'recent tasks')..." />
        <button class="btn btn-secondary" id="btn-memory-search">Search</button>
        <select class="form-input" id="memory-type-filter" style="width: 180px;">
          <option value="">All Memory Types</option>
          <option value="LONG_TERM">Long-Term</option>
          <option value="SHORT_TERM">Short-Term</option>
          <option value="EPISODIC">Episodic</option>
        </select>
      </div>
    </div>

    <!-- Add Memory Box (Collapsible) -->
    <div id="add-memory-box" class="glass-card" style="display: none; margin-bottom: 20px; border-left: 3px solid #06b6d4;">
      <div class="card-title">
        <span>Store New Memory</span>
      </div>
      <form id="add-memory-form" style="display: flex; flex-direction: column; gap: 10px; margin-top: 10px;">
        <textarea class="form-input" id="new-memory-content" rows="3" placeholder="Enter memory knowledge or preference to persist..." required></textarea>
        <div style="display: flex; gap: 10px;">
          <select class="form-input" id="new-memory-type">
            <option value="LONG_TERM">LONG_TERM (Persistent)</option>
            <option value="SHORT_TERM">SHORT_TERM (Session)</option>
            <option value="EPISODIC">EPISODIC (Task Outcome)</option>
          </select>
          <input type="text" class="form-input" id="new-memory-tags" placeholder="Tags comma-separated (e.g. preferences, python)" />
          <button type="submit" class="btn btn-primary" style="white-space: nowrap;">Store</button>
          <button type="button" class="btn btn-secondary" id="btn-cancel-add-memory">Cancel</button>
        </div>
      </form>
    </div>

    <!-- Memories Grid / List -->
    <div class="glass-card">
      <div class="card-title">
        <span>Stored Knowledge & Episodes</span>
        <span class="brand-badge" id="memory-count-badge">0 items</span>
      </div>
      <div id="memories-container" style="display: flex; flex-direction: column; gap: 10px; margin-top: 14px;">
        <div style="color: var(--text-muted); font-size: 12px;">Loading memories...</div>
      </div>
    </div>
  `;

  const searchInput = container.querySelector('#memory-search-input');
  const searchBtn = container.querySelector('#btn-memory-search');
  const typeFilter = container.querySelector('#memory-type-filter');
  const addBox = container.querySelector('#add-memory-box');
  const showAddBtn = container.querySelector('#btn-show-add-memory');
  const cancelAddBtn = container.querySelector('#btn-cancel-add-memory');
  const addForm = container.querySelector('#add-memory-form');
  const listContainer = container.querySelector('#memories-container');
  const countBadge = container.querySelector('#memory-count-badge');

  showAddBtn.addEventListener('click', () => { addBox.style.display = 'block'; });
  cancelAddBtn.addEventListener('click', () => { addBox.style.display = 'none'; });

  async function loadMemories() {
    try {
      const type = typeFilter.value || null;
      const res = await api.listMemories(type);
      const items = res.memories || [];
      countBadge.textContent = `${items.length} items`;

      if (items.length === 0) {
        listContainer.innerHTML = `<div style="color: var(--text-muted); font-size: 13px; padding: 20px 0; text-align: center;">No memories found. Store a memory above or instruct ZETTA in Chat.</div>`;
        return;
      }

      listContainer.innerHTML = items.map((m) => {
        const typeColor = m.memory_type === 'LONG_TERM' ? '#06b6d4' : m.memory_type === 'EPISODIC' ? '#a855f7' : '#eab308';
        return `
          <div style="padding: 12px 14px; background: var(--bg-surface-elevated); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); display: flex; flex-direction: column; gap: 6px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
              <span style="font-size: 11px; font-weight: 700; color: ${typeColor};">${m.memory_type}</span>
              <button class="btn btn-secondary btn-sm btn-delete-mem" data-id="${m.id}" style="padding: 2px 6px; font-size: 10px; color: #f87171;">Delete</button>
            </div>
            <div style="font-size: 13px; color: #fff; line-height: 1.5;">${escapeHtml(m.content)}</div>
            <div style="display: flex; justify-content: space-between; font-size: 10px; color: var(--text-muted); margin-top: 4px;">
              <span>Tags: ${(m.tags || []).join(', ') || 'none'}</span>
              <span>Source: ${m.source || 'user'} • Importance: ${m.importance || 0.5}</span>
            </div>
          </div>
        `;
      }).join('');

      listContainer.querySelectorAll('.btn-delete-mem').forEach((btn) => {
        btn.addEventListener('click', async () => {
          const id = btn.getAttribute('data-id');
          if (confirm('Delete this memory?')) {
            try {
              await api.deleteMemory(id);
              loadMemories();
            } catch (e) {
              alert(`Delete failed: ${e.message}`);
            }
          }
        });
      });
    } catch (err) {
      listContainer.innerHTML = `<div style="color: #ef4444; font-size: 12px;">Failed to load memories: ${err.message}</div>`;
    }
  }

  searchBtn.addEventListener('click', async () => {
    const q = searchInput.value.trim();
    if (!q) return loadMemories();

    try {
      const res = await api.searchMemories(q);
      const results = res.results || [];
      countBadge.textContent = `${results.length} matches`;

      if (results.length === 0) {
        listContainer.innerHTML = `<div style="color: var(--text-muted); font-size: 13px; padding: 20px 0; text-align: center;">No matches found for "${q}".</div>`;
        return;
      }

      listContainer.innerHTML = results.map((r) => `
        <div style="padding: 12px 14px; background: var(--bg-surface-elevated); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); display: flex; flex-direction: column; gap: 6px;">
          <div style="display: flex; justify-content: space-between;">
            <span style="font-size: 11px; font-weight: 700; color: #06b6d4;">${r.memory.memory_type}</span>
            <span style="font-size: 11px; font-weight: 600; color: #4ade80;">Score: ${(r.score * 100).toFixed(1)}%</span>
          </div>
          <div style="font-size: 13px; color: #fff;">${escapeHtml(r.memory.content)}</div>
        </div>
      `).join('');
    } catch (err) {
      alert(`Search failed: ${err.message}`);
    }
  });

  addForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const content = container.querySelector('#new-memory-content').value.trim();
    const memType = container.querySelector('#new-memory-type').value;
    const rawTags = container.querySelector('#new-memory-tags').value.trim();
    const tags = rawTags ? rawTags.split(',').map(s => s.trim()).filter(Boolean) : [];

    if (!content) return;
    try {
      await api.addMemory(content, memType, tags);
      addBox.style.display = 'none';
      addForm.reset();
      loadMemories();
    } catch (err) {
      alert(`Failed to store: ${err.message}`);
    }
  });

  typeFilter.addEventListener('change', loadMemories);
  loadMemories();
}

function escapeHtml(str) {
  return str.replace(/[&<>'"]/g, 
    tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
  );
}
