/**
 * ZETTA UI - Autonomous Tasks & Workflow Planner
 */

import { api } from '../api.js';

export async function renderTasks(container) {
  container.innerHTML = `
    <div class="view-header" style="display: flex; justify-content: space-between; align-items: flex-end;">
      <div>
        <div class="view-title">Autonomous Workspace & Tasks</div>
        <div class="view-subtitle">Monitor, plan, and orchestrate multi-step autonomous workflows and DAG plans</div>
      </div>
      <button class="btn btn-secondary btn-sm" id="btn-refresh-tasks">Refresh</button>
    </div>

    <!-- Workflow Goal Planner Card -->
    <div class="glass-card" style="margin-bottom: 24px; border-left: 3px solid #3b82f6;">
      <div class="card-title">
        <span>Autonomous Workflow Planner</span>
        <span class="brand-badge">Autonomous Execution DAG</span>
      </div>
      <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px;">
        State a high-level goal. ZETTA Autonomous Planner will decompose it into a structured subtask graph.
      </div>
      <form id="workflow-form" style="display: flex; gap: 10px;">
        <input type="text" class="form-input" id="workflow-goal-input" placeholder="e.g. Research latest Python 3.12 features and write summary document..." required />
        <button type="submit" class="btn btn-primary" id="btn-plan-workflow">Decompose & Plan</button>
      </form>

      <div id="plan-output" style="margin-top: 14px; display: none;">
        <div style="font-weight: 600; font-size: 13px; color: #60a5fa; margin-bottom: 8px;">Generated Execution Graph (DAG):</div>
        <div id="plan-steps-container" style="display: flex; flex-direction: column; gap: 6px;"></div>
      </div>
    </div>

    <!-- Tasks Board -->
    <div class="glass-card">
      <div class="card-title">
        <span>System Task Registry</span>
        <span class="brand-badge" id="tasks-total-count">0 tasks</span>
      </div>
      <div id="tasks-table-container" style="margin-top: 14px;">
        <div style="color: var(--text-muted); font-size: 12px;">Loading tasks...</div>
      </div>
    </div>
  `;

  const refreshBtn = container.querySelector('#btn-refresh-tasks');
  const workflowForm = container.querySelector('#workflow-form');
  const goalInput = container.querySelector('#workflow-goal-input');
  const planOutput = container.querySelector('#plan-output');
  const planSteps = container.querySelector('#plan-steps-container');
  const tableContainer = container.querySelector('#tasks-table-container');
  const countBadge = container.querySelector('#tasks-total-count');

  async function loadTasks() {
    try {
      const res = await api.getTasks();
      const tasks = res.tasks || [];
      countBadge.textContent = `${tasks.length} tasks`;

      if (tasks.length === 0) {
        tableContainer.innerHTML = `<div style="color: var(--text-muted); font-size: 13px; padding: 20px 0; text-align: center;">No tasks registered in this session. Use the planner above to generate a workflow.</div>`;
        return;
      }

      tableContainer.innerHTML = `
        <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
          <thead>
            <tr style="border-bottom: 1px solid var(--border-subtle); color: var(--text-muted); text-align: left;">
              <th style="padding: 8px 10px;">ID</th>
              <th style="padding: 8px 10px;">Task Name</th>
              <th style="padding: 8px 10px;">Status</th>
              <th style="padding: 8px 10px;">Created</th>
              <th style="padding: 8px 10px; text-align: right;">Action</th>
            </tr>
          </thead>
          <tbody>
            ${tasks.map((t) => {
              const statusColor = t.status === 'COMPLETED' ? '#22c55e' : t.status === 'RUNNING' ? '#3b82f6' : t.status === 'CANCELLED' ? '#9aa5b8' : '#eab308';
              return `
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                  <td style="padding: 10px; font-family: var(--font-mono); font-size: 11px; color: var(--text-muted);">${(t.id || '').slice(0, 8)}...</td>
                  <td style="padding: 10px; font-weight: 600; color: #fff;">${t.name}</td>
                  <td style="padding: 10px;"><span style="color: ${statusColor}; font-weight: 600; font-size: 11px;">${t.status}</span></td>
                  <td style="padding: 10px; font-size: 11px; color: var(--text-muted);">${(t.created_at || '').slice(11, 19)}</td>
                  <td style="padding: 10px; text-align: right;">
                    ${t.status === 'RUNNING' || t.status === 'PENDING' ? `<button class="btn btn-danger btn-sm btn-cancel-task" data-id="${t.id}">Cancel</button>` : `<span style="color: var(--text-muted); font-size: 11px;">—</span>`}
                  </td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      `;

      // Attach cancel listeners
      tableContainer.querySelectorAll('.btn-cancel-task').forEach((btn) => {
        btn.addEventListener('click', async () => {
          const id = btn.getAttribute('data-id');
          try {
            await api.cancelTask(id);
            loadTasks();
          } catch (e) {
            alert(`Failed to cancel: ${e.message}`);
          }
        });
      });
    } catch (err) {
      tableContainer.innerHTML = `<div style="color: #ef4444; font-size: 12px;">Failed to load tasks: ${err.message}</div>`;
    }
  }

  workflowForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const goal = goalInput.value.trim();
    if (!goal) return;

    const planBtn = container.querySelector('#btn-plan-workflow');
    planBtn.disabled = true;
    planBtn.textContent = 'Planning...';

    try {
      const res = await api.planWorkflow(goal);
      planOutput.style.display = 'block';
      const steps = res.plan?.steps || [];
      planSteps.innerHTML = steps.map((s, idx) => `
        <div style="display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: var(--bg-surface-elevated); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); font-size: 12px;">
          <span style="width: 22px; height: 22px; border-radius: 50%; background: rgba(59,130,246,0.2); color: #60a5fa; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 11px;">${idx + 1}</span>
          <span style="font-weight: 600; color: #fff; flex: 1;">${s.name}</span>
          <span style="color: #60a5fa; font-size: 11px;">${s.assigned_agent || 'AutoAgent'}</span>
        </div>
      `).join('');
      loadTasks();
    } catch (err) {
      alert(`Planning failed: ${err.message}`);
    } finally {
      planBtn.disabled = false;
      planBtn.textContent = 'Decompose & Plan';
    }
  });

  refreshBtn.addEventListener('click', loadTasks);
  loadTasks();
}
