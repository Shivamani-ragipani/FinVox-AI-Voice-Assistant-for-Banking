from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from loguru import logger
from pydantic_ai import RunContext

from ai_services.agent import Dependencies

DEFAULT_CUSTOMER = "Shivamani"


async def get_account_balance(
    ctx: RunContext[Dependencies],
    customer_name: str = DEFAULT_CUSTOMER,
) -> Dict[str, Any]:
    try:
        sqlite_db = ctx.deps.sqlite_db

        query = """
            SELECT account_number, bank_name, currency, current_balance
            FROM account_balances
            WHERE LOWER(customer_name) = LOWER(?)
            LIMIT 1;
        """

        logger.debug(f"[get_account_balance] Executing query for {customer_name}")

        cursor = await sqlite_db.execute(query, (customer_name,))
        row = await cursor.fetchone()
        await cursor.close()

        if not row:
            return {"message": f"No account found for {customer_name}."}

        return {
            "customer_name": customer_name,
            "bank_name": row["bank_name"],
            "account_number": row["account_number"],
            "balance_inr": f"₹{row['current_balance']:,.2f}",
        }

    except Exception as e:
        logger.error(f"❌ ERROR in get_account_balance: {e}")
        return {"error": str(e)}


async def get_recent_transactions(
    ctx: RunContext[Dependencies],
    last_n: int = 10,
    customer_name: str = DEFAULT_CUSTOMER,
) -> List[Dict[str, Any]]:
    try:
        sqlite_db = ctx.deps.sqlite_db

        query = """
            SELECT t.txn_date, t.amount, t.txn_type,
                   t.merchant_name, t.category
            FROM transactions t
            JOIN accounts a ON a.id = t.account_id
            JOIN customers c ON c.id = a.customer_id
            WHERE LOWER(c.name) = LOWER(?)
            ORDER BY t.txn_date DESC
            LIMIT ?;
        """

        params = (customer_name, last_n)
        logger.debug(f"[get_recent_transactions] Executing: Params={params}")

        cursor = await sqlite_db.execute(query, params)
        rows = await cursor.fetchall()
        await cursor.close()

        results: List[Dict[str, Any]] = []
        for row in rows:
            amt = float(row["amount"])
            results.append(
                {
                    "date": row["txn_date"],
                    "amount_inr": f"₹{abs(amt):,.2f}",
                    "direction": "debit" if amt < 0 else "credit",
                    "merchant": row["merchant_name"],
                    "category": row["category"],
                }
            )

        return results

    except Exception as e:
        logger.error(f"❌ ERROR in get_recent_transactions: {e}")
        return []


async def summarize_spending(
    ctx: RunContext[Dependencies],
    customer_name: str = DEFAULT_CUSTOMER,
    time_period: str = "this month",
) -> Dict[str, float]:
    try:
        sqlite_db = ctx.deps.sqlite_db
        today = datetime.today()

        if "week" in time_period.lower():
            start = today - timedelta(days=7)
        else:
            start = today - timedelta(days=30)

        start_str = start.strftime("%Y-%m-%d")

        query = """
            SELECT t.category, SUM(ABS(t.amount)) AS total_spent
            FROM transactions t
            JOIN accounts a ON a.id = t.account_id
            JOIN customers c ON a.customer_id = c.id
            WHERE LOWER(c.name) = LOWER(?)
              AND t.amount < 0
              AND t.txn_date >= ?
            GROUP BY t.category;
        """

        params = (customer_name, start_str)
        logger.debug(f"[summarize_spending] Executing: Params={params}")

        cursor = await sqlite_db.execute(query, params)
        rows = await cursor.fetchall()
        await cursor.close()

        return {row["category"]: float(row["total_spent"]) for row in rows}

    except Exception as e:
        logger.error(f"❌ ERROR in summarize_spending: {e}")
        return {}


async def detect_unusual_spending(
    ctx: RunContext[Dependencies],
    customer_name: str = DEFAULT_CUSTOMER,
    threshold_multiplier: float = 1.5,
) -> List[Dict[str, Any]]:
    try:
        sqlite_db = ctx.deps.sqlite_db
        start = datetime.today() - timedelta(days=30)
        start_str = start.strftime("%Y-%m-%d")

        avg_query = """
            SELECT AVG(ABS(t.amount))
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            WHERE LOWER(c.name) = LOWER(?)
              AND t.amount < 0
              AND t.txn_date >= ?;
        """

        cursor = await sqlite_db.execute(avg_query, (customer_name, start_str))
        avg_row = await cursor.fetchone()
        await cursor.close()

        avg_val = float(avg_row[0]) if avg_row and avg_row[0] else 0
        if avg_val == 0:
            return []

        threshold = avg_val * threshold_multiplier

        query = """
            SELECT t.txn_date, t.amount, t.merchant_name, t.category
            FROM transactions t
            JOIN accounts a ON a.id = t.account_id
            JOIN customers c ON a.customer_id = c.id
            WHERE LOWER(c.name) = LOWER(?)
              AND t.amount < 0
              AND ABS(t.amount) > ?
              AND t.txn_date >= ?;
        """

        params = (customer_name, threshold, start_str)
        logger.debug(f"[detect_unusual_spending] Executing: Params={params}")

        cursor2 = await sqlite_db.execute(query, params)
        rows = await cursor2.fetchall()
        await cursor2.close()

        results: List[Dict[str, Any]] = []
        for row in rows:
            amt = abs(float(row["amount"]))
            results.append(
                {
                    "date": row["txn_date"],
                    "amount_inr": f"₹{amt:,.2f}",
                    "merchant": row["merchant_name"],
                    "category": row["category"],
                }
            )

        return results

    except Exception as e:
        logger.error(f"❌ ERROR in detect_unusual_spending: {e}")
        return []


async def get_bank_schemes(
    ctx: RunContext[Dependencies],
    bank_name: str,
) -> List[Dict[str, Any]]:
    try:
        sqlite_db = ctx.deps.sqlite_db

        query = """
            SELECT scheme_name, description, interest_rate, min_amount
            FROM bank_schemes
            WHERE LOWER(bank_name) = LOWER(?);
        """

        logger.debug(f"[get_bank_schemes] Executing for {bank_name}")
        cursor = await sqlite_db.execute(query, (bank_name,))
        rows = await cursor.fetchall()
        await cursor.close()

        schemes: List[Dict[str, Any]] = []
        for row in rows:
            schemes.append(
                {
                    "scheme_name": row["scheme_name"],
                    "description": row["description"],
                    "interest_rate_percent": row["interest_rate"],
                    "minimum_amount_inr": f"₹{row['min_amount']:,.2f}",
                }
            )

        return schemes

    except Exception as e:
        logger.error(f"❌ ERROR in get_bank_schemes: {e}")
        return []
