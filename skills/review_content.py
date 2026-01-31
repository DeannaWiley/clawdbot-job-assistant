"""
Content Review & Validation Module

This module provides a second-pass review system for AI-generated resumes and cover letters.
It validates content against best practices and catches common AI mistakes.

Key checks:
1. ATS Optimization - Keywords, formatting, structure
2. Factual Accuracy - No hallucinated skills/experience
3. Grammar & Style - Professional tone, no clichés
4. Completeness - Required sections present
5. Consistency - Matches between resume and cover letter
"""
import os
import re
import yaml
from typing import Dict, List, Tuple, Optional
import requests


def load_config() -> dict:
    """Load configuration from config.yaml"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def call_openrouter(prompt: str, config: dict) -> str:
    """Call OpenRouter API for review tasks."""
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")
    
    llm_config = config['llm']
    
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": llm_config['model'],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,  # Low temp for consistent review
            "max_tokens": 2000,
        }
    )
    
    if response.status_code != 200:
        raise Exception(f"API error: {response.status_code}")
    
    return response.json()['choices'][0]['message']['content']


# =============================================================================
# CHECKLIST-BASED VALIDATORS (Rule-based, no AI needed)
# =============================================================================

def check_ats_formatting(text: str) -> Dict:
    """
    Check for ATS-friendly formatting issues.
    """
    issues = []
    warnings = []
    
    # Check for problematic characters
    if '│' in text or '┃' in text or '║' in text:
        issues.append("Contains table/box characters that ATS may not parse")
    
    if '★' in text or '●' in text or '◆' in text:
        warnings.append("Contains special bullet characters - use standard bullets")
    
    # Check for images/graphics references
    if re.search(r'\[image\]|\[logo\]|\[photo\]', text.lower()):
        issues.append("References to images detected - ATS cannot parse images")
    
    # Check section headers
    standard_headers = ['experience', 'education', 'skills', 'summary', 'objective', 'work history']
    text_lower = text.lower()
    has_standard_headers = any(h in text_lower for h in standard_headers)
    if not has_standard_headers:
        warnings.append("Missing standard section headers (Experience, Education, Skills)")
    
    # Check for dates format
    date_patterns = [
        r'\d{1,2}/\d{1,2}/\d{2,4}',  # MM/DD/YYYY
        r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}',  # Month YYYY
    ]
    has_dates = any(re.search(p, text) for p in date_patterns)
    if not has_dates:
        warnings.append("No date formatting detected - ensure work history includes dates")
    
    # Check for contact info
    has_email = bool(re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text))
    has_phone = bool(re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text))
    
    if not has_email:
        issues.append("No email address detected")
    if not has_phone:
        warnings.append("No phone number detected")
    
    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "score": max(0, 100 - len(issues) * 20 - len(warnings) * 5)
    }


def check_keyword_presence(text: str, job_keywords: List[str]) -> Dict:
    """
    Check if required keywords from job description are present.
    """
    text_lower = text.lower()
    
    found = []
    missing = []
    
    for keyword in job_keywords:
        if keyword.lower() in text_lower:
            found.append(keyword)
        else:
            missing.append(keyword)
    
    coverage = len(found) / len(job_keywords) if job_keywords else 0
    
    return {
        "passed": coverage >= 0.6,  # At least 60% coverage
        "found_keywords": found,
        "missing_keywords": missing,
        "coverage": f"{coverage:.0%}",
        "score": int(coverage * 100)
    }


def check_quantified_achievements(text: str) -> Dict:
    """
    Check if achievements include quantifiable metrics.
    """
    # Patterns for quantified achievements
    quantity_patterns = [
        r'\d+%',  # Percentages
        r'\$[\d,]+',  # Dollar amounts
        r'\d+ (clients?|customers?|users?|projects?|teams?|people)',
        r'(increased|decreased|improved|reduced|grew|saved).*\d+',
        r'\d+x',  # Multipliers
    ]
    
    matches = []
    for pattern in quantity_patterns:
        found = re.findall(pattern, text.lower())
        matches.extend(found)
    
    # Count bullet points (approximate)
    bullet_count = len(re.findall(r'^[-•*]\s', text, re.MULTILINE))
    bullet_count = max(bullet_count, text.count('\n- '), text.count('\n• '))
    
    quantified_ratio = len(matches) / max(bullet_count, 1)
    
    return {
        "passed": len(matches) >= 2,
        "quantified_achievements": len(matches),
        "total_bullets": bullet_count,
        "ratio": f"{quantified_ratio:.0%}",
        "recommendation": "Add more numbers/metrics to achievements" if len(matches) < 3 else "Good use of metrics",
        "score": min(100, len(matches) * 20)
    }


def check_cliches_and_buzzwords(text: str) -> Dict:
    """
    Detect overused phrases and buzzwords that weaken content.
    """
    cliches = [
        "team player",
        "think outside the box",
        "go-getter",
        "self-starter",
        "detail-oriented",  # Okay in skills, bad in summary
        "results-driven",
        "synergy",
        "leverage",
        "dynamic",
        "passionate about",
        "seasoned professional",
        "extensive experience",
        "proven track record",
        "excellent communication skills",
        "strong work ethic",
        "fast-paced environment",
        "hit the ground running",
        "wear many hats",
    ]
    
    text_lower = text.lower()
    found_cliches = [c for c in cliches if c in text_lower]
    
    return {
        "passed": len(found_cliches) <= 2,
        "found_cliches": found_cliches,
        "count": len(found_cliches),
        "recommendation": "Replace clichés with specific achievements" if found_cliches else "Good - no major clichés detected",
        "score": max(0, 100 - len(found_cliches) * 15)
    }


def check_length(text: str, doc_type: str = "resume") -> Dict:
    """
    Check if document length is appropriate.
    """
    word_count = len(text.split())
    
    if doc_type == "resume":
        ideal_min, ideal_max = 400, 800
        absolute_max = 1200
    else:  # cover letter
        ideal_min, ideal_max = 200, 350
        absolute_max = 500
    
    if word_count < ideal_min:
        status = "too_short"
        recommendation = f"Add more detail - currently {word_count} words, aim for {ideal_min}-{ideal_max}"
    elif word_count > absolute_max:
        status = "too_long"
        recommendation = f"Trim content - currently {word_count} words, aim for under {ideal_max}"
    elif word_count > ideal_max:
        status = "slightly_long"
        recommendation = f"Consider trimming - {word_count} words is acceptable but {ideal_max} is ideal"
    else:
        status = "good"
        recommendation = f"Good length at {word_count} words"
    
    return {
        "passed": status in ["good", "slightly_long"],
        "word_count": word_count,
        "status": status,
        "recommendation": recommendation,
        "score": 100 if status == "good" else 70 if status == "slightly_long" else 50
    }


# =============================================================================
# AI-POWERED VALIDATORS (Second LLM pass for deeper review)
# =============================================================================

def ai_check_hallucinations(
    generated_content: str,
    original_resume: str,
    config: dict
) -> Dict:
    """
    Use AI to verify generated content doesn't fabricate skills/experience.
    """
    prompt = f"""You are a fact-checker reviewing AI-generated job application content.

