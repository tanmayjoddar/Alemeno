import json
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job, Transaction, JobSummary
from app.schemas import (
    JobResponse,
    JobStatusResponse,
    JobResultResponse,
    TransactionResponse,
    CategoryBreakdown,
    JobListResponse,
)
from app.tasks import process_csv

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/upload", status_code=201, response_model=JobResponse)
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only CSV files are allowed")

    content = await file.read()
    csv_text = content.decode("utf-8-sig")

    job = Job(filename=file.filename, status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)

    process_csv.delay(job.id, csv_text)

    return job


@router.get("/{job_id}/status", response_model=JobStatusResponse)
def get_job_status(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")

    summary_data = None
    if job.status == "completed" and job.summary:
        summary_data = {
            "row_count_raw": job.row_count_raw,
            "row_count_clean": job.row_count_clean,
            "anomaly_count": job.summary.anomaly_count,
            "total_spend_inr": job.summary.total_spend_inr,
            "total_spend_usd": job.summary.total_spend_usd,
            "risk_level": job.summary.risk_level,
        }

    return JobStatusResponse(job_id=job.id, status=job.status, summary=summary_data)


@router.get("/{job_id}/results", response_model=JobResultResponse)
def get_job_results(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")

    if job.status != "completed":
        raise HTTPException(400, f"Job is not completed (status: {job.status})")

    transactions = db.query(Transaction).filter(Transaction.job_id == job_id).all()
    anomalies = [t for t in transactions if t.is_anomaly]

    cat_totals: dict[str, dict] = {}
    for t in transactions:
        cat_totals.setdefault(t.category, {"count": 0, "total": 0.0})
        cat_totals[t.category]["count"] += 1
        cat_totals[t.category]["total"] += t.amount

    category_breakdown = [
        CategoryBreakdown(category=c, count=v["count"], total=round(v["total"], 2))
        for c, v in sorted(cat_totals.items())
    ]

    summary_data = None
    if job.summary:
        summary_data = {
            "total_spend_inr": job.summary.total_spend_inr,
            "total_spend_usd": job.summary.total_spend_usd,
            "top_merchants": json.loads(job.summary.top_merchants) if job.summary.top_merchants else [],
            "anomaly_count": job.summary.anomaly_count,
            "narrative": job.summary.narrative,
            "risk_level": job.summary.risk_level,
        }

    return JobResultResponse(
        job_id=job.id,
        status=job.status,
        transactions=[TransactionResponse.model_validate(t) for t in transactions],
        anomalies=[TransactionResponse.model_validate(t) for t in anomalies],
        category_breakdown=category_breakdown,
        summary=summary_data,
    )


@router.get("", response_model=list[JobListResponse])
def list_jobs(
    status: str = Query(None, pattern="^(pending|processing|completed|failed)?$"),
    db: Session = Depends(get_db),
):
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status)
    query = query.order_by(Job.created_at.desc())
    jobs = query.all()
    return [
        JobListResponse(
            id=j.id,
            filename=j.filename,
            status=j.status,
            row_count_raw=j.row_count_raw,
            created_at=j.created_at,
        )
        for j in jobs
    ]
