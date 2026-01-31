"""
Resume Tailoring Module - Uses LLM to customize resume for specific jobs
"""
import os
import sys
import yaml
import json
import subprocess
from typing import Dict, Optional
import requests


def _load_env_from_user_scope(var_name: str) -> str:
    """Load environment variable from Windows User scope if not in session."""
    value = os.environ.get(var_name)
    if value and len(value) > 10:
        return value
    
    if sys.platform == 'win32':
        try:
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command', 
                 f'[Environment]::GetEnvironmentVariable("{var_name}", "User")'],
                capture_output=True, text=True
            )
            value = result.stdout.strip()
            if value and len(value) > 10:
                os.environ[var_name] = value
                return value
        except:
            pass
    return None


# Pre-load API keys on module import
_load_env_from_user_scope('OPENROUTER_API_KEY')
_load_env_from_user_scope('GROQ_API_KEY')
_load_env_from_user_scope('GEMINI_API_KEY')


def load_config() -> dict:
    """Load configuration from config.yaml"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


FREE_FALLBACK_MODELS = [
    "meta-llama/llama-3.1-405b-instruct:free",  # Best: 405B params, excellent writing
    "nousresearch/hermes-3-llama-3.1-405b:free",  # 405B creative writing tuned
    "meta-llama/llama-3.3-70b-instruct:free",  # Great instruction following
    "qwen/qwen3-next-80b-a3b-instruct:free",  # 80B strong reasoning
    "mistralai/mistral-small-3.1-24b-instruct:free",  # Good for JSON/structured
    "google/gemma-3-27b-it:free",  # Solid general purpose
    "openai/gpt-oss-120b:free",  # OpenAI open source 120B
]


def call_gemini_fallback(prompt: str, config: dict) -> str:
    """
    Call Google Gemini API as fallback (free tier available).
    """
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")
    
    llm_config = config['llm']
    
    gemini_models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-flash-8b"]
    
    for model in gemini_models:
        try:
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": llm_config.get('temperature', 0.7),
                        "maxOutputTokens": llm_config.get('max_tokens', 2000),
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 429:
                print(f"  ⚠️ Gemini {model} rate limited, trying next...")
                continue
            else:
                print(f"  ⚠️ Gemini {model} error: {response.status_code}, trying next...")
                continue
        except Exception as e:
            print(f"  ⚠️ Gemini {model} exception: {e}, trying next...")
            continue
    
    raise ValueError("All Gemini models failed or rate limited")


def call_groq_fallback(prompt: str, config: dict) -> str:
    """
    Call Groq API - primary LLM provider (free tier).
    """
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        raise ValueError("GROQ_API_KEY not set")
    
    llm_config = config.get('llm', {})
    
    # Groq models - use llama-3.1-8b-instant as primary (faster, more reliable)
    groq_models = ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"]
    
    for model in groq_models:
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": llm_config.get('temperature', 0.7),
                    "max_tokens": min(llm_config.get('max_tokens', 2000), 8000),
                },
                timeout=90
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                # Only print error for first model, silently try next
                if model == groq_models[0]:
                    print(f"  ⚠️ Groq {model}: {response.status_code}, trying backup...")
                continue
        except Exception as e:
            if model == groq_models[0]:
                print(f"  ⚠️ Groq {model}: {e}, trying backup...")
            continue
    
    raise ValueError("Groq API failed - check API key or try again")


def call_free_fallback(prompt: str, config: dict) -> str:
    """
    Try all free LLM providers in order: Groq -> Gemini.
    Groq first since it's more reliable and has generous limits.
    """
    errors = []
    
    # Try Groq first (most reliable, generous free tier)
    if os.environ.get('GROQ_API_KEY'):
        try:
            print("  🔄 Trying Groq free tier...")
            return call_groq_fallback(prompt, config)
        except Exception as e:
            errors.append(f"Groq: {e}")
            print(f"  ⚠️ Groq failed: {e}")
    
    # Try Gemini as backup
    if os.environ.get('GEMINI_API_KEY'):
        try:
            print("  🔄 Trying Gemini free tier...")
            return call_gemini_fallback(prompt, config)
        except Exception as e:
            errors.append(f"Gemini: {e}")
            print(f"  ⚠️ Gemini failed: {e}")
    
    raise Exception(f"All free fallbacks failed: {'; '.join(errors)}. Set GROQ_API_KEY or GEMINI_API_KEY.")


def call_openrouter(prompt: str, config: dict) -> str:
    """
    Call LLM API - Groq only (OpenRouter credits exhausted).
    """
    # Use Groq directly - it's free and fast
    return call_groq_fallback(prompt, config)


def call_openrouter_legacy(prompt: str, config: dict) -> str:
    """
    Legacy OpenRouter call - kept for reference but not used.
    """
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        return call_groq_fallback(prompt, config)
    
    llm_config = config['llm']
    models_to_try = [llm_config['model']] + FREE_FALLBACK_MODELS
    
    for model in models_to_try:
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/job-assistant",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": llm_config['temperature'],
                    "max_tokens": llm_config['max_tokens'],
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            elif response.status_code == 402:
                print(f"  ⚠️ Credits exhausted for {model}, trying fallback...")
                continue
            else:
                print(f"  ⚠️ Error with {model}: {response.status_code}, trying fallback...")
                continue
        except Exception as e:
            print(f"  ⚠️ Exception with {model}: {e}, trying fallback...")
            continue
    
    # All OpenRouter models failed - try free fallbacks (Gemini, Groq)
    print("  ⚠️ All OpenRouter models failed, trying free fallbacks...")
    return call_free_fallback(prompt, config)


def extract_job_keywords(job_description: str, config: dict) -> Dict:
    """
    Extract key requirements and keywords from job description.
    """
    prompt = f"""Analyze this job description and extract:
