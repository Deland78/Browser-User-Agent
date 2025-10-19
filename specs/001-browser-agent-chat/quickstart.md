# Quickstart Guide: Browser Automation Agent

**Feature**: 001-browser-agent-chat
**Version**: 1.0.0
**Date**: 2025-10-18

---

## Overview

This quickstart guide helps developers get the Browser Automation Agent running locally for development and testing. For production deployment, see the full deployment documentation.

**What You'll Build**: A chat-based browser automation agent that:

- Accepts natural language commands ("Go to google.com", "Click the login button")
- Controls a web browser via Playwright
- Uses OpenRouter (Claude 3.5 Sonnet) for command interpretation
- Returns results in a conversational chat interface

---

## Prerequisites

### Required Software

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/) (for frontend)
- **Git** - [Download](https://git-scm.com/)

### Required Accounts

- **OpenRouter API Key** - [Sign up](https://openrouter.ai/)
  - Used for LLM command interpretation (accesses Claude, GPT-4, and other models)
  - Pay-per-use pricing, no subscription required
  - Free credits available for testing

### System Requirements

- **OS**: Windows 10+, macOS 11+, or Linux (Ubuntu 20.04+)
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 2GB for dependencies and browser binaries

---

## Quick Start (5 minutes)

### 1. Clone Repository

```bash
git clone https://github.com/your-org/browser-user-agent.git
cd browser-user-agent
git checkout 001-browser-agent-chat
```

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Create .env file from example
cp .env.example .env
# Edit .env and add your OpenRouter API key

# Alternative: Set environment variable directly (not recommended for development)
# Windows:
# set OPENROUTER_API_KEY=your_api_key_here
# macOS/Linux:
# export OPENROUTER_API_KEY=your_api_key_here

# Start backend server
# (Database will be created automatically on first run)
uvicorn src.main:app --reload
```

Backend will be available at: `http://localhost:8000`

### 3. Frontend Setup

Open a **new terminal window**:

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at: `http://localhost:5173`

### 4. Test the System

1. Open browser to `http://localhost:5173`
2. You'll see the chat interface
3. Try these test commands:
   - "Go to google.com"
   - "What is the page title?"
   - "Find the search box and type 'weather'"

---

## Project Structure

```
browser-user-agent/
├── backend/                    # Python FastAPI backend
│   ├── src/
│   │   ├── agent/             # AI agent logic
│   │   ├── browser/           # Playwright automation
│   │   ├── chat/              # Chat session management
│   │   ├── api/               # REST/WebSocket endpoints
│   │   └── main.py            # Entry point
│   ├── tests/                 # pytest test suite
│   └── requirements.txt
│
├── frontend/                   # React + TypeScript frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── services/          # API clients
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
│
└── specs/001-browser-agent-chat/  # Design documents
    ├── spec.md                # Feature specification
    ├── plan.md                # Implementation plan
    ├── research.md            # Technology research
    ├── data-model.md          # Data structures
    ├── contracts/             # API contracts
    └── quickstart.md          # This file
```

---

## Configuration

### Backend Configuration

Edit `backend/src/config/settings.py`:

```python
class Settings:
    # API Settings
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY")
    openrouter_model: str = "anthropic/claude-3.5-sonnet"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Browser Settings
    browser_headless: bool = False  # Set True for production
    default_timeout_seconds: int = 20
    max_timeout_seconds: int = 300

    # Chat Settings
    max_conversation_history: int = 200
    session_timeout_minutes: int = 60

    # Confidence Threshold
    confidence_threshold: float = 0.90  # Per FR-014

    # Database
    database_url: str = "sqlite:///./browser_agent.db"
```

### Frontend Configuration

Edit `frontend/src/config.ts`:

```typescript
export const config = {
  apiBaseUrl: import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1",
  wsBaseUrl: import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws",
  enableDebugMode: import.meta.env.DEV,
};
```

### Environment Variables

Create `.env` files from the example templates:

```bash
# Backend - Copy example and add your API key
cd backend
cp .env.example .env
# Edit .env and replace the placeholder with your actual OpenRouter API key

# Frontend - Copy example (defaults should work)
cd ../frontend
cp .env.example .env
```

**backend/.env** (see `backend/.env.example` for full template):

```bash
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  # Replace with your actual key!
ENVIRONMENT=development
LOG_LEVEL=INFO
BROWSER_HEADLESS=false
# Optional: Your site URL for OpenRouter credits
OPENROUTER_SITE_URL=http://localhost:5173
OPENROUTER_APP_NAME=Browser-Agent-Chat
```

**frontend/.env** (see `frontend/.env.example` for full template):

```bash
VITE_API_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/ws
```

⚠️ **Security Note**: Never commit `.env` files to git. The `.gitignore` is configured to exclude them.

---

## Development Workflow

### Running Tests

**Backend Tests**:

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_command_parser.py

# Run user story E2E tests
pytest tests/e2e/test_user_story_1.py -v
```

**Frontend Tests**:

```bash
cd frontend

# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch
```

### Code Quality

**Backend** (runs automatically in CI):

```bash
# Linting
ruff check src/ tests/

# Type checking
mypy src/

# Format code
black src/ tests/
```

**Frontend**:

```bash
# Linting
npm run lint

# Type checking
npm run type-check

# Format code
npm run format
```

### Running in Debug Mode

**Backend**:

```python
# src/main.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug"
    )
```

Run with debugger:

```bash
python -m debugpy --listen 5678 --wait-for-client -m uvicorn src.main:app --reload
```

**Frontend**:

- Use React DevTools browser extension
- Enable source maps (already configured in `vite.config.ts`)
- Use browser debugger with breakpoints in TypeScript files

---

## Common Commands

### Start Everything (One Command)

Create `start.sh` (macOS/Linux) or `start.bat` (Windows):

```bash
#!/bin/bash
# start.sh

# Start backend in background
cd backend
source venv/bin/activate
uvicorn src.main:app --reload &
BACKEND_PID=$!

# Start frontend in background
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "Press Ctrl+C to stop all services"

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
```

```bash
chmod +x start.sh
./start.sh
```

### Reset Database

```bash
cd backend
# Remove the SQLite database file
rm browser_agent.db
# Database will be recreated automatically on next server start
```

### View API Documentation

With backend running, visit:

- **OpenAPI Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### View Logs

**Backend**:

```bash
# Real-time logs
tail -f backend/logs/app.log

# Structured logs (JSON format)
cat backend/logs/app.log | jq '.'
```

**Frontend**:

- Open browser DevTools → Console tab

---

## Example Usage Scenarios

### Scenario 1: Simple Navigation

```
User: Go to example.com
Agent: Successfully navigated to https://example.com
User: What is the page title?
Agent: The page title is "Example Domain"
```

### Scenario 2: Multi-Step Workflow

```
User: Go to google.com, search for "weather boston", and tell me the temperature
Agent: Step 1/3: Navigating to google.com...
Agent: Step 2/3: Typing "weather boston" in search box...
Agent: Step 3/3: Extracting temperature...
Agent: The current temperature in Boston is 72°F
```

### Scenario 3: Clarification Flow

```
User: Click the button
Agent: I found 5 buttons. Which one?
      1) Search
      2) Login
      3) Sign Up
      4) Submit
      5) Cancel
