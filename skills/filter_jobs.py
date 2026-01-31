"""
Job Filtering Module - Filters out scams, low-quality listings, and mismatches
"""
import os
import re
import yaml
import pandas as pd
from typing import List, Dict, Tuple, Optional


def load_config() -> dict:
    """Load configuration from config.yaml"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def check_scam_keywords(text: str, scam_keywords: List[str]) -> Tuple[bool, List[str]]:
    """
    Check if text contains scam indicator keywords.
    
    Returns:
        Tuple of (is_scam, list of matched keywords)
    """
    if not text or pd.isna(text):
        return False, []
    
    text_lower = text.lower()
    matched = [kw for kw in scam_keywords if kw.lower() in text_lower]
    
    return len(matched) > 0, matched


def check_unrealistic_pay(description: str) -> bool:
    """
    Check for unrealistic pay claims that indicate scam.
    """
    if not description or pd.isna(description):
        return False
    
    # Patterns for unrealistic pay
    unrealistic_patterns = [
        r'\$\d{4,}\s*/?\s*(day|daily)',  # $1000+/day
        r'\$\d{5,}\s*/?\s*(week|weekly)',  # $10000+/week
        r'guaranteed.*\$\d{4,}',
        r'earn.*\$\d{4,}.*easily',
        r'make.*\$\d{4,}.*from home',
    ]
    
    for pattern in unrealistic_patterns:
        if re.search(pattern, description.lower()):
            return True
    
    return False


def check_trusted_domain(job_url: str, trusted_domains: List[str]) -> bool:
    """
    Check if job URL is from a trusted domain.
    """
    if not job_url or pd.isna(job_url):
        return False
    
    job_url_lower = job_url.lower()
    return any(domain in job_url_lower for domain in trusted_domains)


def check_missing_company_info(company: str, description: str) -> bool:
    """
    Flag jobs with vague or missing company information.
    """
    if not company or pd.isna(company):
        return True
    
    company_lower = company.lower().strip()
    
    # Suspicious company names
    suspicious = [
        'confidential',
        'anonymous',
        'undisclosed',
        'private company',
        'hiring now',
        'urgent hiring',
    ]
    
    return any(s in company_lower for s in suspicious)


def check_deal_breakers(title: str, description: str, deal_breakers: List[str]) -> Tuple[bool, List[str]]:
    """
    Check if job contains any deal-breaker terms.
    
    Returns:
        Tuple of (has_deal_breaker, list of matched terms)
    """
    if not deal_breakers:
        return False, []
    
    text = f"{title or ''} {description or ''}".lower()
    matched = []
    
    for term in deal_breakers:
        term_lower = term.lower()
        # Check for exact or partial match
        if term_lower in text:
            matched.append(term)
    
    return len(matched) > 0, matched


def check_category_relevance(
    title: str, 
    description: str, 
    category: str,
    required_skills: List[str]
) -> Tuple[bool, float]:
    """
    Check if job is actually relevant to the searched category.
    
    Returns:
        Tuple of (is_relevant, relevance_score 0-1)
    """
    if not title:
        return False, 0.0
    
    text = f"{title} {description or ''}".lower()
    
    # Category-specific relevance keywords
    category_keywords = {
        'graphic_design': ['graphic', 'visual', 'design', 'creative', 'brand', 'adobe', 'photoshop', 'illustrator'],
        'multimedia': ['video', 'motion', 'animation', 'after effects', 'premiere', 'multimedia', '3d'],
        'administrative': ['admin', 'assistant', 'office', 'clerical', 'receptionist', 'scheduling', 'calendar'],
        'cannabis': ['cannabis', 'dispensary', 'budtender', 'marijuana', 'thc', 'cbd'],
    }
    
    keywords = category_keywords.get(category, [])
    if not keywords:
        return True, 0.5  # Unknown category, assume relevant
    
    # Count keyword matches
    matches = sum(1 for kw in keywords if kw in text)
    relevance_score = matches / len(keywords)
    
    # Check required skills
    skill_matches = 0
    if required_skills:
        for skill in required_skills:
            if skill.lower() in text:
                skill_matches += 1
        skill_score = skill_matches / len(required_skills)
        relevance_score = (relevance_score + skill_score) / 2
    
    is_relevant = relevance_score >= 0.1  # At least 10% keyword match
    
    return is_relevant, relevance_score


def filter_jobs(jobs_df: pd.DataFrame) -> pd.DataFrame:
    """
    Main filtering function - applies all filters to job listings.
    
    Args:
        jobs_df: DataFrame with job listings
    
    Returns:
        Filtered DataFrame with additional columns for filter results
    """
    if jobs_df.empty:
        return jobs_df
    
    config = load_config()
    filter_config = config['filtering']
    search_config = config['search']
    
    # Create copies to avoid SettingWithCopyWarning
    df = jobs_df.copy()
    
    # Initialize filter result columns
    df['is_scam'] = False
    df['scam_reasons'] = ''
    df['is_trusted_source'] = True
    df['is_relevant'] = True
    df['relevance_score'] = 0.5
    df['filter_passed'] = True
    
    scam_keywords = filter_config['scam_keywords']
    trusted_domains = filter_config['trusted_domains']
    
    # Get deal-breakers from preferences
    preferences = config.get('preferences', {})
    deal_breakers = preferences.get('deal_breakers', [])
    
    for idx, row in df.iterrows():
        reasons = []
        title = str(row.get('title', ''))
        description = str(row.get('description', ''))
        
        # Check deal-breakers FIRST (most important filter)
        has_deal_breaker, matched_breakers = check_deal_breakers(title, description, deal_breakers)
        if has_deal_breaker:
            reasons.append(f"Deal-breaker: {', '.join(matched_breakers)}")
        
        # Check scam keywords in description
        is_scam, matched_kw = check_scam_keywords(description, scam_keywords)
        if is_scam:
            reasons.append(f"Scam keywords: {', '.join(matched_kw)}")
        
        # Check unrealistic pay
        if check_unrealistic_pay(description):
            is_scam = True
            reasons.append("Unrealistic pay claims")
        
        # Check company info
        if check_missing_company_info(row.get('company', ''), description):
            reasons.append("Missing/vague company info")
        
        # Check trusted domain
        job_url = str(row.get('job_url', ''))
        is_trusted = check_trusted_domain(job_url, trusted_domains)
        
        # Check category relevance
        category = row.get('category', '')
        category_config = search_config['categories'].get(category, {})
        required_skills = category_config.get('required_skills', [])
        
        is_relevant, relevance_score = check_category_relevance(
            str(row.get('title', '')),
            description,
            category,
            required_skills
        )
        
        if not is_relevant:
            reasons.append(f"Low relevance ({relevance_score:.0%})")
        
        # Update row
        df.at[idx, 'is_scam'] = is_scam
        df.at[idx, 'scam_reasons'] = '; '.join(reasons)
        df.at[idx, 'is_trusted_source'] = is_trusted
        df.at[idx, 'is_relevant'] = is_relevant
        df.at[idx, 'relevance_score'] = relevance_score
        
        # Overall filter decision
        df.at[idx, 'filter_passed'] = (
            not is_scam and 
            is_trusted and 
            is_relevant and
            not has_deal_breaker and
            len(reasons) <= 1  # Allow 1 minor issue (like low relevance warning)
        )
    
    # Count deal-breakers
    deal_breaker_count = sum(1 for r in df['scam_reasons'] if 'Deal-breaker' in str(r))
    
    # Summary
    passed = df['filter_passed'].sum()
    total = len(df)
    print(f"\nFiltering Results:")
    print(f"  Total jobs: {total}")
    print(f"  Passed filters: {passed}")
    print(f"  Filtered out: {total - passed}")
    print(f"    - Deal-breakers: {deal_breaker_count}")
    print(f"    - Scams detected: {df['is_scam'].sum()}")
    print(f"    - Untrusted sources: {(~df['is_trusted_source']).sum()}")
    print(f"    - Irrelevant: {(~df['is_relevant']).sum()}")
    
    return df


def get_filtered_jobs(jobs_df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply filters and return only jobs that passed all checks.
    """
    filtered = filter_jobs(jobs_df)
    return filtered[filtered['filter_passed']].copy()


if __name__ == "__main__":
    # Test with sample data
    sample_jobs = pd.DataFrame([
        {
            'title': 'Graphic Designer',
            'company': 'ACME Corp',
            'location': 'San Francisco, CA',
            'description': 'Looking for a skilled graphic designer with Adobe Creative Suite experience.',
            'job_url': 'https://linkedin.com/jobs/123',
            'category': 'graphic_design'
        },
        {
            'title': 'Work From Home - $5000/Day!',
            'company': 'Confidential',
            'location': 'Remote',
            'description': 'Earn $5000 per day from home! No experience necessary! Wire transfer payments!',
            'job_url': 'https://sketchy-site.com/job',
            'category': 'administrative'
        },
    ])
    
    filtered = filter_jobs(sample_jobs)
    print("\nFiltered results:")
    print(filtered[['title', 'company', 'filter_passed', 'scam_reasons']])
