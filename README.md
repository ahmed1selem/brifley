# 🧠 Briefley: AI-Powered News Summarization & Comparison Engine (Python Module)

**Briefley** is an AI-driven backend system designed to enhance the way users consume and analyze news. This Python module handles news extraction, summarization, categorization, and clustering — making it easier to compare coverage across sources and detect biases.

While the full system integrates with a .NET backend and database, this repo focuses on the core **Python-powered intelligence engine**.

---

## 🌍 What It Does

- **Fetches News from 20+ Global Agencies**  
  Scrapes articles (both English & Arabic) from top news outlets using `requests`, `BeautifulSoup`, and `Selenium`. The system runs every 5 minutes, ensuring fresh content is always available.

- **Abstractive Summarization**  
  Automatically condenses long articles using:
  - 🟣 **PEGASUS** for English articles
  - 🟢 **Arabic BART** for Arabic content

- **Categorizes Articles into Topics**  
  Articles are classified into 5 main categories:
  - 📰 Politics
  - ⚽ Sports
  - 💰 Economy
  - 🎭 Entertainment
  - 🏥 tech

  Categorization is done using two ML models:  
  - **Decision Trees**  
  - **Naive Bayes**

- **Groups Similar Stories Together**  
  To detect multiple perspectives on the same event, Briefley clusters news stories using:
  - **Sentence Transformers** for embeddings  
  - **DBSCAN** for density-based clustering

- **Supports Bias Awareness**  
  For each news story, the system identifies alternate versions from different agencies — letting users compare headlines, tone, and narrative.

---

## 🛠 Tech Stack & Components

| Component         | Details                                |
|------------------|----------------------------------------|
| Language          | Python                                 |
| Summarizers       | PEGASUS, Arabic BART                   |
| Categorization    | Decision Trees, Naive Bayes            |
| Clustering        | DBSCAN + Sentence Transformer Embeddings |
| Scraping Tools    | BeautifulSoup, Requests, Selenium      |
| Scheduling        | Runs every 5 minutes (custom loop)     |
| Backend Interface | REST API for .NET backend integration  |

> **Note:** This module **interacts with the backend database via API** — the DB and user personalization system are managed by the backend (.NET) team.

---

## 📦 What's Not Included

This repo **only contains the Python side** of the project. It does **not** include:
- The database schema or implementation
- User personalization features (handled in the backend)
- The frontend interface

---

## 🚀 Coming Soon / Ideas

- Interactive architecture diagram
- CLI / API usage guide
- Model benchmarking results
- Installation & dev setup instructions

---
