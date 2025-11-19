from typing import List, Dict, Optional
from datetime import datetime, timedelta
from loguru import logger
from pydantic_ai import RunContext

from ai_services.agent import Dependencies


# ======================================================
#  GET RECENT TRANSACTIONS
# ======================================================
async def get_recent_transactions(
    ctx: RunContext[Dependencies],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    merchant: Optional[str] = None,
    last_n: Optional[int] = 10,
) -> List[Dict]:

    query = """
        SELECT Transaction_Amount, Date, Merchant_Name, Category
        FROM Transactions
        WHERE 1=1
    """

    params: list = []

    # Filters
    if start_date:
        query += " AND Date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND Date <= ?"
        params.append(end_date)

    if category:
        query += " AND Category = ?"
        params.append(category)

    if merchant:
        query += " AND Merchant_Name = ?"
        params.append(merchant)

    # Sort & limit
    query += " ORDER BY Date DESC LIMIT ?"
    params.append(int(last_n))

    try:
        sqlite_db = ctx.deps.sqlite_db

        logger.debug(f"\n[get_recent_transactions] Executing:\n{query}\nParams={params}")

        cursor = await sqlite_db.execute(query, params)
        rows = await cursor.fetchall()
        await cursor.close()

        results = [dict(row) for row in rows]

        logger.debug(f"[get_recent_transactions] Returned {len(results)} rows")
        return results

    except Exception as e:
        logger.error(f"❌ ERROR in get_recent_transactions: {e}")
        return []


# ======================================================
#  SUMMARIZE SPENDING
# ======================================================
async def summarize_spending(
    ctx: RunContext[Dependencies],
    time_period: str = "this week",
    return_budget_status: bool = False,
    budget_limits: Dict[str, int] = {
        "Cosmetic": 20000,
        "Travel": 100000,
        "Clothing": 300000,
        "Electronics": 150000,
        "Food": 50000,
        "Restaurant": 60000,
        "Shopping": 120000,
    },
) -> Dict:

    today = datetime.today()

    time_period_lower = time_period.lower()

    if "week" in time_period_lower:
        start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    elif "month" in time_period_lower:
        start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    else:
        start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")

    query = """
        SELECT Category, SUM(Transaction_Amount)
        FROM Transactions
        WHERE Date >= ?
        GROUP BY Category
    """

    try:
        sqlite_db = ctx.deps.sqlite_db

        logger.debug(f"\n[summarize_spending] Executing:\n{query}\nParams={[start_date]}")

        cursor = await sqlite_db.execute(query, [start_date])
        rows = await cursor.fetchall()
        await cursor.close()

        totals = {row[0]: row[1] for row in rows}

        if not return_budget_status:
            return totals

        # Budget comparison
        output = {}
        for category, spent in totals.items():
            limit = budget_limits.get(category, float("inf"))
            output[category] = {
                "spent": spent,
                "budget": limit,
                "status": "over budget" if spent > limit else "within budget",
            }

        return output

    except Exception as e:
        logger.error(f"❌ ERROR in summarize_spending: {e}")
        return {}


# ======================================================
#  DETECT UNUSUAL SPENDING
# ======================================================
async def detect_unusual_spending(
    ctx: RunContext[Dependencies],
    threshold: Optional[float] = None,
    time_period: str = "last month",
) -> List[Dict]:

    today = datetime.today()
    time_period_lower = time_period.lower()

    if "month" in time_period_lower:
        start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    else:
        start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")

    avg_query = """
        SELECT AVG(Transaction_Amount)
        FROM Transactions
        WHERE Date >= ?
    """

    try:
        sqlite_db = ctx.deps.sqlite_db

        logger.debug(f"\n[detect_unusual_spending] AVG Query:\n{avg_query}\nParams={[start_date]}")

        cursor = await sqlite_db.execute(avg_query, [start_date])
        avg_row = await cursor.fetchone()
        await cursor.close()

        avg_val = avg_row[0] if avg_row and avg_row[0] is not None else 0

        if avg_val == 0:
            logger.debug("[detect_unusual_spending] No transactions found.")
            return []

        # Default threshold = 150% of average
        if threshold is None:
            threshold = avg_val * 1.5

        query = """
            SELECT Transaction_Amount, Date, Merchant_Name, Category
            FROM Transactions
            WHERE Transaction_Amount > ?
              AND Date >= ?
        """

        params = [threshold, start_date]

        logger.debug(f"[detect_unusual_spending] Executing:\n{query}\nParams={params}")

        cursor2 = await sqlite_db.execute(query, params)
        rows = await cursor2.fetchall()
        await cursor2.close()

        results = [dict(row) for row in rows]

        logger.debug(f"[detect_unusual_spending] Found {len(results)} unusual transactions")

        return results

    except Exception as e:
        logger.error(f"❌ ERROR in detect_unusual_spending: {e}")
        return []
