# Phase 06: Browser & Web Control Subsystem

## Status: COMPLETE

## Objective
Implement a modular, secure, and extensible browser automation and web control subsystem capable of headless and visible navigation, structured DOM and interactive element discovery, clicking, typing, keyboard actions, scrolling, history management, visual viewport captures, and deep integration with `ToolRouter`, `SecurityManager`, `InteractionManager`, and `VisionManager`.

---

## Architectural Flow

```
Natural Language / Chat Shell / CLI
                ↓
       InteractionManager
                ↓
           ToolRouter (Regex Intent Patterns & Structured Routing)
                ↓
        SecurityManager (Permission Gating + Confirmation Policy + Audit Trail)
                ↓
          Browser Tools (12 Tool Subclasses in ToolRegistry)
                ↓
        BrowserController (Session Lifecycles, Navigation, Action Dispatch)
                ↓
         BrowserManager (Orchestration Facade & Provider Factory)
         ↙                    ↘
FakeBrowserProvider      LocalBrowserProvider (Chrome/Chromium)
(Deterministic/Offline)          ↕
         ↕                 VisionManager
   Mock Web World     (Hybrid Visual/DOM Understanding)
```

---

## Components Implemented

### 1. Core Browser Models (`core/zetta/browser/models/`)
- `session.py`: `BrowserSession`, `BrowserTab`, `BrowserType`, `SessionState`.
- `page.py`: `PageInfo` (URL, title, visible text summary, links count, buttons count, inputs count, viewport, load timing).
- `elements.py`: `WebElement`, `ElementType` (`BUTTON`, `INPUT`, `LINK`, `SELECT`, `TEXTAREA`, `HEADING`, `FORM`, etc.), `ElementLocation`.
- `actions.py`: `BrowserAction`, `ActionResult`, `ScrollDirection`, `HistoryAction`.

### 2. Browser Providers (`core/zetta/browser/providers/`)
- `base.py`: Abstract `BrowserProvider` interface.
- `fake.py`: 100% deterministic, zero-network `FakeBrowserProvider` with simulated DOMs, navigation stacks, interactive elements, typing state, and mock PNG capture.
- `local.py`: `LocalBrowserProvider` discovering installed host browsers (`google-chrome`, `chromium`, `firefox`), with temporary user-data isolation, DOM dump extraction, and process cleanup.

### 3. Controller & Orchestrator (`core/zetta/browser/`)
- `controller.py`: `BrowserController` enforcing URL security policies (blocking `javascript:`, `vbscript:`, path traversal outside sandbox), credential masking for sensitive fields (`password`, `token`), and tab management.
- `manager.py`: `BrowserManager` facade with singleton access (`get_browser_manager()`, `set_browser_manager()`) and screenshot export to `<project_root>/runtime/captures/`.

### 4. Browser Tools (`core/zetta/tools/browser/`)
12 tools registered in `ToolRegistry`:

| Tool Name | Category | Permission | Confirmation | Description |
| :--- | :---: | :---: | :---: | :--- |
| `browser_status` | browser | `LOW` | No | Discover installed browsers and active sessions |
| `browser_launch` | browser | `MEDIUM` | No | Launch a new browser session |
| `browser_close` | browser | `MEDIUM` | No | Terminate an active browser session |
| `browser_navigate` | browser | `MEDIUM` | No | Navigate to website URL |
| `browser_get_page` | browser | `LOW` | No | Extract page title, URL, visible text, and stats |
| `browser_detect_elements` | browser | `LOW` | No | Detect interactive elements (buttons, links, inputs) |
| `browser_click` | browser | `MEDIUM` | No | Click button, link, or element |
| `browser_type` | browser | `MEDIUM` | No | Type text into input field or textarea |
| `browser_keyboard` | browser | `MEDIUM` | No | Send keyboard keys (Enter, Escape, Tab, etc.) |
| `browser_scroll` | browser | `LOW` | No | Scroll page (up, down, top, bottom) |
| `browser_history` | browser | `LOW` | No | Navigate history (back, forward, reload) |
| `browser_screenshot` | browser | `LOW` | No | Capture viewport PNG screenshot |

---

## Security & Privacy Guardrails

1. **URL Protocol Restriction**: Strictly permits safe web protocols (`http://`, `https://`, `about:blank`). Blocks dangerous schemes (`javascript:`, `vbscript:`, `data:`) and blocks `file://` access outside the project workspace root.
2. **Sensitive Input Masking**: Field names or selectors matching passwords, tokens, pins, or secrets have values masked with `***REDACTED***` in audit logs and event payloads.
3. **Memory Isolation**: Web page content and HTML DOMs are strictly ephemeral and are never automatically promoted into long-term memory.
4. **Deterministic Offline Testing**: Zero tests rely on external network access. Full browser simulation runs under `FakeBrowserProvider`.

---

## Multimodal Vision Integration

`BrowserManager.capture_screenshot()` captures valid PNG bytes identical in format to `VisionManager.capture_screen()`. This enables direct pipelining into:
- `VisionManager.perform_ocr()` (extracting visual text from canvas or raster elements).
- `VisionManager.detect_ui()` (validating visual bounding boxes alongside DOM elements).
- `VisionManager.analyze_screen()` (generating high-level multimodal page comprehension).

---

---

## CDP Lifecycle & History Target Recovery

- **Native Protocol Navigation**: Employs `Page.getNavigationHistory` + `Page.navigateToHistoryEntry` and `Page.reload` instead of evaluating window history expressions in JavaScript, preventing execution context destruction during frame unloads.
- **Dynamic Target Recovery**: Detects transient frame transitions or `Inspected target navigated or closed` errors, re-queries Chrome's `/json/list`, reconnects WebSocket to the active page target, and retries the command.
- **Document Readiness Settling**: Waits for `document.readyState` to enter `"complete"` or `"interactive"` before resolving page details.
- **Cross-Process Session Persistence**: Preserves active target pointers and session state across independent CLI processes (`runtime/browser/local_sessions.json`), with automatic cleanup of terminated processes.
- **Screenshot Integrity**: Guarantees that screenshots captured after history back/forward/reload resolve against the settled, fresh page target.

---

## Test Coverage

- **Unit Tests**: `tests/unit/test_phase06_browser.py` (47 tests)
- **Integration Tests**: `tests/integration/test_phase06_integration.py` (4 tests)
- **Full Test Suite**: **221 / 221 PASSED** across Phases 00 through 06.