1. Required skills (list)
2. Preferred skills (list)
3. Key responsibilities (list)
4. Important keywords for ATS (list)
5. Experience level required
6. Industry/domain

Job Description:
{job_description}

Respond in JSON format:
{{
    "required_skills": [],
    "preferred_skills": [],
    "responsibilities": [],
    "ats_keywords": [],
    "experience_level": "",
    "industry": ""
}}"""

    response = call_openrouter(prompt, config)
    
    # Parse JSON from response
    try:
        # Find JSON in response
        start = response.find('{')
        end = response.rfind('}') + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
    except json.JSONDecodeError:
        pass
    
    return {
        "required_skills": [],
        "preferred_skills": [],
        "responsibilities": [],
        "ats_keywords": [],
        "experience_level": "entry-level",
        "industry": "unknown"
    }


def tailor_resume_summary(
    resume_text: str,
    job_title: str,
    company: str,
    job_keywords: Dict,
    config: dict
) -> str:
    """
    Generate a tailored professional summary for the resume.
    Uses enhanced human-authentic prompts.
    """
    requirements_str = ", ".join(job_keywords.get('required_skills', [])[:5])
    
    prompt = f"""Write a professional summary for a resume applying to {job_title} at {company}.

CANDIDATE BACKGROUND:
{resume_text[:2000]}

KEY JOB REQUIREMENTS: {requirements_str}

STRICT RULES:
1. Write 2-3 sentences ONLY
2. Use FIRST PERSON implied (no "I" statements)
3. NO banned phrases: leveraged, proven track record, results-driven, dynamic, cutting-edge, synergy, passionate about, eager to, thrilled, spearheaded, orchestrated, pioneered, revolutionized, overall, in conclusion
4. NO generic buzzwords: hardworking, team player, detail-oriented, self-starter
5. Include ONE specific achievement from the background
6. Match 2-3 skills from job requirements naturally
7. Sound like a real human describing themselves
8. Do NOT fabricate facts

GOOD: "Graphic designer with 3 years creating brand identities for B2B clients. Increased engagement 40% through redesigned email templates. Skilled in Adobe Creative Suite and Figma."

BAD (never write like this): "Results-driven professional with proven track record leveraging cutting-edge tools."

Output ONLY the summary:"""

    return call_openrouter(prompt, config)


def tailor_resume_bullets(
    resume_text: str,
    job_keywords: Dict,
    config: dict
) -> str:
    """
    Suggest modifications to resume bullet points to better match job.
    """
    prompt = f"""You are a resume optimization expert. Review this resume and suggest 
specific modifications to make it better match this job's requirements.

Original Resume:
{resume_text}

Target Job Requirements:
- Required skills: {', '.join(job_keywords.get('required_skills', []))}
- Key responsibilities: {', '.join(job_keywords.get('responsibilities', [])[:5])}
- ATS keywords to include: {', '.join(job_keywords.get('ats_keywords', [])[:10])}

IMPORTANT RULES:
1. Only suggest changes for experiences the candidate ACTUALLY has
2. Do NOT fabricate or invent new experiences
3. Focus on rewording existing bullets to highlight relevant skills
4. Add missing keywords where they genuinely apply

Provide your suggestions in this format:
ORIGINAL: [original bullet point]
SUGGESTED: [improved version with relevant keywords]

