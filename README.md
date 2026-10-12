# ZETTA AI Employee

ZETTA is a local-first AI assistant designed to help with multi-step tasks through a modular set of AI, memory, desktop, browser, voice, and agent capabilities. It is built in Python, with explicit safety checks and user-confirmation gates for actions that can affect the system or external services.

> **Project status:** The backend project status records Phases 00–08 as complete. The next planned milestone is the UI/product presentation layer. See [PROJECT_STATUS.md](PROJECT_STATUS.md) and the [changelog](CHANGELOG.md) for the detailed status and history.

## Capabilities

- Interactive command-line assistant, task management, and health checks.
- Pluggable AI providers, prompt/context handling, and response parsing.
- Short- and long-term memory backed by local storage.
- Permission-aware tools for files, applications, processes, and desktop interaction.
- Screen capture, OCR, and browser automation.
- Voice input and output with configurable providers, including local Kokoro TTS.
- Task planning, agent orchestration, skills, plugins, and reusable workflows.
- Unit, integration, system, and end-to-end test suites.

Some capabilities require optional local model files, OS permissions, external services, or API credentials. Those are not bundled with this repository.

## Requirements

- Python 3.10 or newer.
- Linux, macOS, or Windows may work, but desktop, audio, and browser features depend on platform-specific tools and permissions.
- For integrations that use a cloud provider, the provider's account and API credentials.

## Installation

From the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## Configuration

Create a local environment file from the safe template:

```bash
cp .env.example .env
```

Edit `.env` to configure providers and any required API keys. Never commit `.env` or paste credentials into source files; `.env` is excluded from Git. The checked-in `.env.example` contains placeholders only.

Kokoro model weights and voice data are large local assets and are not stored in this repository. Obtain them from their official source, follow their licensing terms, and set `KOKORO_MODEL_PATH` and `KOKORO_VOICES_PATH` in `.env` if the defaults do not match their locations. Local database files, logs, browser profiles, and screen captures are also machine-specific and are excluded from Git.

## Run

Run commands from the project directory:

```bash
python core/zetta/cli.py --help
```

For example, start the interactive chat or inspect system health:

```bash
python core/zetta/cli.py chat
python core/zetta/cli.py
```

The CLI includes additional commands for tasks, memory, tools, vision, browser, voice, agents, and workflows. Use `--help` with the relevant command to see its options. Some commands perform real desktop or browser actions; review their permissions and confirmation prompts before use.

## Tests and validation

Run the test suite:

```bash
python -m pytest
```

Run the project's full import, health, and test validation:

```bash
./run_all.sh
```

The validation script uses `.venv/bin/python` when that environment exists, otherwise it uses `python3`. Tests that need optional hardware, credentials, or downloaded models may be skipped or require additional setup.

## Repository layout

```text
apps/       Desktop and Android client work
config/     Environment-specific configuration
core/       ZETTA engine: AI, agents, memory, tools, voice, vision, browser
data/       Local databases, model assets, logs, cache, and memory
docs/       Architecture notes, phase documentation, and decisions
runtime/    Local browser profiles and screen captures (not versioned)
scripts/    Development, testing, and deployment utilities
shared/     Shared schemas, types, and constants
tests/      Unit, integration, system, and end-to-end tests
```

## Documentation

- [Project status and audit trail](PROJECT_STATUS.md)
- [Changelog](CHANGELOG.md)
- [Architecture documentation](docs/architecture/)
- [Phase documentation](docs/phases/)

## License

This project is distributed under the [MIT License](LICENSE).
