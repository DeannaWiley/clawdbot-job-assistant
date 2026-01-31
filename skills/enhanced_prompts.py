#!/usr/bin/env python3
"""
Enhanced Resume & Cover Letter Generation Prompts
==================================================
Human-authentic, ATS-optimized prompts with anti-AI language validation.
"""

# Banned AI-style phrases that reveal AI origin
BANNED_PHRASES = [
    "leveraged", "proven track record", "results-driven", "dynamic",
    "best-in-class", "cutting-edge", "synergy", "synergies", "paradigm",
    "innovative solutions", "thought leader", "game-changer", "disruptive",
    "value-add", "value proposition", "actionable insights", "drive results",
    "spearheaded", "orchestrated", "revolutionized", "pioneered",
    "passionate about", "eager to", "thrilled to", "excited to join",
    "hit the ground running", "think outside the box", "move the needle",
    "low-hanging fruit", "circle back", "deep dive", "bandwidth",
    "stakeholder alignment", "cross-functional collaboration",
    "in conclusion", "in summary", "to summarize", "overall",
    "i believe", "i think", "in my opinion",
]

# Generic buzzwords to avoid
BUZZWORDS_TO_AVOID = [
    "hardworking", "team player", "detail-oriented", "self-starter",
    "go-getter", "motivated", "dedicated", "responsible for",
    "duties included", "various tasks", "helped with", "assisted in",
]


def get_job_analysis_prompt(job_description: str, job_title: str) -> str:
    """Generate prompt for analyzing job requirements."""
    return f"""Analyze this job posting and extract the core requirements.

Job Title: {job_title}
Job Description:
{job_description}

Extract and return JSON only:
{{
    "must_have_skills": ["skill1", "skill2"],
    "nice_to_have_skills": ["skill1", "skill2"],
    "key_responsibilities": ["resp1", "resp2"],
    "experience_years": "X years",
    "education_required": "degree type",
    "ats_keywords": ["keyword1", "keyword2"],
    "company_values": ["value1", "value2"],
    "role_priority": "What problem does this role solve?"
}}

Return ONLY the JSON, no explanation."""


def get_resume_summary_prompt(
    candidate_profile: str,
    job_title: str,
    company: str,
    key_requirements: list
) -> str:
    """Generate prompt for human-authentic resume summary."""
    requirements_str = ", ".join(key_requirements[:5])
    
    return f"""Write a professional summary for a resume applying to {job_title} at {company}.

CANDIDATE BACKGROUND:
{candidate_profile}

KEY JOB REQUIREMENTS: {requirements_str}

STRICT RULES:
1. Write 2-3 sentences ONLY
2. Use FIRST PERSON implied (no "I" statements, just describe background)
3. NO banned phrases: leveraged, proven track record, results-driven, dynamic, cutting-edge, synergy, passionate about, eager to, thrilled
4. NO generic buzzwords: hardworking, team player, detail-oriented, self-starter
5. Include ONE specific, quantified achievement from the candidate's background
6. Match 2-3 skills from the job requirements naturally
7. Sound like a real human wrote this about themselves
8. Do NOT fabricate any facts, numbers, or experiences

GOOD EXAMPLE:
"Graphic designer with 3 years creating brand identities and marketing materials for B2B clients. Increased client engagement by 40% through redesigned email templates at previous agency. Skilled in Adobe Creative Suite, Figma, and motion graphics."

BAD EXAMPLE (DO NOT WRITE LIKE THIS):
"Results-driven design professional with a proven track record of leveraging cutting-edge tools to deliver dynamic solutions. Passionate team player eager to drive value."

Output ONLY the summary paragraph:"""


def get_experience_bullet_prompt(
    original_bullet: str,
    job_keywords: list,
    company_context: str
) -> str:
    """Generate prompt for rewriting experience bullets."""
    keywords_str = ", ".join(job_keywords[:8])
    
    return f"""Rewrite this resume bullet point to be more impactful and ATS-friendly.

ORIGINAL: {original_bullet}

TARGET KEYWORDS TO INCORPORATE: {keywords_str}
APPLYING TO: {company_context}

RULES:
1. Start with a strong ACTION VERB (not "Responsible for" or "Helped with")
2. Follow pattern: [Action] + [What you did] + [Result/Impact]
3. Include a SPECIFIC number or metric if possible
4. NO AI phrases: leveraged, spearheaded, orchestrated, revolutionized
5. Keep it under 2 lines
6. Sound natural, like a human describing their work
7. Do NOT invent metrics - if none exist, describe the scope instead

GOOD: "Redesigned company website navigation, reducing bounce rate by 23% and increasing time-on-page from 45s to 2m 10s"
GOOD: "Created 50+ social media graphics monthly for 8 client accounts across Instagram, LinkedIn, and Twitter"
BAD: "Leveraged cutting-edge design methodologies to revolutionize brand presence"

Output ONLY the rewritten bullet:"""


