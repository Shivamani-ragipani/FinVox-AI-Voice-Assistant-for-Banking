import os
import aiosqlite

async def get_customer_sqlite_client():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "transactions.db")

    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row

    try:
        yield db
    finally:
        await db.close()
