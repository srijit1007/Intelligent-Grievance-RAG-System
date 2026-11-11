
import os
from dotenv import load_dotenv

# Load environment variables from the project root .env file
load_dotenv()
e = os.getenv

# Gemini API Configuration
GEMINI_API_KEY = e("GEMINI_API_KEY", "")
LLM_MODEL = e("LLM_MODEL", "gemini-3.1-flash-lite")

# Dashboard / FastAPI Authentication
API_KEY = e("API_KEY", "")

# Database Configuration
DB_PATH = e("DB_PATH", "data/tickets.db")
CHROMA_DIR = e("CHROMA_DIR", "data/chroma")
KB_DIR = e("KB_DIR", "kb")

# Grievance Classification Categories
CATEGORIES = (
    "billing",
    "delivery",
    "account",
    "service",
    "other"
)

# RAG Confidence and Retrieval Settings
CONFIDENCE_MIN = float(e("CONFIDENCE_MIN", "0.6"))
MAX_DISTANCE = float(e("MAX_DISTANCE", "1.3"))

# Gmail Integration
GMAIL_POLL_SECONDS = int(e("GMAIL_POLL_SECONDS", "0"))
AUTO_SEND = e("AUTO_SEND", "false").lower() == "true"
GMAIL_CREDS = e("GMAIL_CREDS", "credentials.json")
GMAIL_TOKEN = e("GMAIL_TOKEN", "data/token.json")

# Turso Cloud Database Configuration
TURSO_DATABASE_URL = e("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN = e("TURSO_AUTH_TOKEN", "")