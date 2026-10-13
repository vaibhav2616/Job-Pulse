import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.models.schemas import CandidateProfile, JobPosting
from app.core.database import get_all_jobs, get_profile

# Open-Source ATS Power Verbs Library (High-impact action verbs)
POWER_VERBS = {
    "architected", "spearheaded", "engineered", "orchestrated", "scaled", "optimized",
    "automated", "streamlined", "delivered", "implemented", "designed", "built",
    "deployed", "refactored", "accelerated", "pioneered", "mentored", "standardized",
    "established", "reduced", "increased", "maximized", "minimized", "negotiated",
    "formulated", "conceptualized", "executed", "launched", "migrated", "championed",
    "consolidated", "directed", "overhauled", "restructured", "developed", "authored"
}

# Weak / Passive Verbs & Buzzwords penalized by ATS systems
WEAK_WORDS = {
    "worked on", "assisted with", "responsible for", "helped", "participated in",
    "handled", "attempted", "hard worker", "team player", "go-getter", "detail-oriented",
    "results-driven", "synergy", "think outside the box", "dynamic", "self-starter"
}


class ATSCategoryScore(BaseModel):
    category: str
    score: float  # 0 to 100
    status: str  # Excellent, Good, Fair, Needs Improvement
    feedback: str


class ATSSuggestion(BaseModel):
    id: str
    category: str
    severity: str  # high, medium, low
    title: str
    description: str
    example: Optional[str] = None
    action_type: str  # add_skill, rephrase, add_metric, structure


class ATSDiagnosticReport(BaseModel):
    overall_score: int  # 0 to 100
    grade: str  # A+, A, B, C, D
    category_scores: List[ATSCategoryScore]
    suggestions: List[ATSSuggestion]
    action_verbs_found: List[str]
    missing_market_skills: List[str]
    metrics_detected_count: int
    readability_word_count: int


