"""
Job Search Module - Aggregates job listings from multiple sources using JobSpy
"""
import os
import yaml
from datetime import datetime
from typing import List, Dict, Optional
from jobspy import scrape_jobs
import pandas as pd


def load_config() -> dict:
    """Load configuration from config.yaml"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def search_jobs_for_category(
    category_name: str,
    keywords: List[str],
    locations: List[str],
    sources: List[str],
    hours_old: int = 72,
    results_wanted: int = 20
) -> pd.DataFrame:
    """
    Search for jobs in a specific category across multiple sources.
    
    Args:
        category_name: Name of the job category (for logging)
        keywords: List of search terms for this category
        locations: List of locations to search
        sources: List of job boards to search
        hours_old: How recent the jobs should be (in hours)
        results_wanted: Max results per search
    
    Returns:
        DataFrame with job listings
    """
    all_jobs = []
    
    for keyword in keywords:
        for location in locations:
            try:
                print(f"[{category_name}] Searching '{keyword}' in {location}...")
                
                jobs = scrape_jobs(
                    site_name=sources,
                    search_term=keyword,
                    location=location,
                    results_wanted=results_wanted,
                    hours_old=hours_old,
                    country_indeed='USA'
                )
                
                if jobs is not None and len(jobs) > 0:
                    jobs['category'] = category_name
                    jobs['search_keyword'] = keyword
                    jobs['search_location'] = location
                    jobs['scraped_at'] = datetime.now().isoformat()
                    all_jobs.append(jobs)
                    print(f"  Found {len(jobs)} jobs")
                    
            except Exception as e:
                print(f"  Error searching {keyword} in {location}: {e}")
                continue
    
    if all_jobs:
        combined = pd.concat(all_jobs, ignore_index=True)
        return combined
    
    return pd.DataFrame()


def deduplicate_jobs(jobs_df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicate job listings based on title, company, and location.
    """
    if jobs_df.empty:
        return jobs_df
    
    # Create a composite key for deduplication
    jobs_df['dedup_key'] = (
        jobs_df['title'].str.lower().str.strip() + '|' +
        jobs_df['company'].str.lower().str.strip() + '|' +
        jobs_df['location'].str.lower().str.strip()
    )
    
    # Keep the first occurrence (usually the most recent)
    deduped = jobs_df.drop_duplicates(subset=['dedup_key'], keep='first')
    deduped = deduped.drop(columns=['dedup_key'])
    
    print(f"Removed {len(jobs_df) - len(deduped)} duplicates")
    return deduped


def search_all_jobs(include_extended_boards: bool = True) -> pd.DataFrame:
    """
    Main function to search all job categories defined in config.
    
    Args:
        include_extended_boards: Whether to also search Ashby, Wellfound, etc.
    
    Returns:
        DataFrame with all aggregated and deduplicated jobs
    """
    config = load_config()
    search_config = config['search']
    
    all_jobs = []
    
    # Standard JobSpy sources (LinkedIn, Indeed, Glassdoor, Google)
    for category_name, category_config in search_config['categories'].items():
        print(f"\n{'='*50}")
        print(f"Searching category: {category_name}")
        print(f"{'='*50}")
        
        jobs = search_jobs_for_category(
            category_name=category_name,
            keywords=category_config['keywords'],
            locations=search_config['locations'],
            sources=search_config['sources'],
            hours_old=search_config['hours_old'],
            results_wanted=search_config['results_wanted']
        )
        
        if not jobs.empty:
            all_jobs.append(jobs)
    
    # Extended job boards (Ashby, Wellfound, WeWorkRemotely, RemoteOK, etc.)
    if include_extended_boards:
        try:
            from job_boards import search_all_extended_boards
            
            # Collect all keywords from categories
            all_keywords = []
            for cat_config in search_config['categories'].values():
                all_keywords.extend(cat_config.get('keywords', []))
            
            extended_jobs = search_all_extended_boards(
                keywords=all_keywords[:5],  # Limit to avoid too many requests
                location=search_config['locations'][0] if search_config['locations'] else "San Francisco",
                include_remote=True
            )
            
            if not extended_jobs.empty:
                # Add category column for compatibility
                extended_jobs['category'] = 'extended_boards'
                all_jobs.append(extended_jobs)
                
        except ImportError:
            print("Extended job boards module not available")
        except Exception as e:
            print(f"Error searching extended boards: {e}")
    
    if all_jobs:
        combined = pd.concat(all_jobs, ignore_index=True)
        deduped = deduplicate_jobs(combined)
        
        print(f"\n{'='*50}")
        print(f"Total unique jobs found: {len(deduped)}")
        print(f"{'='*50}")
        
        return deduped
    
    print("No jobs found.")
    return pd.DataFrame()


def save_jobs(jobs_df: pd.DataFrame, output_path: Optional[str] = None) -> str:
    """Save jobs to CSV file."""
    if output_path is None:
        output_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 'data', 
            f'jobs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    
    jobs_df.to_csv(output_path, index=False)
    print(f"Saved {len(jobs_df)} jobs to {output_path}")
    return output_path


if __name__ == "__main__":
    # Test the job search
    jobs = search_all_jobs()
    if not jobs.empty:
        save_jobs(jobs)
        print("\nSample of jobs found:")
        print(jobs[['title', 'company', 'location', 'category']].head(10))