User: The login button
Agent: Clicked 'Login' button successfully
```

### Scenario 4: Information Extraction

```
User: List all the links on this page
Agent: Found 12 links:
      1) Home - /home
      2) About - /about
      3) Contact - /contact
      ...
```

### Scenario 5: Configuration

```
User: /timeout 60
Agent: Updated page load timeout to 60 seconds (was 20 seconds)
User: Go to slow-loading-site.com
Agent: [waits up to 60 seconds before timeout]
```

---

## Troubleshooting

### Backend Issues

**Issue**: `ImportError: No module named 'playwright'`

```bash
# Solution: Reinstall dependencies
pip install -r requirements.txt
playwright install chromium
```

**Issue**: `OpenRouter API connection error`

```bash
# Solution: Check API key
echo $OPENROUTER_API_KEY  # Should show your key (sk-or-v1-...)
# If empty, set it:
export OPENROUTER_API_KEY=your_key_here
# Test the API key:
curl https://openrouter.ai/api/v1/auth/key \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"
```

**Issue**: Browser doesn't launch

```bash
# Solution: Reinstall browser binaries
playwright install --force chromium
```

### Frontend Issues

**Issue**: `Failed to fetch` errors

```bash
# Solution: Check backend is running
curl http://localhost:8000/api/v1/health
# Should return: {"status": "healthy"}
```

**Issue**: WebSocket connection fails

- Check firewall/antivirus isn't blocking port 8000
- Verify WS URL in frontend config matches backend

### Common Errors

**Error**: "Confidence threshold not met after 3 clarifications"

- **Cause**: User's clarifications aren't resolving ambiguity
- **Solution**: Be more specific in responses, or try rephrasing the original command

**Error**: "Element not found: button with text 'Login'"

- **Cause**: Element doesn't exist or page hasn't loaded
- **Solution**: Wait a few seconds, or ask "List all buttons" first

---

## Next Steps

1. **Read the Specification**: [spec.md](spec.md) - Understand all requirements
2. **Review Architecture**: [plan.md](plan.md) - See technical decisions
3. **Explore API Contracts**: [contracts/](contracts/) - Learn API endpoints
4. **Run User Story Tests**: Test each acceptance scenario
5. **Start Development**: Pick a task from [tasks.md](tasks.md) (generated via `/speckit.tasks`)

---

## Additional Resources

- **Playwright Documentation**: https://playwright.dev/python/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **React Documentation**: https://react.dev/
- **OpenRouter Documentation**: https://openrouter.ai/docs
- **Constitution**: `../.speckit.constitution` - Project engineering standards

---

## Getting Help

- **Issues**: File a GitHub issue with reproduction steps
- **Questions**: Check FAQ in [spec.md](spec.md) or ask in team chat
- **Contributing**: See CONTRIBUTING.md for guidelines

---

**Last Updated**: 2025-10-18
**Version**: 1.0.0
