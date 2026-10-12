/**
 * ZETTA UI - Real-Time Voice Center View
 * Voice session control, microphone status, VAD, STT, and TTS.
 */

import { api } from '../api.js';

export async function renderVoice(container) {
  container.innerHTML = `
    <div class="view-header" style="display: flex; justify-content: space-between; align-items: flex-end;">
      <div>
        <div class="view-title">Real-Time Voice Center</div>
        <div class="view-subtitle">Voice activity detection (VAD), speech-to-text (STT), and neural voice synthesis (TTS)</div>
      </div>
      <button class="btn btn-secondary btn-sm" id="btn-refresh-voice">Refresh Audio Devices</button>
    </div>

    <!-- Voice Control Hero Card -->
    <div class="glass-card" style="margin-bottom: 24px; text-align: center; padding: 36px 20px;">
      <div style="display: inline-flex; width: 72px; height: 72px; border-radius: 50%; background: rgba(59, 130, 246, 0.15); border: 2px solid rgba(59, 130, 246, 0.4); align-items: center; justify-content: center; margin-bottom: 16px; cursor: pointer; transition: all 0.2s ease;" id="mic-hero-btn">
        <svg id="mic-icon" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>
      </div>

      <div style="font-size: 18px; font-weight: 700; color: #fff; margin-bottom: 4px;" id="mic-status-headline">
        Microphone Idle
      </div>
      <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 20px;" id="mic-status-subline">
        Click to start real-time voice listening session
      </div>

      <button class="btn btn-primary" id="btn-toggle-voice-session" style="min-width: 180px;">Start Voice Session</button>
    </div>

    <!-- Telemetry Cards -->
    <div class="card-grid" style="margin-bottom: 24px;">
      <div class="glass-card">
        <div class="card-title">
          <span>STT Transcriber</span>
          <span class="status-dot"></span>
        </div>
        <div class="metric-value" style="font-size: 18px;" id="stt-provider-val">Whisper / Groq</div>
        <div class="metric-label">Voice Activity Detection: EnergyVAD</div>
      </div>

      <div class="glass-card">
        <div class="card-title">
          <span>TTS Voice Synthesis</span>
          <span class="status-dot"></span>
        </div>
        <div class="metric-value" style="font-size: 18px;" id="tts-provider-val">Kokoro / Groq Orpheus</div>
        <div class="metric-label">Default Voice: af_heart (Neural)</div>
      </div>
    </div>

    <!-- Speech Synthesis Test Form -->
    <div class="glass-card">
      <div class="card-title">
        <span>Test Speech Synthesis (TTS)</span>
      </div>
      <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">
        Type any response to test ZETTA's voice playback engine.
      </div>
      <form id="speak-test-form" style="display: flex; gap: 10px;">
        <input type="text" class="form-input" id="speak-text-input" placeholder="e.g. Hello, I am ZETTA, your AI employee." required />
        <button type="submit" class="btn btn-secondary" id="btn-speak-text">Speak</button>
      </form>
    </div>
  `;

  const micHero = container.querySelector('#mic-hero-btn');
  const micIcon = container.querySelector('#mic-icon');
  const micHeadline = container.querySelector('#mic-status-headline');
  const micSubline = container.querySelector('#mic-status-subline');
  const toggleBtn = container.querySelector('#btn-toggle-voice-session');
  const refreshBtn = container.querySelector('#btn-refresh-voice');
  const speakForm = container.querySelector('#speak-test-form');
  const speakInput = container.querySelector('#speak-text-input');
  const sttVal = container.querySelector('#stt-provider-val');
  const ttsVal = container.querySelector('#tts-provider-val');

  let isListening = false;

  async function updateVoiceStatus() {
    try {
      const res = await api.getVoiceStatus();
      const details = res.details || {};
      sttVal.textContent = details.stt_provider || 'Whisper';
      ttsVal.textContent = details.tts_provider || 'KokoroTTS';
    } catch (err) {
      console.warn('Voice status error:', err);
    }
  }

  async function toggleSession() {
    if (!isListening) {
      toggleBtn.disabled = true;
      try {
        await api.startVoiceSession();
        isListening = true;
        micHeadline.textContent = 'Listening (VAD Active)...';
        micSubline.textContent = 'Speak naturally to give ZETTA voice commands';
        micHero.style.borderColor = '#22c55e';
        micHero.style.background = 'rgba(34, 197, 94, 0.2)';
        micIcon.setAttribute('stroke', '#22c55e');
        toggleBtn.textContent = 'Stop Voice Session';
        toggleBtn.className = 'btn btn-danger';
      } catch (err) {
        alert(`Failed to start voice: ${err.message}`);
      } finally {
        toggleBtn.disabled = false;
      }
    } else {
      toggleBtn.disabled = true;
      try {
        await api.stopVoiceSession();
        isListening = false;
        micHeadline.textContent = 'Microphone Idle';
        micSubline.textContent = 'Click to start real-time voice listening session';
        micHero.style.borderColor = 'rgba(59, 130, 246, 0.4)';
        micHero.style.background = 'rgba(59, 130, 246, 0.15)';
        micIcon.setAttribute('stroke', '#3b82f6');
        toggleBtn.textContent = 'Start Voice Session';
        toggleBtn.className = 'btn btn-primary';
      } catch (err) {
        alert(`Failed to stop voice: ${err.message}`);
      } finally {
        toggleBtn.disabled = false;
      }
    }
  }

  toggleBtn.addEventListener('click', toggleSession);
  micHero.addEventListener('click', toggleSession);

  speakForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = speakInput.value.trim();
    if (!text) return;

    const btn = container.querySelector('#btn-speak-text');
    btn.disabled = true;
    btn.textContent = 'Synthesizing...';
    try {
      await api.speakText(text);
    } catch (err) {
      alert(`TTS playback error: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Speak';
    }
  });

  refreshBtn.addEventListener('click', updateVoiceStatus);
  updateVoiceStatus();
}
