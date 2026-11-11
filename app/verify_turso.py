import os
from dotenv import load_dotenv
import turso_serverless

load_dotenv()

conn = turso_serverless.connect(
    os.getenv("TURSO_DATABASE_URL"),
    auth_token=os.getenv("TURSO_AUTH_TOKEN")
)

try:
    result = conn.execute(
        "SELECT id, category, priority, status FROM tickets ORDER BY id"
    )

    rows = result.fetchall()

    print("Total cloud tickets:", len(rows))
    print("First ticket:", rows[0] if rows else "No tickets found")
    print("Row type:", type(rows[0]) if rows else "N/A")

finally:
    conn.close()