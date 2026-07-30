# VerifPay 🛡️

**AI-Powered Financial Fraud & Scam Detection for Indian Consumers**

> Built for American Express Codestreet 2026 | HackerEarth

## What is VerifPay?

VerifPay detects fake UPI requests, phishing links, fraudulent bank messages, and financial scams **before you click or share details**. Paste any suspicious message and get an instant AI-powered verdict with a plain-language explanation.

## Architecture

- **ML Ensemble**: 5-model scikit-learn classifier (Random Forest, SVM, Gradient Boosting, Logistic Regression, Naive Bayes)
- **RAG Pipeline**: ChromaDB + sentence-transformers for matching known fraud patterns
- **LLM Explainer**: Groq Llama 3.3 70B for generating plain-language fraud explanations
- **Voice Input**: Groq Whisper for transcribing scam call recordings
- **URL Checking**: PhishTank + Google Safe Browsing API

## Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/imkoushal/verifpay.git
cd verifpay
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 2. Configure environment
copy .env.example .env
# Fill in your API keys in .env

# 3. Train ML models
python scripts/train_models.py

# 4. Run the server
uvicorn app.main:app --reload

# 5. Open API docs
# http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install

# Point the app at your backend
copy .env.example .env   # then set VITE_API_URL (default http://localhost:8000)

npm run dev      # http://localhost:5173
npm run build    # production bundle in frontend/dist
```

> The backend already allows `http://localhost:5173` via CORS. For any other
> origin, set `FRONTEND_URL` in the backend `.env`.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service health check |
| `POST` | `/analyse` | Analyse text/URL for fraud |
| `POST` | `/voice` | Transcribe + analyse voice note |
| `GET` | `/stats` | Analysis statistics |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Groq Llama 3.3 70B |
| Speech-to-Text | Groq Whisper |
| ML | scikit-learn 5-model ensemble |
| RAG | LangChain + ChromaDB |
| Backend | FastAPI + Python 3.11 |
| Frontend | React + Tailwind CSS |
| Database | PostgreSQL |
| Deployment | Docker + Render + Vercel |

## Built By

**Koushal Kishor Ray** — AI Engineer

---

*Domain pivot of [VerifAI](https://github.com/imkoushal/fake-news-detector-ai) (96.46% accuracy)*
