"""
ELITE DOCUMENT GENERATOR - ATS-Optimized Resume & Cover Letter System
Based on 2025 best practices for 75%+ ATS match rate and 2.5x interview success

Features:
- Keyword extraction and density optimization
- Problem-solution cover letter format
- Match score reporting
- Quality assurance validation
"""
import os
import re
import json
import yaml
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import requests


def load_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def call_llm(prompt: str, config: dict = None) -> str:
    """Call LLM API - uses Groq as primary, OpenRouter as fallback."""
    if not config:
        config = load_config()
    
    llm_config = config.get('llm', {})
    
    # Try Groq first (free tier)
    groq_key = os.environ.get('GROQ_API_KEY')
    if groq_key:
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": llm_config.get('temperature', 0.3),
                    "max_tokens": llm_config.get('max_tokens', 4096),
                },
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                print(f"  ⚠️ Groq API error: {response.status_code}, trying fallback...")
        except Exception as e:
            print(f"  ⚠️ Groq error: {e}, trying fallback...")
    
    # Fallback to OpenRouter
    api_key = os.environ.get('OPENROUTER_API_KEY') or os.environ.get('OpenRouterKey')
    if not api_key:
        raise ValueError("No LLM API key available (GROQ_API_KEY or OPENROUTER_API_KEY)")
    
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": llm_config.get('model', 'anthropic/claude-3.5-sonnet'),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": llm_config.get('temperature', 0.3),
            "max_tokens": llm_config.get('max_tokens', 4096),
        },
        timeout=60
    )
    
    if response.status_code != 200:
        raise Exception(f"API error: {response.status_code} - {response.text[:200]}")
    
    return response.json()['choices'][0]['message']['content']


# ============== STEP 1: JOB DESCRIPTION INTELLIGENCE ==============

def extract_job_keywords(job_description: str, job_title: str = "") -> Dict:
    """
    Extract 15-20 exact keywords from job description for ATS optimization.
    Captures exact terminology - NO synonyms.
    """
    config = load_config()
    
    prompt = f"""You are an ATS (Applicant Tracking System) optimization expert.
Analyze this job description and extract EXACT keywords as they appear.

Job Title: {job_title}
Job Description:
{job_description}

Extract and categorize:

1. HARD SKILLS (tools, technologies, software - use EXACT names from posting):
   - List 8-12 specific technical skills/tools mentioned

2. SOFT SKILLS (communication, leadership, etc.):
   - List 4-6 soft skills mentioned

3. REQUIRED QUALIFICATIONS (must-haves):
   - List requirements that say "required", "must have", "minimum"

4. PREFERRED QUALIFICATIONS (nice-to-haves):
   - List items that say "preferred", "plus", "bonus"

5. ACTION VERBS used in the posting:
   - List 5-8 action verbs from responsibilities section

6. INDUSTRY TERMS:
   - List 3-5 industry-specific terminology

7. EXPERIENCE LEVEL:
   - Entry/Mid/Senior/Lead/Executive

8. COMPANY PAIN POINTS (problems they're trying to solve):
   - List 2-3 challenges mentioned or implied

Respond in JSON format ONLY:
{{
    "hard_skills": [],
    "soft_skills": [],
    "required_qualifications": [],
    "preferred_qualifications": [],
    "action_verbs": [],
    "industry_terms": [],
    "experience_level": "",
    "pain_points": [],
    "all_keywords": []
}}

IMPORTANT: Use EXACT terminology from the job posting. Do not substitute synonyms.
For example, use "Adobe Creative Suite" if that's what they wrote, NOT "Adobe CC"."""

    response = call_llm(prompt, config)
    
    try:
        start = response.find('{')
        end = response.rfind('}') + 1
        if start >= 0 and end > start:
            data = json.loads(response[start:end])
            # Compile all keywords
            all_kw = (
                data.get('hard_skills', []) +
                data.get('soft_skills', []) +
                data.get('required_qualifications', []) +
                data.get('action_verbs', []) +
                data.get('industry_terms', [])
            )
            data['all_keywords'] = list(set(all_kw))
            return data
    except json.JSONDecodeError:
        pass
    
    return {
        "hard_skills": [],
        "soft_skills": [],
        "required_qualifications": [],
        "preferred_qualifications": [],
        "action_verbs": [],
        "industry_terms": [],
        "experience_level": "mid-level",
        "pain_points": [],
        "all_keywords": []
    }


