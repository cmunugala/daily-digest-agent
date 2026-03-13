# 📰 Daily Digest Agent

The **Daily Digest Agent** is a personalized AI-powered news assistant that researches topics of interest and generates concise, human-readable summaries. It intelligently classifies user queries, searches multiple sources (Arxiv, Hacker News, The Guardian), and maintains a history of "seen" articles to ensure you only get fresh content every day.

---

## ✨ Features

- **Multi-Source Research:**
  - 🎓 **Arxiv:** Latest research papers and breakthroughs.
  - 👨‍💻 **Hacker News:** Top tech and developer stories.
  - 🌍 **The Guardian:** Global news and current events.
- **Personalized History:** Tracks your past interests and "seen" articles across sessions using a PostgreSQL database.
- **Smart Filtering:** If you've already seen an article, the agent will dig deeper to find something new.

---

## 🛠️ Tech Stack

- **Agent Logic:** Python, OpenAI (GPT-4o-mini)
- **Deployment:** [FastAPI], [Streamlit],[Docker]
- **Database:** [PostgreSQL]
- **Package Manager:** [uv]

---

## 📂 Project Structure

```text
.
├── src/
│   ├── agent.py         # Main LLM orchestration logic
│   ├── api.py           # FastAPI endpoints
│   ├── database.py      # DB connection & initialization
│   ├── models.py        # SQLModel schema (User, Article, Interest)
│   ├── streamlit.py     # Streamlit UI
│   └── tools.py         # Search tool implementations (Arxiv, HN, Guardian)
├── docker-compose.yaml  # Infrastructure orchestration
├── Dockerfile           # App container definition
└── pyproject.toml       # Dependencies & metadata
```

---

## 📖 Usage

1.  Open the **Streamlit** interface.
2.  Enter your **Username** in the sidebar. This allows the agent to track your reading history.
3.  Ask a question or provide a topic (e.g., *"What's new in Quantum Computing?"* or *"Latest breakthroughs in React"*).
4.  The agent will research, filter out anything you've seen before, and generate a personalized digest for you.

