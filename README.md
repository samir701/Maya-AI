# ZETTA AI EMPLOYEE

ZETTA is a personal, local-first AI employee and desktop assistant designed to execute complex, multi-step tasks autonomously.

## Overview
ZETTA operates as an intelligent local assistant capable of understanding natural language and voice commands, controlling desktop elements, performing browser automation, managing memory, and coordinating specialized tools and agents.

## Core Architectural Principles
- **Desktop-First & Local-First**: Core logic runs locally with full privacy and local resource control.
- **Incremental Development**: Features are implemented and locked step-by-step through a strict pipeline (Design → Implement → Test → Verify → Fix → Refactor → Document → Git Commit → Lock Feature → Next Feature).
- **Strict Modularity**: Core logic is completely decoupled from UI interfaces (Desktop and Mobile apps). Tools, agents, memory modules, and AI providers are pluggable and isolated.
- **Verification & Safety**: Autonomous decisions undergo safety verification, audit logging, and explicit confirmation protocols.
- **Assisted Engineering**: AI coding assistants serve strictly as implementation support, not autonomous architectural decision-makers.

## Project Structure
```
ZETTA-AI-EMPLOYEE/
├── apps/              # Client application interfaces (Desktop, Android)
├── core/              # Core ZETTA AI logic, agents, tools, engine
├── shared/            # Shared types, schemas, and constants
├── tests/             # Comprehensive unit, integration, system, and E2E tests
├── docs/              # Phase documentation, architecture notes, security policies
├── scripts/           # Utility scripts for development, testing, and deployment
├── config/            # Environment configurations
├── data/              # Local database, memory storage, logs, and temporary caches
└── .github/           # CI/CD workflows and automated pipelines
```