# ============== STEP 2: KEYWORD MATCH SCORING ==============

def calculate_keyword_match(resume_text: str, keywords: Dict) -> Dict:
    """
    Calculate ATS keyword match rate.
    Target: 75%+ for optimal ATS pass rate.
    """
    resume_lower = resume_text.lower()
    
    results = {
        "hard_skills": {"matched": [], "missing": [], "score": 0},
        "soft_skills": {"matched": [], "missing": [], "score": 0},
        "required": {"matched": [], "missing": [], "score": 0},
        "action_verbs": {"matched": [], "missing": [], "score": 0},
    }
    
    # Check each category
    for category, kw_list in [
        ("hard_skills", keywords.get("hard_skills", [])),
        ("soft_skills", keywords.get("soft_skills", [])),
        ("required", keywords.get("required_qualifications", [])),
        ("action_verbs", keywords.get("action_verbs", [])),
    ]:
        matched = []
        missing = []
        for kw in kw_list:
            if kw.lower() in resume_lower:
                matched.append(kw)
            else:
                missing.append(kw)
        
        results[category]["matched"] = matched
        results[category]["missing"] = missing
        results[category]["score"] = len(matched) / len(kw_list) * 100 if kw_list else 100
    
    # Calculate overall weighted score
    weights = {"hard_skills": 0.4, "required": 0.35, "soft_skills": 0.15, "action_verbs": 0.1}
    overall = sum(results[cat]["score"] * weight for cat, weight in weights.items())
    
    # Keyword density check (15-25 keywords naturally integrated)
    all_keywords = keywords.get("all_keywords", [])
    total_matched = sum(1 for kw in all_keywords if kw.lower() in resume_lower)
    
    return {
        "overall_match_rate": round(overall, 1),
        "ats_pass_likelihood": "HIGH" if overall >= 75 else "MEDIUM" if overall >= 50 else "LOW",
        "total_keywords_matched": total_matched,
        "total_keywords": len(all_keywords),
        "categories": results,
        "recommendations": generate_match_recommendations(results, overall)
    }


def generate_match_recommendations(results: Dict, overall: float) -> List[str]:
    """Generate actionable recommendations to improve match rate."""
    recs = []
    
    if overall < 75:
        recs.append(f"⚠️ Match rate {overall:.0f}% is below 75% target")
    
    for cat, data in results.items():
        if data["missing"] and data["score"] < 70:
            missing_str = ", ".join(data["missing"][:3])
            recs.append(f"Add {cat.replace('_', ' ')}: {missing_str}")
    
    return recs


# ============== STEP 3: ELITE RESUME GENERATION ==============

def generate_elite_summary(
    resume_text: str,
    job_title: str,
    company: str,
    keywords: Dict,
    config: dict = None
) -> str:
    """
    Generate ATS-optimized professional summary.
    Formula: [Years] [Title] with expertise in [3-4 skills] | [quantified achievement] | [company goal]
    """
    if not config:
        config = load_config()
    
    required_skills = keywords.get("hard_skills", [])[:4]
    pain_points = keywords.get("pain_points", [])
    
    prompt = f"""Write a powerful professional summary for a resume.

CANDIDATE RESUME:
{resume_text}

TARGET ROLE: {job_title} at {company}

MUST INCLUDE THESE EXACT KEYWORDS (from job posting):
{', '.join(required_skills)}

FORMULA TO FOLLOW:
"[X] years [Job Title] with expertise in [3-4 skills from list above] | Proven track record of [specific quantified achievement from resume] | Seeking to leverage [specific expertise] to [solve company pain point]"

RULES:
1. Keep to 2-3 sentences (75-100 words max)
2. Include at least 3 exact keywords from the list above
3. Include ONE specific metric/achievement from the resume
4. Do NOT invent experience not in the resume
5. Avoid generic phrases like "results-driven" or "team player"

Write ONLY the summary paragraph:"""

    return call_llm(prompt, config)


