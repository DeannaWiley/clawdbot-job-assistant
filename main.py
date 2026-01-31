"""
Job Application Assistant - Main Orchestrator

This is the main entry point that orchestrates the entire job application workflow:
1. Search for jobs matching configured criteria
2. Filter out scams and low-quality listings
3. Tailor resume and cover letter for each job
4. Send Slack notification with approval buttons
5. Process approvals and submit applications
6. Track application status

Usage:
    python main.py                  # Run full daily workflow
    python main.py --search-only    # Only search and filter jobs
    python main.py --status         # Show application status report
"""

import os
import sys
import argparse
import asyncio
from datetime import datetime
from typing import List, Dict

# Add skills directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'skills'))

from job_search import search_all_jobs, save_jobs
from filter_jobs import filter_jobs, get_filtered_jobs
from tailor_resume import tailor_resume
from write_cover_letter import write_cover_letter
from slack_notify import send_job_summary, send_application_status
from track_status import log_application, get_stats, format_status_report
from review_content import review_generated_content, get_improvement_suggestions
from job_history import (
    filter_new_jobs, mark_job_seen, mark_job_applied, mark_job_skipped,
    get_history_stats, is_job_seen, get_job_status
)


def load_base_resume() -> str:
    """Load the user's base resume text."""
    resume_paths = [
        os.path.join(os.path.dirname(__file__), 'data', 'base_resume.txt'),
        os.path.join(os.path.dirname(__file__), 'data', 'base_resume.md'),
    ]
    
    for path in resume_paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
    
    # Return placeholder if no resume found
    print("WARNING: No base resume found in data/base_resume.txt")
    print("Please add your resume to continue.")
    return ""


def run_job_search() -> List[Dict]:
    """Run job search and filtering."""
    print("\n" + "="*60)
    print("STEP 1: Searching for jobs...")
    print("="*60)
    
    jobs_df = search_all_jobs()
    
    if jobs_df.empty:
        print("No jobs found matching criteria.")
        return []
    
    # Save raw results
    save_jobs(jobs_df, os.path.join(
        os.path.dirname(__file__), 'data', 
        f'raw_jobs_{datetime.now().strftime("%Y%m%d")}.csv'
    ))
    
    print("\n" + "="*60)
    print("STEP 2: Filtering jobs...")
    print("="*60)
    
    filtered_df = get_filtered_jobs(jobs_df)
    
    if filtered_df.empty:
        print("No jobs passed filtering.")
        return []
    
    # Convert to list of dicts
    jobs = filtered_df.to_dict('records')
    print(f"\n{len(jobs)} jobs passed all filters")
    
    # DEDUPLICATION: Filter out jobs we've already seen/applied to
    print("\n" + "="*60)
    print("STEP 2b: Removing previously seen jobs...")
    print("="*60)
    
    history_stats = get_history_stats()
    print(f"  Job history: {history_stats['total_jobs_seen']} seen, {history_stats['total_applied']} applied, {history_stats['total_skipped']} skipped")
    
    new_jobs = filter_new_jobs(jobs)
    removed_count = len(jobs) - len(new_jobs)
    
    if removed_count > 0:
        print(f"  Removed {removed_count} previously seen jobs")
    
    print(f"  ✅ {len(new_jobs)} NEW jobs to review")
    
    return new_jobs


