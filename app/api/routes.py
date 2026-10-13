import shutil
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Query, HTTPException, status
from fastapi.responses import HTMLResponse

from app.core.config import settings, UPLOAD_DIR
from app.core.database import (
    get_profile, save_profile, get_matches, get_all_jobs, 
    update_match_status, get_connection
)
from app.models.schemas import (
    CandidateProfile, JobMatch, OpportunityPipelineSummary, 
    ApplicationStatus, EmailDigestRequest
)
from app.services.resume_service import resume_service
from app.services.job_service import job_service
from app.services.matching_service import matching_engine
from app.services.email_service import email_service
from app.services.ats_service import ats_engine

router = APIRouter()


@router.get("/profile", response_model=CandidateProfile)
def fetch_candidate_profile():
    return get_profile()


@router.put("/profile", response_model=CandidateProfile)
def update_candidate_profile(profile_data: CandidateProfile):
    save_profile(profile_data)
    # Re-score existing jobs against updated skills
    all_jobs = get_all_jobs(limit=200)
    matching_engine.evaluate_and_rank_jobs(profile_data, all_jobs)
    return profile_data


@router.post("/resume/upload")
async def upload_resume(
    file: UploadFile = File(...)
):
    ext = Path(file.filename).suffix.lower()
    if ext not in [".pdf", ".docx", ".doc", ".txt"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload PDF, DOCX, or TXT."
        )

    # Save to disk safely
    saved_filename = f"{Path(file.filename).stem[:30]}_{file.filename}"
    file_path = UPLOAD_DIR / saved_filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Parse resume
    try:
        raw_text = resume_service.extract_text_from_file(str(file_path))
        if not raw_text.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not extract text from document. Ensure it is not a scanned image."
            )
        
        parsed_profile = resume_service.parse_resume_text(raw_text, original_filename=file.filename)
        save_profile(parsed_profile)

        # Sync or match against current job inventory
        all_jobs = get_all_jobs(limit=200)
        if not all_jobs:
            all_jobs = await job_service.sync_all_jobs()
        
        matches = matching_engine.evaluate_and_rank_jobs(parsed_profile, all_jobs)

        return {
            "status": "success",
            "message": f"Resume parsed successfully! Extracted {len(parsed_profile.skills)} skills and found {len(matches)} matching positions.",
            "profile": parsed_profile,
            "top_match_count": len([m for m in matches if m.match_score >= parsed_profile.min_match_threshold])
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error parsing resume: {str(e)}"
        )


@router.post("/resume/paste")
async def paste_resume_text(req: dict):
    raw_text = req.get("text", "").strip()
    if not raw_text or len(raw_text) < 20:
        raise HTTPException(status_code=400, detail="Please provide at least 20 characters of resume text.")

    candidate_name = req.get("candidate_name")
    parsed_profile = resume_service.parse_resume_text(raw_text, original_filename=candidate_name or "Pasted Resume")
    save_profile(parsed_profile)

    all_jobs = get_all_jobs(limit=200)
    if not all_jobs:
        all_jobs = await job_service.sync_all_jobs()

    matches = matching_engine.evaluate_and_rank_jobs(parsed_profile, all_jobs)

    return {
        "status": "success",
        "message": f"Resume text analyzed! Found {len(parsed_profile.skills)} skills and {len(matches)} job matches.",
        "profile": parsed_profile,
        "top_match_count": len([m for m in matches if m.match_score >= parsed_profile.min_match_threshold])
    }


@router.get("/resume/samples")
def list_sample_resumes():
    samples = resume_service.get_sample_profiles()
    return [
        {
            "id": k,
            "name": p.full_name,
            "title": p.title,
            "skills": p.skills[:5],
            "experience": f"{p.years_of_experience} yrs"
        }
        for k, p in samples.items()
    ]


@router.post("/resume/sample/{sample_id}")
async def load_sample_resume(sample_id: str):
    samples = resume_service.get_sample_profiles()
    if sample_id not in samples:
        raise HTTPException(status_code=404, detail="Sample profile not found.")

    selected_profile = samples[sample_id]
    save_profile(selected_profile)

    all_jobs = get_all_jobs(limit=200)
    if not all_jobs:
        all_jobs = await job_service.sync_all_jobs()

    matches = matching_engine.evaluate_and_rank_jobs(selected_profile, all_jobs)

    return {
        "status": "success",
        "message": f"Loaded '{selected_profile.title}' sample profile!",
        "profile": selected_profile,
        "top_match_count": len([m for m in matches if m.match_score >= selected_profile.min_match_threshold])
    }


@router.post("/profile/skills/add")
def add_profile_skill(skill: str = Query(...)):
    profile = get_profile()
    skill_clean = skill.strip()
    if skill_clean and skill_clean not in profile.skills:
        profile.skills.append(skill_clean)
        save_profile(profile)
        all_jobs = get_all_jobs(limit=200)
        matching_engine.evaluate_and_rank_jobs(profile, all_jobs)
    return profile


