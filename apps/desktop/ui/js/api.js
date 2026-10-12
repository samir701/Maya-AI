/**
 * ZETTA UI - REST API Client Module
 * Provides unified HTTP interaction with FastAPI backend bridge.
 */

const API_BASE = '';

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  try {
    const response = await fetch(url, config);
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `HTTP error ${response.status}`);
    }
    return await response.json();
  } catch (err) {
    console.error(`[API Error] ${options.method || 'GET'} ${path}:`, err);
    throw err;
  }
}

export const api = {
  // System & Health
  getSystemStatus: () => request('/api/status'),
  getHealth: () => request('/api/health'),

  // Chat
  getChatSessions: () => request('/api/chat/sessions'),
  createChatSession: (name) => request('/api/chat/sessions', { method: 'POST', body: JSON.stringify({ name }) }),
  getChatHistory: (sessionId) => request(`/api/chat/sessions/${sessionId}`),
  sendMessage: (message, sessionId = 'default-ui-session') =>
    request('/api/chat/message', { method: 'POST', body: JSON.stringify({ message, session_id: sessionId }) }),

  // Agents
  getAgents: () => request('/api/agents'),
  getAgentDetails: (name) => request(`/api/agents/${encodeURIComponent(name)}`),
  runAgentTask: (agentName, taskName, taskDescription = '') =>
    request('/api/agents/run', { method: 'POST', body: JSON.stringify({ agent_name: agentName, task_name: taskName, task_description: taskDescription }) }),

  // Tasks & Workflows
  getTasks: () => request('/api/tasks'),
  createTask: (name, description = '', metadata = {}) =>
    request('/api/tasks', { method: 'POST', body: JSON.stringify({ name, description, metadata }) }),
  getTask: (taskId) => request(`/api/tasks/${taskId}`),
  cancelTask: (taskId) => request(`/api/tasks/${taskId}/cancel`, { method: 'POST' }),
  planWorkflow: (goal) => request('/api/workflows/plan', { method: 'POST', body: JSON.stringify({ goal }) }),
  executeWorkflow: (planId) => request('/api/workflows/execute', { method: 'POST', body: JSON.stringify({ plan_id: planId }) }),

  // Computer Control
  getComputerStatus: () => request('/api/computer/status'),
  getScreenshot: () => request('/api/computer/screenshot'),
  executeComputerAction: (action, parameters = {}) =>
    request('/api/computer/action', { method: 'POST', body: JSON.stringify({ action, parameters }) }),

  // Browser Control
  getBrowserStatus: () => request('/api/browser/status'),
  launchBrowser: (headless = true) => request('/api/browser/launch', { method: 'POST', body: JSON.stringify({ headless }) }),
  browserNavigate: (url, sessionId = null) => request('/api/browser/navigate', { method: 'POST', body: JSON.stringify({ url, session_id: sessionId }) }),
  browserClick: (target, sessionId = null) => request('/api/browser/click', { method: 'POST', body: JSON.stringify({ target, session_id: sessionId }) }),
  browserType: (target, text, sessionId = null) => request('/api/browser/type', { method: 'POST', body: JSON.stringify({ target, text, session_id: sessionId }) }),

  // Vision
  getVisionStatus: () => request('/api/vision/status'),
  captureScreen: (displayId = null) => request('/api/vision/capture', { method: 'POST', body: JSON.stringify({ display_id: displayId }) }),
  runOcr: () => request('/api/vision/ocr', { method: 'POST' }),
  detectUi: () => request('/api/vision/detect', { method: 'POST' }),

  // Voice
  getVoiceStatus: () => request('/api/voice/status'),
  getVoiceCapabilities: () => request('/api/voice/capabilities'),
  startVoiceSession: (sessionId = null) => request('/api/voice/session/start', { method: 'POST', body: JSON.stringify({ session_id: sessionId }) }),
  stopVoiceSession: () => request('/api/voice/session/stop', { method: 'POST' }),
  speakText: (text, voice = null) => request('/api/voice/speak', { method: 'POST', body: JSON.stringify({ text, voice }) }),

  // Memory
  listMemories: (type = null, tag = null, limit = 50) => {
    const params = new URLSearchParams();
    if (type) params.append('memory_type', type);
    if (tag) params.append('tag', tag);
    params.append('limit', limit);
    return request(`/api/memory/list?${params.toString()}`);
  },
  searchMemories: (query, limit = 10) => request(`/api/memory/search?query=${encodeURIComponent(query)}&limit=${limit}`),
  addMemory: (content, memoryType = 'LONG_TERM', tags = []) =>
    request('/api/memory', { method: 'POST', body: JSON.stringify({ content, memory_type: memoryType, tags }) }),
  deleteMemory: (memoryId) => request(`/api/memory/${memoryId}`, { method: 'DELETE' }),

  // Skills & Plugins
  getSkills: () => request('/api/skills'),
  getPlugins: () => request('/api/plugins'),
  togglePlugin: (name, enabled) => request(`/api/plugins/${encodeURIComponent(name)}/toggle`, { method: 'POST', body: JSON.stringify({ enabled }) }),

  // Confirmations
  getConfirmations: () => request('/api/confirmations'),
  createConfirmationRequest: (action, description, requiredPermission = 'HIGH') =>
    request('/api/confirmations/request', { method: 'POST', body: JSON.stringify({ action, description, required_permission: requiredPermission }) }),
  resolveConfirmation: (id, approved, reason = '') =>
    request(`/api/confirmations/${id}/resolve`, { method: 'POST', body: JSON.stringify({ approved, reason }) }),

  // Documents & Research
  listDocuments: () => request('/api/documents/list'),
  runResearch: (query, tools = []) => request('/api/documents/research', { method: 'POST', body: JSON.stringify({ query, tools }) }),
  generateDocument: (title, instructions, outputFilename = null) =>
    request('/api/documents/generate', { method: 'POST', body: JSON.stringify({ title, instructions, output_filename: outputFilename }) }),

  // Settings & Personas
  getSettings: () => request('/api/settings'),
  getPersonas: () => request('/api/personas'),
  switchPersona: (personaType) => request('/api/settings/persona', { method: 'POST', body: JSON.stringify({ persona_type: personaType }) }),
};
