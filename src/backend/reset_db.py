import asyncio
import aiosqlite
from datetime import datetime

DB_PATH = "customer_transaction_db/transactions.db"

USERS = ["Shivamani", "Mani", "Razak", "Nandhu", "Sai", "Aparna"]

BANKS = ["SBI", "HDFC"]

SAMPLE_TXNS = [
    ("Amazon", 1299.0, "2025-02-10", "Electronics"),
    ("Swiggy", 450.0, "2025-02-08", "Food"),
    ("Myntra", 3200.0, "2025-02-05", "Shopping"),
    ("Rapido", 80.0, "2025-02-02", "Travel"),
    ("Flipkart", 999.0, "2024-12-20", "Electronics"),
    ("Dominos", 600.0, "2024-12-18", "Restaurant"),
    ("Reliance Trends", 1500.0, "2024-11-28", "Clothing"),
]

SCHEMES = [
    (
        "SBI",
        "SBI Green Term Deposit",
        "Fixed deposit scheme encouraging investment in environmentally friendly projects.",
        7.10,
        10000.0,
    ),
    (
        "SBI",
        "SBI Senior Citizen Savings",
        "Higher interest rate term deposit for senior citizens.",
        7.50,
        5000.0,
    ),
    (
        "HDFC",
        "HDFC SavingsMax Account",
        "Premium savings account with free insurance and offers.",
        None,
        10000.0,
    ),
    (
        "HDFC",
        "HDFC Fixed Deposit – Regular",
        "Standard fixed deposit product with flexible tenures.",
        7.00,
        5000.0,
    ),
]


async def reset_db() -> None:
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row

    # enable foreign key constraints
    await db.execute("PRAGMA foreign_keys = ON;")

    print("Dropping old tables if they exist...")
    await db.execute("DROP TABLE IF EXISTS bank_schemes;")
    await db.execute("DROP TABLE IF EXISTS transactions;")
    await db.execute("DROP TABLE IF EXISTS accounts;")
    await db.execute("DROP TABLE IF EXISTS customers;")

    print("Creating new tables...")
    await db.execute(
        """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
        """
    )

    await db.execute(
        """
        CREATE TABLE accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            bank_name TEXT NOT NULL,
            account_number TEXT NOT NULL UNIQUE,
            account_type TEXT NOT NULL DEFAULT 'savings',
            opening_balance REAL NOT NULL DEFAULT 0.0,
            currency TEXT NOT NULL DEFAULT 'INR',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
        );
        """
    )

    await db.execute(
        """
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            txn_date TEXT NOT NULL,
            amount REAL NOT NULL,              -- positive for credit, negative for debit
            txn_type TEXT NOT NULL,            -- 'debit' or 'credit'
            merchant_name TEXT,
            category TEXT,
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
        );
        """
    )

    await db.execute(
        """
        CREATE TABLE bank_schemes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bank_name TEXT NOT NULL,
            scheme_name TEXT NOT NULL,
            description TEXT,
            interest_rate REAL,                -- store as percentage, e.g., 7.10 for 7.10%
            min_amount REAL,
            currency TEXT NOT NULL DEFAULT 'INR'
        );
        """
    )

    # Helpful view for quick balance lookup
    await db.execute(
        """
        CREATE VIEW IF NOT EXISTS account_balances AS
        SELECT
            a.id AS account_id,
            c.name AS customer_name,
            a.bank_name,
            a.account_number,
            a.currency,
            a.opening_balance + IFNULL(SUM(t.amount), 0) AS current_balance
        FROM accounts a
        JOIN customers c ON c.id = a.customer_id
        LEFT JOIN transactions t ON t.account_id = a.id
        GROUP BY a.id;
        """
    )

    print("Inserting customers and accounts...")
    for idx, username in enumerate(USERS):
        # Insert customer
        cur = await db.execute(
            "INSERT INTO customers (name) VALUES (?) RETURNING id;",
            (username,),
        )
        row = await cur.fetchone()
        customer_id = row[0]

        # Assign alternating banks just for demo
        bank_name = BANKS[idx % len(BANKS)]
        account_number = f"{bank_name.upper()}-{100000 + idx}"
        opening_balance = 25000.0 + (idx * 5000.0)

        await db.execute(
            """
            INSERT INTO accounts (
                customer_id, bank_name, account_number,
                account_type, opening_balance, currency
            ) VALUES (?, ?, ?, 'savings', ?, 'INR');
            """,
            (customer_id, bank_name, account_number, opening_balance),
        )

    print("Inserting sample transactions...")
    # For each user, add same set of sample transactions
    async with db.execute("SELECT id, customer_id FROM accounts") as cursor:
        accounts = await cursor.fetchall()

    for acc in accounts:
        account_id = acc["id"]

        for merchant, amount, date_str, category in SAMPLE_TXNS:
            txn_type = "debit"
            signed_amount = -float(amount)  # debit → negative

            await db.execute(
                """
                INSERT INTO transactions (
                    account_id, txn_date, amount, txn_type,
                    merchant_name, category
                ) VALUES (?, ?, ?, ?, ?, ?);
                """,
                (account_id, date_str, signed_amount, txn_type, merchant, category),
            )

    print("Inserting bank schemes...")
    for bank_name, scheme_name, description, rate, min_amount in SCHEMES:
        await db.execute(
            """
            INSERT INTO bank_schemes (
                bank_name, scheme_name, description,
                interest_rate, min_amount, currency
            ) VALUES (?, ?, ?, ?, ?, 'INR');
            """,
            (bank_name, scheme_name, description, rate, min_amount),
        )

    await db.commit()
    await db.close()
    print("DONE! SQLite banking DB ready.")


if __name__ == "__main__":
    asyncio.run(reset_db())