class ATSScoringEngine:
    """
    Open-Source Inspired Diagnostic ATS Resume Scorer.
    Evaluates resumes against formatting rules, quantifiable metrics,
    strong active verbs, and live market keyword alignment.
    """

    def analyze_resume(
        self,
        profile: CandidateProfile,
        raw_text: Optional[str] = None
    ) -> ATSDiagnosticReport:
        # Build composite text from profile if raw_text is not supplied
        if not raw_text:
            raw_text = f"{profile.full_name}\n{profile.title}\n{profile.summary}\n"
            raw_text += " ".join(profile.skills) + "\n"
            for w in profile.work_history:
                raw_text += f"{w.role} at {w.company} {w.duration}\n"
                raw_text += "\n".join(w.highlights) + "\n"

        text_lower = raw_text.lower()
        words = re.findall(r"\b[a-zA-Z0-9-+#.]+\b", text_lower)
        word_count = len(words)

        suggestions: List[ATSSuggestion] = []
        category_scores: List[ATSCategoryScore] = []

        # =========================================================
        # 1. Quantifiable Impact & Metrics Analysis (Weight: 25%)
        # =========================================================
        # Detect numbers, percentages, currency, latency, scale
        metric_matches = re.findall(
            r"(\b\d+(?:\.\d+)?%|\$\d+(?:,\d+)*(?:[kmbKMB])?|\b\d+(?:,\d+)*\+?\s*(?:users|qps|ms|requests|clients|projects|million|k)\b|\b\d+\s*(?:fold|x)\b)",
            raw_text,
            re.IGNORECASE
        )
        metric_count = len(metric_matches)
        
        if metric_count >= 5:
            impact_score = 95.0
            impact_status = "Excellent"
            impact_feedback = f"Outstanding quantifiable impact: found {metric_count} measurable outcomes."
        elif metric_count >= 3:
            impact_score = 80.0
            impact_status = "Good"
            impact_feedback = f"Good impact metrics ({metric_count} detected). Consider adding percentages or scale to remaining bullets."
        elif metric_count >= 1:
            impact_score = 55.0
            impact_status = "Fair"
            impact_feedback = "Only 1-2 metrics detected. ATS algorithms favor quantified achievements."
            suggestions.append(ATSSuggestion(
                id="metric_gap",
                category="Impact & Metrics",
                severity="high",
                title="Add Quantifiable Metrics to Achievements",
                description="Hiring managers and ATS parsers rank bullet points with concrete numbers significantly higher.",
                example="Change 'Optimized database queries' to 'Reduced PostgreSQL query latency by 42% for 200k daily active users'",
                action_type="add_metric"
            ))
        else:
            impact_score = 35.0
            impact_status = "Needs Improvement"
            impact_feedback = "No measurable metrics detected (% savings, latency reduction, user volume)."
            suggestions.append(ATSSuggestion(
                id="no_metrics",
                category="Impact & Metrics",
                severity="high",
                title="Quantify Your Bullet Points",
                description="Include numbers, percentages, or dollar savings in at least 3 bullet points.",
                example="Example: 'Scaled asynchronous API handling 1,500 requests/sec with zero downtime'",
                action_type="add_metric"
            ))

        category_scores.append(ATSCategoryScore(
            category="Impact & Metrics",
            score=impact_score,
            status=impact_status,
            feedback=impact_feedback
        ))

        # =========================================================
        # 2. Action Verbs & Power Words Analysis (Weight: 20%)
        # =========================================================
        verbs_found = [v for v in POWER_VERBS if v in text_lower]
        weak_found = [w for w in WEAK_WORDS if w in text_lower]

        if len(verbs_found) >= 6:
            verb_score = 96.0
            verb_status = "Excellent"
            verb_feedback = f"Rich action verb vocabulary: {len(verbs_found)} high-impact verbs detected."
        elif len(verbs_found) >= 3:
            verb_score = 78.0
            verb_status = "Good"
            verb_feedback = f"Found {len(verbs_found)} power verbs. Elevate remaining bullet points with active verbs."
        else:
            verb_score = 50.0
            verb_status = "Needs Improvement"
            verb_feedback = "Low power verb density. Use strong action verbs like 'Architected', 'Spearheaded', 'Optimized'."
            suggestions.append(ATSSuggestion(
                id="weak_verbs",
                category="Action Verbs",
                severity="medium",
                title="Start Bullet Points with Power Verbs",
                description="Start every work experience bullet point with an active past-tense power verb.",
                example="Use 'Engineered', 'Orchestrated', 'Automated' instead of 'Worked on' or 'Was part of'",
                action_type="rephrase"
            ))

        # Penalize for weak clichés
        if weak_found:
            verb_score = max(20.0, verb_score - (len(weak_found) * 8.0))
            suggestions.append(ATSSuggestion(
                id="cliche_penalty",
                category="Action Verbs",
                severity="medium",
                title=f"Remove Generic Clichés ({', '.join(weak_found[:2])})",
                description="Replace generic buzzwords with specific technical achievements.",
                example="Replace 'responsible for team tasks' with 'Orchestrated weekly agile sprints across 5 engineers'",
                action_type="rephrase"
            ))

        category_scores.append(ATSCategoryScore(
            category="Action Verbs",
            score=verb_score,
            status=verb_status,
            feedback=verb_feedback
        ))

        # =========================================================
        # 3. Live Market Skills Alignment (Weight: 25%)
        # =========================================================
        # Analyze current active jobs in SQLite to find most in-demand skills
        all_jobs = get_all_jobs(limit=100)
        market_skill_counts: Dict[str, int] = {}
        for job in all_jobs:
            for tag in job.tags:
                tag_title = tag.strip().title()
                market_skill_counts[tag_title] = market_skill_counts.get(tag_title, 0) + 1

        top_market_skills = sorted(market_skill_counts.items(), key=lambda x: x[1], reverse=True)[:12]
        candidate_skills_lower = {s.lower() for s in profile.skills}

        missing_skills = []
        matched_skills = []
        for skill_name, count in top_market_skills:
            if skill_name.lower() in candidate_skills_lower:
                matched_skills.append(skill_name)
            else:
                missing_skills.append(skill_name)

        if len(matched_skills) >= 7:
            skill_score = 95.0
            skill_status = "Excellent"
            skill_feedback = f"Exceptional market alignment! Matches {len(matched_skills)} top market skills."
        elif len(matched_skills) >= 4:
            skill_score = 80.0
            skill_status = "Good"
            skill_feedback = f"Matches {len(matched_skills)} core in-demand skills. {len(missing_skills[:3])} high-value gaps found."
        else:
            skill_score = 60.0
            skill_status = "Fair"
            skill_feedback = f"Matches {len(matched_skills)} skills. Missing {', '.join(missing_skills[:3])} which appear frequently in current job listings."

        if missing_skills:
            top_missing = missing_skills[:4]
            suggestions.append(ATSSuggestion(
                id="missing_market_skills",
                category="Market Alignment",
                severity="high",
                title=f"Add High-Demand Market Skills: {', '.join(top_missing[:3])}",
                description=f"These skills are actively required by {len(all_jobs)} open postings in the database. Add them to your skills list if applicable.",
                example=f"Add tags: {', '.join(top_missing)}",
                action_type="add_skill"
            ))

        category_scores.append(ATSCategoryScore(
            category="Market Alignment",
            score=skill_score,
            status=skill_status,
            feedback=skill_feedback
        ))

        # =========================================================
        # 4. ATS Structure & Section Completeness (Weight: 20%)
        # =========================================================
        structure_score = 100.0
        missing_sections = []

        if not profile.email or "@" not in profile.email:
            structure_score -= 20
            missing_sections.append("Valid Contact Email")
        if not profile.summary or len(profile.summary) < 30:
            structure_score -= 20
            missing_sections.append("Professional Summary Statement")
        if not profile.skills or len(profile.skills) < 4:
            structure_score -= 20
            missing_sections.append("Core Technical Skills List")
        if word_count < 120:
            structure_score -= 20
            missing_sections.append("Sufficient Experience Details (Resume is too brief)")

        structure_status = "Excellent" if structure_score >= 90 else ("Good" if structure_score >= 75 else "Needs Improvement")
        structure_feedback = "Clean structure complying with standard ATS headers." if not missing_sections else f"Missing: {', '.join(missing_sections)}"

        if missing_sections:
            suggestions.append(ATSSuggestion(
                id="structure_fix",
                category="Structure & Format",
                severity="high",
                title="Complete Required ATS Sections",
                description=f"Ensure your resume contains: {', '.join(missing_sections)}.",
                action_type="structure"
            ))

        category_scores.append(ATSCategoryScore(
            category="Structure & Format",
            score=max(30.0, structure_score),
            status=structure_status,
            feedback=structure_feedback
        ))

        # =========================================================
        # 5. Length & Readability (Weight: 10%)
        # =========================================================
        if 200 <= word_count <= 800:
            readability_score = 95.0
            readability_status = "Excellent"
            readability_feedback = f"Ideal single-column length ({word_count} words). High machine readability."
        elif word_count < 200:
            readability_score = 65.0
            readability_status = "Fair"
            readability_feedback = f"Resume is relatively brief ({word_count} words). Add project or experience depth."
        else:
            readability_score = 75.0
            readability_status = "Good"
            readability_feedback = f"Length is substantial ({word_count} words). Keep under 2 pages for optimal ATS parsing."

        category_scores.append(ATSCategoryScore(
            category="Readability & Length",
            score=readability_score,
            status=readability_status,
            feedback=readability_feedback
        ))

        # Overall Composite Calculation
        overall = int(
            (0.25 * impact_score) +
            (0.20 * verb_score) +
            (0.25 * skill_score) +
            (0.20 * structure_score) +
            (0.10 * readability_score)
        )
        overall = max(25, min(99, overall))

        grade = "A+" if overall >= 92 else ("A" if overall >= 84 else ("B" if overall >= 74 else ("C" if overall >= 60 else "D")))

        return ATSDiagnosticReport(
            overall_score=overall,
            grade=grade,
            category_scores=category_scores,
            suggestions=suggestions,
            action_verbs_found=verbs_found[:8],
            missing_market_skills=missing_skills[:6],
            metrics_detected_count=metric_count,
            readability_word_count=word_count
        )


ats_engine = ATSScoringEngine()
