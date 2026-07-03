# AI-Powered Transaction Processing Pipeline

A backend API that processes CSV transaction files asynchronously through a job queue, uses an LLM to classify transactions and flag anomalies, and generates a structured summary report.

## Tech Stack

- **API**: FastAPI
- **Database**: PostgreSQL
- **Job Queue**: Celery + Redis
- **LLM**: Google Gemini 2.0 Flash
- **Containerisation**: Docker + Docker Compose

## Quick Start

1. Clone the repo:
   ```bash
   git clone https://github.com/tanmayjoddar/Alemeno.git
   cd Alemeno
   ```

2. Copy the env example and add your Gemini API key:
   ```bash
   cp .env.example .env
   # Edit .env and set GEMINI_API_KEY=your_key
   ```
   Get a free key at: https://aistudio.google.com/apikey

3. Start everything with a single command:
   ```bash
   docker compose up --build
   ```

4. The API will be available at `http://localhost:8000`

## API Endpoints

### Upload CSV
```bash
curl -X POST http://localhost:8000/jobs/upload \
  -F "file=@transactions.csv"
```

### Check Job Status
```bash
curl http://localhost:8000/jobs/1/status
```

### Get Full Results
```bash
curl http://localhost:8000/jobs/1/results
```

### List All Jobs
```bash
curl http://localhost:8000/jobs
curl "http://localhost:8000/jobs?status=completed"
```

### Health Check
```bash
curl http://localhost:8000/health
```

## Project Structure

```
├── app/
│   ├── api/
│   │   └── jobs.py          # API endpoints
│   ├── services/
│   │   ├── cleaning.py       # CSV parsing & data cleaning
│   │   ├── anomalies.py      # Anomaly detection logic
│   │   └── llm_client.py     # Gemini LLM client
│   ├── main.py               # FastAPI app entry point
│   ├── config.py             # Environment configuration
│   ├── database.py           # SQLAlchemy setup
│   ├── models.py             # ORM models
│   ├── schemas.py            # Pydantic schemas
│   ├── celery_app.py         # Celery configuration
│   └── tasks.py              # Async task pipeline
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.celery
└── requirements.txt
```

## Processing Pipeline

1. **Upload** → CSV validated, Job created (status=pending), task enqueued
2. **Data Cleaning** → Normalise dates, strip currency symbols, uppercase status, fill missing categories, remove exact duplicates
3. **Anomaly Detection** → Statistical outliers (>3x account median), domestic-only merchants with USD transactions
4. **LLM Classification** → Uncategorised transactions classified via Gemini into predefined categories
5. **LLM Narrative Summary** → Single LLM call generates spend summary, top merchants, risk level
6. **Retry Logic** → Failed LLM calls retried 3x with exponential backoff

## Sample Output

### Job Status (completed)
```json
{
  "job_id": 1,
  "status": "completed",
  "summary": {
    "row_count_raw": 95,
    "row_count_clean": 85,
    "anomaly_count": 5,
    "total_spend_inr": 1339923.0,
    "total_spend_usd": 74185.14,
    "risk_level": "medium"
  }
}
```

### Anomalies Detected
| txn_id | Merchant | Amount | Account | Reason |
|--------|----------|--------|---------|--------|
| TXN2000 | Jio Recharge | ₹175,917.65 | ACC002 | 3x account median |
| TXN2001 | Flipkart | ₹146,100.68 | ACC005 | 3x account median |
| TXN2002 | Ola | ₹91,185.10 | ACC001 | 3x account median |
| TXN2003 | IRCTC | ₹193,647.29 | ACC002 | 3x account median |
| TXN2004 | IRCTC | ₹191,918.37 | ACC003 | 3x account median |

### Data Cleaning Summary
- **95 raw rows** ingested
- **10 duplicate rows** removed
- **85 clean rows** stored
- Dates normalised to ISO 8601, `$` prefixes stripped, status values uppercased, blank categories filled as "Uncategorised"