TASK: Compare the generated content against the original resume and identify ANY claims that:
1. Add skills NOT mentioned in the original resume
2. Add experiences or jobs NOT in the original resume  
3. Add certifications or education NOT in the original resume
4. Exaggerate metrics or achievements beyond what's stated
5. Claim years of experience not supported by the resume dates

ORIGINAL RESUME:
{original_resume}

GENERATED CONTENT TO VERIFY:
{generated_content}

Respond in this exact format:
HALLUCINATIONS_FOUND: [YES/NO]
FABRICATED_ITEMS:
- [List each fabricated claim, or "None found" if clean]
EXAGGERATIONS:
- [List any exaggerations, or "None found" if clean]
VERDICT: [PASS/FAIL]
CONFIDENCE: [HIGH/MEDIUM/LOW]"""

    response = call_openrouter(prompt, config)
    
    # Parse response
    has_hallucinations = "HALLUCINATIONS_FOUND: YES" in response.upper()
    passed = "VERDICT: PASS" in response.upper()
    
    return {
        "passed": passed,
        "has_hallucinations": has_hallucinations,
        "full_analysis": response,
        "score": 100 if passed else 30
    }


def ai_check_tone_and_professionalism(
    content: str,
    doc_type: str,
    config: dict
) -> Dict:
    """
    Use AI to evaluate tone, professionalism, and persuasiveness.
    """
    prompt = f"""You are an expert career coach reviewing a {doc_type}.

