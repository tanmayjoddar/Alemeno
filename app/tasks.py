import json
import time
from datetime import datetime, timezone

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Job, Transaction, JobSummary
from app.services.cleaning import parse_csv, clean_transactions
from app.services.anomalies import detect_outliers, detect_domestic_usd
from app.services.llm_client import classify_transactions, generate_narrative_summary


def _update_job_status(job_id: int, status: str, error: str = None):
    db = None
    try:
        db = SessionLocal()
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = status
            if error:
                job.error_message = error
            if status in ("completed", "failed"):
                job.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        if db is not None:
            db.close()


@celery_app.task(bind=True, max_retries=3)
def process_csv(self, job_id: int, csv_content: str):
    db = None
    try:
        db = SessionLocal()
        _update_job_status(job_id, "processing")

        raw_rows = parse_csv(csv_content)
        job = db.query(Job).filter(Job.id == job_id).first()
        job.row_count_raw = len(raw_rows)
        db.commit()

        cleaned = clean_transactions(raw_rows)
        job.row_count_clean = len(cleaned)
        db.commit()

        cleaned = detect_outliers(cleaned)
        cleaned = detect_domestic_usd(cleaned)

        uncategorised = [t for t in cleaned if t["category"] == "Uncategorised"]
        if uncategorised:
            for attempt in range(3):
                try:
                    classify_transactions(uncategorised)
                    break
                except Exception:
                    if attempt < 2:
                        time.sleep(2 ** attempt)
                    else:
                        for t in uncategorised:
                            t["llm_failed"] = True

        for t in cleaned:
            db_txn = Transaction(
                job_id=job_id,
                txn_id=t.get("txn_id"),
                date=t["date"],
                merchant=t["merchant"],
                amount=t["amount"],
                currency=t["currency"],
                status=t["status"],
                category=t.get("llm_category", t["category"]),
                account_id=t["account_id"],
                is_anomaly=t.get("is_anomaly", False),
                anomaly_reason=t.get("anomaly_reason"),
                llm_category=t.get("llm_category"),
                llm_raw_response=None,
                llm_failed=t.get("llm_failed", False),
            )
            db.add(db_txn)
        db.commit()

        anomalies = [t for t in cleaned if t.get("is_anomaly")]
        total_inr = sum(t["amount"] for t in cleaned if t["currency"] == "INR")
        total_usd = sum(t["amount"] for t in cleaned if t["currency"] == "USD")

        merchant_totals: dict[str, float] = {}
        for t in cleaned:
            merchant_totals[t["merchant"]] = merchant_totals.get(t["merchant"], 0) + t["amount"]
        top_merchants = sorted(merchant_totals.items(), key=lambda x: -x[1])[:3]
        top_merchants_list = [{"merchant": m, "total": round(v, 2)} for m, v in top_merchants]

        narrative_data = None
        for attempt in range(3):
            try:
                narrative_data = generate_narrative_summary(
                    total_spend_inr=total_inr,
                    total_spend_usd=total_usd,
                    top_merchants=top_merchants_list,
                    anomaly_count=len(anomalies),
                    transactions_count=len(cleaned),
                )
                break
            except Exception:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    narrative_data = {
                        "narrative": "LLM narrative generation failed after retries.",
                        "risk_level": "medium",
                    }

        risk_level = narrative_data.get("risk_level", "low") if narrative_data else "low"
        narrative = narrative_data.get("narrative", "") if narrative_data else ""

        db_summary = JobSummary(
            job_id=job_id,
            total_spend_inr=round(total_inr, 2),
            total_spend_usd=round(total_usd, 2),
            top_merchants=json.dumps(top_merchants_list),
            anomaly_count=len(anomalies),
            narrative=narrative,
            risk_level=risk_level,
        )
        db.add(db_summary)
        db.commit()

        _update_job_status(job_id, "completed")

    except Exception as e:
        if db is not None:
            db.rollback()
        _update_job_status(job_id, "failed", str(e))
        raise
    finally:
        if db is not None:
            db.close()
