"""
Cover Letter Generation Module - Uses LLM to create personalized cover letters
"""
import os
import sys
import yaml
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
    
    # Try primary model first, then fallback to free models
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


def generate_cover_letter(
    resume_text: str,
    job_title: str,
    company: str,
    job_description: str,
    job_keywords: Optional[Dict] = None,
    user_name: Optional[str] = None
) -> str:
    """
    Generate a personalized cover letter for a specific job.
    
    Args:
        resume_text: The candidate's resume text
        job_title: Title of the job
        company: Company name
        job_description: Full job description
        job_keywords: Optional pre-extracted keywords from tailor_resume
        user_name: Candidate's name (will be extracted from config if not provided)
    
    Returns:
        Generated cover letter text
    """
    config = load_config()
    
    if not user_name:
        user_name = config['user']['name']
    
    # Build context about matched skills if keywords provided
    skills_context = ""
    if job_keywords:
        matched = job_keywords.get('matched_required', [])
        if matched:
            skills_context = f"\n\nThe candidate's key matching skills include: {', '.join(matched)}"
    
    prompt = f"""Write a cover letter for {job_title} at {company}.

CANDIDATE: {user_name}

BACKGROUND:
{resume_text[:2500]}

JOB REQUIREMENTS:
{job_description[:1500]}
{skills_context}

STRUCTURE (4 short paragraphs, 250-350 words total):
1. Opening: Why THIS role at THIS company interests you (be specific, not generic)
2. Body 1: One achievement from background that matches their needs (with metrics if available)
3. Body 2: Another relevant skill/experience with concrete example
4. Closing: Confident close, mention next step

BANNED LANGUAGE (NEVER use these - will cause rejection):
- "I am writing to express my interest..."
- "I believe I would be a great fit..."
- "I am excited/thrilled/eager to..."
- "proven track record", "results-driven", "dynamic"
- "leverage", "synergy", "paradigm"
- "spearhead", "spearheaded", "orchestrated", "pioneered", "revolutionized"
- "passionate about", "dedicated to"
- "In conclusion", "To summarize", "Overall"
- "hardworking", "team player", "self-starter"
- "extensive experience", "significant experience"

REQUIRED:
- Mention {company} by name at least once
- Include ONE quantified result from candidate's experience
- Sound like a real human wrote this, not a template
- Do NOT fabricate facts

GOOD OPENING:
"The Designer role at Acme caught my attention - your recent app rebrand with the bold color system stood out. I've spent three years doing similar work for SaaS companies."

BAD OPENING (never write like this):
"I am writing to express my keen interest in this exciting opportunity. I believe my proven track record makes me an ideal candidate."

OUTPUT RULES:
- Start with "Dear Hiring Manager," 
- End with "Best regards," then {user_name}
- Output ONLY the letter, no notes or explanations

Write the cover letter now:"""

    cover_letter = call_openrouter(prompt, config)
    
    # Clean any AI markers that might have slipped through
    cover_letter = clean_ai_markers(cover_letter)
    
    return cover_letter


def clean_ai_markers(text: str) -> str:
    """Remove any AI-generated markers or prefixes from text."""
    import re
    
    # Common AI introduction patterns to remove
    ai_patterns = [
        r"^Here'?s?\s+(a\s+)?tailored\s+cover\s+letter[^:]*:\s*",
        r"^Here\s+is\s+(the\s+)?cover\s+letter[^:]*:\s*",
        r"^I'?ve\s+written[^:]*:\s*",
        r"^Below\s+is[^:]*:\s*",
        r"^The\s+following[^:]*:\s*",
        r"^\*\*Cover\s+Letter\*\*\s*",
        r"^Cover\s+Letter:?\s*\n+",
    ]
    
    for pattern in ai_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)
    
    # Remove markdown citations like [berkeley.edu] or [source]
    text = re.sub(r'\[[\w\.\-/]+\]\([^)]+\)', '', text)
    text = re.sub(r'\[[^\]]+\.(edu|com|org|net)[^\]]*\]', '', text)
    
    # Remove trailing notes/explanations after signature
    signature_patterns = [
        r'(Best regards,?\s*\n[^\n]+)(\n\n---.*$)',
        r'(Sincerely,?\s*\n[^\n]+)(\n\n---.*$)',
        r'(Warm regards,?\s*\n[^\n]+)(\n\nThis cover letter.*$)',
        r'(Best,?\s*\n[^\n]+)(\n\nNote:.*$)',
    ]
    
    for pattern in signature_patterns:
        text = re.sub(pattern, r'\1', text, flags=re.IGNORECASE | re.DOTALL)
    
    return text.strip()