List up to 5 suggested changes:"""

    return call_openrouter(prompt, config)


def calculate_match_score(
    resume_text: str,
    job_keywords: Dict
) -> Dict:
    """
    Calculate how well the resume matches the job requirements.
    """
    resume_lower = resume_text.lower()
    
    # Check required skills
    required = job_keywords.get('required_skills', [])
    required_matches = sum(1 for skill in required if skill.lower() in resume_lower)
    required_score = required_matches / len(required) if required else 0.5
    
    # Check preferred skills
    preferred = job_keywords.get('preferred_skills', [])
    preferred_matches = sum(1 for skill in preferred if skill.lower() in resume_lower)
    preferred_score = preferred_matches / len(preferred) if preferred else 0.5
    
    # Check ATS keywords
    ats_keywords = job_keywords.get('ats_keywords', [])
    ats_matches = sum(1 for kw in ats_keywords if kw.lower() in resume_lower)
    ats_score = ats_matches / len(ats_keywords) if ats_keywords else 0.5
    
    # Weighted overall score
    overall_score = (required_score * 0.5 + preferred_score * 0.3 + ats_score * 0.2)
    
    return {
        "overall_score": round(overall_score * 100),
        "required_skills_match": f"{required_matches}/{len(required)}",
        "preferred_skills_match": f"{preferred_matches}/{len(preferred)}",
        "ats_keywords_match": f"{ats_matches}/{len(ats_keywords)}",
        "matched_required": [s for s in required if s.lower() in resume_lower],
        "missing_required": [s for s in required if s.lower() not in resume_lower],
    }


def tailor_resume(
    resume_text: str,
    job_title: str,
    company: str,
    job_description: str
) -> Dict:
    """
    Main function to tailor a resume for a specific job.
    
    Args:
        resume_text: The candidate's base resume text
        job_title: Title of the job applying for
        company: Company name
        job_description: Full job description text
    
    Returns:
        Dictionary with tailored content and match score
    """
    config = load_config()
    
    print(f"Tailoring resume for: {job_title} at {company}")
    
    # Extract job keywords
    print("  Analyzing job requirements...")
    job_keywords = extract_job_keywords(job_description, config)
    
    # Calculate match score
    print("  Calculating match score...")
    match_score = calculate_match_score(resume_text, job_keywords)
    
    # Generate tailored summary
    print("  Generating tailored summary...")
    tailored_summary = tailor_resume_summary(
        resume_text, job_title, company, job_keywords, config
    )
    
    # Generate bullet point suggestions
    print("  Generating bullet point suggestions...")
    bullet_suggestions = tailor_resume_bullets(resume_text, job_keywords, config)
    
    return {
        "job_title": job_title,
        "company": company,
        "match_score": match_score,
        "job_keywords": job_keywords,
        "tailored_summary": tailored_summary,
        "bullet_suggestions": bullet_suggestions,
    }


if __name__ == "__main__":
    # Test with sample data
    sample_resume = """
    Deanna Wiley
    Graphic Designer | Oakland, CA
    
    EXPERIENCE
    Junior Graphic Designer - Creative Agency (2023-Present)
    - Designed marketing materials including brochures, social media graphics, and email templates
    - Collaborated with marketing team on brand consistency across campaigns
    - Used Adobe Photoshop and Illustrator daily for design work
    
    Design Intern - Local Startup (2022-2023)
    - Created visual content for social media platforms
    - Assisted senior designers with client projects
    
    SKILLS
    Adobe Creative Suite (Photoshop, Illustrator, InDesign)
    Figma, Canva
    Social Media Design
    Brand Identity
    """
    
    sample_job = """
    Graphic Designer at ACME Corp
    
    We're looking for a creative Graphic Designer to join our marketing team.
    
    Requirements:
    - 1-3 years of graphic design experience
    - Proficiency in Adobe Creative Suite
    - Experience with social media content creation
    - Strong portfolio demonstrating brand design work
    
    Responsibilities:
    - Create visual content for digital and print campaigns
    - Maintain brand consistency across all materials
    - Collaborate with marketing and product teams
    """
    
    result = tailor_resume(
        sample_resume,
        "Graphic Designer",
        "ACME Corp",
        sample_job
    )
    
    print("\n" + "="*50)
    print(f"Match Score: {result['match_score']['overall_score']}%")
    print(f"Matched Skills: {result['match_score']['matched_required']}")
    print(f"Missing Skills: {result['match_score']['missing_required']}")
    print("\nTailored Summary:")
    print(result['tailored_summary'])
