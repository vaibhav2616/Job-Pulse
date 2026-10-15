# Job-Pulse ⚡

> An intelligent, real-time job discovery platform and open-source inspired ATS diagnostic suite built with FastAPI, SQLite, and vanilla modern web technologies.

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Architecture](https://img.shields.io/badge/Architecture-Bento%20Grid%20%2B%20Hybrid%20SSR-orange.svg)

---

## 🌟 Overview

**Job-Pulse** automates job discovery for engineering and tech professionals by bridging real-time multi-source job aggregation with rigorous resume scoring and diagnostic evaluation. Rather than relying on rigid, synthetic keyword matchers, Job-Pulse implements a multi-vector heuristic and semantic scoring pipeline paired with an interactive Harvard-style single-column ATS Resume Studio.

---

## ✨ Key Capabilities

### 1. Multi-Source Live Aggregator
- **Zero-Barrier Ingestion:** Aggregates fresh remote and on-site engineering roles across top developer job boards:
  - **RemoteOK API** (JSON feed)
  - **Remotive API** (Curated developer listings)
  - **Jobicy API** (Remote software & tech listings)
  - **Arbeitnow API** (European and global visa-sponsored tech roles)
- **Automatic Deduplication & Normalization:** Employs SHA-256 fingerprinting on normalized title and company tokens to eliminate duplicate listings across providers.
- **Automated Background Crawler:** Runs periodic background jobs via `asyncio` to continuously refresh the local catalog without blocking incoming requests.

### 2. Multi-Vector Resume Matching Engine
- **Jaccard Skill Intersection:** Compares candidate tech stacks with parsed requirement tags.
- **Role & Title Alignment:** Fuzzy string and semantic matching against target engineering positions.
- **Experience & Seniority Calibration:** Ensures candidates are matched with appropriate seniority tiers (Entry, Mid, Senior, Principal, Executive).
- **Work Mode Scoring:** Prioritizes Remote, Hybrid, or On-site roles based on candidate preference vectors.

### 3. Open-Source ATS Diagnostic Engine
Modeled after open-source standard-setters like *Resume-Matcher* and *OpenResume*, the diagnostic suite computes a deterministic 0–100 score across 5 essential dimensions:
- **Quantifiable Impact (25% Weight):** Detects measurable metrics, percentages (`%`), financial impact (`$`), and throughput metrics (`QPS`, `latency`, `scale`).
- **Power Action Verbs (20% Weight):** Checks opening bullet verbs against a 35+ high-impact verb dictionary (*Architected*, *Spearheaded*, *Orchestrated*, *Automated*, *Scaled*).
- **Market Keyword Density (25% Weight):** Dynamically benchmarks the candidate's skills against real-time demand across active listings.
- **Section Structural Integrity (20% Weight):** Validates required standard headers (*Summary*, *Skills*, *Experience*, *Education*).
- **Readability & Length Calibration (10% Weight):** Calibrates word count against standard 1-to-2 page density thresholds (350–750 words).

### 4. Interactive Harvard-Style ATS Studio
- **Dual-Pane Live Editor:** Form-guided builder on the left with instant Harvard-format preview on the right.
- **1-Click Remediation:** Actionable suggestion buttons (e.g., `+ Insert 'Docker' into Skills` or `+ Insert Quantified Metric`) that apply fixes live.
- **Preset Engineering Profiles:** Instant 1-click loading for Python Backend, React Frontend, Cloud Infrastructure, and AI/ML profiles.
- **Native Print & PDF Export:** Clean `@media print` styling that prints a strictly compliant single-column resume formatted for ATS parsers.

### 5. Automated Email Digests (RFC 8058 Compliant)
- **Responsive HTML Digests:** Clean visual email templates summarizing top job matches, compensation, tags, and direct apply links.
- **Deliverability & Unsubscribe:** Includes `List-Unsubscribe` headers, mailto fallbacks, and single-click opt-out endpoints.

### 6. Fluid Responsive Bento UI
- **Zero Heavy Framework Bloat:** Built with Vanilla CSS, CSS Grid, Flexbox, and vanilla ES6 JavaScript.
- **Table-to-Card Adaptation:** Mobile-friendly layouts that automatically transform wide data tables into responsive cards on mobile screens (`<768px`).
- **Floating Pill Navigation Dock:** Quick-access navigation pill supporting smooth scrolling and live status indicators.

---

## 🛠️ Tech Stack

- **Backend:** FastAPI (Python 3.10+), Pydantic v2, Uvicorn, Jinja2 Templates
- **Storage:** SQLite with `aiosqlite` and standard thread-safe connection pooling
- **HTTP Client:** `httpx` for asynchronous HTTP requests
- **Frontend:** Semantic HTML5, Vanilla CSS3 (Custom properties, Bento grid, Glassmorphism), Vanilla ES6 JavaScript
- **Document Processing:** `pdfplumber`, `python-docx`

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/vaibhav2616/Job-Pulse.git
cd Job-Pulse
```

### 2. Set Up Virtual Environment
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS / Linux:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
cp .env.example .env
# Edit .env with your desired configuration
```

### 5. Run the Application
```bash
python main.py
```
The server will start at `http://localhost:8000`.

---

## 📁 Project Architecture

```
Job-Pulse/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py            # API endpoints (jobs, matches, resume, ATS, digest)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # App settings via pydantic-settings
│   │   └── database.py          # SQLite connection and migration management
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py           # Pydantic schemas and enums
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ats_service.py       # Deterministic ATS diagnostic scoring engine
│   │   ├── email_service.py     # HTML email digest builder & sender
│   │   ├── job_service.py       # Multi-source scrapers (RemoteOK, Remotive, etc.)
│   │   ├── matching_service.py  # Multi-vector resume-to-job matching algorithm
│   │   └── resume_service.py    # Resume parsing and candidate profiles
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css        # Fluid Bento grid, ATS studio, mobile CSS
│   │   └── js/
│   │       └── app.js           # Interactive UI controllers, ATS live scorer
│   └── templates/
│       ├── digest_email.html    # Responsive email notification template
│       └── index.html           # Hybrid SSR dashboard & Harvard resume studio
├── data/                        # Local SQLite store and uploads (gitignored)
├── decisions.md                 # 25 in-depth architectural interview Q&As
├── job_finder_research.md       # Comprehensive market & technical research
├── main.py                      # FastAPI server lifecycle & background workers
├── requirements.txt             # Project dependencies
├── .env.example                 # Production environment template
└── .gitignore                   # Standard ignore rules
```

---

## 🧪 Architecture & Decisions Record

For detailed technical justifications, architectural trade-offs, and system design interviews, consult:
- [`decisions.md`](decisions.md) — 25 architectural questions covering database selection, hybrid SSR, deterministic ATS scoring, mobile responsiveness, and resilience patterns.
- [`job_finder_research.md`](job_finder_research.md) — Comprehensive technical blueprint for job aggregation, ATS parsing, and vector matching.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