def generate_email_body(
    job_title: str,
    company: str,
    cover_letter: str,
    user_name: str
) -> str:
    """
    Generate a brief email body to accompany the cover letter/resume attachment.
    """
    config = load_config()
    
    prompt = f"""Write a brief, professional email body (3-4 sentences) to accompany 
a job application for the {job_title} position at {company}.

The email should:
- Be concise and professional
- Reference the attached resume and cover letter
- Express interest in the role
- Include a polite sign-off

Candidate name: {user_name}

Write only the email body (no subject line):"""

    return call_openrouter(prompt, config)


def format_cover_letter_for_pdf(
    cover_letter: str,
    user_name: str,
    user_email: str,
    user_phone: str,
    job_title: str,
    company: str
) -> str:
    """
    Format cover letter with proper header for PDF generation.
    """
    from datetime import datetime
    
    header = f"""{user_name}
{user_email}
{user_phone}

{datetime.now().strftime('%B %d, %Y')}

Hiring Manager
{company}

Re: {job_title} Position

"""
    
    return header + cover_letter


def write_cover_letter(
    resume_text: str,
    job_title: str,
    company: str,
    job_description: str,
    job_keywords: Optional[Dict] = None
) -> Dict:
    """
    Main function to generate a complete cover letter package.
    
    Returns:
        Dictionary with cover letter, email body, and formatted version
    """
    config = load_config()
    user_config = config['user']
    
    print(f"Generating cover letter for: {job_title} at {company}")
    
    # Generate main cover letter
    print("  Writing cover letter...")
    cover_letter = generate_cover_letter(
        resume_text=resume_text,
        job_title=job_title,
        company=company,
        job_description=job_description,
        job_keywords=job_keywords,
        user_name=user_config['name']
    )
    
    # Generate email body
    print("  Writing email body...")
    email_body = generate_email_body(
        job_title=job_title,
        company=company,
        cover_letter=cover_letter,
        user_name=user_config['name']
    )
    
    # Format for PDF
    formatted = format_cover_letter_for_pdf(
        cover_letter=cover_letter,
        user_name=user_config['name'],
        user_email=user_config.get('email', ''),
        user_phone=user_config.get('phone', ''),
        job_title=job_title,
        company=company
    )
    
    return {
        "job_title": job_title,
        "company": company,
        "cover_letter": cover_letter,
        "email_body": email_body,
        "formatted_letter": formatted,
        "word_count": len(cover_letter.split()),
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
    - Increased social media engagement by 35% through improved visual content
    
    Design Intern - Local Startup (2022-2023)
    - Created visual content for social media platforms
    - Assisted senior designers with client projects
    
    SKILLS
    Adobe Creative Suite, Figma, Brand Identity, Social Media Design
    """
    
    sample_job = """
    Graphic Designer at ACME Corp
    
    We're looking for a creative Graphic Designer to join our marketing team.
    
    Requirements:
    - 1-3 years of graphic design experience
    - Proficiency in Adobe Creative Suite
    - Experience with social media content creation
    """
    
    result = write_cover_letter(
        sample_resume,
        "Graphic Designer",
        "ACME Corp",
        sample_job
    )
    
    print("\n" + "="*50)
    print(f"Word Count: {result['word_count']}")
    print("\nCover Letter:")
    print(result['cover_letter'])
    print("\nEmail Body:")
    print(result['email_body'])
