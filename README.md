# Dossier Agent

An AI-powered research agent that generates structured dossiers on people or companies, with risk analysis and key facts. Run as a Streamlit web app or via the command line.

---

## Features
- **Automated Research**: Uses LLMs and web search tools to gather and analyze information.
- **Structured Reports**: Produces a dossier with overview, key facts, risk level, and confidence score.
- **Flexible Interface**: Run interactively in a web browser (Streamlit) or from the command line.
- **Configurable Workflow**: Modular agent graph with customizable nodes and logic.

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set up environment variables
Copy `.env.example` to `.env` and fill in your API keys:
```bash
cp .env.example .env
```
- `GROQ_API_KEY`: For LLM access
- `TAVILY_API_KEY`: For web search

### 3. Run the agent
- **Web app:**
  ```bash
  streamlit run app.py
  ```
- **Command line:**
  ```bash
  python run.py "Elon Musk"
  ```

---

## Project Structure

```
Dossier/
├── app.py            # Streamlit web app entry point
├── run.py            # CLI entry point
├── requirements.txt  # Python dependencies
├── .env.example      # Example environment variables
├── agent/
│   ├── __init__.py
│   ├── config.py     # All config/constants
│   ├── graph.py      # Agent workflow graph
│   ├── nodes.py      # Node implementations (intake, planner, tools, etc.)
│   ├── state.py      # State and report schemas
│   └── tools.py      # Web search and risk tools
└── outputs/          # Generated reports (gitignored)
```

---

## How It Works
- **Workflow**: The agent runs through a series of nodes (intake, planning, search, grading, enrichment, writing) defined in `agent/graph.py` and `agent/nodes.py`.
- **State**: All data is tracked in a central `AgentState` (see `agent/state.py`).
- **Tools**: Web search and risk analysis are handled via LangChain and Tavily (see `agent/tools.py`).
- **Config**: All settings and thresholds are in `agent/config.py`.

---

## Requirements
- Python 3.9+
- API keys for Groq (LLM) and Tavily (web search)

---

