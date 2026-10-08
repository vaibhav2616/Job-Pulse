# Job Finding & Intelligent Matching Engine: Architecture & Research Document

## 1. Executive Summary & Product Vision
The objective of this application is to automate the job search lifecycle for job seekers by continuously scanning the web for new career opportunities, intelligently matching them against candidate resumes using hybrid semantic and keyword algorithms, and delivering curated, high-relevance job digests directly to their email inbox.

Built on **FastAPI (Python)**, the system prioritizes high-throughput asynchronous execution, deterministic resume parsing, robust data normalization across disparate job APIs and web sources, explainable match scoring, and automated email delivery.

---

## 2. System Architecture Overview

The system is decomposed into six core pipelines:

```
+---------------------------------------------------------------------------------------+
|                                    USER INTERFACE                                     |
|  Resume Upload  |  Profile / Preferences Tuning  |  Live Match Feed  |  Digest Setup  |
+------------------------------------------+--------------------------------------------+
                                           | HTTP / REST
                                           v
+---------------------------------------------------------------------------------------+
|                               FASTAPI APPLICATION LAYER                               |
|  - Auth & Profile Management      - Parsing Controller        - Matching Service      |
|  - Source Ingestion Dispatcher    - BackgroundTasks Worker    - Email Delivery Engine |
+------------------+-----------------------+-----------------------+--------------------+
                   |                       |                       |
                   v                       v                       v
      +------------------------+ +--------------------+ +-----------------------+
      |  RESUME PARSING & NLP  | |  JOB AGGREGATOR    | |  MATCHING & SCORING   |
      | - pdfplumber / pypdf   | | - RemoteOK API     | | - Hard Filters        |
      | - Pydantic Schemas     | | - Jobicy API       | | - Vector Embeddings   |
      | - LLM Structuring      | | - Arbeitnow API    | | - BM25 / Keyword      |
      | - Skill Normalization  | | - Remotive API     | | - Explainable Why-You-|
      | - Profile Embeddings   | | - ATS Feeds / RSS  | |   Match Summaries     |
      +------------------------+ +--------------------+ +-----------------------+
                   |                       |                       |
                   +-----------------------+-----------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                               PERSISTENCE & VECTOR STORE                              |
|  - Relational Database: SQLite / PostgreSQL (SQLAlchemy / SQLModel)                   |
|  - Embeddings & Vector Index: FastEmbed / Chroma / sqlite-vec / Numpy Cosine Store    |
|  - Deduplication Cache: Job Content Hash & Source Canonical URL                       |
+------------------------------------------+--------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                        SCHEDULED DISPATCH & EMAIL NOTIFICATION                        |
|  - Ingestion & Matching Cron / APScheduler / FastAPI BackgroundTasks                  |
|  - Dynamic Jinja2 Responsive HTML Templates (Dark/Light Mode + CTA Buttons)           |
|  - Async SMTP Delivery (`aiosmtplib` / Resend / SendGrid / Amazon SES)                |
|  - Unsubscribe & One-Click Frequency Controls (CAN-SPAM / GDPR Compliant)             |
+---------------------------------------------------------------------------------------+
```

---

## 3. Live Job Ingestion Sources (Internet Aggregation)

To ensure high data freshness without requiring exorbitant paid API subscriptions during development and launch, the ingestion engine utilizes a multi-source aggregator strategy:

| Source | Endpoints / Protocol | Authentication | Coverage & Strengths | Constraints & Rate Limits |
| :--- | :--- | :--- | :--- | :--- |
| **RemoteOK** | `https://remoteok.io/api` | None (Free) | Remote tech, marketing, engineering, design | Cache locally; explicit source attribution required with non-redirect links. |
| **Jobicy** | `https://jobicy.com/api/v2/remote-jobs` | None (Public tier) | Global remote roles, categorized by industry & geo-region | Commercial ATS links require paid tier, public feed provides title, tags, description, application URL. |
| **Arbeitnow** | `https://www.arbeitnow.com/api/job-board-api` | None (100% Free) | Europe, UK, and global remote; direct ATS syndication (Greenhouse, Lever, Personio) | Strong European & visa-sponsorship data. Few duplicate listings. |
| **Remotive** | `https://remotive.com/api/remote-jobs` | None (Public tier) | Curated remote tech, dev, product, and devops positions | Max 2 requests/min; recommended sync 2-4 times daily; 24h lag on public feed. |
| **Adzuna** | `https://api.adzuna.com/v1/api/jobs/{country}/search` | App ID + App Key (Free Dev Tier) | Massive multi-country index across 20+ countries, salary histograms | Truncated snippets on free tier; redirect links. |
| **Direct ATS Feeds** | Greenhouse (`boards-api.greenhouse.io`), Lever (`api.lever.co/v0/postings/`) | None (Public job boards) | Direct employer applications for high-growth tech companies | Requires list of target company slugs. |

