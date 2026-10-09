import json
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.core.config import settings
from app.models.schemas import CandidateProfile, JobPosting, JobMatch, ApplicationStatus


def get_connection():
    conn = sqlite3.connect(settings.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Profile Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidate_profile (
        id TEXT PRIMARY KEY,
        data_json TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 2. Jobs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        dedupe_hash TEXT UNIQUE NOT NULL,
        source TEXT NOT NULL,
        title TEXT NOT NULL,
        company TEXT NOT NULL,
        company_logo TEXT,
        location TEXT,
        is_remote BOOLEAN,
        salary_range TEXT,
        description TEXT,
        tags_json TEXT,
        url TEXT NOT NULL,
        published_at TIMESTAMP,
        is_active BOOLEAN DEFAULT 1
    )
    """)
    
    # 3. Matches Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS job_matches (
        id TEXT PRIMARY KEY,
        job_id TEXT NOT NULL,
        match_score REAL NOT NULL,
        semantic_score REAL NOT NULL,
        skill_score REAL NOT NULL,
        matched_skills_json TEXT,
        missing_skills_json TEXT,
        rationale TEXT,
        status TEXT DEFAULT 'Matched',
        notified BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (job_id) REFERENCES jobs(id)
    )
    """)
    
    # 4. Email Dispatches Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS email_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipient_email TEXT NOT NULL,
        subject TEXT NOT NULL,
        job_count INTEGER NOT NULL,
        status TEXT NOT NULL,
        error_message TEXT,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()


def get_profile() -> CandidateProfile:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT data_json FROM candidate_profile ORDER BY updated_at DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return CandidateProfile.model_validate_json(row["data_json"])
    
    # Default profile
    default_profile = CandidateProfile()
    save_profile(default_profile)
    return default_profile


def save_profile(profile: CandidateProfile):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO candidate_profile (id, data_json, updated_at) 
    VALUES (?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(id) DO UPDATE SET data_json = excluded.data_json, updated_at = CURRENT_TIMESTAMP
    """, (profile.id, profile.model_dump_json()))
    conn.commit()
    conn.close()


def save_jobs(jobs: List[JobPosting]):
    conn = get_connection()
    cursor = conn.cursor()
    for job in jobs:
        cursor.execute("""
        INSERT INTO jobs (
            id, dedupe_hash, source, title, company, company_logo, 
            location, is_remote, salary_range, description, tags_json, url, published_at, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(dedupe_hash) DO UPDATE SET 
            salary_range = COALESCE(excluded.salary_range, jobs.salary_range),
            tags_json = COALESCE(excluded.tags_json, jobs.tags_json),
            is_active = excluded.is_active
        """, (
            job.id, job.dedupe_hash, job.source, job.title, job.company, job.company_logo,
            job.location, 1 if job.is_remote else 0, job.salary_range, job.description,
            json.dumps(job.tags), job.url, job.published_at.isoformat(), 1 if job.is_active else 0
        ))
    conn.commit()
    conn.close()


def get_all_jobs(limit: int = 200) -> List[JobPosting]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE is_active = 1 ORDER BY published_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    jobs = []
    for r in rows:
        jobs.append(JobPosting(
            id=r["id"],
            source=r["source"],
            dedupe_hash=r["dedupe_hash"],
            title=r["title"],
            company=r["company"],
            company_logo=r["company_logo"],
            location=r["location"] or "Remote",
            is_remote=bool(r["is_remote"]),
            salary_range=r["salary_range"],
            description=r["description"] or "",
            tags=json.loads(r["tags_json"]) if r["tags_json"] else [],
            url=r["url"],
            published_at=datetime.fromisoformat(r["published_at"]) if r["published_at"] else datetime.utcnow()
        ))
    return jobs


def save_matches(matches: List[JobMatch]):
    conn = get_connection()
    cursor = conn.cursor()
    for m in matches:
        cursor.execute("""
        INSERT INTO job_matches (
            id, job_id, match_score, semantic_score, skill_score,
            matched_skills_json, missing_skills_json, rationale, status, notified, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            match_score = excluded.match_score,
            semantic_score = excluded.semantic_score,
            skill_score = excluded.skill_score,
            matched_skills_json = excluded.matched_skills_json,
            missing_skills_json = excluded.missing_skills_json,
            rationale = excluded.rationale
        """, (
            m.job.id, m.job.id, m.match_score, m.semantic_score, m.skill_score,
            json.dumps(m.matched_skills), json.dumps(m.missing_skills),
            m.match_rationale, m.status.value, 1 if m.notified else 0
        ))
    conn.commit()
    conn.close()


def get_matches(min_score: float = 0.0, limit: int = 100) -> List[JobMatch]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT m.*, j.dedupe_hash, j.source, j.title, j.company, j.company_logo,
           j.location, j.is_remote, j.salary_range, j.description, j.tags_json, j.url, j.published_at
    FROM job_matches m
    JOIN jobs j ON m.job_id = j.id
    WHERE m.match_score >= ? AND j.is_active = 1
    ORDER BY m.match_score DESC
    LIMIT ?
    """, (min_score, limit))
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        job = JobPosting(
            id=r["job_id"],
            source=r["source"],
            dedupe_hash=r["dedupe_hash"],
            title=r["title"],
            company=r["company"],
            company_logo=r["company_logo"],
            location=r["location"] or "Remote",
            is_remote=bool(r["is_remote"]),
            salary_range=r["salary_range"],
            description=r["description"] or "",
            tags=json.loads(r["tags_json"]) if r["tags_json"] else [],
            url=r["url"],
            published_at=datetime.fromisoformat(r["published_at"]) if r["published_at"] else datetime.utcnow()
        )
        results.append(JobMatch(
            job=job,
            match_score=float(r["match_score"]),
            semantic_score=float(r["semantic_score"]),
            skill_score=float(r["skill_score"]),
            matched_skills=json.loads(r["matched_skills_json"]) if r["matched_skills_json"] else [],
            missing_skills=json.loads(r["missing_skills_json"]) if r["missing_skills_json"] else [],
            match_rationale=r["rationale"] or "",
            status=ApplicationStatus(r["status"]) if r["status"] in [s.value for s in ApplicationStatus] else ApplicationStatus.MATCHED,
            notified=bool(r["notified"])
        ))
    return results


def update_match_status(job_id: str, new_status: ApplicationStatus):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE job_matches SET status = ? WHERE job_id = ?", (new_status.value, job_id))
    conn.commit()
    conn.close()


def save_email_log(recipient: str, subject: str, job_count: int, status: str, error: Optional[str] = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO email_logs (recipient_email, subject, job_count, status, error_message)
    VALUES (?, ?, ?, ?, ?)
    """, (recipient, subject, job_count, status, error))
    conn.commit()
    conn.close()


def mark_matches_as_notified(job_ids: List[str]):
    if not job_ids:
        return
    conn = get_connection()
    cursor = conn.cursor()
    placeholders = ",".join(["?"] * len(job_ids))
    cursor.execute(f"UPDATE job_matches SET notified = 1 WHERE job_id IN ({placeholders})", job_ids)
    conn.commit()
    conn.close()
