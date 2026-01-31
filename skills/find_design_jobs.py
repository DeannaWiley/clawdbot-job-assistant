import asyncio
from playwright.async_api import async_playwright

async def find_jobs():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Check multiple companies
        companies = [
            'https://jobs.lever.co/spotify',
            'https://jobs.lever.co/databricks',
            'https://jobs.lever.co/reddit',
        ]
        
        design_jobs = []
        
        for company_url in companies:
            company_name = company_url.split('/')[-1]
            print(f"\nChecking {company_name}...")
            
            try:
                await page.goto(company_url, wait_until='networkidle', timeout=30000)
                await page.wait_for_timeout(2000)
                
                postings = await page.query_selector_all('.posting')
                print(f"  Found {len(postings)} total jobs")
                
                for posting in postings:
                    title = await posting.query_selector('h5')
                    link = await posting.query_selector('a.posting-title')
                    location = await posting.query_selector('.location')
                    
                    if title and link:
                        title_text = await title.inner_text()
                        href = await link.get_attribute('href')
                        loc_text = await location.inner_text() if location else 'Unknown'
                        
                        keywords = ['design', 'creative', 'brand', 'visual', 'graphic', 'ux', 'ui', 'art director']
                        if any(x in title_text.lower() for x in keywords):
                            print(f"  >> {title_text} | {loc_text}")
                            print(f"     {href}")
                            design_jobs.append({
                                'title': title_text,
                                'company': company_name,
                                'location': loc_text,
                                'url': href
                            })
            except Exception as e:
                print(f"  Error: {e}")
        
        await browser.close()
        
        print(f"\n\n=== FOUND {len(design_jobs)} DESIGN JOBS ===")
        for job in design_jobs[:5]:
            print(f"{job['title']} at {job['company']}")
            print(f"  {job['url']}")
        
        return design_jobs

if __name__ == "__main__":
    asyncio.run(find_jobs())
