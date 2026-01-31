import requests
from bs4 import BeautifulSoup

boards = [
    'https://jobs.lever.co/gusto',
    'https://jobs.lever.co/calm',
    'https://jobs.lever.co/canva',
    'https://jobs.lever.co/mixpanel',
]

for url in boards:
    try:
        r = requests.get(url, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        postings = soup.find_all('div', class_='posting')
        company = url.split('/')[-1]
        print(f"\n{company.upper()}: {len(postings)} jobs")
        
        for posting in postings:
            title_elem = posting.find('h5')
            link = posting.find('a', class_='posting-title')
            if title_elem and link:
                title = title_elem.text.strip()
                href = link.get('href', '')
                keywords = ['design', 'creative', 'brand', 'visual', 'graphic', 'ux', 'ui', 'product design']
                if any(x in title.lower() for x in keywords):
                    print(f"  >> {title}")
                    print(f"     {href}")
    except Exception as e:
        print(f"{url}: Error - {e}")
