
import os
from dotenv import load_dotenv
import turso_serverless

load_dotenv()

url = os.getenv("TURSO_DATABASE_URL")
token = os.getenv("TURSO_AUTH_TOKEN")

if not url or not token:
    raise RuntimeError("Turso credentials are missing from .env")

conn = turso_serverless.connect(
    url,
    auth_token=token
)

conn.execute("""
    CREATE TABLE IF NOT EXISTS connection_test (
        id INTEGER PRIMARY KEY,
        message TEXT
    )
""")

conn.execute(
    "INSERT INTO connection_test (message) VALUES (?)",
    ("Grievance RAG connection successful",)
)
conn.commit()

rows = conn.execute(
    "SELECT * FROM connection_test"
).fetchall()

print("Turso connection successful!")
print("Test records:", len(rows))

conn.close()
