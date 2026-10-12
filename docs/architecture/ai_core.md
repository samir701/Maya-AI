# ZETTA AI EMPLOYEE — AI CORE ARCHITECTURE (PHASE 01)

## 1. Executive Summary
Phase 01 implements the modular, provider-agnostic AI Core for ZETTA AI EMPLOYEE. The AI Core provides provider abstraction, a centralized orchestration AI Brain, structured request/response contracts, prompt template management, context construction, response parsing, and standard AI event notifications.

## 2. Core Components Architecture

```
                                 ┌──────────────────────────┐
                                 │     Calling System       │
                                 └────────────┬─────────────┘
                                              │
                                              ▼
                                 ┌──────────────────────────┐
                                 │      AIBrain             │
                                 └──────┬────────────┬──────┘
                                        │            │
                  ┌─────────────────────┘            └─────────────────────┐
                  ▼                                                        ▼
      ┌───────────────────────┐                                ┌───────────────────────┐
      │   ContextBuilder      │                                │    ResponseParser     │
      └───────────────────────┘                                └───────────────────────┘
                  │                                                        │
                  ▼                                                        ▼
      ┌───────────────────────┐                                ┌───────────────────────┐
      │    PromptRegistry     │                                │   EventBus Notifier   │
      └───────────────────────┘                                └───────────────────────┘
                                              │
                                              ▼
                                 ┌──────────────────────────┐
                                 │    ProviderFactory       │
                                 └────────────┬─────────────┘
                                              │
                  ┌───────────────────────────┼───────────────────────────┐
                  ▼                           ▼                           ▼
      ┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
      │    FakeAIProvider     │   │    OpenAIProvider     │   │    GeminiProvider     │
      └───────────────────────┘   └───────────────────────┘   └───────────────────────┘
```

## 3. Data Contracts
- `AIRequest`: Standard payload containing message list, model name, temperature, max tokens, streaming parameters, stop sequences, and response format.
- `AIResponse`: Provider-normalized response containing choices, message role and text, token usage, duration, raw provider payload, and unique ID.
- `AIStreamChunk`: Normalized token stream chunk emitted during streaming responses.

## 4. Key Security & Privacy Controls
- Secret masking: API keys and authorization tokens are strictly redacted from `repr()`, `str()`, error exceptions, and log statements.
- Strict isolation: The AI Core performs thinking and response generation only. It has zero capability or access to tool execution, file manipulation, screen capture, or OS actions.
