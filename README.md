# ORACLE - AI Investment Intelligence Dashboard

AI-powered investment intelligence system that aggregates market data, technical indicators, sentiment analysis, macroeconomic context, and portfolio tracking into an explainable decision-support dashboard.

**This system does NOT execute trades or provide financial advice.**

## Architecture

- **Frontend**: Next.js 15 + Tailwind CSS 4 + Recharts
- **Backend**: Python + FastAPI + WebSockets
- **Database**: Supabase (PostgreSQL)

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API available at http://localhost:8000. Docs at http://localhost:8000/docs.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard available at http://localhost:3000.

## Configuration

Copy the example env files and fill in your credentials:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
```

## Disclaimer

ORACLE does not provide financial advice. All outputs are for decision support and informational purposes only. Users retain full control over their investment decisions.
