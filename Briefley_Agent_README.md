# Briefley — Full Project Context for AI Agent

## Who I Am & What I Want

I am Ahmed Saleem (`ahmedashsaleem` on GitHub), a junior AI/ML engineer based in Egypt, graduating from an ITI AI & Machine Learning Professional Track (1431-hour program). I hold a B.Sc. in Computer and Automatic Control Engineering from Tanta University and am pursuing an M.Sc.

**My goal with this project is purely career-focused.** I want Briefley to be a polished, impressive, live portfolio project that helps me land an AI/ML engineering role — locally in Egypt or internationally via remote. I have roughly 40 days. I am strong in ML/NLP and have limited DevOps experience. I know Django basics.

**I am not building a business.** I want the project live cheaply (free or near-free), open-source on GitHub, and impressive enough that a technical hiring manager or senior engineer stops and reads it.

---

## What the Project Is

**Briefley** is an Arabic/English AI news intelligence platform. It was originally built as a graduation project (documentation: `brifely.pdf`). The Python AI module is the part I own and am improving.

The system:
- Scrapes Arabic and English news from 20+ major outlets (BBC, CNN, Al Jazeera, Al-Masry Al-Youm, Al-Ahram, etc.)
- Classifies articles by language and topic
- Summarizes using fine-tuned transformer models (PEGASUS for English, AraBART for Arabic)
- Clusters related stories across sources using embeddings + UMAP + HDBSCAN
- (Planned) Ingests public Telegram news channels and verifies them against the article corpus
- (Planned) Powers a RAG chatbot grounded in verified news

---

## Current State of the Codebase

GitHub repo: `ahmedashsaleem/brifley` (public)

### Files That Exist and Work

**`scraping.py` + `BrowserInit.py` + `responce_init.py`**
- Hybrid scraper: `requests` + rotating fake browser headers via ScrapeOps API for simple sites; Selenium fallback for JS-heavy sites
- Uses `Goose3` for article content extraction (cleaned text, title, main image)
- Covers 20+ Arabic and English outlets

**`classifier.py`**
- Language detection via `langdetect`
- Pre-trained sklearn TF-IDF pipeline (CountVectorizer + TfidfTransformer + classifier) loaded from local `.pkl` files
- 7 categories: culture, finance, medical, politics, religion, sports, tech
- Separate pipelines for Arabic and English

**`summarizer.py`**
- Abstractive summarization using locally stored fine-tuned models
- **PEGASUS** (fine-tuned on XLSum English, ~330k rows) for English → deployed at `a7mid/EnglishSummarization` on HuggingFace
- **AraBART** (`moussaKam/AraBART` fine-tuned on XLSum Arabic, 46,897 rows) for Arabic → deployed at `a7mid/ArabicSummarization` on HuggingFace
- Models loaded from local directories `./arabic` and `./english` (NOT from HuggingFace Hub at runtime, due to Egyptian payment restrictions blocking cloud APIs at time of original development)

**`clustering.py`**
- Embeds article summaries using `distiluse-base-multilingual-cased-v1` SentenceTransformer (loaded locally from `./embadder/`)
- Dimensionality reduction: UMAP (n_components=2, n_neighbors=100, min_dist=0.02)
- Clustering: HDBSCAN (min_cluster_size=2, cluster_selection_epsilon=8.54187817e-12)
- The epsilon value was empirically tuned in a separate notebook — it is NOT a magic number
- Articles with label `-1` are noise — intentionally filtered out
- Returns dict mapping article IDs to cluster labels

**`item.py`**
- `paragraph` class orchestrating: scrape → clean → classify → summarize for one URL

**`main.py`**
- Entry point, currently half-commented out
- Has a commented-out FastAPI endpoint stub

### Known Bugs That Must Be Fixed Before New Features

1. **SECURITY — hardcoded API key**: ScrapeOps API key is hardcoded in `responce_init.py` and `BrowserInit.py` in a public GitHub repo. Must be rotated and moved to environment variables immediately.

2. **Silent classifier failure**: In `classifier.py`, `englishCategories` dict has two empty string keys `''` — one for 'Medical' and one for 'Religion'. These categories silently fail on every English article. Fix the keys to `'health'` and `'religion'` (verify against actual sklearn label strings first).

3. **Model reloading on every call**: `summarizer.py` and `clustering.py` reload models from disk on every single invocation. Catastrophically slow in production. Refactor to module-level singletons using `functools.lru_cache` or a simple global pattern — loaded once when the process starts.

