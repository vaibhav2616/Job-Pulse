import re
from typing import List, Dict, Any, Tuple
from app.models.schemas import (
    CandidateProfile, JobPosting, JobMatch, ApplicationStatus, OpportunityPipelineSummary
)
from app.core.database import save_matches, get_matches, get_all_jobs


class HybridMatchingEngine:
    def calculate_match(self, profile: CandidateProfile, job: JobPosting) -> JobMatch:
        profile_skills_lower = {s.lower(): s for s in profile.skills}
        
        # Combine job text
        job_content = f"{job.title} {job.description} {' '.join(job.tags)}".lower()

        # 1. Skill Overlap Calculation
        matched_skills = []
        for s_low, s_orig in profile_skills_lower.items():
            pattern = rf"\b{re.escape(s_low)}\b"
            if re.search(pattern, job_content):
                matched_skills.append(s_orig)

        # Identify key job tags not in profile skills
        missing_skills = []
        for tag in job.tags:
            tag_clean = tag.strip().lower()
            if len(tag_clean) > 2 and tag_clean not in profile_skills_lower:
                missing_skills.append(tag.title())

        # Skill Score (0 to 100)
        # Ratio of candidate's skills present in job description
        skill_score = 0.0
        if profile.skills:
            # Weighted by importance of matching at least 3-4 skills
            overlap_count = len(matched_skills)
            skill_score = min(100.0, (overlap_count / max(3, min(len(profile.skills), 7))) * 100.0)

        # 2. Semantic & Title Alignment Score
        title_score = 40.0
        job_title_lower = job.title.lower()
        for role in profile.target_roles:
            role_words = [w.lower() for w in role.split() if len(w) > 2]
            matched_words = [w for w in role_words if w in job_title_lower]
            if matched_words:
                ratio = len(matched_words) / len(role_words)
                title_score = max(title_score, ratio * 100.0)

        # Remote / Location Alignment
        location_score = 90.0 if job.is_remote else 60.0

        # Composite Score: 45% Skill match + 35% Title alignment + 20% Semantic/Workmode
        composite_score = (0.45 * skill_score) + (0.35 * title_score) + (0.20 * location_score)
        composite_score = round(min(99.0, max(15.0, composite_score)), 1)

        # 3. Formulate Explainable Rationale
        if len(matched_skills) >= 4:
            rationale = f"Strong alignment with {len(matched_skills)} core competencies ({', '.join(matched_skills[:3])}). Matches your {profile.seniority.value} background."
        elif len(matched_skills) >= 2:
            rationale = f"Good technical match for {', '.join(matched_skills[:2])}. Ideal for expanding into {', '.join(missing_skills[:2]) if missing_skills else 'this tech stack'}."
        else:
            rationale = f"Domain opportunity matching your interest in {job.title}. Focuses on {', '.join(job.tags[:3]) if job.tags else 'modern software engineering'}."

        return JobMatch(
            job=job,
            match_score=composite_score,
            semantic_score=round(title_score, 1),
            skill_score=round(skill_score, 1),
            matched_skills=matched_skills[:8],
            missing_skills=missing_skills[:5],
            match_rationale=rationale,
            status=ApplicationStatus.MATCHED
        )

    def evaluate_and_rank_jobs(self, profile: CandidateProfile, jobs: List[JobPosting]) -> List[JobMatch]:
        matches: List[JobMatch] = []
        for job in jobs:
            match = self.calculate_match(profile, job)
            matches.append(match)

        # Sort descending by match score
        matches.sort(key=lambda m: m.match_score, reverse=True)
        save_matches(matches)
        return matches

    def get_pipeline_summary(self, profile: CandidateProfile) -> OpportunityPipelineSummary:
        all_matches = get_matches(min_score=0.0, limit=500)
        all_jobs = get_all_jobs(limit=500)

        total_scanned = max(len(all_jobs), len(all_matches))
        
        # Stage distribution
        stages = {
            ApplicationStatus.DISCOVERED.value: 0,
            ApplicationStatus.MATCHED.value: 0,
            ApplicationStatus.SAVED.value: 0,
            ApplicationStatus.APPLIED.value: 0,
            ApplicationStatus.INTERVIEWING.value: 0,
            ApplicationStatus.OFFER.value: 0,
        }

        high_score_matches = []
        for m in all_matches:
            st = m.status.value
            if st in stages:
                stages[st] += 1
            else:
                stages[ApplicationStatus.MATCHED.value] += 1
            
            if m.match_score >= profile.min_match_threshold:
                high_score_matches.append(m.match_score)

        # 100% Real-Time Dynamic Stage Calculation from Database State
        stages[ApplicationStatus.DISCOVERED.value] = total_scanned
        
        # Count exact status distribution
        matched_counter = 0
        for m in all_matches:
            st = m.status.value
            if st in stages and st != ApplicationStatus.DISCOVERED.value:
                stages[st] += 1
            if m.match_score >= profile.min_match_threshold:
                matched_counter += 1
                high_score_matches.append(m.match_score)

        stages[ApplicationStatus.MATCHED.value] = matched_counter

        # Calculate exact average score
        avg_score = round(sum(high_score_matches) / len(high_score_matches), 1) if high_score_matches else (
            round(sum(m.match_score for m in all_matches) / len(all_matches), 1) if all_matches else 0.0
        )

        # Dynamic live domain aggregation from current database jobs
        domain_counts: Dict[str, int] = {}
        for m in all_matches:
            for tag in m.job.tags:
                tag_name = tag.strip().title()
                if len(tag_name) >= 2:
                    domain_counts[tag_name] = domain_counts.get(tag_name, 0) + 1

        sorted_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_domains = [{"name": d[0], "count": d[1]} for d in sorted_domains]

        return OpportunityPipelineSummary(
            total_scanned_jobs=total_scanned,
            matched_count=stages[ApplicationStatus.MATCHED.value],
            applied_count=stages[ApplicationStatus.APPLIED.value],
            interviewing_count=stages[ApplicationStatus.INTERVIEWING.value],
            offers_count=stages[ApplicationStatus.OFFER.value],
            avg_match_score=avg_score,
            top_domains=top_domains,
            stage_breakdown=stages
        )


matching_engine = HybridMatchingEngine()
