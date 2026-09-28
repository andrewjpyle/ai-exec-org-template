"""Stripe reader: the CRO's revenue per day, from balance transactions.

Key: a Stripe RESTRICTED key with read access to Balance only, in $STRIPE_API_KEY.
Never give a seat a secret key that can create charges or refunds.

Revenue here = charges + payments minus refunds, in the currency you choose, averaged over
the window. It is a gross operating number, not an accounting figure.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from ._http import get_json

API = "https://api.stripe.com/v1/balance_transactions"
INCOME = {"charge", "payment"}
REFUND = {"refund", "payment_refund"}
MAX_PAGES = 50


def revenue_per_day(days: int = 7, currency: str = "usd", key: str = "revenue_per_day",
                    now: datetime | None = None) -> Callable[[], dict]:

    def _snapshot() -> dict:
        api_key = os.environ.get("STRIPE_API_KEY", "")
        if not api_key:
            return {"unavailable": "STRIPE_API_KEY not set"}
        if api_key.startswith("sk_live_") or api_key.startswith("sk_test_"):
            return {"unavailable": "use a restricted read-only key (rk_...), not a secret key"}
        since = int(((now or datetime.now(timezone.utc)) - timedelta(days=days)).timestamp())
        params = {"created[gte]": since, "limit": 100}
        total_cents = 0
        seen = 0
        for _ in range(MAX_PAGES):
            page = get_json(API, params=params, headers={"Authorization": f"Bearer {api_key}"})
            for tx in page.get("data", []):
                if tx.get("currency") != currency:
                    continue
                seen += 1
                if tx.get("type") in INCOME:
                    total_cents += tx.get("amount", 0)
                elif tx.get("type") in REFUND:
                    total_cents += tx.get("amount", 0)  # refunds are already negative
            if not page.get("has_more") or not page.get("data"):
                break
            params["starting_after"] = page["data"][-1]["id"]
        return {key: round(total_cents / 100 / days, 2), "transactions": seen, "currency": currency}

    return _snapshot
