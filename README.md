# Ghanex Tech GenAI & Open-Source Developer Intern Assessment

Three independent Streamlit applications built with Python, the Groq API and free public APIs, plus an open-source contribution.

| Task | Folder | What it does |
|------|--------|--------------|
| 1 | [`task1-rag`](./task1-rag) | PDF question answering with retrieval-augmented generation and page-level citations |
| 2 | [`task2-agent`](./task2-agent) | Chat agent that decides when to call a calculator, weather, Wikipedia or currency tool |
| 3 | [`task3-github-analyzer`](./task3-github-analyzer) | GitHub repository analyzer with metrics, an AI review and contribution ideas |

Each folder is self-contained with its own `requirements.txt`, `.env.example`, tests and README, so each can be deployed on its own.

## Live demos

| Task | Live app |
|------|----------|
| 1. PDF Document Assistant (RAG) | https://task1-pdf-assistant.streamlit.app/ |
| 2. Tool-Calling AI Agent | https://task2-ai-agent.streamlit.app/ |
| 3. GitHub Repository AI Analyzer | https://task3-repo-analyzer.streamlit.app/ |

If an app is asleep, open it and click the wake-up button. Apps on the free tier need a few seconds to start, and the RAG app downloads its embedding model on the first run.

## Repository layout

```
.
├── README.md
├── SUBMISSION.md
├── task1-rag/
│   ├── app.py
│   ├── rag/
│   └── tests/
├── task2-agent/
│   ├── app.py
│   ├── agent/
│   └── tests/
└── task3-github-analyzer/
    ├── app.py
    ├── analyzer/
    └── tests/
```

## Shared technology choices

- **LLM:** Groq API with `openai/gpt-oss-120b` (free tier, native tool calling, JSON mode). Override with the `GROQ_MODEL` variable.
- **UI:** Streamlit, deployable to Streamlit Community Cloud.
- **Secrets:** read from environment variables or Streamlit secrets. No keys are committed.
- **Testing:** `pytest` suites run offline using fake LLM clients and fake HTTP sessions, so they need no network or API key.

## Quick start

```bash
cd task1-rag
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python -m pytest
streamlit run app.py
```

Replace `task1-rag` with `task2-agent` or `task3-github-analyzer` for the other projects. Get a free Groq key at https://console.groq.com.

## Deploying on Streamlit Community Cloud

1. Push this repository to GitHub as a public repository.
2. On https://share.streamlit.io choose New app and select the repository.
3. Set the main file path to `task1-rag/app.py`, `task2-agent/app.py` or `task3-github-analyzer/app.py`. Create one app per task.
4. Under Advanced settings, add secrets in TOML form:

```toml
GROQ_API_KEY = "your_key"
GITHUB_TOKEN = "optional_for_task_3"
```

5. Deploy. Streamlit installs the `requirements.txt` found next to the main file.
