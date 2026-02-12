#!/usr/bin/env python3
"""
Fetch delayed job listings from Scoutify API and write them as individual markdown files.

Environment variables:
  JOBS_API_URL  - URL of the read-only delayed jobs API endpoint
  REPO_TOPIC   - Topic filter (e.g., "software-engineer", "remote", "new-grad")
  REPO_CAMPAIGN - UTM campaign tag for links (e.g., "swe-jobs")
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

JOBS_DIR = Path(__file__).parent.parent / "jobs"
SCOUTIFY_BASE = "https://scoutify.ai"


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:80].rstrip("-")


def fetch_jobs(api_url: str, topic: str) -> list[dict]:
    """Fetch delayed jobs from the API."""
    params = {"topic": topic, "limit": 500}
    response = requests.get(api_url, params=params, timeout=30)
    response.raise_for_status()
    return response.json().get("jobs", [])


def job_to_markdown(job: dict, campaign: str) -> str:
    """Convert a job dict to a markdown file."""
    company = job.get("company_name", "Unknown")
    company_slug = job.get("company_slug", slugify(company))
    title = job.get("title", "Untitled Position")
    location = job.get("location", "Not specified")
    category = job.get("category", "General")
    posted_date = job.get("posted_date", "Unknown")
    job_url = job.get("url", "")

    company_link = f"{SCOUTIFY_BASE}/companies/{company_slug}?utm_source=github&utm_medium=repo&utm_campaign={campaign}"
    signup_link = f"{SCOUTIFY_BASE}?utm_source=github&utm_medium=repo&utm_campaign={campaign}"

    lines = [
        f"# {title} at {company}",
        "",
        "| Field | Details |",
        "|-------|---------|",
        f"| Company | [{company}]({company_link}) |",
        f"| Location | {location} |",
        f"| Category | {category} |",
        f"| Posted | {posted_date} |",
    ]

    if job_url:
        lines.append(f"| Apply | [View on company site]({job_url}) |")

    lines.extend([
        "",
        "## About This Role",
        "",
        f"This {category.lower()} position at {company} was posted on {posted_date}.",
        "",
        "## Get Real-Time Alerts",
        "",
        "This job was posted 7+ days ago. For instant alerts on new jobs like this:",
        "",
        f"**[Get Instant Job Alerts on Scoutify]({signup_link})** - Be first to apply at 8,800+ companies.",
        "",
        "---",
        f"*Data sourced from [Scoutify]({SCOUTIFY_BASE}) | Updated daily*",
    ])

    return "\n".join(lines)


def clean_old_jobs(max_age_days: int = 30) -> int:
    """Remove job files older than max_age_days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    removed = 0

    for filepath in JOBS_DIR.glob("*.md"):
        if filepath.stat().st_mtime < cutoff.timestamp():
            filepath.unlink()
            removed += 1

    return removed


def main():
    api_url = os.environ.get("JOBS_API_URL")
    topic = os.environ.get("REPO_TOPIC", "software-engineer")
    campaign = os.environ.get("REPO_CAMPAIGN", "swe-jobs")

    if not api_url:
        print("Error: JOBS_API_URL environment variable is required")
        sys.exit(1)

    # Ensure jobs directory exists
    JOBS_DIR.mkdir(exist_ok=True)

    # Fetch jobs
    print(f"Fetching {topic} jobs from API...")
    try:
        jobs = fetch_jobs(api_url, topic)
    except requests.RequestException as e:
        print(f"Error fetching jobs: {e}")
        sys.exit(1)

    print(f"  Found {len(jobs)} jobs")

    # Write job files
    written = 0
    for job in jobs:
        company_slug = slugify(job.get("company_name", "unknown"))
        title_slug = slugify(job.get("title", "untitled"))
        filename = f"{company_slug}-{title_slug}.md"
        filepath = JOBS_DIR / filename

        markdown = job_to_markdown(job, campaign)
        filepath.write_text(markdown, encoding="utf-8")
        written += 1

    print(f"  Wrote {written} job files")

    # Clean old jobs
    removed = clean_old_jobs()
    if removed:
        print(f"  Removed {removed} old job files")

    print("Done!")


if __name__ == "__main__":
    main()