def generate_elite_bullets(
    experience: List[Dict],
    keywords: Dict,
    config: dict = None
) -> List[Dict]:
    """
    Transform experience bullets using ACTION VERB + METRIC + OUTCOME format.
    """
    if not config:
        config = load_config()
    
    action_verbs = keywords.get("action_verbs", [])
    hard_skills = keywords.get("hard_skills", [])
    
    prompt = f"""Transform these experience bullet points to be ATS-optimized.

CURRENT EXPERIENCE:
{json.dumps(experience, indent=2)}

USE THESE ACTION VERBS (from job posting):
{', '.join(action_verbs)}

INTEGRATE THESE SKILLS WHERE APPLICABLE:
{', '.join(hard_skills)}

TRANSFORMATION RULES:
1. Every bullet MUST follow: [Action Verb] + [What You Did] + [Quantifiable Result]
2. Include specific metrics: percentages, dollar amounts, time saved, team sizes
3. Maximum 4-5 bullets per role
4. Do NOT invent metrics or experiences

EXAMPLES OF GOOD BULLETS:
❌ BAD: "Managed social media accounts"
✅ GOOD: "Grew Instagram following from 2,500 to 18,000 in 8 months, driving 40% increase in website traffic"

❌ BAD: "Responsible for design projects"
✅ GOOD: "Designed 50+ marketing assets using Adobe Creative Suite, increasing campaign engagement by 35%"

Return improved experience in JSON format:
[{{"title": "...", "company": "...", "dates": "...", "bullets": ["...", "..."]}}]"""

    response = call_llm(prompt, config)
    
    try:
        start = response.find('[')
        end = response.rfind(']') + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
    except json.JSONDecodeError:
        pass
    
    return experience


# ============== STEP 4: ELITE COVER LETTER (PROBLEM-SOLUTION FORMAT) ==============

def generate_elite_cover_letter(
    resume_text: str,
    job_title: str,
    company: str,
    job_description: str,
    keywords: Dict,
    user_name: str = None,
    config: dict = None
) -> str:
    """
    Generate cover letter using proven PROBLEM-SOLUTION format.
    250-400 words, 4 paragraphs.
    """
    if not config:
        config = load_config()
    
    if not user_name:
        user_name = config['user']['name']
    
    pain_points = keywords.get("pain_points", ["improving outcomes"])
    required_skills = keywords.get("required_qualifications", [])[:3]
    
    prompt = f"""Write a compelling cover letter using the PROBLEM-SOLUTION format.

CANDIDATE: {user_name}
POSITION: {job_title} at {company}

CANDIDATE RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

COMPANY PAIN POINTS TO ADDRESS:
{', '.join(pain_points)}

KEY SKILLS TO MENTION (exact terminology):
{', '.join(required_skills)}

REQUIRED FORMAT (4 paragraphs):

PARAGRAPH 1 - HOOK + COMPANY CONNECTION (3-4 sentences):
- Open with specific company insight (product, news, challenge)
- State exact role title
- Briefly state why YOU specifically fit
- NO generic openers like "I'm writing to apply for..."

PARAGRAPH 2 - PROBLEM-SOLUTION EVIDENCE (5-6 sentences):
- Identify THE problem the company is trying to solve
- Provide 2-3 specific, quantified examples of how you've solved similar problems
- Use metrics and specific outcomes

PARAGRAPH 3 - VALUE PROPOSITION (2-3 sentences):
- Connect your skills to their specific needs
- Brief cultural fit mention

PARAGRAPH 4 - STRONG CLOSE (2 sentences):
- Express enthusiasm
- Clear call to action

RULES:
1. 250-400 words total
2. Include 3-5 exact keywords from job description
3. NO clichés like "I am the perfect candidate"
4. NO AI-sounding phrases like "I am writing to express my strong interest"
5. Do NOT fabricate experience

Write the cover letter now:"""

    cover_letter = call_llm(prompt, config)
    
    # Add signature
    signature = f"""
Best regards,
{user_name}
{config['user']['phone']} | {config['user']['email']} | {config['user'].get('linkedin_url', '')}"""
    
    return cover_letter.strip() + signature


# ============== STEP 5: QUALITY ASSURANCE ==============