4. **Epsilon not documented**: Add a comment explaining the HDBSCAN epsilon value and expose it as a configurable parameter.

5. **Project not runnable by anyone else**: No `requirements.txt`, no `.env.example`, no setup instructions. Must be fixed for open-source use.

---

## The Fine-Tuned Models — Critical Context

Both models were fine-tuned on XLSum (BBC multilingual dataset, Hasan et al. 2021):

### Arabic — AraBART (`moussaKam/AraBART`)
- Fine-tuned on XLSum Arabic: **46,897 article-summary pairs**
- AraBART is the first Arabic model based on BART with encoder and decoder both pre-trained end-to-end on Arabic text
- Architecture: BART-Base, 6 encoder + 6 decoder layers, 768 hidden dimensions, **139M parameters**
- Chosen over PEGASUS and mBART because it outperforms on ROUGE-L and ROUGE-Lsum for Arabic news — these metrics measure sentence-level coherence across the whole text, most relevant for news summarization
- Reference benchmark: AraBART fine-tuned on AHS dataset achieved ROUGE-1=55, ROUGE-2=40.15, ROUGE-L=54.55, BLEU=56.26, BERTScore=88.06
- **Deployed at: `a7mid/ArabicSummarization` on HuggingFace Hub**

### English — PEGASUS (`google/pegasus-large`)
- Fine-tuned on XLSum English: **~330,000 article-summary pairs**
- PEGASUS pre-trains with Gap Sentence Generation (GSG) — entire sentences are masked and model reconstructs them from remaining text, structurally identical to summarization
- Chosen because it outperforms BART-large on CNN/DailyMail and XSum benchmarks; PEGASUS-Large reports best ROUGE-1 and ROUGE-2 among compared models
- **Deployed at: `a7mid/EnglishSummarization` on HuggingFace Hub**

### Using HuggingFace Models for Validation
Both fine-tuned models are now available on HuggingFace Hub (`a7mid/EnglishSummarization` and `a7mid/ArabicSummarization`). These should be used to:
1. Validate fine-tuning results in the cleaned notebook (load from Hub for evaluation)
2. Replace local directory loading in the pipeline (cleaner, more portable)
3. Generate baseline vs fine-tuned ROUGE score comparisons

---

## The Summarization Notebook — Current Status & What Needs Doing

A notebook (`Text_Summarization__1_.ipynb`) exists but has serious problems:
- **Dataset mismatch**: Loaded XLSum but used SAMSum column names (`dialogue` instead of `text`)
- **Trained on test split**: `train_dataset=dataset["test"]` — this is a critical bug
- **No base model comparison**: Cannot claim improvement without before/after ROUGE scores
- **Version conflicts on Kaggle**: Several dependency issues already debugged (see below)

### Kaggle Dependency Issues Already Solved
The notebook runs on Kaggle (GPU T4). These issues were encountered and resolved:

**Issue 1 — peft/accelerate conflict:**
```
ImportError: cannot import name 'clear_device_cache' from 'accelerate.utils.memory'
```
**Fix:** Upgrade both together, then restart kernel:
```python
%%capture
!pip install -q --upgrade peft accelerate
```
Then: Run → Restart & Run All. Do not skip the restart.

**Issue 2 — eval_strategy not recognized:**
```
TypeError: Seq2SeqTrainingArguments.__init__() got an unexpected keyword argument 'eval_strategy'
```
**Fix:** In `transformers==4.40.0`, use `"evaluation_strategy"` not `"eval_strategy"`.

**Issue 3 — CUDA kernel image error with fp16:**
```
AcceleratorError: CUDA error: no kernel image is available for execution on the device
```
**Fix:** Set `"fp16": False` in TRAIN_CONFIG. Kaggle T4 has a PyTorch/CUDA version mismatch when fp16 mixed precision is enabled. Training without fp16 works correctly.

### What the Cleaned Notebook Should Do
A refactored notebook has been written and is the current working version. It should:
1. Install only what Kaggle doesn't have (`rouge_score`, `evaluate`, `sentencepiece`) — do NOT pin torch/transformers/accelerate/peft versions
2. Single `LANGUAGE` toggle: `"english"` or `"arabic"` switches everything automatically
3. Load the HuggingFace Hub models (`a7mid/EnglishSummarization`, `a7mid/ArabicSummarization`) for validation/evaluation
4. Correct dataset: XLSum with `"text"` and `"summary"` columns (not `"dialogue"`)
5. Correct split: `train_dataset=tokenized["train"]` (not test)
6. Base model vs fine-tuned ROUGE comparison with bar chart visualization
7. `"fp16": False` in training config
8. `"evaluation_strategy": "steps"` (not `"eval_strategy"`)
9. Qualitative examples: article → reference summary → generated summary
10. Save ROUGE results as CSV