### Ingestion Best Practices:
1. **Deduplication Engine**: Hash job attributes (`md5(company_name.lower() + title.lower() + location.lower())`) to prevent showing duplicates sourced across multiple boards.
2. **Normalized Job Schema**: Transform all disparate payloads into a uniform Pydantic model (`JobPosting`).
3. **Storage & Expiration**: Automatically mark jobs inactive if they disappear from upstream feeds or exceed 30–45 days.

---

## 4. Resume Parsing & Profile Extraction Pipeline

Extracting unstructured resume data into actionable career profiles requires a resilient, multi-step pipeline:

```
[Uploaded Resume: PDF / DOCX / TXT]
                │
                ▼
  [Text Extraction Layer]
  - pdfplumber (layout-preserving, column-aware)
  - pypdf (fast fallback)
  - python-docx (for DOCX support)
                │
                ▼
  [Sanitization & Chunking]
  - Remove control characters & excessive whitespace
  - Strip personally sensitive data if not required (SSN, ID numbers)
                │
                ▼
  [Structured Entity Extraction (Pydantic + LLM / Instructor)]
  - Candidate Name, Email, Phone, Portfolio / LinkedIn Links
  - Career Summary & Target Roles
  - Experience Level (Junior, Mid, Senior, Principal, Staff, Executive)
  - Core Competencies & Skills (categorized: Languages, Frameworks, Tools, Soft Skills)
  - Work History (Company, Role, Duration, Bullet Achievements)
  - Education & Certifications
  - Preferences (Remote-only, Hybrid, Onsite, Preferred Locations)
                │
                ▼
  [Vector Representation]
  - Dense semantic profile embedding (capturing domain depth, tech stack, and responsibilities)
```

### Resume Schema Representation
```python
class WorkExperience(BaseModel):
  company: str
  role: str
  duration: Optional[str] = None
  highlights: list[str] = []


class ParsedCandidateProfile(BaseModel):
  full_name: str
  email: str
  phone: Optional[str] = None
  linkedin_url: Optional[str] = None
  github_url: Optional[str] = None
  portfolio_url: Optional[str] = None
  headline: str
  years_of_experience: float
  seniority_level: str  # Junior, Mid, Senior, Principal, Executive
  skills: list[str]
  frameworks_and_tools: list[str]
  education: list[str] = []
  work_history: list[WorkExperience] = []
  target_roles: list[str] = []
  preferred_work_modes: list[str] = [
      "Remote"
  ]  # Remote, Hybrid, On-site, Any
  preferred_locations: list[str] = []
```

---

## 5. Intelligent Matchmaking & Ranking Engine

A common pitfall of naive job finders is over-reliance on basic keyword matching (leading to low precision) or pure vector search (matching irrelevant roles that merely share corporate buzzwords). 

We adopt a **3-Stage Hybrid Scoring Architecture**:

```
                       [Candidate Profile + Resumes]
                                     │
    ┌────────────────────────────────┴────────────────────────────────┐
    ▼                                                                 ▼
[Hard Filters (Boolean Gate)]                         [Candidate Semantic Embedding]
- Work mode (Remote vs Onsite)                                        │
- Geographic eligibility                                              │
- Seniority bounds                                                    ▼
    │                                                 [Job Semantic Embedding]
    ▼                                                                 │
[Passing Candidate Jobs Pool]                                         │
    │                                                                 ▼
    ├─────────────────────────────────────────────────► [Dense Vector Similarity (0-100)]
    │                                                   - Cosine distance
    ▼                                                                 │
[Keyword & Skill Taxonomy Match (0-100)]                              │
- Explicit skill overlap                                              │
- Mandatory vs preferred technology matches                           │
    │                                                                 │
    └────────────────────────────────┬────────────────────────────────┘
                                     ▼
                      [Weighted Composite Score]
        Score = (0.50 * SemanticScore) + (0.35 * SkillScore) + (0.15 * TitleScore)
                                     │
                                     ▼
                       [Top-N High-Confidence Candidates]
                                     │
                                     ▼
              [LLM Match Explainer (For Top Email Digest Items)]
              Generates concise "Why you match" rationales:
              - "Matches 4/4 core skills: Python, FastAPI, Docker, PostgreSQL"
              - "Aligned with your Senior Backend Engineer background"
```

---

