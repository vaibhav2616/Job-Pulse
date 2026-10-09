import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"

# Ensure runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseModel):
    APP_NAME: str = "JobPulse"
    APP_TAGLINE: str = "Automated AI Career Matchmaker"
    API_V1_PREFIX: str = "/api"
    
    # Database
    DATABASE_PATH: str = str(DATA_DIR / "job_finder.db")
    
    # Ingestion Sources
    ENABLE_REMOTEOK: bool = True
    ENABLE_JOBICY: bool = True
    ENABLE_ARBEITNOW: bool = True
    ENABLE_REMOTIVE: bool = True
    
    # Matching defaults
    MIN_MATCH_THRESHOLD: float = 65.0  # Percentage
    TOP_DIGEST_COUNT: int = 5
    CRAWLER_INTERVAL_SECONDS: int = int(os.getenv("CRAWLER_INTERVAL_SECONDS", "3600"))
    
    # SMTP / Email Settings
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "notifications@jobpulse.local")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "JobPulse Alerts <alerts@jobpulse.local>")
    SMTP_STARTTLS: bool = True
    
    # Testing mode (if True, logs email HTML and saves preview instead of failing if SMTP is unset)
    SIMULATE_EMAIL_IF_UNCONFIGURED: bool = True


settings = Settings()
