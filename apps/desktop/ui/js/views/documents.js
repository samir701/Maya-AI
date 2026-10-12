/**
 * ZETTA UI - Documents & Deep Research View
 * Orchestrates ResearchAgent investigations and DocumentAgent report compiling.
 */

import { api } from '../api.js';

export function renderDocuments(container) {
  container.innerHTML = `
    <div class="view-header" style="display: flex; justify-content: space-between; align-items: flex-end;">
      <div>
        <div class="view-title">Research & Document Generation</div>
        <div class="view-subtitle">Execute deep source investigation with ResearchAgent and structured reports with DocumentAgent</div>
      </div>
    </div>

    <!-- Two-Column Workspace -->
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
      <!-- Deep Research Investigation -->
      <div class="glass-card">
        <div class="card-title">
          <span>Deep Research Agent</span>
          <span class="brand-badge" style="background: rgba(59,130,246,0.15); color: #60a5fa;">Multi-Source</span>
        </div>
        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">
          Direct ResearchAgent to investigate topics, synthesize findings, and extract structured evidence.
        </div>
        <form id="research-form" style="display: flex; flex-direction: column; gap: 10px;">
          <input type="text" class="form-input" id="research-query-input" placeholder="Enter research objective (e.g. 'State of Rust in Linux Kernel')..." required />
          <button type="submit" class="btn btn-primary" id="btn-run-research">Start Investigation</button>
        </form>

        <div id="research-output" style="margin-top: 14px; display: none; padding: 12px; background: var(--bg-surface-elevated); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); font-size: 12px; line-height: 1.6; max-height: 350px; overflow-y: auto; white-space: pre-wrap;"></div>
      </div>

      <!-- Document Generation -->
      <div class="glass-card">
        <div class="card-title">
          <span>Document Writer Agent</span>
          <span class="brand-badge" style="background: rgba(168,85,247,0.15); color: #c084fc;">Markdown</span>
        </div>
        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">
          Compile structured Markdown reports, system documentation, and briefings with DocumentAgent.
        </div>
        <form id="doc-form" style="display: flex; flex-direction: column; gap: 10px;">
          <input type="text" class="form-input" id="doc-title-input" placeholder="Document Title..." required />
          <textarea class="form-input" id="doc-instructions-input" rows="3" placeholder="Document requirements and section instructions..." required></textarea>
          <button type="submit" class="btn btn-secondary" id="btn-generate-doc">Compile Document</button>
        </form>

        <div id="doc-output" style="margin-top: 14px; display: none; padding: 12px; background: var(--bg-surface-elevated); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); font-size: 12px; line-height: 1.6; max-height: 350px; overflow-y: auto; white-space: pre-wrap; font-family: var(--font-mono);"></div>
      </div>
    </div>
  `;

  const researchForm = container.querySelector('#research-form');
  const researchQuery = container.querySelector('#research-query-input');
  const researchOutput = container.querySelector('#research-output');
  const researchBtn = container.querySelector('#btn-run-research');

  const docForm = container.querySelector('#doc-form');
  const docTitle = container.querySelector('#doc-title-input');
  const docInstructions = container.querySelector('#doc-instructions-input');
  const docOutput = container.querySelector('#doc-output');
  const docBtn = container.querySelector('#btn-generate-doc');

  researchForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const q = researchQuery.value.trim();
    if (!q) return;

    researchBtn.disabled = true;
    researchBtn.textContent = 'Investigating...';
    researchOutput.style.display = 'block';
    researchOutput.textContent = 'ResearchAgent dispatched. Gathering source evidence...';

    try {
      const res = await api.runResearch(q);
      const findings = res.result?.data?.findings || 'Investigation completed with no text output.';
      researchOutput.textContent = findings;
    } catch (err) {
      researchOutput.textContent = `Research failed: ${err.message}`;
    } finally {
      researchBtn.disabled = false;
      researchBtn.textContent = 'Start Investigation';
    }
  });

  docForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const title = docTitle.value.trim();
    const inst = docInstructions.value.trim();
    if (!title || !inst) return;

    docBtn.disabled = true;
    docBtn.textContent = 'Compiling...';
    docOutput.style.display = 'block';
    docOutput.textContent = 'DocumentAgent drafting document...';

    try {
      const res = await api.generateDocument(title, inst);
      const content = res.document?.content || 'Document compilation finished.';
      docOutput.textContent = content;
    } catch (err) {
      docOutput.textContent = `Compilation failed: ${err.message}`;
    } finally {
      docBtn.disabled = false;
      docBtn.textContent = 'Compile Document';
    }
  });
}