## 6. Email Delivery & Notification Engine

Job seekers experience email fatigue quickly if notifications are repetitive, unstyled, or delivered at erratic hours. The email pipeline must be bulletproof:

### Email Architecture Specifications:
1. **Digest Cadence**:
   - **Instant Alerts**: Triggered only for match scores exceeding 90%.
   - **Daily Digest (Recommended Default)**: Aggregated top 5–10 new matches delivered at 8:00 AM candidate local time.
   - **Weekly Digest**: Executive summary of trends, top salary matches, and new company openings.
2. **HTML Email Aesthetics & Ergonomics**:
   - Clean, modern, responsive email layout compatible with Apple Mail, Gmail, Outlook (desktop & mobile).
   - High-contrast typography, company avatar badges, salary indicators, work-mode badges (Remote / Hybrid / On-site).
   - Direct CTA buttons with deep links to the canonical job post.
   - Transparent match breakdown badge (e.g., `96% Match` with highlighted matching skills).
3. **Asynchronous Transport**:
   - Uses `aiosmtplib` inside FastAPI's non-blocking `BackgroundTasks` (or Celery/ARQ for distributed workers).
   - Pluggable backend: Standard SMTP, Resend API, SendGrid, or AWS SES.
4. **Anti-Spam & Deliverability (RFC 8058, CAN-SPAM, GDPR)**:
   - One-click unsubscribe header (`List-Unsubscribe` & `List-Unsubscribe-Post`).
   - Clear physical address and sender contact details in email footer.
   - Frequency management links ("Change to Weekly" / "Pause for 2 weeks").
   - Strict SPF, DKIM, and DMARC alignment guidance.

---

## 7. Data Model & Persistence Design

```
+----------------------------------------------------------------------------------------+
|                                  DATABASE ENTITIES                                     |
+----------------------------------------------------------------------------------------+

[User]
- id (UUID, PK)
- email (String, Unique, Indexed)
- full_name (String)
- created_at (DateTime)
- is_active (Boolean)
- email_frequency (Enum: DAILY, WEEKLY, INSTANT, PAUSED)
- min_match_threshold (Float, e.g. 0.75)

[Resume]
- id (UUID, PK)
- user_id (UUID, FK -> User.id)
- file_name (String)
- file_hash (String, Indexed)
- raw_text (Text)
- parsed_data (JSON / Dict)
- embedding (Vector / BLOB)
- created_at (DateTime)

[JobPosting]
- id (UUID, PK)
- source (String: "remoteok", "jobicy", "arbeitnow", "remotive")
- external_id (String, Indexed)
- dedupe_hash (String, Unique, Indexed)
- title (String, Indexed)
- company (String, Indexed)
- company_logo (String, Nullable)
- location (String)
- is_remote (Boolean, Indexed)
- salary_currency (String, Nullable)
- salary_min (Float, Nullable)
- salary_max (Float, Nullable)
- description (Text)
- tags (JSON / List[String])
- url (String)
- embedding (Vector / BLOB, Nullable)
- published_at (DateTime, Indexed)
- expires_at (DateTime, Nullable)
- is_active (Boolean, Default True)

[JobMatch]
- id (UUID, PK)
- user_id (UUID, FK -> User.id)
- job_id (UUID, FK -> JobPosting.id)
- match_score (Float, Indexed)
- semantic_score (Float)
- skill_score (Float)
- matched_skills (JSON / List[String])
- missing_skills (JSON / List[String])
- match_rationale (Text)
- notified (Boolean, Default False)
- notified_at (DateTime, Nullable)
- clicked (Boolean, Default False)
- created_at (DateTime)

[EmailLog]
- id (UUID, PK)
- user_id (UUID, FK -> User.id)
- recipient_email (String)
- subject (String)
- job_count (Integer)
- dispatched_at (DateTime)
- status (Enum: SENT, FAILED, BOUNCED)
- error_message (Text, Nullable)
```

---

## 8. Security, Privacy & Compliance Considerations

1. **Candidate PII Protection**: Resumes contain phone numbers, home addresses, personal links, and education history. Raw PDF documents must be securely stored, access-controlled, and never exposed via public URLs.
2. **Job Content Scraping Legality**:
   - Adhere to `robots.txt` and website terms of service.
   - Give attribution and non-redirect canonical URLs back to the origin boards (strictly required by RemoteOK, Remotive, and Jobicy).
   - Do not circumvent authentication walls or CAPTCHAs.
3. **Data Retention & Right to be Forgotten**:
   - Provide a 1-click "Delete my profile and resume" button that purges database records, vector indexes, and file uploads.
