![IterLens Banner](./assets/banner.png)

# IterLens - LangGraph Project

## Overview

IterLens is a conversational AI application built using LangGraph and FastAPI, designed to handle Telegram and WhatsApp messages for reporting and managing machine failures in an industrial environment. The system uses a state graph to manage conversation flows, allowing operators to report issues, list machines, confirm reports, and interact naturally through messaging platforms.

## Features

- **Conversational AI**: Powered by LangGraph and Mistral AI for managing complex conversation states and intent routing.
- **Telegram Integration**: Native webhook handling with voice transcription support.
- **WhatsApp Integration**: Evolution API webhook handling for message processing.
- **Machine Failure Reporting**: Guided flow for reporting failures with field extraction, validation, and confirmation.
- **State Management**: Persistent conversation state using LangGraph's checkpointer, isolated per user.
- **Web Simulator**: Frontend simulator to test the WhatsApp-like interaction.
- **Supabase Integration**: Database for storing machines, failure types, and reports.

## Installation

### Prerequisites

- Python 3.10 or higher
- Supabase account (for database)

### Setup

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd IterLens-langgraph
   ```

2. Create a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your actual credentials. See [Configuration](#configuration) for all available options.

5. Run the application:

   ```bash
   python main.py
   ```

   The API will be available at `http://localhost:8000`.

## Configuration

All settings are managed via environment variables. See `.env.example` for the full list:

| Variable | Description | Default |
|----------|-------------|---------|
| `DEV` | Enable hot reload | `false` |
| `PORT` | Server port | `8000` |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | `*` |
| `LLM_MODEL` | Mistral AI model to use | `mistral-large-latest` |
| `MISTRAL_API_KEY` | Mistral AI API key | — |
| `SUPABASE_URL` | Supabase project URL | — |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | — |
| `TIMEZONE` | Timezone for date calculations | `America/Bogota` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | — |
| `TELEGRAM_BOT_USERNAME` | Telegram bot username | — |
| `WEBHOOK_URL` | Telegram webhook URL | — |
| `EVOLUTION_API_URL` | Evolution API base URL | — |
| `EVOLUTION_API_KEY` | Evolution API key | — |
| `EVOLUTION_INSTANCE` | Evolution API instance name | `lensbot-whatsapp` |
| `ELEVENLABS_API_KEY` | ElevenLabs API key for STT | — |
| `ELEVENLABS_MODEL` | ElevenLabs STT model | `scribe_v2` |
| `OLD_MESSAGE_THRESHOLD_SECONDS` | Ignore messages older than this | `60` |

## Usage

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/webhook/telegram` | Telegram webhook |
| `POST` | `/webhook/whatsapp` | WhatsApp webhook (Evolution API) |
| `POST` | `/webhook/test` | Direct test endpoint |

### Frontend Simulator

Open `frontend/index.html` in your browser to simulate conversations. Configure the API URL and phone number, then send messages to test the LangGraph flow.

### Conversation Flow

The LangGraph handles various intents:

- **Greeting**: Responds to hello messages and offers to report an incident.
- **Report Failure**: Guides the user through collecting machine, failure type, shift, duration, and priority.
- **List Machines**: Shows available machines grouped by cell.
- **List Failures**: Shows failure types grouped by OEE category.
- **Confirm/Cancel**: Displays a summary for confirmation or cancels the report.
- **Fallback**: Handles unrecognized messages with contextual responses.

## Project Structure

```
IterLens-langgraph/
├── .env.example              # Environment variables template
├── pyproject.toml            # Project metadata and tool config
├── requirements.txt          # Python dependencies
├── main.py                   # FastAPI app entry point (lifespan, CORS, router registration)
├── constants.py              # Shared constants (questions, fields, stop words, emoji maps)
│
├── api/                      # FastAPI route handlers
│   ├── __init__.py
│   └── routes/
│       ├── __init__.py
│       ├── telegram.py       # Telegram webhook handler
│       ├── whatsapp.py       # WhatsApp webhook handler
│       └── test.py           # Direct test endpoint
│
├── services/                 # Shared business logic
│   ├── __init__.py
│   ├── graph_runner.py       # invoke_graph() — DRY graph invocation
│   └── supabase.py           # Supabase client and database queries
│
├── integrations/             # Platform-specific adapters
│   ├── __init__.py
│   ├── telegram/
│   │   ├── __init__.py
│   │   ├── client.py         # send_message() via Telegram API
│   │   └── parser.py         # extract_message_data(), is_bot_mentioned(), build_thread_id()
│   ├── whatsapp/
│   │   ├── __init__.py
│   │   ├── client.py         # send_whatsapp_message() via Evolution API
│   │   └── parser.py         # extract_whatsapp_message()
│   └── elevenlabs/
│       ├── __init__.py
│       └── stt.py            # transcribe_audio() — single STT function for all platforms
│
├── graph/ (src/)             # LangGraph orchestration
│   ├── config.py             # LLM initialization, memory, thread config
│   ├── graph.py              # build_graph() — state machine builder
│   ├── nodes.py              # All node functions (intent, greeting, report, etc.)
│   ├── routers.py            # Conditional routing logic
│   ├── schema.py             # Pydantic extraction schemas
│   └── state.py              # ReportState TypedDict
│
├── scripts/
│   └── generate_diagram.py   # Generate LangGraph workflow diagram
│
└── frontend/                 # WhatsApp simulator
    ├── index.html
    ├── styles.css
    └── app.js
```

## Development

### Linting and Type Checking

```bash
pip install ".[dev]"
ruff check .
mypy .
```

### Generate Diagram

```bash
python scripts/generate_diagram.py
```
