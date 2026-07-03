import json
from typing import Optional
from google import genai

from app.config import settings

CATEGORIES = [
    "Food", "Shopping", "Travel", "Transport",
    "Utilities", "Cash Withdrawal", "Entertainment", "Other",
]


def _get_client():
    return genai.Client(api_key=settings.gemini_api_key)


def classify_transactions(merchant_descriptions: list[dict]) -> list[dict]:
    if not merchant_descriptions:
        return merchant_descriptions

    prompt = (
        "You are a transaction categorizer. For each item below, assign one of these "
        f"categories: {', '.join(CATEGORIES)}.\n"
        "Return ONLY a valid JSON array of objects, each with keys 'index' (int) and 'category' (str). "
        "No markdown, no explanation.\n\n"
        "Items:\n"
    )
    for i, item in enumerate(merchant_descriptions):
        prompt += f"{i}: merchant={item['merchant']}, notes={item.get('notes', '')}\n"

    client = _get_client()
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
    )

    text = response.text.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    results = json.loads(text)
    for r in results:
        idx = r["index"]
        if 0 <= idx < len(merchant_descriptions):
            merchant_descriptions[idx]["llm_category"] = r["category"]

    return merchant_descriptions


def generate_narrative_summary(
    total_spend_inr: float,
    total_spend_usd: float,
    top_merchants: list[dict],
    anomaly_count: int,
    transactions_count: int,
) -> Optional[dict]:
    prompt = (
        "You are a financial analyst. Given the following transaction summary, produce a JSON output.\n"
        "Return ONLY valid JSON with keys: narrative (2-3 sentence spending summary as string), "
        "risk_level (one of low/medium/high).\n"
        "No markdown, no explanation.\n\n"
        f"Total spend INR: {total_spend_inr:.2f}\n"
        f"Total spend USD: {total_spend_usd:.2f}\n"
        f"Top merchants: {json.dumps(top_merchants)}\n"
        f"Anomaly count: {anomaly_count}\n"
        f"Total transactions: {transactions_count}\n"
    )

    client = _get_client()
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
    )

    text = response.text.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)
