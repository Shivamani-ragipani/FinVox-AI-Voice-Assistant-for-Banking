import asyncio
import aiosqlite

DB_PATH = "customer_transaction_db/transactions.db"

USERS = ["Shivamani", "Mani", "Razak", "Nandhu", "Sai", "Aparna"]

SAMPLE_DATA = [
    (u, 1299.0, "2025-02-10", "Amazon", "Electronics") for u in USERS
] + [
    (u, 450.0, "2025-02-08", "Swiggy", "Food") for u in USERS
] + [
    (u, 3200.0, "2025-02-05", "Myntra", "Shopping") for u in USERS
] + [
    (u, 80.0, "2025-02-02", "Rapido", "Travel") for u in USERS
] + [
    (u, 999.0, "2024-12-20", "Flipkart", "Electronics") for u in USERS
] + [
    (u, 600.0, "2024-12-18", "Dominos", "Restaurant") for u in USERS
] + [
    (u, 1500.0, "2024-11-28", "Reliance Trends", "Clothing") for u in USERS
]


async def reset_db():
    db = await aiosqlite.connect(DB_PATH)

    print("Dropping old table if exists...")
    await db.execute("DROP TABLE IF EXISTS Transactions")

    print("Creating new table...")
    await db.execute("""
        CREATE TABLE Transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            User_Name TEXT,
            Transaction_Amount REAL,
            Date TEXT,
            Merchant_Name TEXT,
            Category TEXT
        )
    """)

    print("Inserting new sample data (2024–2025)...")
    for row in SAMPLE_DATA:
        await db.execute("""
            INSERT INTO Transactions 
            (User_Name, Transaction_Amount, Date, Merchant_Name, Category)
            VALUES (?, ?, ?, ?, ?)
        """, row)

    await db.commit()
    await db.close()
    print("DONE! Database has been reset with new data.")


if __name__ == "__main__":
    asyncio.run(reset_db())