def get_cover_letter_prompt(
    candidate_profile: str,
    job_title: str,
    company: str,
    job_description: str,
    specific_achievements: list
) -> str:
    """Generate prompt for human-authentic cover letter."""
    achievements_str = "\n".join([f"- {a}" for a in specific_achievements[:3]])
    
    return f"""Write a cover letter for {job_title} at {company}.

CANDIDATE PROFILE:
{candidate_profile}

CANDIDATE'S KEY ACHIEVEMENTS:
{achievements_str}

JOB DESCRIPTION SUMMARY:
{job_description[:1500]}

STRICT REQUIREMENTS:

1. TONE: Conversational but professional. Sound like a real person, not a corporate robot.

2. STRUCTURE (4 paragraphs):
   - Opening: Why you're interested in THIS specific role at THIS company (not generic)
   - Middle 1: One specific achievement from your background that maps to their needs
   - Middle 2: Another relevant skill/experience with concrete example
   - Closing: Brief, confident close with clear next step

3. BANNED LANGUAGE (do NOT use):
   - "I am writing to express my interest..."
   - "I believe I would be a great fit..."
   - "I am excited/thrilled/eager to..."
   - "proven track record", "results-driven", "dynamic"
   - "leverage", "synergy", "paradigm"
   - "passionate about", "dedicated to"
   - "In conclusion", "To summarize"

4. REQUIRED ELEMENTS:
   - Mention company name at least once specifically
   - Reference ONE specific thing about the company/role that attracted you
   - Include at least ONE quantified result from candidate's experience
   - Show you understand what problem this role solves

5. LENGTH: 250-350 words maximum

6. DO NOT FABRICATE: Only use facts from the candidate profile

GOOD OPENING EXAMPLE:
"The Senior Designer role at Acme caught my attention because of your recent rebrand of the mobile app - the simplified navigation and bold color system stood out. I've spent the last three years doing similar work for B2B SaaS companies."

BAD OPENING (do not write like this):
"I am writing to express my keen interest in the exciting opportunity at your esteemed organization. I believe my proven track record makes me an ideal candidate."

Write the cover letter now:"""


def validate_document(text: str) -> dict:
    """
    Validate generated document for AI-tells and quality.
    Returns dict with score and issues found.
    """
    issues = []
    text_lower = text.lower()
    
    # Check for banned phrases
    for phrase in BANNED_PHRASES:
        if phrase.lower() in text_lower:
            issues.append(f"AI-tell phrase found: '{phrase}'")
    
    # Check for buzzwords
    buzzword_count = 0
    for word in BUZZWORDS_TO_AVOID:
        if word.lower() in text_lower:
            buzzword_count += 1
    if buzzword_count > 2:
        issues.append(f"Too many generic buzzwords: {buzzword_count} found")
    
    # Check for repetitive patterns
    sentences = text.split('.')
    if len(sentences) > 3:
        starts = [s.strip().split()[0].lower() for s in sentences if s.strip() and len(s.strip().split()) > 0]
        if len(starts) != len(set(starts)):
            issues.append("Repetitive sentence structure detected")
    
    # Check for overly formal AI patterns
    formal_patterns = [
        "in order to", "it is important to note", "it should be noted",
        "one of the key", "a wide range of", "a variety of",
        "significant experience", "extensive experience", "proven ability"
    ]
    for pattern in formal_patterns:
        if pattern in text_lower:
            issues.append(f"Overly formal pattern: '{pattern}'")
    
    # Calculate score - less harsh penalties for minor issues
    base_score = 100
    
    # Count critical vs minor issues
    critical_count = sum(1 for i in issues if 'proven track record' in i.lower() or 'leveraged' in i.lower())
    minor_count = len(issues) - critical_count
    
    penalty = (critical_count * 15) + (minor_count * 5)
    score = max(0, base_score - penalty)
    
    return {
        "score": score,
        "passed": score >= 70,  # Lower threshold since base resume may have some phrases
        "issues": issues,
        "issue_count": len(issues)
    }


def get_confidence_score(resume_validation: dict, cover_letter_validation: dict, job_alignment: float) -> dict:
    """
    Calculate overall confidence score for document quality.
    """
    resume_score = resume_validation.get("score", 0)
    cl_score = cover_letter_validation.get("score", 0)
    
    # Weight: 40% resume, 30% cover letter, 30% job alignment
    overall = (resume_score * 0.4) + (cl_score * 0.3) + (job_alignment * 100 * 0.3)
    
    return {
        "overall_score": round(overall, 1),
        "resume_score": resume_score,
        "cover_letter_score": cl_score,
        "job_alignment_score": round(job_alignment * 100, 1),
        "ready_to_submit": overall >= 80,
        "resume_issues": resume_validation.get("issues", []),
        "cover_letter_issues": cover_letter_validation.get("issues", [])
    }
