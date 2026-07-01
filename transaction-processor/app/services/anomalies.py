from statistics import median

DOMESTIC_ONLY_BRANDS = {"SWIGGY", "OLA", "IRCTC"}


def detect_outliers(transactions: list[dict]) -> list[dict]:
    account_amounts: dict[str, list[float]] = {}
    for txn in transactions:
        acc = txn["account_id"]
        account_amounts.setdefault(acc, []).append(txn["amount"])

    account_medians = {acc: median(vals) for acc, vals in account_amounts.items()}

    for txn in transactions:
        med = account_medians.get(txn["account_id"], 0)
        if med > 0 and txn["amount"] > 3 * med:
            txn["is_anomaly"] = True
            txn["anomaly_reason"] = (
                f"Amount {txn['amount']} exceeds 3x account median ({med})"
            )

    return transactions


def detect_domestic_usd(transactions: list[dict]) -> list[dict]:
    for txn in transactions:
        if txn["currency"] == "USD" and txn["merchant"].upper() in DOMESTIC_ONLY_BRANDS:
            txn.setdefault("is_anomaly", False)
            if txn["is_anomaly"]:
                txn["anomaly_reason"] += "; "
            else:
                txn["is_anomaly"] = True
                txn["anomaly_reason"] = ""
            txn["anomaly_reason"] += (
                f"USD transaction on domestic-only merchant {txn['merchant']}"
            )

    return transactions
