"""ARPT Pipeline Configuration"""
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

SUPABASE_URL = "https://ejbbdtjoqapheqieoohs.supabase.co"
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", 
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqYmJkdGpvcWFwaGVxaWVvb2hzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzEwNDQ0MiwiZXhwIjoyMDg4NjgwNDQyfQ.AI9JRcDGC7DWknoEmBSxFEbXM5fMxNyO7dH3Mur774M")

XAI_API_KEY = os.getenv("XAI_API_KEY", "")
XAI_MODEL = "grok-4-1-fast-reasoning"
XAI_BASE_URL = "https://api.x.ai/v1/responses"

INFRANODUS_API_KEY = os.getenv("INFRANODUS_API_KEY", "")  # 유저가 설정
INFRANODUS_BASE_URL = "https://infranodus.com/api/v1"

# Scoring weights presets
WEIGHT_PRESETS = {
    "default": {"efficacy": 0.30, "formulation": 0.20, "consumer": 0.20, "value": 0.15, "differentiation": 0.15},
    "trend": {"efficacy": 0.25, "formulation": 0.15, "consumer": 0.15, "value": 0.15, "differentiation": 0.30},
    "stable": {"efficacy": 0.25, "formulation": 0.25, "consumer": 0.30, "value": 0.10, "differentiation": 0.10},
    "innovation": {"efficacy": 0.20, "formulation": 0.25, "consumer": 0.10, "value": 0.10, "differentiation": 0.35},
}

# Scrapling commands
SCRAPLING_BASE = "scrapling extract"
SCRAPLING_VENV = os.path.join(os.path.dirname(__file__), '..', '.venv', 'bin')

GROK_TIMEOUT = 120  # seconds
BATCH_SIZE = 5      # products per sub-agent batch
