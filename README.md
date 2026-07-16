# 🧬 LabSafe Mom

> Laboratory Safety for Expecting Researchers

AI-powered risk assessment of laboratory protocols for **pregnant**, **trying-to-conceive**, and **breastfeeding** researchers.

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- OpenAI API Key

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env — set your OPENAI_API_KEY
```

### 2. Start All Services

```bash
docker-compose up -d
```

This starts:
- **PostgreSQL** on port `5432`
- **FastAPI Backend** on port `8000`
- **Next.js Frontend** on port `3000`

### 3. Open the App

Visit **http://localhost:3000**

---

## Without Docker (Development)

### Backend

```bash
cd backend
pip install -r requirements.txt
# Set environment variables
export DATABASE_URL=postgresql://labsafe:labsafe_secret@localhost:5432/labsafe
export OPENAI_API_KEY=sk-your-key
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Project Structure

```
LabSafeMom/
├── frontend/                    # Next.js + TypeScript + Tailwind
│   └── src/
│       ├── app/                 # App Router pages
│       │   ├── page.tsx         # Home / Upload
│       │   ├── analysis/[id]/   # Analysis progress
│       │   └── report/[id]/     # Report view
│       ├── components/          # Reusable components
│       └── lib/                 # API client + types
├── backend/                     # Python FastAPI
│   └── app/
│       ├── api/routes/          # REST API endpoints
│       ├── services/            # Business logic
│       ├── models/              # SQLAlchemy ORM
│       ├── schemas/             # Pydantic schemas
│       └── db/                  # DB connection + seed data
├── docker-compose.yml
└── .env.example
```

---

## Features

- 📁 **File Upload** — PDF, DOCX, TXT
- 🔬 **Substance Detection** — 8 categories of hazardous materials
- 👩‍🔬 **Population-Specific Risk** — Pregnancy, Fertility, Lactation
- 🛡️ **Safety Recommendations** — PPE and precaution suggestions
- 📊 **Structured Reports** — Printable risk assessment reports
- 🗄️ **Local Risk Database** — 100+ pre-seeded common lab hazards

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/upload` | Upload protocol file |
| POST | `/api/v1/analyze/{id}` | Start analysis |
| GET | `/api/v1/analyze/{id}/status` | Check analysis status |
| GET | `/api/v1/report/{id}` | Get full report |
| GET | `/api/v1/substances` | Search risk database |
| GET | `/api/v1/health` | Health check |

---

## Disclaimer

This software provides laboratory safety **reference only**. It does not replace professional occupational health consultation. Always consult your physician or institutional safety officer before making decisions based on this report.