Evaluate this content for:
1. TONE: Is it professional yet personable? Not too stiff or too casual?
2. CLARITY: Are sentences clear and easy to understand?
3. PERSUASIVENESS: Does it effectively sell the candidate's value?
4. GRAMMAR: Any grammatical errors or awkward phrasing?
5. SPECIFICITY: Are claims specific or vague?

CONTENT TO REVIEW:
{content}

Provide your assessment in this format:
TONE_SCORE: [1-10]
CLARITY_SCORE: [1-10]
PERSUASIVENESS_SCORE: [1-10]
GRAMMAR_ISSUES: [List any issues or "None"]
SPECIFIC_IMPROVEMENTS:
- [List 2-3 specific suggestions to improve this content]
OVERALL_GRADE: [A/B/C/D/F]"""

    response = call_openrouter(prompt, config)
    
    # Extract scores
    tone_match = re.search(r'TONE_SCORE:\s*(\d+)', response)
    clarity_match = re.search(r'CLARITY_SCORE:\s*(\d+)', response)
    persuasive_match = re.search(r'PERSUASIVENESS_SCORE:\s*(\d+)', response)
    grade_match = re.search(r'OVERALL_GRADE:\s*([A-F])', response)
    
    tone = int(tone_match.group(1)) if tone_match else 5
    clarity = int(clarity_match.group(1)) if clarity_match else 5
    persuasive = int(persuasive_match.group(1)) if persuasive_match else 5
    grade = grade_match.group(1) if grade_match else 'C'
    
    avg_score = (tone + clarity + persuasive) / 3
    
    return {
        "passed": grade in ['A', 'B'],
        "tone_score": tone,
        "clarity_score": clarity,
        "persuasiveness_score": persuasive,
        "overall_grade": grade,
        "full_analysis": response,
        "score": int(avg_score * 10)
    }


def ai_check_job_alignment(
    content: str,
    job_description: str,
    config: dict
) -> Dict:
    """
    Use AI to verify content is well-aligned with the specific job.
    """
    prompt = f"""You are an expert recruiter reviewing an application for alignment with a job posting.

JOB DESCRIPTION:
{job_description[:2000]}

APPLICATION CONTENT:
{content}

Evaluate:
1. Does the content address the key requirements mentioned in the job?
2. Is there clear connection between candidate's experience and job needs?
3. Does it feel tailored to THIS job or generic?
4. Are the most relevant qualifications highlighted prominently?