def process_jobs_for_application(jobs: List[Dict], resume_text: str) -> List[Dict]:
    """
    Process each job: tailor resume and generate cover letter.
    """
    print("\n" + "="*60)
    print("STEP 3: Tailoring documents for each job...")
    print("="*60)
    
    processed_jobs = []
    
    for i, job in enumerate(jobs):
        print(f"\n[{i+1}/{len(jobs)}] Processing: {job.get('title')} at {job.get('company')}")
        
        try:
            # Get job description
            description = job.get('description', '')
            if not description:
                print("  Skipping: No job description available")
                continue
            
            # Tailor resume
            tailored = tailor_resume(
                resume_text=resume_text,
                job_title=job.get('title', ''),
                company=job.get('company', ''),
                job_description=description
            )
            
            # Generate cover letter
            cover_letter = write_cover_letter(
                resume_text=resume_text,
                job_title=job.get('title', ''),
                company=job.get('company', ''),
                job_description=description,
                job_keywords=tailored.get('job_keywords')
            )
            
            # REVIEW STEP: Validate AI-generated content
            print("  Reviewing generated content...")
            review_results = review_generated_content(
                generated_resume_content=tailored.get('tailored_summary', ''),
                generated_cover_letter=cover_letter.get('cover_letter', ''),
                original_resume=resume_text,
                job_description=description,
                job_keywords=tailored.get('job_keywords', {}).get('required_skills', []),
                run_ai_checks=True  # Enable AI-powered validation
            )
            
            # Store review results
            job['review_results'] = review_results
            job['review_passed'] = review_results.get('overall', {}).get('passed', False)
            job['review_score'] = review_results.get('overall', {}).get('score', 0)
            
            # Get improvement suggestions if review found issues
            if not job['review_passed']:
                suggestions = get_improvement_suggestions(review_results)
                job['improvement_suggestions'] = suggestions
                print(f"  ⚠️ Review flagged issues - {len(suggestions)} suggestions")
            
            # Combine everything
            job['tailored_resume'] = tailored
            job['cover_letter'] = cover_letter
            job['match_score'] = tailored.get('match_score', {})
            
            processed_jobs.append(job)
            print(f"  ✅ Match: {tailored.get('match_score', {}).get('overall_score', 'N/A')}% | Review: {job['review_score']}/100")
            
        except Exception as e:
            print(f"  ❌ Error processing job: {e}")
            continue
    
    # Sort by match score
    processed_jobs.sort(
        key=lambda x: x.get('match_score', {}).get('overall_score', 0),
        reverse=True
    )
    
    return processed_jobs


def send_to_slack(jobs: List[Dict], user_id: str = None) -> Dict:
    """
    Send processed jobs to Slack for approval.
    Also marks jobs as 'seen' in history to prevent duplicates.
    """
    print("\n" + "="*60)
    print("STEP 4: Sending to Slack...")
    print("="*60)
    
    if not jobs:
        print("No jobs to send.")
        return {"success": False, "error": "No jobs"}
    
    # Mark all jobs as seen BEFORE sending to Slack
    # This ensures we won't ask about them again even if Slack fails
    for job in jobs:
        mark_job_seen(job, status='pending_review')
    
    result = send_job_summary(jobs, user_id=user_id)
    
    if result.get('success'):
        print(f"✅ Sent {len(jobs)} jobs to Slack")
        print(f"   Jobs marked as 'seen' - won't appear again tomorrow")
    else:
        print(f"❌ Failed to send to Slack: {result.get('error')}")
    
    return result


def run_daily_workflow(user_id: str = None, max_jobs: int = 10):
    """
    Run the complete daily workflow.
    """
    print("\n" + "#"*60)
    print(f"# JOB APPLICATION ASSISTANT - Daily Run")
    print(f"# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#"*60)
    
    # Load resume
    resume_text = load_base_resume()
    if not resume_text:
        print("\nERROR: No resume found. Please add your resume to data/base_resume.txt")
        return
    
    # Search and filter
    jobs = run_job_search()
    
    if not jobs:
        print("\nNo jobs found today. Will try again tomorrow!")
        return
    
    # Limit to top N jobs
    jobs = jobs[:max_jobs]
    print(f"\nProcessing top {len(jobs)} jobs...")
    
    # Process each job
    processed_jobs = process_jobs_for_application(jobs, resume_text)
    
    if not processed_jobs:
        print("\nNo jobs successfully processed.")
        return
    
    # Send to Slack
    send_to_slack(processed_jobs, user_id)
    
    print("\n" + "#"*60)
    print("# WORKFLOW COMPLETE")
    print(f"# Processed {len(processed_jobs)} jobs")
    print("# Waiting for approvals in Slack...")
    print("#"*60)


def show_status():
    """Display application status report."""
    print(format_status_report())


def main():
    parser = argparse.ArgumentParser(
        description='Job Application Assistant',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    Run full daily workflow
  python main.py --search-only      Only search (no Slack notification)
  python main.py --status           Show application status
  python main.py --max-jobs 5       Process only top 5 matches
        """
    )
    
    parser.add_argument(
        '--search-only',
        action='store_true',
        help='Only run job search and filtering'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show application status report'
    )
    
    parser.add_argument(
        '--max-jobs',
        type=int,
        default=10,
        help='Maximum number of jobs to process (default: 10)'
    )
    
    parser.add_argument(
        '--user-id',
        type=str,
        default=None,
        help='Slack user ID to DM (optional)'
    )
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
        return
    
    if args.search_only:
        jobs = run_job_search()
        print(f"\nFound {len(jobs)} jobs matching criteria")
        return
    
    # Run full workflow
    run_daily_workflow(user_id=args.user_id, max_jobs=args.max_jobs)


if __name__ == "__main__":
    main()
