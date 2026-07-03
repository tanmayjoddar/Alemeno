import re
import csv
import io
from datetime import datetime


def parse_date(date_str: str) -> str:
    date_str = date_str.strip()
    for fmt in ("%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).date().isoformat()
        except ValueError:
            pass
    return date_str


def clean_amount(amount_str: str) -> float:
    cleaned = re.sub(r'[^0-9.]', '', str(amount_str))
    return float(cleaned) if cleaned else 0.0


def clean_transactions(raw_rows: list[dict]) -> list[dict]:
    cleaned = []
    seen = set()

    for row in raw_rows:
        txn_id = row.get("txn_id", "").strip()
        raw_date = row.get("date", "").strip()
        merchant = row.get("merchant", "").strip()
        raw_amount = row.get("amount", "")
        raw_currency = row.get("currency", "").strip().upper()
        raw_status = row.get("status", "").strip().upper()
        raw_category = row.get("category", "").strip()
        account_id = row.get("account_id", "").strip()
        notes = row.get("notes", "").strip()

        if not raw_date or not merchant or not account_id:
            continue

        date = parse_date(raw_date)
        amount = clean_amount(raw_amount)

        if raw_status not in ("SUCCESS", "FAILED", "PENDING"):
            raw_status = "FAILED"

        category = raw_category if raw_category else "Uncategorised"

        dup_key = (txn_id, date, merchant, str(amount), raw_currency, raw_status, category, account_id)
        if dup_key in seen:
            continue
        seen.add(dup_key)

        cleaned.append({
            "txn_id": txn_id if txn_id else None,
            "date": date,
            "merchant": merchant,
            "amount": amount,
            "currency": raw_currency,
            "status": raw_status,
            "category": category,
            "account_id": account_id,
            "notes": notes,
        })

    return cleaned


def parse_csv(content: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(content))
    return [row for row in reader]
