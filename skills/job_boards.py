"""
Extended Job Boards Module - Additional sources beyond JobSpy defaults

Supports:
- Ashby (modern ATS with public job boards)
- Wellfound (AngelList - startup jobs)
- WeWorkRemotely (remote-focused)
- RemoteOK (remote jobs)
- Greenhouse public boards
- Lever public boards
- BuiltIn (tech jobs by city)
"""
import os
import re
import json
import requests
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd


# Common headers to avoid blocking
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


def scrape_wellfound(keywords: List[str], location: str = "San Francisco", max_results: int = 20) -> List[Dict]:
    """
    Scrape jobs from Wellfound (formerly AngelList).
    Great for startup jobs in tech, design, and more.
    """
    jobs = []
    
    for keyword in keywords:
        try:
            # Wellfound search URL
            search_url = f"https://wellfound.com/role/l/{keyword.lower().replace(' ', '-')}/{location.lower().replace(' ', '-').replace(',', '')}"
            
            response = requests.get(search_url, headers=HEADERS, timeout=15)
            if response.status_code != 200:
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find job cards
            job_cards = soup.find_all('div', {'class': re.compile(r'styles_component.*StartupResult')})
            
            for card in job_cards[:max_results]:
                try:
                    title_elem = card.find('a', {'class': re.compile(r'styles_defaultLink')})
                    company_elem = card.find('span', {'class': re.compile(r'styles_startupName')})
                    
                    if title_elem and company_elem:
                        job = {
                            'title': title_elem.get_text(strip=True),
                            'company': company_elem.get_text(strip=True),
                            'location': location,
                            'job_url': f"https://wellfound.com{title_elem.get('href', '')}",
                            'source': 'wellfound',
                            'scraped_at': datetime.now().isoformat(),
                        }
                        jobs.append(job)
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"Wellfound scrape error for {keyword}: {e}")
            continue
    
    return jobs


def scrape_ashby_company(company_slug: str) -> List[Dict]:
    """
    Scrape jobs from an Ashby-powered job board.
    Many modern startups use Ashby for hiring.
    
    Args:
        company_slug: The company's Ashby subdomain (e.g., 'notion', 'figma')
    """
    jobs = []
    
    try:
        # Ashby API endpoint for job listings
        api_url = f"https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams"
        
        payload = {
            "operationName": "ApiJobBoardWithTeams",
            "variables": {"organizationHostedJobsPageName": company_slug},
            "query": """
                query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) {
                    jobBoard: jobBoardWithTeams(
                        organizationHostedJobsPageName: $organizationHostedJobsPageName
                    ) {
                        jobs {
                            id
                            title
                            departmentName
                            locationName
                            employmentType
                            publishedDate
                        }
                    }
                }
            """
        }
        
        response = requests.post(api_url, json=payload, headers={**HEADERS, 'Content-Type': 'application/json'}, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            job_list = data.get('data', {}).get('jobBoard', {}).get('jobs', [])
            
            for job in job_list:
                jobs.append({
                    'title': job.get('title', ''),
                    'company': company_slug.title(),
                    'location': job.get('locationName', 'Unknown'),
                    'department': job.get('departmentName', ''),
                    'employment_type': job.get('employmentType', ''),
                    'job_url': f"https://jobs.ashbyhq.com/{company_slug}/{job.get('id', '')}",
                    'source': 'ashby',
                    'scraped_at': datetime.now().isoformat(),
                })
                
    except Exception as e:
        print(f"Ashby scrape error for {company_slug}: {e}")
    
    return jobs


def scrape_weworkremotely(categories: List[str] = None) -> List[Dict]:
    """
    Scrape jobs from WeWorkRemotely - excellent for remote positions.
    
    Categories: design, programming, copywriting, devops-sysadmin, 
                customer-support, sales-marketing, product, management-finance
    """
    if categories is None:
        categories = ['design', 'copywriting', 'sales-marketing']
    
    jobs = []
    
    for category in categories:
        try:
            url = f"https://weworkremotely.com/categories/{category}"
            response = requests.get(url, headers=HEADERS, timeout=15)
            
            if response.status_code != 200:
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find job listings
            job_items = soup.find_all('li', {'class': 'feature'})
            
            for item in job_items[:20]:
                try:
                    link = item.find('a', href=True)
                    if not link:
                        continue
                    
                    title_elem = item.find('span', {'class': 'title'})
                    company_elem = item.find('span', {'class': 'company'})
                    
                    if title_elem and company_elem:
                        jobs.append({
                            'title': title_elem.get_text(strip=True),
                            'company': company_elem.get_text(strip=True),
                            'location': 'Remote',
                            'job_url': f"https://weworkremotely.com{link.get('href', '')}",
                            'source': 'weworkremotely',
                            'category': category,
                            'scraped_at': datetime.now().isoformat(),
                        })
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"WeWorkRemotely scrape error for {category}: {e}")
            continue
    
    return jobs


