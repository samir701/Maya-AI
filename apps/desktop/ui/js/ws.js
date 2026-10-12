/**
 * ZETTA UI - WebSocket Event Client
 * Real-time event listener connected to ZETTA EventBus.
 */

class EventStreamClient {
  constructor() {
    this.socket = null;
    this.listeners = new Map();
    this.allListeners = [];
    this.reconnectAttempts = 0;
    this.maxReconnectDelay = 10000;
    this.connected = false;
    this.pingInterval = null;
  }

  connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host || '127.0.0.1:8000';
    const wsUrl = `${protocol}//${host}/ws`;

    console.log(`[WS] Connecting to ${wsUrl}...`);
    try {
      this.socket = new WebSocket(wsUrl);

      this.socket.onopen = () => {
        console.log('[WS] Connected to ZETTA EventBus.');
        this.connected = true;
        this.reconnectAttempts = 0;
        this._dispatch('connection', { status: 'connected' });

        // Start ping keepalive
        if (this.pingInterval) clearInterval(this.pingInterval);
        this.pingInterval = setInterval(() => {
          if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send('ping');
          }
        }, 25000);
      };

      this.socket.onmessage = (event) => {
        if (event.data === 'pong') return;
        try {
          const payload = JSON.parse(event.data);
          this._handleEvent(payload);
        } catch (err) {
          console.warn('[WS] Failed to parse message:', event.data);
        }
      };

      this.socket.onclose = () => {
        console.warn('[WS] Connection closed. Scheduling reconnect...');
        this.connected = false;
        if (this.pingInterval) clearInterval(this.pingInterval);
        this._dispatch('connection', { status: 'disconnected' });
        this._scheduleReconnect();
      };

      this.socket.onerror = (err) => {
        console.error('[WS] Connection error:', err);
      };
    } catch (err) {
      console.error('[WS] Failed to create WebSocket:', err);
      this._scheduleReconnect();
    }
  }

  _scheduleReconnect() {
    const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), this.maxReconnectDelay);
    this.reconnectAttempts++;
    setTimeout(() => this.connect(), delay);
  }

  _handleEvent(event) {
    const type = event.event_type || 'UNKNOWN';

    // Notify specific type listeners
    if (this.listeners.has(type)) {
      this.listeners.get(type).forEach((fn) => {
        try { fn(event); } catch (e) { console.error(`[WS listener error for ${type}]:`, e); }
      });
    }

    // Notify global listeners
    this.allListeners.forEach((fn) => {
      try { fn(event); } catch (e) { console.error('[WS global listener error]:', e); }
    });
  }

  _dispatch(customType, data) {
    if (this.listeners.has(customType)) {
      this.listeners.get(customType).forEach((fn) => fn(data));
    }
  }

  on(eventType, callback) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, []);
    }
    this.listeners.get(eventType).push(callback);
    return () => this.off(eventType, callback);
  }

  off(eventType, callback) {
    if (this.listeners.has(eventType)) {
      const arr = this.listeners.get(eventType).filter((fn) => fn !== callback);
      this.listeners.set(eventType, arr);
    }
  }

  subscribeAll(callback) {
    this.allListeners.push(callback);
    return () => {
      this.allListeners = this.allListeners.filter((fn) => fn !== callback);
    };
  }
}

export const wsClient = new EventStreamClient();
