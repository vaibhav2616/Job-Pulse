import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pdfplumber
import docx
from app.models.schemas import CandidateProfile, SeniorityLevel, WorkMode, WorkExperience

# Comprehensive technology & professional skill dictionary
KNOWN_SKILLS = [
    # Languages
    "Python", "JavaScript", "TypeScript", "Go", "Golang", "Java", "C++", "C#", "Rust", "Ruby", "PHP", "SQL", "HTML", "CSS",
    # Frameworks & Libraries
    "FastAPI", "Django", "Flask", "React", "Next.js", "Vue", "Angular", "Node.js", "Express", "Spring Boot", "PyTorch", "TensorFlow",
    # Databases & Caching
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "DynamoDB", "Elasticsearch", "Cassandra", "Chroma", "Qdrant",
    # DevOps & Infrastructure
    "Docker", "Kubernetes", "AWS", "GCP", "Azure", "Terraform", "CI/CD", "Linux", "Nginx", "Git", "GitHub Actions",
    # Methodologies & Architecture
    "REST APIs", "GraphQL", "Microservices", "System Design", "AsyncIO", "Agile", "Scrum", "TDD", "Distributed Systems",
    # AI & Data
    "Machine Learning", "LLMs", "NLP", "Pandas", "NumPy", "Data Pipelines", "Prompt Engineering"
]


