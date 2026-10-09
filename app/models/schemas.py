import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class WorkMode(str, Enum):
    REMOTE = "Remote"
    HYBRID = "Hybrid"
    ONSITE = "On-site"
    ANY = "Any"


class SeniorityLevel(str, Enum):
    ENTRY = "Entry / Junior"
    MID = "Mid-Level"
    SENIOR = "Senior"
    PRINCIPAL = "Principal / Staff"
    EXECUTIVE = "Director / Executive"


class ApplicationStatus(str, Enum):
    DISCOVERED = "Discovered"
    MATCHED = "Matched"
    SAVED = "Saved"
    APPLIED = "Applied"
    INTERVIEWING = "Interviewing"
    OFFER = "Offer"
    ARCHIVED = "Archived"


class WorkExperience(BaseModel):
    company: str
    role: str
    duration: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)


class CandidateProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    full_name: str = "Alex Mercer"
    email: str = "alex.mercer@example.com"
    phone: Optional[str] = "+1 (555) 234-5678"
    title: str = "Senior Full-Stack Engineer"
    summary: str = "Full-stack software engineer with 5+ years of experience designing scalable Python backends, FastAPI microservices, and modern responsive web architectures."
    years_of_experience: float = 5.5
    seniority: SeniorityLevel = SeniorityLevel.SENIOR
    skills: List[str] = Field(default_factory=lambda: [
        "Python", "FastAPI", "PostgreSQL", "Docker", "JavaScript", 
        "REST APIs", "Redis", "AsyncIO", "Git", "System Design"
    ])
    work_history: List[WorkExperience] = Field(default_factory=lambda: [
        WorkExperience(
            company="Apex Technologies",
            role="Senior Software Engineer",
            duration="2021 - Present",
            highlights=[
                "Architected high-throughput FastAPI microservices handling 2.4M daily requests with 99.99% uptime.",
                "Engineered distributed caching layer using Redis and PostgreSQL, reducing query latency by 45%.",
                "Automated multi-stage Docker container deployments via GitHub Actions, accelerating release cycles by 3x."
            ]
        ),
        WorkExperience(
            company="DataPulse Labs",
            role="Backend Developer",
            duration="2018 - 2021",
            highlights=[
                "Built scalable RESTful endpoints in Python for real-time analytics dashboards serving 150k active users.",
                "Optimized database schema and indexing strategies, eliminating query bottlenecks and saving $18k in cloud resources."
            ]
        )
    ])
    education: List[str] = Field(default_factory=lambda: [
        "B.S. in Computer Science - University of California (2014 - 2018)"
    ])
    preferred_work_modes: List[WorkMode] = Field(default_factory=lambda: [WorkMode.REMOTE])
    target_roles: List[str] = Field(default_factory=lambda: [
        "Senior Backend Engineer", "Full-Stack Developer", "Python Engineer"
    ])
    min_desired_salary: Optional[int] = 120000
    preferred_locations: List[str] = Field(default_factory=lambda: ["Remote", "Global", "United States"])
    email_notifications_enabled: bool = True
    notification_cadence: str = "Daily"  # Daily, Weekly, Instant
    min_match_threshold: float = 75.0


class JobPosting(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str  # remoteok, jobicy, arbeitnow, remotive, ats
    external_id: Optional[str] = None
    dedupe_hash: str
    title: str
    company: str
    company_logo: Optional[str] = None
    location: str = "Remote"
    is_remote: bool = True
    salary_range: Optional[str] = None
    salary_currency: Optional[str] = "$"
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    url: str
    published_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    is_active: bool = True


class JobMatch(BaseModel):
    job: JobPosting
    match_score: float  # 0 to 100
    semantic_score: float
    skill_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    match_rationale: str
    status: ApplicationStatus = ApplicationStatus.MATCHED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    notified: bool = False


class OpportunityPipelineSummary(BaseModel):
    total_scanned_jobs: int
    matched_count: int
    applied_count: int
    interviewing_count: int
    offers_count: int
    avg_match_score: float
    top_domains: List[Dict[str, Any]]
    stage_breakdown: Dict[str, int]


class EmailDigestRequest(BaseModel):
    recipient_email: str
    candidate_name: str
    top_n: int = 5
    min_score: float = 75.0
