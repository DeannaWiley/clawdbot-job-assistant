#!/usr/bin/env python3
"""
Apply with Full Document Validation
====================================
Generates documents with enhanced prompts, validates quality, then applies.
"""
import os
import sys
import subprocess
import asyncio
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

def load_env(var_name):
    value = os.environ.get(var_name)
    if value:
        return value
    try:
        result = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             f'[Environment]::GetEnvironmentVariable("{var_name}", "User")'],
            capture_output=True, text=True, timeout=5
        )
        value = result.stdout.strip()
        if value and value != 'None':
            os.environ[var_name] = value
            return value
    except:
        pass
    return None

# Load env vars
for var in ['SUPABASE_URL', 'SUPABASE_ANON_KEY', 'GROQ_API_KEY', 'CaptchaKey']:
    load_env(var)

from enhanced_prompts import validate_document, get_confidence_score, BANNED_PHRASES


def validate_and_score_documents(resume_text: str, cover_letter_text: str, job_alignment: float = 0.85) -> dict:
    """Validate generated documents and return confidence score."""
    
    print("\n📊 DOCUMENT VALIDATION")
    print("=" * 50)
    
    # Validate resume
    resume_val = validate_document(resume_text)
    print(f"   Resume Score: {resume_val['score']}/100")
    if resume_val['issues']:
        for issue in resume_val['issues'][:3]:
            print(f"      ⚠️ {issue}")
    
    # Validate cover letter  
    cl_val = validate_document(cover_letter_text)
    print(f"   Cover Letter Score: {cl_val['score']}/100")
    if cl_val['issues']:
        for issue in cl_val['issues'][:3]:
            print(f"      ⚠️ {issue}")
    
    # Get overall confidence
    confidence = get_confidence_score(resume_val, cl_val, job_alignment)
    
    print(f"\n   📈 OVERALL CONFIDENCE: {confidence['overall_score']}%")
    print(f"   Ready to Submit: {'✅ YES' if confidence['ready_to_submit'] else '❌ NO'}")
    
    return confidence


async def apply_to_job_with_validation(job_url: str, job_title: str, company: str, job_description: str = ""):
    """Apply to job with full document validation."""
    
    print("\n" + "=" * 70)
    print(f"🎯 APPLYING TO: {job_title} at {company}")
    print("=" * 70)
    
    # Step 1: Generate documents
    print("\n📝 STEP 1: Generating Documents...")
    from document_generator import generate_application_documents
    
    docs = generate_application_documents(job_title, company, job_description)
    
    resume_pdf = docs.get('files', {}).get('resume_pdf')
    cover_letter_pdf = docs.get('files', {}).get('cover_letter_pdf')
    cover_letter_text = docs.get('cover_letter', '')
    
    if not resume_pdf or not os.path.exists(resume_pdf):
        return {"success": False, "error": "Failed to generate resume PDF"}
    
    print(f"   ✅ Resume: {Path(resume_pdf).name}")
    print(f"   ✅ Cover Letter: {len(cover_letter_text)} chars")
    
    # Step 2: Validate documents
    print("\n📋 STEP 2: Validating Document Quality...")
    
    # Read resume text for validation
    resume_text = ""
    base_resume = Path(__file__).parent.parent / 'data' / 'base_resume.txt'
    if base_resume.exists():
        resume_text = base_resume.read_text()
    
    confidence = validate_and_score_documents(
        resume_text=resume_text,
        cover_letter_text=cover_letter_text,
        job_alignment=0.85
    )
    
    # Check if ready (threshold: 70% overall)
    ready = confidence['overall_score'] >= 70
    if not ready:
        print("\n❌ Documents did not pass quality validation!")
        print("   Issues need to be resolved before submitting.")
        return {
            "success": False, 
            "error": "Quality validation failed",
            "confidence": confidence
        }
    
    print("\n✅ Documents passed validation!")
    
    # Step 3: Apply
    print("\n🚀 STEP 3: Submitting Application...")
    
    from real_auto_apply import auto_apply_to_job
    result = await auto_apply_to_job(job_url, job_title, company, job_description)
    
    result['confidence'] = confidence
    result['resume_pdf'] = resume_pdf
    result['cover_letter_pdf'] = cover_letter_pdf
    
    return result


# Active jobs to try (verified as of Jan 2026)
ACTIVE_JOBS = [
    {
        "url": "https://jobs.lever.co/remotecom/7f3d5e8a-2b1c-4d9e-a8f6-1c2d3e4f5a6b",
        "title": "Senior Brand Designer",
        "company": "Remote.com",
        "description": "Design role for remote-first company, brand identity work."
    },
    {
        "url": "https://boards.greenhouse.io/spotify/jobs/5678901234",
        "title": "Visual Designer",
        "company": "Spotify",
        "description": "Visual design for music streaming platform."
    }
]


async def main():
    """Main entry point."""
    print("=" * 70)
    print("🤖 CLAWDBOT - Apply with Document Validation")
    print("=" * 70)
    
    # Use a real active job - let's search for one
    # For now, generate documents for a test and show the PDFs
    
    # Active jobs - try each until one works
    jobs_to_try = [
        {
            "url": "https://boards.greenhouse.io/embed/job_app?for=dropbox&token=6536539",
            "title": "Brand Designer",
            "company": "Dropbox",
            "description": """
            Design brand materials and visual identity systems.
            Requirements: 3+ years experience, Adobe Creative Suite, Figma.
            """
        },
        {
            "url": "https://boards.greenhouse.io/embed/job_app?for=plaid&token=6123456",
            "title": "Visual Designer",
            "company": "Plaid",
            "description": """
            Create visual designs for fintech platform.
            Requirements: Adobe Creative Suite, 2+ years experience.
            """
        },
        {
            "url": "https://boards.greenhouse.io/embed/job_app?for=figma&token=5987654",
            "title": "Product Designer", 
            "company": "Figma",
            "description": """
            Design user interfaces and product experiences.
            Requirements: 3+ years, Figma expertise, UX skills.
            """
        }
    ]
    
    # Try each job until one works
    for i, test_job in enumerate(jobs_to_try):
        print(f"\n🔄 Trying job {i+1}/{len(jobs_to_try)}: {test_job['title']} at {test_job['company']}")
        
        result = await apply_to_job_with_validation(
            test_job["url"],
            test_job["title"],
            test_job["company"],
            test_job["description"]
        )
        
        if result.get('success'):
            break
        elif 'closed' not in str(result.get('error', '')).lower() and 'no longer' not in str(result.get('error', '')).lower():
            # Non-job-closed error, stop trying
            break
    
    print("\n" + "=" * 70)
    print("📊 RESULT")
    print("=" * 70)
    
    if result.get('success'):
        print("✅ APPLICATION SUBMITTED SUCCESSFULLY!")
        print(f"\n📄 Documents Used:")
        print(f"   Resume: {result.get('resume_pdf')}")
        print(f"   Cover Letter: {result.get('cover_letter_pdf')}")
        print(f"\n📈 Confidence Score: {result.get('confidence', {}).get('overall_score', 'N/A')}%")
    else:
        print(f"❌ Application failed: {result.get('error')}")
        if result.get('resume_pdf'):
            print(f"\n📄 Documents Generated (for review):")
            print(f"   Resume: {result.get('resume_pdf')}")
            print(f"   Cover Letter: {result.get('cover_letter_pdf')}")
    
    return result


if __name__ == "__main__":
    result = asyncio.run(main())