class ResumeParsingService:
    def extract_text_from_file(self, file_path: str) -> str:
        path = Path(file_path)
        ext = path.suffix.lower()
        text = ""

        if ext == ".pdf":
            try:
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        extracted = page.extract_text()
                        if extracted:
                            text += extracted + "\n"
            except Exception as e:
                print(f"[ResumeParser] Error reading PDF with pdfplumber: {e}")
        elif ext in [".docx", ".doc"]:
            try:
                doc = docx.Document(file_path)
                for para in doc.paragraphs:
                    text += para.text + "\n"
            except Exception as e:
                print(f"[ResumeParser] Error reading DOCX: {e}")
        elif ext == ".txt":
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except Exception as e:
                print(f"[ResumeParser] Error reading TXT: {e}")
        else:
            raise ValueError(f"Unsupported resume format: {ext}. Please upload a PDF, DOCX, or TXT file.")

        return text.strip()

    def parse_resume_text(self, text: str, original_filename: str = "") -> CandidateProfile:
        """Extracts structured entities, skills, contact data, and experience from resume text."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        # 1. Extract Email
        email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        emails = re.findall(email_pattern, text)
        email = emails[0] if emails else "candidate@example.com"

        # 2. Extract Phone
        phone_pattern = r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
        phones = re.findall(phone_pattern, text)
        phone = phones[0] if phones else None

        # 3. Extract Candidate Name
        # Heuristic: First 1-3 lines usually contain the candidate name
        full_name = "Candidate"
        if lines:
            first_line = lines[0]
            # Avoid picking up header junk or URLs
            if len(first_line.split()) in [2, 3, 4] and not "@" in first_line and not "http" in first_line:
                full_name = first_line
            elif len(lines) > 1 and len(lines[1].split()) in [2, 3]:
                full_name = lines[1]
            elif original_filename:
                clean_name = Path(original_filename).stem.replace("_", " ").replace("-", " ")
                clean_name = re.sub(r"(?i)\bresume\b|\bcv\b", "", clean_name).strip()
                if clean_name:
                    full_name = clean_name.title()

        # 4. Extract Skills
        extracted_skills = []
        text_lower = text.lower()
        for skill in KNOWN_SKILLS:
            # Word boundary check for short skills like Go or C#
            escaped = re.escape(skill.lower())
            if re.search(rf"\b{escaped}\b", text_lower):
                extracted_skills.append(skill)

        if not extracted_skills:
            extracted_skills = ["Python", "FastAPI", "PostgreSQL", "Docker", "REST APIs", "Git"]

        # 5. Determine Seniority & Years of Experience
        yoe = 4.0
        # Look for phrases like "X+ years of experience"
        yoe_match = re.search(r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)", text_lower)
        if yoe_match:
            try:
                yoe = float(yoe_match.group(1))
            except ValueError:
                pass
        else:
            # Count graduation or job date ranges
            year_matches = re.findall(r"\b(20\d{2}|19\d{2})\b", text)
            if len(year_matches) >= 2:
                years = [int(y) for y in year_matches]
                span = max(years) - min(years)
                if 1 <= span <= 30:
                    yoe = float(span)

        seniority = SeniorityLevel.MID
        if yoe >= 8 or re.search(r"\b(principal|staff|director|head of)\b", text_lower):
            seniority = SeniorityLevel.PRINCIPAL
        elif yoe >= 5 or re.search(r"\b(senior|sr\.)\b", text_lower):
            seniority = SeniorityLevel.SENIOR
        elif yoe <= 2 or re.search(r"\b(junior|entry|intern)\b", text_lower):
            seniority = SeniorityLevel.ENTRY

        # 6. Headline & Target Roles
        title = "Software Engineer"
        target_roles = ["Software Engineer", "Backend Developer"]
        if "fastapi" in text_lower or "python" in text_lower:
            title = f"{seniority.value.split('/')[0].strip()} Python Backend Engineer"
            target_roles = ["Senior Backend Engineer", "Python Developer", "Full-Stack Engineer"]
        elif "frontend" in text_lower or "react" in text_lower:
            title = f"{seniority.value.split('/')[0].strip()} Frontend Developer"
            target_roles = ["Frontend Engineer", "React Developer", "Web Developer"]

        # 7. Summary
        summary = f"{seniority.value} professional with approximately {yoe:.1f} years of demonstrated experience in {', '.join(extracted_skills[:4])}. Focused on building reliable, high-performance systems."

        return CandidateProfile(
            full_name=full_name,
            email=email,
            phone=phone,
            title=title,
            summary=summary,
            years_of_experience=round(yoe, 1),
            seniority=seniority,
            skills=extracted_skills,
            preferred_work_modes=[WorkMode.REMOTE],
            target_roles=target_roles,
            preferred_locations=["Remote", "Global"]
        )

    def get_sample_profiles(self) -> Dict[str, CandidateProfile]:
        return {
            "python-senior": CandidateProfile(
                full_name="Alex Mercer",
                email="alex.mercer@example.com",
                phone="+1 (555) 234-5678",
                title="Senior Python & FastAPI Backend Engineer",
                summary="Senior backend developer with 6+ years of experience designing scalable asynchronous APIs with FastAPI, PostgreSQL, Docker, and Redis. Proven track record reducing query latencies and scaling microservices.",
                years_of_experience=6.0,
                seniority=SeniorityLevel.SENIOR,
                skills=["Python", "FastAPI", "Docker", "PostgreSQL", "Redis", "AsyncIO", "REST APIs", "Git", "AWS", "System Design"],
                target_roles=["Senior Backend Engineer", "Python Developer", "Principal Software Engineer"],
                preferred_work_modes=[WorkMode.REMOTE],
                work_history=[
                    WorkExperience(
                        company="Apex Technologies",
                        role="Senior Backend Engineer",
                        duration="2021 - Present",
                        highlights=[
                            "Architected high-throughput FastAPI microservices handling 2.4M daily requests with 99.99% uptime.",
                            "Engineered distributed caching layer using Redis and PostgreSQL, reducing query latency by 45%.",
                            "Automated multi-stage Docker container deployments via GitHub Actions, accelerating release cycles by 3x."
                        ]
                    ),
                    WorkExperience(
                        company="DataPulse Labs",
                        role="Software Engineer",
                        duration="2018 - 2021",
                        highlights=[
                            "Built scalable RESTful endpoints in Python for real-time analytics dashboards serving 150k active users.",
                            "Optimized database schema and indexing strategies, eliminating query bottlenecks and saving $18k in cloud resources."
                        ]
                    )
                ],
                education=["B.S. in Computer Science - University of California, Berkeley (2014 - 2018)"]
            ),
            "frontend-react": CandidateProfile(
                full_name="Sarah Chen",
                email="sarah.chen@example.com",
                phone="+1 (555) 876-5432",
                title="Staff Frontend & UI/UX Engineer",
                summary="Frontend specialist with 7 years crafting high-performance, accessible web interfaces using Next.js, React, TypeScript, and modern CSS architectures. Passionate about sub-second load times and intuitive user journeys.",
                years_of_experience=7.0,
                seniority=SeniorityLevel.SENIOR,
                skills=["React", "Next.js", "TypeScript", "JavaScript", "HTML", "CSS", "REST APIs", "GraphQL", "Git", "CI/CD"],
                target_roles=["Staff Frontend Engineer", "React Developer", "UI/UX Engineer"],
                preferred_work_modes=[WorkMode.REMOTE],
                work_history=[
                    WorkExperience(
                        company="Veloce Digital",
                        role="Staff Frontend Engineer",
                        duration="2021 - Present",
                        highlights=[
                            "Spearheaded redesign of design system across 40+ React applications, cutting bundle size by 38%.",
                            "Engineered core Next.js application delivering sub-1.2s LCP and perfect 100 Lighthouse accessibility scores.",
                            "Mentored 6 junior engineers on TypeScript clean code and test-driven development."
                        ]
                    ),
                    WorkExperience(
                        company="CloudSphere UI",
                        role="Frontend Developer",
                        duration="2017 - 2021",
                        highlights=[
                            "Implemented interactive responsive dashboards in React and CSS serving 500k monthly visitors.",
                            "Streamlined front-end CI/CD build times by 50% using Vite and automated Jest test suites."
                        ]
                    )
                ],
                education=["B.S. in Software Engineering - University of Washington (2013 - 2017)"]
            ),
            "devops-cloud": CandidateProfile(
                full_name="Marcus Vance",
                email="marcus.vance@example.com",
                phone="+1 (555) 432-8765",
                title="Principal Cloud & DevOps Infrastructure Architect",
                summary="Cloud architect with 8+ years managing Kubernetes clusters, automated CI/CD pipelines, and infrastructure-as-code on AWS and GCP. Deep expertise in high-availability and zero-downtime deployments.",
                years_of_experience=8.5,
                seniority=SeniorityLevel.PRINCIPAL,
                skills=["Kubernetes", "Docker", "AWS", "Terraform", "CI/CD", "Linux", "Python", "Nginx", "Git", "PostgreSQL"],
                target_roles=["Cloud Infrastructure Engineer", "DevOps Architect", "Site Reliability Engineer"],
                preferred_work_modes=[WorkMode.REMOTE],
                work_history=[
                    WorkExperience(
                        company="ScaleOps Cloud",
                        role="Principal Infrastructure Architect",
                        duration="2020 - Present",
                        highlights=[
                            "Orchestrated multi-region Kubernetes migration on AWS EKS, reducing cloud computing costs by $120,000 annually.",
                            "Engineered automated Terraform pipelines and GitOps workflows with ArgoCD, achieving zero-downtime deployments.",
                            "Standardized Prometheus and Grafana telemetry monitoring for 80+ microservices."
                        ]
                    ),
                    WorkExperience(
                        company="PacketStream Networks",
                        role="DevOps Engineer",
                        duration="2016 - 2020",
                        highlights=[
                            "Automated Docker container security scans and reduced production vulnerabilities by 75%.",
                            "Designed high-availability PostgreSQL disaster recovery cluster with automated failover under 30 seconds."
                        ]
                    )
                ],
                education=["B.S. in Computer Systems Engineering - Georgia Tech (2012 - 2016)"]
            ),
            "ai-ml": CandidateProfile(
                full_name="Elena Rostova",
                email="elena.rostova@example.com",
                phone="+1 (555) 901-2345",
                title="AI & Machine Learning Application Engineer",
                summary="AI engineer specializing in LLM application architecture, vector search, embeddings, PyTorch model deployment, and FastAPI service integration. Focused on productionizing scalable generative AI systems.",
                years_of_experience=5.0,
                seniority=SeniorityLevel.SENIOR,
                skills=["Python", "PyTorch", "LLMs", "NLP", "FastAPI", "Docker", "Pandas", "NumPy", "Prompt Engineering", "PostgreSQL"],
                target_roles=["AI Engineer", "Machine Learning Specialist", "Python Developer"],
                preferred_work_modes=[WorkMode.REMOTE],
                work_history=[
                    WorkExperience(
                        company="Cognitive Intelligence Labs",
                        role="Senior AI Application Engineer",
                        duration="2021 - Present",
                        highlights=[
                            "Architected enterprise RAG retrieval pipelines using FAISS, embeddings, and FastAPI, serving 1.2M queries/month.",
                            "Fine-tuned open-source LLM models on proprietary datasets, boosting domain response accuracy by 34%.",
                            "Optimized model inference latency from 850ms to 180ms using TensorRT and vLLM acceleration."
                        ]
                    ),
                    WorkExperience(
                        company="Synapse Data Systems",
                        role="Machine Learning Engineer",
                        duration="2019 - 2021",
                        highlights=[
                            "Engineered predictive classification pipelines processing 5TB of streaming sensor telemetry daily.",
                            "Pioneered automated ML model drift monitoring and retraining pipelines in Python."
                        ]
                    )
                ],
                education=["M.S. in Artificial Intelligence - Stanford University (2017 - 2019)"]
            )
        }


resume_service = ResumeParsingService()

