/**
 * ZETTA UI - Central Reactive State Store
 */

class StateStore {
  constructor() {
    this.state = {
      activeView: 'home',
      systemStatus: {
        employee_name: 'ZETTA',
        version: '0.1.0',
        state: 'CONNECTING...',
        active_agent: 'GeneralAssistantAgent',
        active_persona: 'ZETTA Default',
        agents_count: 6,
        active_tasks_count: 0,
        active_task: null,
      },
      activityEvents: [],
      pendingConfirmations: [],
      activeSessionId: 'default-ui-session',
      connected: false,
    };
    this.listeners = new Set();
    this.viewListeners = new Set();
  }

  get() {
    return this.state;
  }

  set(partial) {
    this.state = { ...this.state, ...partial };
    this._notify();
  }

  setActiveView(viewName) {
    if (this.state.activeView !== viewName) {
      const prevView = this.state.activeView;
      this.state.activeView = viewName;
      this.viewListeners.forEach((fn) => {
        try { fn(viewName, prevView); } catch (err) { console.error('[View subscriber error]:', err); }
      });
      this._notify();
    }
  }

  subscribeView(listener) {
    this.viewListeners.add(listener);
    return () => this.viewListeners.delete(listener);
  }

  addActivityEvent(event) {
    const formatted = {
      id: event.id || Math.random().toString(36).slice(2),
      type: event.event_type || 'SYSTEM_EVENT',
      payload: event.payload || {},
      timestamp: event.timestamp || new Date().toISOString(),
    };
    this.state.activityEvents = [formatted, ...this.state.activityEvents].slice(0, 100);
    this._notify();
  }

  setPendingConfirmations(list) {
    this.state.pendingConfirmations = list || [];
    this._notify();
  }

  subscribe(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  _notify() {
    this.listeners.forEach((fn) => {
      try { fn(this.state); } catch (err) { console.error('[State subscriber error]:', err); }
    });
  }
}

export const store = new StateStore();