Respond in this format:
ALIGNMENT_SCORE: [1-10]
KEY_REQUIREMENTS_ADDRESSED: [List which key job requirements are addressed]
REQUIREMENTS_MISSING: [List any key requirements NOT addressed]
FEELS_TAILORED: [YES/NO]
SUGGESTIONS:
- [2-3 specific ways to better align with this job]"""

    response = call_openrouter(prompt, config)
    
    alignment_match = re.search(r'ALIGNMENT_SCORE:\s*(\d+)', response)
    tailored_match = re.search(r'FEELS_TAILORED:\s*(YES|NO)', response.upper())
    
    alignment = int(alignment_match.group(1)) if alignment_match else 5
    is_tailored = tailored_match.group(1) == 'YES' if tailored_match else False
    
    return {
        "passed": alignment >= 7 and is_tailored,
        "alignment_score": alignment,
        "feels_tailored": is_tailored,
        "full_analysis": response,
        "score": alignment * 10
    }


# =============================================================================
# MAIN REVIEW FUNCTION
# =============================================================================

def review_generated_content(
    generated_resume_content: str,
    generated_cover_letter: str,
    original_resume: str,
    job_description: str,
    job_keywords: List[str],
    run_ai_checks: bool = True
) -> Dict:
    """
    Comprehensive review of AI-generated application materials.
    
    Args:
        generated_resume_content: The AI-tailored resume summary/bullets
        generated_cover_letter: The AI-generated cover letter
        original_resume: The user's original resume (ground truth)
        job_description: The job posting text
        job_keywords: Extracted keywords from job description
        run_ai_checks: Whether to run AI-powered checks (costs tokens)
    
    Returns:
        Comprehensive review results with pass/fail and suggestions
    """
    config = load_config()
    
    results = {
        "resume_checks": {},
        "cover_letter_checks": {},
        "cross_checks": {},
        "overall": {}
    }
    
    print("\n" + "="*60)
    print("REVIEWING AI-GENERATED CONTENT")
    print("="*60)
    
    # ===================
    # RESUME CHECKS
    # ===================
    print("\n[Resume Review]")
    
    # Rule-based checks
    results["resume_checks"]["ats_formatting"] = check_ats_formatting(generated_resume_content)
    print(f"  ATS Formatting: {'✅' if results['resume_checks']['ats_formatting']['passed'] else '❌'}")
    
    results["resume_checks"]["keywords"] = check_keyword_presence(generated_resume_content, job_keywords)
    print(f"  Keyword Coverage: {results['resume_checks']['keywords']['coverage']}")
    
    results["resume_checks"]["quantified"] = check_quantified_achievements(generated_resume_content)
    print(f"  Quantified Achievements: {results['resume_checks']['quantified']['quantified_achievements']} found")
    
    results["resume_checks"]["cliches"] = check_cliches_and_buzzwords(generated_resume_content)
    print(f"  Clichés: {results['resume_checks']['cliches']['count']} found")
    
    # ===================
    # COVER LETTER CHECKS
    # ===================
    print("\n[Cover Letter Review]")
    
    results["cover_letter_checks"]["length"] = check_length(generated_cover_letter, "cover_letter")
    print(f"  Length: {results['cover_letter_checks']['length']['word_count']} words - {results['cover_letter_checks']['length']['status']}")
    
    results["cover_letter_checks"]["cliches"] = check_cliches_and_buzzwords(generated_cover_letter)
    print(f"  Clichés: {results['cover_letter_checks']['cliches']['count']} found")
    
    results["cover_letter_checks"]["keywords"] = check_keyword_presence(generated_cover_letter, job_keywords[:10])
    print(f"  Keyword Coverage: {results['cover_letter_checks']['keywords']['coverage']}")
    
    # ===================
    # AI-POWERED CHECKS
    # ===================
    if run_ai_checks:
        print("\n[AI-Powered Deep Review]")
        
        # Hallucination check (critical!)
        print("  Checking for hallucinations...")
        results["cross_checks"]["hallucinations"] = ai_check_hallucinations(
            f"{generated_resume_content}\n\n{generated_cover_letter}",
            original_resume,
            config
        )
        print(f"  Hallucination Check: {'✅ PASS' if results['cross_checks']['hallucinations']['passed'] else '❌ FAIL - Review needed!'}")
        
        # Tone check
        print("  Checking tone and professionalism...")
        results["cover_letter_checks"]["tone"] = ai_check_tone_and_professionalism(
            generated_cover_letter,
            "cover letter",
            config
        )
        print(f"  Tone Grade: {results['cover_letter_checks']['tone']['overall_grade']}")
        
        # Job alignment check
        print("  Checking job alignment...")
        results["cross_checks"]["alignment"] = ai_check_job_alignment(
            generated_cover_letter,
            job_description,
            config
        )
        print(f"  Alignment Score: {results['cross_checks']['alignment']['alignment_score']}/10")
    
    # ===================
    # CALCULATE OVERALL
    # ===================
    all_scores = []
    all_passed = []
    critical_failures = []
    
    for category, checks in results.items():
        if category == "overall":
            continue
        for check_name, check_result in checks.items():
            if isinstance(check_result, dict) and 'score' in check_result:
                all_scores.append(check_result['score'])
                all_passed.append(check_result.get('passed', True))
                
                # Track critical failures
                if not check_result.get('passed', True):
                    if check_name == 'hallucinations':
                        critical_failures.append("⚠️ CRITICAL: AI may have fabricated content")
                    elif check_name == 'ats_formatting':
                        critical_failures.append("ATS formatting issues detected")
    
    overall_score = sum(all_scores) / len(all_scores) if all_scores else 0
    overall_passed = all(all_passed) and len(critical_failures) == 0
    
    results["overall"] = {
        "score": int(overall_score),
        "passed": overall_passed,
        "grade": "A" if overall_score >= 90 else "B" if overall_score >= 80 else "C" if overall_score >= 70 else "D" if overall_score >= 60 else "F",
        "critical_failures": critical_failures,
        "recommendation": "Ready to send!" if overall_passed else "Review and fix issues before sending"
    }
    
    print(f"\n{'='*60}")
    print(f"OVERALL SCORE: {results['overall']['score']}/100 (Grade: {results['overall']['grade']})")
    print(f"STATUS: {'✅ APPROVED' if overall_passed else '❌ NEEDS REVISION'}")
    if critical_failures:
        print(f"CRITICAL ISSUES:")
        for failure in critical_failures:
            print(f"  - {failure}")
    print(f"{'='*60}")
    
    return results


def get_improvement_suggestions(review_results: Dict) -> List[str]:
    """
    Extract actionable improvement suggestions from review results.
    """
    suggestions = []
    
    # Check resume issues
    resume_checks = review_results.get("resume_checks", {})
    
    if not resume_checks.get("ats_formatting", {}).get("passed", True):
        for issue in resume_checks["ats_formatting"].get("issues", []):
            suggestions.append(f"Fix: {issue}")
    
    if resume_checks.get("keywords", {}).get("missing_keywords"):
        missing = resume_checks["keywords"]["missing_keywords"][:5]
        suggestions.append(f"Add missing keywords: {', '.join(missing)}")
    
    if resume_checks.get("quantified", {}).get("quantified_achievements", 0) < 3:
        suggestions.append("Add more quantified achievements with numbers/percentages")
    
    if resume_checks.get("cliches", {}).get("found_cliches"):
        cliches = resume_checks["cliches"]["found_cliches"][:3]
        suggestions.append(f"Replace clichés: {', '.join(cliches)}")
    
    # Check cover letter issues
    cl_checks = review_results.get("cover_letter_checks", {})
    
    if cl_checks.get("length", {}).get("status") == "too_long":
        suggestions.append("Shorten cover letter - aim for 250-350 words")
    elif cl_checks.get("length", {}).get("status") == "too_short":
        suggestions.append("Expand cover letter with more specific examples")
    
    # Cross-check issues
    cross_checks = review_results.get("cross_checks", {})
    
    if not cross_checks.get("hallucinations", {}).get("passed", True):
        suggestions.insert(0, "⚠️ CRITICAL: Review for fabricated content and correct")
    
    if cross_checks.get("alignment", {}).get("alignment_score", 10) < 7:
        suggestions.append("Better align content with specific job requirements")
    
    return suggestions


if __name__ == "__main__":
    # Test the review system
    sample_resume = """
    John Doe - Graphic Designer
    Experience:
    - Designed marketing materials at ABC Corp
    - Created social media graphics
    Skills: Adobe Photoshop, Illustrator
    """
    
    sample_generated = """
    Experienced graphic designer with 5+ years creating impactful visual content.
    Increased engagement by 40% through redesigned social media strategy.
    Expert in Adobe Creative Suite, Figma, and brand identity development.
    """
    
    sample_cover = """
    Dear Hiring Manager,
    
    I am excited to apply for the Graphic Designer position. With my extensive 
    experience in visual design and proven track record of success, I am the 
    perfect candidate for this role.
    
    At ABC Corp, I designed marketing materials that helped drive business growth.
    I am a team player who thrives in fast-paced environments.
    
    Thank you for your consideration.
    """
    
    sample_job_keywords = ["Adobe Creative Suite", "Brand Design", "Social Media", "Marketing"]
    
    # Run review (without AI checks for testing)
    results = review_generated_content(
        generated_resume_content=sample_generated,
        generated_cover_letter=sample_cover,
        original_resume=sample_resume,
        job_description="Looking for a graphic designer...",
        job_keywords=sample_job_keywords,
        run_ai_checks=False  # Set True to test AI checks
    )
    
    print("\nImprovement Suggestions:")
    for suggestion in get_improvement_suggestions(results):
        print(f"  • {suggestion}")
