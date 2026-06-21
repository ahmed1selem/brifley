# 🧠 Briefley — Multilingual News Intelligence Engine

**Briefley** is the Python AI engine behind an AI-powered news platform. It scrapes news from 20+ Arabic & English outlets, summarizes and classifies articles, clusters the same story across sources for bias/coverage comparison, and answers questions through an **agentic RAG** assistant. The wider product also has a .NET backend and a React frontend (built by other team members); **this repository is the Python intelligence engine.**

---

## ✨ What it does

- **Scraping (20+ AR/EN sources)** — `requests`, `BeautifulSoup`, `Selenium`, and `Goose3`, plus a Telegram ingestor (Telethon), on a periodic refresh loop.
- **Abstractive summarization** — **PEGASUS** for English (ROUGE-1 ≈ 30.3 on held-out data) and **AraBART** for Arabic.
- **News classification** — a **nearest-centroid classifier** over multilingual Sentence-Transformer embeddings (`distiluse-base-multilingual-cased-v1`): each article is assigned to the topic whose category centroid is closest by cosine similarity.
- **Cross-source clustering** — **Agglomerative clustering** (cosine distance, average linkage) *within each category*, grouping different outlets' coverage of the same event so readers can compare headlines, tone, and framing.
- **Agentic RAG assistant** — a local **Llama-3.2** model (via Ollama) with **native tool-calling** over three skills: Qdrant vector search, news-cluster lookup, and Wikipedia. Answers are grounded and source-cited.
- **Serving** — a **FastAPI** service exposing the engine, with a lightweight static frontend and Docker Compose.

---

## 🛠 Tech Stack

| Layer | Tools |
| --- | --- |
| Summarization | PEGASUS (EN), AraBART (AR) |
| Classification | Nearest-centroid + Sentence-Transformers (DistilUSE multilingual) |
| Clustering | Agglomerative (cosine, average linkage) |
| Agentic RAG | Ollama Llama-3.2 (tool-calling), Qdrant, Wikipedia |
| Scraping | requests, BeautifulSoup, Selenium, Goose3, Telethon |
| Serving | FastAPI, Uvicorn, Docker Compose |

---

## 📦 Scope

This repository contains the **Python intelligence engine** only. The database/personalization layer (.NET backend) and the web UI (React frontend) are maintained by other team members and are not included here.