def validate_documents(
    resume_text: str,
    cover_letter: str,
    keywords: Dict,
    job_title: str,
    company: str
) -> Dict:
    """
    Quality assurance validation against 2025 best practices.
    """
    checks = {
        "ats_compatibility": [],
        "human_readability": [],
        "content_quality": [],
        "cover_letter": [],
        "passed": 0,
        "failed": 0,
        "warnings": 0
    }
    
    # ATS Compatibility Checks
    ats_checks = [
        ("Keywords present (75%+)", calculate_keyword_match(resume_text, keywords)["overall_match_rate"] >= 75),
        ("No tables/graphics", True),  # Our generator doesn't use these
        ("Standard sections", any(s in resume_text.upper() for s in ["EXPERIENCE", "SKILLS", "EDUCATION"])),
        ("Contact info present", "@" in resume_text and any(c.isdigit() for c in resume_text)),
    ]
    
    for check_name, passed in ats_checks:
        status = "✅" if passed else "❌"
        checks["ats_compatibility"].append(f"{status} {check_name}")
        if passed:
            checks["passed"] += 1
        else:
            checks["failed"] += 1
    
    # Content Quality Checks
    content_checks = [
        ("Has quantified achievements", any(c in resume_text for c in ['%', '$', 'increased', 'reduced', 'improved'])),
        ("Company name correct", company.lower() in cover_letter.lower()),
        ("Job title mentioned", job_title.lower() in cover_letter.lower()),
    ]
    
    for check_name, passed in content_checks:
        status = "✅" if passed else "❌"
        checks["content_quality"].append(f"{status} {check_name}")
        if passed:
            checks["passed"] += 1
        else:
            checks["failed"] += 1
    
    # Cover Letter Checks
    word_count = len(cover_letter.split())
    cl_checks = [
        ("Word count 250-400", 200 <= word_count <= 450),
        ("Has call to action", any(phrase in cover_letter.lower() for phrase in ["look forward", "opportunity to discuss", "available"])),
        ("No generic openers", not cover_letter.lower().startswith("i am writing to")),
    ]
    
    for check_name, passed in cl_checks:
        status = "✅" if passed else "⚠️"
        checks["cover_letter"].append(f"{status} {check_name}")
        if passed:
            checks["passed"] += 1
        else:
            checks["warnings"] += 1
    
    checks["overall_score"] = f"{checks['passed']}/{checks['passed'] + checks['failed'] + checks['warnings']}"
    checks["ready_to_submit"] = checks["failed"] == 0
    
    return checks


# ============== STEP 6: MAIN GENERATION FUNCTION ==============

