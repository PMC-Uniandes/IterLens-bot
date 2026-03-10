# IterLens - LangGraph Project

## Overview

IterLens is a conversational AI application built using LangGraph and FastAPI, designed to handle WhatsApp messages for reporting and managing machine failures in an industrial environment. The system uses a state graph to manage conversation flows, allowing users to report issues, list machines, confirm reports, and interact naturally through a WhatsApp-like interface.

## Features

- **Conversational AI**: Powered by LangGraph for managing complex conversation states and routing.
- **WhatsApp Integration**: Simulates WhatsApp webhook handling for message processing.
- **Machine Failure Reporting**: Users can report machine failures, list available machines, and confirm reports.
- **State Management**: Persistent conversation state using LangGraph's checkpointer.
- **Web Simulator**: Frontend simulator to test the WhatsApp-like interaction.
- **Supabase Integration**: Backend database integration for storing reports and data.

## Installation

### Prerequisites

- Python 3.8 or higher
- Node.js (for frontend development, optional)
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
   Create a `.env` file in the root directory with your configuration:

   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   MISTRAL_API_KEY=your_mistral_api_key
   ```

5. Run the application:

   ```bash
   python main.py
   ```

   The API will be available at `http://localhost:8000`.

## Usage

### Backend API

- **GET /**: Health check endpoint.
- **POST /webhook/whatsapp**: Webhook endpoint for WhatsApp messages.

Example request:

```json
{
  "from_number": "+56912345678",
  "body": "Hola, quiero reportar una falla"
}
```

### Frontend Simulator

Open `frontend/index.html` in your browser to simulate WhatsApp conversations. Configure the API URL and phone number, then send messages to test the LangGraph flow.

### Conversation Flow

The LangGraph handles various intents:

- Greeting: Responds to hello messages.
- Report Failure: Guides user through reporting a machine failure.
- List Machines: Shows available machines.
- List Failures: Shows failure types.
- Confirm/Cancel: Handles report confirmation.

## Project Structure

```
IterLens-langgraph/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── generate_diagram.py     # Script to generate LangGraph diagram
├── .gitignore             # Git ignore file
├── backend/
│   └── supabase.py        # Supabase database integration
├── frontend/
│   ├── index.html         # WhatsApp simulator HTML
│   ├── app.js             # Frontend JavaScript
│   └── styles.css         # Frontend styles
└── src/
    ├── config.py          # Configuration and memory setup
    ├── graph.py           # LangGraph definition
    ├── nodes.py           # Graph node implementations
    ├── routers.py         # Routing logic for graph edges
    ├── schema.py          # Data schemas
    └── state.py           # State definitions
```