---

## Roadmap — What to Build Next (Prioritized)

### Priority Order (Agreed)
The order is forced by dependencies — each step enables the next:

```
1. Fix existing bugs (security + classifier + model caching)
2. Qdrant vector DB  ← foundation everything else needs
3. Telegram ingestion
4. Ground-truth verification filter  ← the differentiator
5. RAG chatbot  ← almost free once Qdrant exists
6. Streamlit demo UI  ← the live demo for the CV
7. Clean GitHub README + fine-tuning notebooks visible
```

### Step 1: Qdrant Vector Database
- Self-hosted Qdrant as Docker container
- After pipeline summarizes + clusters an article, embed it and store in Qdrant
- Use the **same** `distiluse-base-multilingual-cased-v1` embeddings already generated in clustering.py — do NOT introduce a second embedding model
- Each Qdrant point payload: article title, source name, category, language, cluster ID, publication timestamp, summary text
- Collection name: `articles`, embedding dim: 512

### Step 2: Telegram Channel Ingestion
- Use `Telethon` (MTProto API, NOT the Bot API — Bot API can't read channels)
- Server-side catalogue of curated public Arabic/English news Telegram channels
- Users do NOT connect their own Telegram accounts — they pick from the server's curated list
- Telethon requires interactive first login (phone + SMS code) — done once manually on server, creates `.session` file, runs headlessly after
- Store each message: message_id, channel name, text, timestamp
- After storing, immediately queue for ground-truth verification

### Step 3: Ground-Truth Verification Filter (The Core Differentiator)
This is the most original part of the project. The concept: verified clustered articles from established outlets = "ground truth". Every Telegram message is measured against this.

**Three labels:**
- `CORROBORATED` (similarity ≥ 0.75): Story verified by mainstream media → attach to cluster
- `NOVEL` (0.45–0.75): Possibly new developing story not yet in mainstream media
- `ORPHAN` (< 0.45): No corroboration → potential misinformation signal or noise

**Implementation:**
1. Embed Telegram message using same SentenceTransformer
2. Cosine similarity search against Qdrant article index
3. Assign label based on top similarity score
4. Store label + matched cluster ID + similarity score with the message

Thresholds (0.75, 0.45) are configurable — not hardcoded — they need tuning on real data.

This turns the existing cluster index into a live noise/misinformation detection signal. This framing must be clearly explained in the README and demo.

### Step 4: RAG Chatbot
- Query: user question → embed → Qdrant similarity search → top-k article summaries as context → LLM API call → answer with source citations
- LLM: Use an **API** (not local LLM) — Together.ai preferred (free tier, supports Llama 3.1 which has strong Arabic support)
- LLM provider configurable via environment variable (swap to OpenAI/Anthropic without code change)
- Works in both Arabic and English
- Answers must cite which articles/sources they are grounded in

### Step 5: Streamlit Demo UI
- Single Streamlit app — deployed **free on Streamlit Cloud** (requires public GitHub repo — already the case)
- Stays live indefinitely as long as repo is public — perfect for a portfolio project with no ongoing cost

**Three panels:**
1. **Today's story clusters**: Top clusters from last 24h, same story from multiple sources side by side — demonstrates bias-awareness feature
2. **Telegram feed with trust labels**: Recent messages with CORROBORATED/NOVEL/ORPHAN labels, color coded green/yellow/red
3. **RAG chatbot**: Chat interface, sourced answers

Add a sidebar explaining each component — the demo viewer may not be technical.

### Step 6: Open-Source Polish
- Clean public GitHub README with: description, architecture diagram, ML model details with fine-tuning results, how to run locally, environment variable reference, future roadmap
- `.env.example` listing all required variables
- `requirements.txt`
- MIT license
- Fine-tuning notebooks under `/notebooks` — cleaned, with ROUGE scores visible
- HDBSCAN epsilon tuning notebook under `/notebooks`
- The README should position this as: multilingual Arabic/English news intelligence, fine-tuned models, vector search, RAG, and the original Telegram ground-truth verification concept

---

## Architecture Diagram

```
[ News Websites (20+) ]
        ↓
  scraping.py (requests + Selenium)
        ↓
  classifier.py (langdetect + TF-IDF sklearn)
        ↓
  summarizer.py (PEGASUS / AraBART — fine-tuned, loaded from HuggingFace)
        ↓
  clustering.py (SentenceTransformer → UMAP → HDBSCAN)
        ↓
  Qdrant (vector store — embeddings + article metadata)
        ↑
[ Telegram Channels (public, curated list) ]
        ↓
  Telethon ingestion
        ↓
  embed → cosine similarity vs Qdrant articles
        ↓
  label: CORROBORATED / NOVEL / ORPHAN
        ↓
  Qdrant (telegram_messages collection)

  Qdrant ← RAG Query → Together.ai LLM API → Answer + Citations

  Streamlit UI (free on Streamlit Cloud)
    - Story clusters view
    - Telegram trust-labeled feed
    - RAG chatbot
```

---

## Deployment Constraints

- **No budget for expensive compute** — free tiers only
- **Egyptian payment restrictions** limit access to some paid APIs — prefer free tiers
- **Models are on HuggingFace Hub** at `a7mid/EnglishSummarization` and `a7mid/ArabicSummarization` — use these, not local directories
- **Streamlit Cloud** is free for public repos — this is the demo deployment target
- **Qdrant** can run locally or on a cheap VPS (Hetzner CX22, €4.35/month, is sufficient)
- **Together.ai** has a free tier and supports Llama 3.1 with Arabic capability — preferred LLM API for RAG
- Heavy models (PEGASUS, AraBART, SentenceTransformer) are loaded for inference only — no GPU needed at demo time, just for training

---

## What This Project Is NOT

- Not a business, not a startup
- Not implementing user authentication or personalized accounts (future v2 idea — mention in README only)
- Not connecting users' personal Telegram accounts (future v2 — mention in README only)
- The social network / following feature is out of scope — mention as future work only
- No Django — Streamlit is the demo UI, not a full web framework

---

## CV / Portfolio Impact Assessment

Current state without improvements: **5.5/10**
- Ideas are strong (7/10), but visible execution is weak (4/10)
- Fine-tuning work is invisible (notebooks not in repo)
- Code has security issues (live API key) and silent bugs

With all planned improvements: **~8.5/10**

Score breakdown:
| Component | Impact |
|---|---|
| Clean code + bug fixes | +0.5 |
| Fine-tuning notebooks visible with ROUGE metrics | +1.5 |
| Good README with architecture + reasoning | +0.5 |
| Qdrant + RAG + Telegram ground-truth filter | +0.5 |
| Live Streamlit demo | +0.5 |

The fine-tuning notebooks are the single highest-impact thing — it's the most impressive ML work done and currently completely invisible.

The Telegram ground-truth filter is the architectural differentiator — no open-source project does this. Clearly explain the concept in README and demo.

---

## Git Branching Strategy — Important

**Do not work on `main` directly.**

Before touching any code, create a branch:

```bash
git checkout -b feature/pipeline-refactor
```

Do all work on this branch. Reasons:
- `main` stays clean and is always the live version visible on Ahmed's CV
- If anything breaks badly the branch can be deleted with nothing lost
- A clean git history with meaningful branch names looks professional to employers

When a step is fully working and tested, merge back:

```bash
git checkout main
git merge feature/pipeline-refactor
git push
```

If the work spans multiple steps, sub-branches are fine too (e.g. `feature/qdrant`, `feature/telegram`) — merge each into `feature/pipeline-refactor` as you go, then merge the whole thing to `main` at the end.

---

## My Ask From the Agent

Help me build this step by step, starting with **fixing the known bugs**, then **Step 1 (Qdrant integration)**.

For each step:
- Explain what we are doing and why before writing code
- Write clean, well-commented, production-quality code
- Tell me what to install and how to run it
- Point out anything that could break given my constraints (HuggingFace Hub models, Egypt payment restrictions, free tier deployments, Kaggle for training)
- Do not over-engineer — this is a portfolio project, not a production system
- When working on the Kaggle notebook: always set `"fp16": False`, use `"evaluation_strategy"` not `"eval_strategy"`, and do not pin torch/transformers/accelerate/peft versions — let Kaggle's pre-installed versions handle those, only install `rouge_score`, `evaluate`, and `sentencepiece`