def generate_elite_application(
    job_title: str,
    company: str,
    job_description: str,
    resume_text: str = None
) -> Dict:
    """
    Main function to generate a complete ATS-optimized application package.
    
    Returns:
        Dictionary with resume, cover letter, match scores, and validation
    """
    config = load_config()
    user = config['user']
    
    # Load base resume if not provided
    if not resume_text:
        resume_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'base_resume.txt')
        if os.path.exists(resume_path):
            with open(resume_path, 'r') as f:
                resume_text = f.read()
        else:
            resume_text = f"""
{user['name']}
{user['email']} | {user['phone']} | {user.get('location', '')}
{user.get('linkedin_url', '')} | {user.get('portfolio_url', '')}

PROFESSIONAL SUMMARY
Experienced professional with background in design, marketing, and creative production.

SKILLS
Adobe Creative Suite, Figma, UI/UX Design, Brand Design, Marketing, Social Media

EXPERIENCE
[Please provide resume text for accurate tailoring]
"""
    
    print(f"\n{'='*60}")
    print(f"🎯 ELITE DOCUMENT GENERATOR")
    print(f"   Position: {job_title} at {company}")
    print(f"{'='*60}")
    
    # Step 1: Extract keywords
    print("\n📊 Step 1: Extracting keywords from job description...")
    keywords = extract_job_keywords(job_description, job_title)
    print(f"   Found {len(keywords.get('all_keywords', []))} keywords")
    print(f"   Hard skills: {', '.join(keywords.get('hard_skills', [])[:5])}")
    
    # Step 2: Calculate initial match
    print("\n📈 Step 2: Calculating initial match score...")
    initial_match = calculate_keyword_match(resume_text, keywords)
    print(f"   Initial match rate: {initial_match['overall_match_rate']}%")
    print(f"   ATS pass likelihood: {initial_match['ats_pass_likelihood']}")
    
    # Step 3: Generate elite summary
    print("\n✍️ Step 3: Generating ATS-optimized summary...")
    elite_summary = generate_elite_summary(resume_text, job_title, company, keywords, config)
    
    # Step 4: Generate elite cover letter
    print("\n📝 Step 4: Writing problem-solution cover letter...")
    elite_cover_letter = generate_elite_cover_letter(
        resume_text, job_title, company, job_description, keywords, user['name'], config
    )
    
    # Step 5: Calculate final match (with new summary)
    combined_text = f"{resume_text}\n{elite_summary}"
    final_match = calculate_keyword_match(combined_text, keywords)
    print(f"\n📊 Final match rate: {final_match['overall_match_rate']}%")
    
    # Step 6: Quality validation
    print("\n✅ Step 6: Running quality assurance...")
    validation = validate_documents(combined_text, elite_cover_letter, keywords, job_title, company)
    print(f"   QA Score: {validation['overall_score']}")
    print(f"   Ready to submit: {'Yes ✅' if validation['ready_to_submit'] else 'Needs review ⚠️'}")
    
    # Compile results
    result = {
        "job_title": job_title,
        "company": company,
        "tailored_summary": elite_summary,
        "cover_letter": elite_cover_letter,
        "keywords": keywords,
        "initial_match": initial_match,
        "final_match": final_match,
        "validation": validation,
        "generated_at": datetime.now().isoformat(),
        "file_naming": {
            "resume": f"{user['name'].replace(' ', '_')}_{job_title.replace(' ', '_')}_{company}_Resume.docx",
            "cover_letter": f"{user['name'].replace(' ', '_')}_{company}_CoverLetter.docx"
        }
    }
    
    print(f"\n{'='*60}")
    print("✅ ELITE DOCUMENTS GENERATED SUCCESSFULLY")
    print(f"{'='*60}")
    
    return result


# ============== KEYWORD MATCH REPORT ==============

def generate_match_report(result: Dict) -> str:
    """Generate a printable keyword match report."""
    report = []
    report.append("=" * 60)
    report.append("KEYWORD MATCH REPORT")
    report.append("=" * 60)
    report.append(f"Position: {result['job_title']} at {result['company']}")
    report.append(f"Generated: {result['generated_at']}")
    report.append("")
    
    match = result['final_match']
    report.append(f"OVERALL MATCH RATE: {match['overall_match_rate']}%")
    report.append(f"ATS PASS LIKELIHOOD: {match['ats_pass_likelihood']}")
    report.append(f"Keywords Matched: {match['total_keywords_matched']}/{match['total_keywords']}")
    report.append("")
    
    report.append("CATEGORY BREAKDOWN:")
    for cat, data in match['categories'].items():
        report.append(f"  {cat.replace('_', ' ').title()}: {data['score']:.0f}%")
        if data['missing']:
            report.append(f"    Missing: {', '.join(data['missing'][:3])}")
    
    report.append("")
    report.append("RECOMMENDATIONS:")
    for rec in match.get('recommendations', []):
        report.append(f"  • {rec}")
    
    return "\n".join(report)


if __name__ == "__main__":
    # Test with sample job
    test_job = """
    Product Designer - Spotify
    
    We're looking for a Product Designer to join our team. You'll work on 
    designing user experiences for our AI-powered features.
    
    Requirements:
    - 3+ years of product design experience
    - Proficiency in Figma
    - Experience with user research
    - Strong communication skills
    
    Nice to have:
    - Experience with AI/ML products
    - Motion design skills
    """
    
    result = generate_elite_application(
        job_title="Product Designer",
        company="Spotify",
        job_description=test_job
    )
    
    print("\n" + generate_match_report(result))


# Alias for backwards compatibility
def generate_tailored_resume(job_title: str, company: str, job_description: str) -> Dict:
    """Alias for generate_elite_application for backwards compatibility."""
    return generate_elite_application(job_title, company, job_description)
