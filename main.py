from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings, BASE_DIR
from app.core.database import init_db, get_all_jobs, get_profile
from app.services.job_service import job_service
from app.services.matching_service import matching_engine
from app.services.ats_service import ats_engine
from app.api.routes import router as api_router
import re


import asyncio


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize SQLite tables
    init_db()
    print("[JobPulse] Database initialized.")
    
    # 2. Check if jobs exist; if empty, seed/sync immediately
    jobs = get_all_jobs(limit=10)
    if not jobs:
        print("[JobPulse] Seeding initial job opportunities...")
        synced_jobs = await job_service.sync_all_jobs()
        profile = get_profile()
        matching_engine.evaluate_and_rank_jobs(profile, synced_jobs)
        print(f"[JobPulse] Seeded and ranked {len(synced_jobs)} jobs.")

    # 3. Automated Continuous Background Ingestion Crawler (Hourly)
    async def automated_job_crawler():
        while True:
            try:
                await asyncio.sleep(settings.CRAWLER_INTERVAL_SECONDS)
                print("[JobPulse Crawler] Starting automated hourly job sync...")
                synced = await job_service.sync_all_jobs()
                active_profile = get_profile()
                matching_engine.evaluate_and_rank_jobs(active_profile, synced)
                print(f"[JobPulse Crawler] Automated sync complete: {len(synced)} unique jobs active.")
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[JobPulse Crawler] Background sync error: {e}")

    crawler_task = asyncio.create_task(automated_job_crawler())

    yield
    crawler_task.cancel()
    print("[JobPulse] Shutting down application gracefully.")


app = FastAPI(
    title=settings.APP_NAME,
    description="Intelligent Resume-to-Job Matching and Email Alert Platform built with FastAPI.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files & Jinja2 templates
STATIC_DIR = BASE_DIR / "app" / "static"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Mount API Router
app.include_router(api_router, prefix="/api")


@app.get("/")
def serve_dashboard(request: Request):
    profile = get_profile()
    jobs = get_all_jobs(limit=100)
    
    # Calculate matches dynamically from SQLite
    matches = matching_engine.evaluate_and_rank_jobs(profile, jobs)
    summary = matching_engine.get_pipeline_summary(profile)
    
    # Calculate top ceiling salary dynamically
    top_ceiling_salary = "$0"
    salaries = []
    for j in jobs:
        if j.salary_range:
            nums = [int(n.replace(",", "")) for n in re.findall(r"\d[\d,]+", j.salary_range)]
            if nums:
                salaries.append(max(nums))
    if salaries:
        top_ceiling_salary = f"${max(salaries):,}"
        
    top_matches = matches[:15]
    ats_report = ats_engine.analyze_resume(profile)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": settings.APP_NAME,
            "profile": profile,
            "summary": summary,
            "top_matches": top_matches,
            "top_ceiling_salary": top_ceiling_salary,
            "ats_report": ats_report
        }
    )


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": settings.APP_NAME, "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
