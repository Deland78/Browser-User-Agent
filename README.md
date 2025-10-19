# Browser Automation Agent

Conversational web automation agent with a FastAPI backend and React (Vite + TypeScript) frontend. Users issue
natural-language commands, the agent evaluates confidence, performs browser actions via Playwright, and responds
through a chat UI.

This repository implements the specification generated under `specs/001-browser-agent-chat` and follows the project
constitution in `.speckit.constitution`.

## Project Structure

```
backend/       # FastAPI service, Playwright automation, SQLite persistence
frontend/      # Vite + React chat client
specs/         # Design artifacts, contracts, task breakdown
```

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 18+  |
| npm | 9+ |
| Playwright | 1.40+ (installed via CLI) |
| Git | latest |

> **Heads-up:** Run all commands from the repository root unless specified.

## Quick Start

### 1. Clone & Install Hooks

```bash
git clone <repo>
cd browser-user-agent
pip install pre-commit
pre-commit install
```

### 2. Backend Setup (`backend/`)

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -e ".[dev]"

# Playwright browser binaries
playwright install chromium

# Environment variables
cp .env.example .env
```

Verify tooling:

```bash
python -m pytest --version
ruff --version
black --version
```

Start the API:

```bash
uvicorn browser_agent.app:create_app --factory --reload
```

### 3. Frontend Setup (`frontend/`)

```bash
cd ../frontend
npm install
cp .env.example .env
npm run dev
```

Visit `http://localhost:5173` in your browser. The chat UI currently shows a mocked interaction until backend
integration tasks are completed.

## Quality Gates

Run linting, formatting, and tests before opening a pull request:

```bash
# Backend
cd backend
ruff check .
black .
mypy .
pytest

# Frontend
cd ../frontend
npm run lint
npm run format
npm test
```

## Environment Variables

### Backend (`backend/.env`)

| Variable | Purpose |
|----------|---------|
| `OPENROUTER_API_KEY` | API key for OpenRouter LLM access |
| `OPENROUTER_SITE_URL`, `OPENROUTER_APP_NAME` | Optional metadata for OpenRouter |
| `ENVIRONMENT` | `development` \| `production` |
| `LOG_LEVEL` | E.g. `INFO`, `DEBUG` |
| `LOG_DIRECTORY` | Folder for JSON log files (`backend/logs` by default) |
| `BROWSER_HEADLESS` | Playwright headless toggle |
| `DATABASE_URL` | Defaults to `sqlite+aiosqlite:///backend/browser_agent.db` |
| `HOST`, `PORT` | FastAPI bind address |
| `CORS_ORIGINS` | Comma-separated list of allowed origins |

### Frontend (`frontend/.env`)

| Variable | Purpose |
|----------|---------|
| `VITE_API_URL` | Backend REST base URL |
| `VITE_WS_URL` | Backend WebSocket endpoint |

## Scripts

| Command | Description |
|---------|-------------|
| `browser-agent-backend` | Launch FastAPI with reload (`uvicorn` factory) |
| `npm run dev` | Start Vite development server |
| `npm run test` | Execute frontend unit tests with Vitest |
| `npm run lint` | Run ESLint with TypeScript rules |
| `npm run format` | Apply Prettier formatting |

## Next Steps

Implementation tasks are tracked in `specs/001-browser-agent-chat/tasks.md`. Complete remaining Phase 0 items before
progressing to Phase 1 infrastructure tasks. Refer to `quickstart.md` and the contracts in `specs/001-browser-agent-chat/contracts/`
for integration details.

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Playwright for Python](https://playwright.dev/python/)
- [Vite Documentation](https://vitejs.dev/)
- [Radix UI](https://www.radix-ui.com/) for accessible React primitives