def scrape_remoteok(tags: List[str] = None) -> List[Dict]:
    """
    Scrape jobs from RemoteOK - another great remote job board.
    """
    jobs = []
    
    try:
        # RemoteOK has a JSON API
        url = "https://remoteok.com/api"
        response = requests.get(url, headers=HEADERS, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            # First item is metadata, skip it
            for job in data[1:50]:  # Limit to 50
                try:
                    # Filter by tags if provided
                    job_tags = [t.lower() for t in job.get('tags', [])]
                    
                    if tags:
                        if not any(tag.lower() in job_tags for tag in tags):
                            continue
                    
                    jobs.append({
                        'title': job.get('position', ''),
                        'company': job.get('company', ''),
                        'location': job.get('location', 'Remote'),
                        'salary': job.get('salary', ''),
                        'job_url': job.get('url', ''),
                        'description': job.get('description', ''),
                        'tags': job.get('tags', []),
                        'source': 'remoteok',
                        'scraped_at': datetime.now().isoformat(),
                    })
                except Exception:
                    continue
                    
    except Exception as e:
        print(f"RemoteOK scrape error: {e}")
    
    return jobs


def scrape_greenhouse_board(company_slug: str) -> List[Dict]:
    """
    Scrape jobs from a company's Greenhouse job board.
    
    Args:
        company_slug: The company's Greenhouse board ID
    """
    jobs = []
    
    try:
        # Greenhouse has a public JSON API
        url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs"
        response = requests.get(url, headers=HEADERS, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            for job in data.get('jobs', []):
                jobs.append({
                    'title': job.get('title', ''),
                    'company': company_slug.replace('-', ' ').title(),
                    'location': job.get('location', {}).get('name', 'Unknown'),
                    'job_url': job.get('absolute_url', ''),
                    'department': ', '.join([d.get('name', '') for d in job.get('departments', [])]),
                    'source': 'greenhouse',
                    'scraped_at': datetime.now().isoformat(),
                })
                
    except Exception as e:
        print(f"Greenhouse scrape error for {company_slug}: {e}")
    
    return jobs


def scrape_lever_board(company_slug: str) -> List[Dict]:
    """
    Scrape jobs from a company's Lever job board.
    """
    jobs = []
    
    try:
        # Lever has a public API
        url = f"https://api.lever.co/v0/postings/{company_slug}"
        response = requests.get(url, headers=HEADERS, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            for job in data:
                jobs.append({
                    'title': job.get('text', ''),
                    'company': company_slug.replace('-', ' ').title(),
                    'location': job.get('categories', {}).get('location', 'Unknown'),
                    'department': job.get('categories', {}).get('team', ''),
                    'commitment': job.get('categories', {}).get('commitment', ''),
                    'job_url': job.get('hostedUrl', ''),
                    'description': job.get('descriptionPlain', ''),
                    'source': 'lever',
                    'scraped_at': datetime.now().isoformat(),
                })
                
    except Exception as e:
        print(f"Lever scrape error for {company_slug}: {e}")
    
    return jobs


# List of companies to check (can be expanded)
ASHBY_COMPANIES = [
    'notion', 'figma', 'ramp', 'brex', 'plaid', 'stripe', 
    'openai', 'anthropic', 'linear', 'vercel', 'supabase'
]

GREENHOUSE_COMPANIES = [
    'airbnb', 'discord', 'coinbase', 'doordash', 'dropbox',
    'lyft', 'pinterest', 'reddit', 'robinhood', 'snap',
    'spotify', 'square', 'twitch', 'uber', 'zoom'
]

LEVER_COMPANIES = [
    'netlify', 'cloudflare', 'zapier', 'airtable', 'notion',
    'webflow', 'canva', 'mailchimp', 'intercom'
]


def search_all_extended_boards(
    keywords: List[str] = None,
    location: str = "San Francisco Bay Area",
    include_remote: bool = True,
    target_companies: List[str] = None
) -> pd.DataFrame:
    """
    Search all extended job boards and aggregate results.
    
    Args:
        keywords: Search keywords for applicable boards
        location: Location for location-based searches
        include_remote: Whether to include remote job boards
        target_companies: Specific companies to check (Ashby/Greenhouse/Lever)
    
    Returns:
        DataFrame with all jobs from extended sources
    """
    all_jobs = []
    
    if keywords is None:
        keywords = ['designer', 'graphic designer', 'brand designer']
    
    print("\n" + "="*50)
    print("Searching Extended Job Boards...")
    print("="*50)
    
    # Wellfound (AngelList) - startup jobs
    print("\n[Wellfound] Searching startup jobs...")
    wellfound_jobs = scrape_wellfound(keywords, location)
    all_jobs.extend(wellfound_jobs)
    print(f"  Found {len(wellfound_jobs)} jobs")
    
    # Remote boards
    if include_remote:
        print("\n[WeWorkRemotely] Searching remote jobs...")
        wwr_jobs = scrape_weworkremotely(['design', 'copywriting', 'sales-marketing'])
        all_jobs.extend(wwr_jobs)
        print(f"  Found {len(wwr_jobs)} jobs")
        
        print("\n[RemoteOK] Searching remote jobs...")
        rok_jobs = scrape_remoteok(['design', 'marketing', 'writing'])
        all_jobs.extend(rok_jobs)
        print(f"  Found {len(rok_jobs)} jobs")
    
    # Company-specific boards
    companies_to_check = target_companies or []
    
    # Add default companies if none specified
    if not companies_to_check:
        companies_to_check = ASHBY_COMPANIES[:5] + GREENHOUSE_COMPANIES[:5] + LEVER_COMPANIES[:5]
    
    print(f"\n[Company Boards] Checking {len(companies_to_check)} companies...")
    
    for company in companies_to_check:
        # Try Ashby first
        ashby_jobs = scrape_ashby_company(company)
        if ashby_jobs:
            all_jobs.extend(ashby_jobs)
            print(f"  {company} (Ashby): {len(ashby_jobs)} jobs")
            continue
        
        # Try Greenhouse
        gh_jobs = scrape_greenhouse_board(company)
        if gh_jobs:
            all_jobs.extend(gh_jobs)
            print(f"  {company} (Greenhouse): {len(gh_jobs)} jobs")
            continue
        
        # Try Lever
        lever_jobs = scrape_lever_board(company)
        if lever_jobs:
            all_jobs.extend(lever_jobs)
            print(f"  {company} (Lever): {len(lever_jobs)} jobs")
    
    print(f"\n{'='*50}")
    print(f"Total from extended boards: {len(all_jobs)} jobs")
    print(f"{'='*50}")
    
    if all_jobs:
        return pd.DataFrame(all_jobs)
    
    return pd.DataFrame()


if __name__ == "__main__":
    # Test the extended boards
    df = search_all_extended_boards(
        keywords=['designer', 'graphic'],
        include_remote=True
    )
    
    if not df.empty:
        print("\nSample results:")
        print(df[['title', 'company', 'source', 'location']].head(20))
