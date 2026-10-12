/**
 * ZETTA UI - Chat & Direct Conversational Interface
 */

import { api } from '../api.js';
import { store } from '../state.js';

let currentSessionId = 'default-ui-session';

export function renderChat(container) {
  container.innerHTML = `
    <div class="view-header" style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 16px;">
      <div>
        <div class="view-title">Conversational Control</div>
        <div class="view-subtitle">Direct natural language instructions and reasoning with ZETTA</div>
      </div>
      <button class="btn btn-secondary btn-sm" id="btn-clear-chat">Clear History</button>
    </div>

    <!-- Quick Prompt Suggestions -->
    <div style="display: flex; gap: 8px; margin-bottom: 14px; overflow-x: auto; padding-bottom: 4px;">
      <button class="btn btn-secondary btn-sm prompt-chip" data-prompt="Take a screen snapshot and analyze active window">📸 Snap & Analyze</button>
      <button class="btn btn-secondary btn-sm prompt-chip" data-prompt="Check active system tasks and report status">📋 Check Tasks</button>
      <button class="btn btn-secondary btn-sm prompt-chip" data-prompt="Launch browser and check latest updates">🌐 Open Browser</button>
      <button class="btn btn-secondary btn-sm prompt-chip" data-prompt="Remember that I prefer dark mode and clean architecture">🧠 Store Memory</button>
    </div>

    <!-- Message Stream -->
    <div class="chat-messages" id="chat-stream">
      <div class="chat-bubble zetta">
        <div style="font-weight: 700; color: #60a5fa; font-size: 11px; margin-bottom: 4px; text-transform: uppercase;">ZETTA AI Employee</div>
        Hello! I am ZETTA, your AI Employee. I have full capability over your browser, desktop tools, persistent memory, vision, and autonomous execution. How can I assist you today?
      </div>
    </div>

    <!-- Input Bar -->
    <form class="chat-input-bar" id="chat-form">
      <input type="text" class="form-input" id="chat-input" placeholder="Give ZETTA an instruction or task (e.g. 'Open Chrome', 'Summarize this document')..." autocomplete="off" />
      <button type="submit" class="btn btn-primary" id="btn-send-message">
        <span>Send</span>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
      </button>
    </form>
  `;

  const stream = container.querySelector('#chat-stream');
  const form = container.querySelector('#chat-form');
  const input = container.querySelector('#chat-input');
  const clearBtn = container.querySelector('#btn-clear-chat');

  // Load existing session history
  loadHistory(stream);

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;

    // Append User Message
    appendBubble(stream, 'user', 'You', text);
    input.value = '';

    // Show typing state
    const typingBubble = appendBubble(stream, 'zetta', 'ZETTA', 'Thinking...', true);

    try {
      const res = await api.sendMessage(text, currentSessionId);
      typingBubble.remove();
      appendBubble(stream, 'zetta', `ZETTA (${res.persona || 'Assistant'})`, res.response || 'Task completed.');
    } catch (err) {
      typingBubble.remove();
      appendBubble(stream, 'zetta', 'System Error', `Failed to execute instruction: ${err.message}`);
    }
  });

  // Prompt chips
  container.querySelectorAll('.prompt-chip').forEach((btn) => {
    btn.addEventListener('click', () => {
      input.value = btn.getAttribute('data-prompt');
      input.focus();
    });
  });

  clearBtn.addEventListener('click', () => {
    currentSessionId = `sess_${Date.now()}`;
    stream.innerHTML = `
      <div class="chat-bubble zetta">
        <div style="font-weight: 700; color: #60a5fa; font-size: 11px; margin-bottom: 4px; text-transform: uppercase;">ZETTA AI Employee</div>
        Session cleared. Starting a fresh conversational workspace.
      </div>
    `;
  });
}

function appendBubble(stream, senderClass, senderName, text, isTyping = false) {
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${senderClass}`;
  bubble.innerHTML = `
    <div style="font-weight: 700; color: ${senderClass === 'user' ? '#fff' : '#60a5fa'}; font-size: 11px; margin-bottom: 4px; text-transform: uppercase;">
      ${senderName}
    </div>
    <div style="white-space: pre-wrap;">${escapeHtml(text)}</div>
  `;
  stream.appendChild(bubble);
  stream.scrollTop = stream.scrollHeight;
  return bubble;
}

async function loadHistory(stream) {
  try {
    const data = await api.getChatHistory(currentSessionId);
    if (data && data.messages && data.messages.length > 0) {
      stream.innerHTML = '';
      data.messages.forEach((m) => {
        const isUser = m.role === 'user';
        appendBubble(stream, isUser ? 'user' : 'zetta', isUser ? 'You' : 'ZETTA', m.content);
      });
    }
  } catch (err) {
    // Session might be fresh, ignore
  }
}

function escapeHtml(str) {
  return str.replace(/[&<>'"]/g, 
    tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
  );
}
