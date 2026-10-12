from email.message import EmailMessage
from pathlib import Path
from typing import List, Dict, Any, Optional
import aiosmtplib
from jinja2 import Environment, FileSystemLoader
from app.core.config import settings, BASE_DIR
from app.core.database import save_email_log, mark_matches_as_notified
from app.models.schemas import JobMatch, CandidateProfile

TEMPLATES_DIR = BASE_DIR / "app" / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)


class EmailNotificationService:
    def render_digest_html(self, profile: CandidateProfile, matches: List[JobMatch]) -> str:
        template = jinja_env.get_template("email_digest.html")
        scores = [m.match_score for m in matches]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        context = {
            "subject": f"🎯 Top {len(matches)} New Job Matches for {profile.full_name}",
            "candidate_name": profile.full_name,
            "matches": matches,
            "avg_score": avg_score,
            "manage_url": "http://localhost:8000/#profile",
            "unsubscribe_url": "http://localhost:8000/#settings",
        }
        return template.render(**context)

    async def send_job_digest(
        self,
        recipient_email: str,
        profile: CandidateProfile,
        matches: List[JobMatch]
    ) -> Dict[str, Any]:
        """Dispatches an email digest asynchronously with full error handling and fallback simulation."""
        if not matches:
            return {"status": "skipped", "message": "No new matches meet the notification threshold."}

        subject = f"🎯 JobPulse Digest: {len(matches)} High-Match Roles for {profile.full_name}"
        html_content = self.render_digest_html(profile, matches)

        # 1. Check if SMTP is configured
        has_smtp_creds = bool(settings.SMTP_PASSWORD and settings.SMTP_USER and "example" not in settings.SMTP_HOST)

        if not has_smtp_creds and settings.SIMULATE_EMAIL_IF_UNCONFIGURED:
            # Simulated delivery: save to preview scratch and log
            preview_file = BASE_DIR / "data" / "latest_email_digest_preview.html"
            preview_file.write_text(html_content, encoding="utf-8")
            
            save_email_log(
                recipient=recipient_email,
                subject=subject,
                job_count=len(matches),
                status="SIMULATED_SUCCESS",
                error=None
            )
            job_ids = [m.job.id for m in matches]
            mark_matches_as_notified(job_ids)
            
            print(f"[EmailService] Simulated delivery to {recipient_email}. Preview saved to {preview_file}")
            return {
                "status": "simulated",
                "message": f"Simulated digest dispatched to {recipient_email} ({len(matches)} jobs). HTML preview generated.",
                "preview_url": "/api/digest/preview",
                "job_count": len(matches)
            }

        # 2. Real SMTP dispatch via aiosmtplib
        try:
            msg = EmailMessage()
            msg["From"] = settings.SMTP_FROM
            msg["To"] = recipient_email
            msg["Subject"] = subject
            # Headers for RFC 8058 1-click unsubscribe compliance
            msg["List-Unsubscribe"] = f"<mailto:unsubscribe@jobpulse.local?subject=unsubscribe>"
            msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

            msg.set_content("Please enable HTML viewing to see your job matches.")
            msg.add_alternative(html_content, subtype="html")

            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                start_tls=settings.SMTP_STARTTLS
            )

            save_email_log(
                recipient=recipient_email,
                subject=subject,
                job_count=len(matches),
                status="SENT",
                error=None
            )
            job_ids = [m.job.id for m in matches]
            mark_matches_as_notified(job_ids)

            return {
                "status": "sent",
                "message": f"Successfully delivered digest email to {recipient_email}.",
                "job_count": len(matches)
            }
        except Exception as e:
            error_str = str(e)
            print(f"[EmailService] Delivery failed to {recipient_email}: {error_str}")
            save_email_log(
                recipient=recipient_email,
                subject=subject,
                job_count=len(matches),
                status="FAILED",
                error=error_str
            )
            return {
                "status": "error",
                "message": f"Failed to send email via SMTP: {error_str}",
                "job_count": len(matches)
            }


email_service = EmailNotificationService()