@router.delete("/profile/skills/remove")
def remove_profile_skill(skill: str = Query(...)):
    profile = get_profile()
    skill_clean = skill.strip()
    if skill_clean in profile.skills:
        profile.skills.remove(skill_clean)
        save_profile(profile)
        all_jobs = get_all_jobs(limit=200)
        matching_engine.evaluate_and_rank_jobs(profile, all_jobs)
    return profile


@router.get("/ats/score")
def get_current_ats_score():
    """Calculates open-source diagnostic ATS score and actionable recommendations for the active candidate profile."""
    profile = get_profile()
    return ats_engine.analyze_resume(profile)


@router.post("/ats/score")
def evaluate_custom_ats_score(payload: dict):
    """Calculates real-time ATS score for draft resume text or candidate profile."""
    if "profile" in payload:
        candidate_data = CandidateProfile.model_validate(payload["profile"])
        return ats_engine.analyze_resume(candidate_data)
    
    raw_text = payload.get("text", "")
    profile = get_profile()
    return ats_engine.analyze_resume(profile, raw_text=raw_text)


@router.post("/resume/builder/save")
async def save_resume_builder_profile(profile_data: CandidateProfile):
    """
    Saves an updated resume created in the interactive ATS Resume Maker,
    persists as the active profile, immediately triggers real-time job re-ranking,
    and returns updated ATS diagnostic report.
    """
    save_profile(profile_data)
    
    all_jobs = get_all_jobs(limit=200)
    if not all_jobs:
        all_jobs = await job_service.sync_all_jobs()
        
    matches = matching_engine.evaluate_and_rank_jobs(profile_data, all_jobs)
    ats_report = ats_engine.analyze_resume(profile_data)
    
    return {
        "status": "success",
        "message": f"Resume saved and set as active profile! Re-ranked {len(matches)} matching positions in real-time.",
        "profile": profile_data,
        "ats_report": ats_report,
        "top_match_count": len([m for m in matches if m.match_score >= profile_data.min_match_threshold])
    }



@router.post("/jobs/sync")
async def trigger_job_sync():
    """Fetches real-time jobs from RemoteOK, Jobicy, Arbeitnow, and updates match scores."""
    profile = get_profile()
    synced_jobs = await job_service.sync_all_jobs()
    matches = matching_engine.evaluate_and_rank_jobs(profile, synced_jobs)
    return {
        "status": "success",
        "synced_count": len(synced_jobs),
        "total_ranked_matches": len(matches)
    }


@router.get("/jobs/feed")
def get_job_feed(
    status_filter: Optional[str] = Query(None, description="Discovered, Matched, Saved, Applied, Interviewing, Offer"),
    query: Optional[str] = Query(None, description="Search by keyword, company, or skill"),
    min_score: float = Query(0.0),
    remote_only: bool = Query(False),
    limit: int = Query(50)
):
    matches = get_matches(min_score=min_score, limit=limit)
    
    # Filter in memory
    filtered = []
    q = query.strip().lower() if query else None

    for m in matches:
        if status_filter and status_filter.lower() != "all" and m.status.value.lower() != status_filter.lower():
            continue
        if remote_only and not m.job.is_remote:
            continue
        if q:
            match_str = f"{m.job.title} {m.job.company} {' '.join(m.job.tags)}".lower()
            if q not in match_str:
                continue
        filtered.append(m)

    return filtered


@router.patch("/jobs/{job_id}/status")
def change_opportunity_status(job_id: str, new_status: ApplicationStatus):
    update_match_status(job_id, new_status)
    return {"status": "success", "job_id": job_id, "new_status": new_status.value}


@router.get("/pipeline/summary", response_model=OpportunityPipelineSummary)
def get_pipeline_overview():
    profile = get_profile()
    return matching_engine.get_pipeline_summary(profile)


@router.post("/digest/send")
async def send_email_digest_now(
    req: Optional[EmailDigestRequest] = None
):
    profile = get_profile()
    target_email = req.recipient_email if req and req.recipient_email else profile.email
    min_threshold = req.min_score if req else profile.min_match_threshold
    top_n = req.top_n if req else 5

    # Get top matching jobs
    all_matches = get_matches(min_score=min_threshold, limit=top_n)
    if not all_matches:
        # Fall back to top matches regardless of score threshold so user gets a demonstration
        all_matches = get_matches(min_score=0.0, limit=top_n)

    result = await email_service.send_job_digest(target_email, profile, all_matches)
    return result


@router.get("/digest/preview", response_class=HTMLResponse)
def preview_email_digest(top_n: int = Query(5)):
    profile = get_profile()
    matches = get_matches(min_score=profile.min_match_threshold, limit=top_n)
    if not matches:
        matches = get_matches(min_score=0.0, limit=top_n)
    
    html = email_service.render_digest_html(profile, matches)
    return HTMLResponse(content=html)


@router.get("/email-logs")
def fetch_email_logs():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM email_logs ORDER BY sent_at DESC LIMIT 20")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
