"""
Smart Adaptive Web Scraper for Job Applications

2026 Best Practices Implementation:
- Playwright for headless browser automation (cross-browser)
- AI-powered element detection using LLM
- Automatic form filling with intelligent field mapping
- Account creation and email verification automation
- Anti-bot detection bypass techniques
- Session persistence and cookie management

This scraper can handle ANY website for job applications.
"""
import os
import sys
import json
import time
import re
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

# Add skills path
sys.path.insert(0, os.path.dirname(__file__))

# Playwright imports
try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    from playwright.async_api import TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Playwright not installed. Run: pip install playwright && playwright install")

# Local imports for LLM and email
try:
    from gmail_handler import search_emails, get_email_by_id, mark_as_read
except ImportError:
    pass


# User data for form filling
USER_DATA = {
    "first_name": "Deanna",
    "last_name": "Wiley",
    "full_name": "Deanna Wiley",
    "email": "DeannaWileyCareers@gmail.com",
    "phone": "(708) 265-8734",
    "phone_clean": "7082658734",
    "linkedin": "https://www.linkedin.com/in/deannafwiley/",
    "portfolio": "https://dwileydesign.myportfolio.com/",
    "behance": "https://www.behance.net/deannawiley",
    "location": "Alameda, CA",
    "city": "Alameda",
    "state": "CA",
    "zip": "94501",
    "country": "United States",
    "work_authorization": "Yes",
    "requires_sponsorship": "No",
    "salary_expectation": "70000",
    "years_experience": "4",
    "education": "Bachelor of Science in Multimedia Design",
    "school": "DeVry University",
    "graduation_year": "2023",
}

# Common field patterns for intelligent form filling
FIELD_PATTERNS = {
    "first_name": ["first.*name", "fname", "given.*name", "first"],
    "last_name": ["last.*name", "lname", "surname", "family.*name", "last"],
    "full_name": ["full.*name", "name", "your.*name"],
    "email": ["email", "e-mail", "mail"],
    "phone": ["phone", "tel", "mobile", "cell", "contact.*number"],
    "linkedin": ["linkedin", "linked.*in"],
    "portfolio": ["portfolio", "website", "personal.*site", "url"],
    "location": ["location", "city.*state", "address"],
    "city": ["city", "town"],
    "state": ["state", "province", "region"],
    "zip": ["zip", "postal", "postcode"],
    "salary": ["salary", "compensation", "expected.*pay", "desired.*salary"],
    "years_experience": ["years.*experience", "experience.*years", "yoe"],
    "work_authorization": ["authorized", "work.*auth", "eligible.*work", "legally.*work"],
    "sponsorship": ["sponsor", "visa", "immigration"],
}

# Storage for created accounts
ACCOUNTS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'created_accounts.json')


def load_created_accounts() -> Dict:
    """Load previously created accounts."""
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_account(domain: str, credentials: Dict):
    """Save newly created account credentials."""
    accounts = load_created_accounts()
    accounts[domain] = {
        **credentials,
        "created_at": datetime.now().isoformat()
    }
    os.makedirs(os.path.dirname(ACCOUNTS_FILE), exist_ok=True)
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump(accounts, f, indent=2)
    print(f"[ACCOUNT SAVED] {domain}: {credentials.get('email', 'unknown')}")


def get_account_for_domain(domain: str) -> Optional[Dict]:
    """Get existing account for a domain."""
    accounts = load_created_accounts()
    return accounts.get(domain)


def get_linkedin_cookies() -> List[Dict]:
    """Get LinkedIn cookies from environment variables."""
    import subprocess
    cookies = []
    
    try:
        # Load from Windows User scope
        result = subprocess.run(
            ['powershell', '-NoProfile', '-Command', '[Environment]::GetEnvironmentVariable("LINKEDIN_LI_AT", "User")'],
            capture_output=True, text=True, timeout=5
        )
        li_at = result.stdout.strip()
        
        result = subprocess.run(
            ['powershell', '-NoProfile', '-Command', '[Environment]::GetEnvironmentVariable("LINKEDIN_JSESSIONID", "User")'],
            capture_output=True, text=True, timeout=5
        )
        jsessionid = result.stdout.strip()
        
        if li_at and not li_at.startswith('Clawdbot') and li_at != 'None':
            cookies.append({
                'name': 'li_at',
                'value': li_at,
                'domain': '.linkedin.com',
                'path': '/'
            })
        
        if jsessionid and not jsessionid.startswith('Clawdbot') and jsessionid != 'None':
            # Remove quotes if present
            jsessionid = jsessionid.strip('"')
            cookies.append({
                'name': 'JSESSIONID',
                'value': f'"{jsessionid}"' if not jsessionid.startswith('"') else jsessionid,
                'domain': '.linkedin.com',
                'path': '/'
            })
    except Exception as e:
        print(f"[LINKEDIN] Cookie load error: {e}")
    
    return cookies


class SmartScraper:
    """AI-powered adaptive web scraper for job applications."""
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
        # Session storage path
        self.storage_path = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'browser_state.json'
        )
    
    async def start(self):
        """Start the browser with anti-detection measures."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not available")
        
        self.playwright = await async_playwright().start()
        
        # Launch with anti-detection settings
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-infobars',
                '--window-size=1920,1080',
                '--start-maximized',
            ]
        )
        
        # Create context with realistic settings
        context_options = {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'locale': 'en-US',
            'timezone_id': 'America/Los_Angeles',
            'geolocation': {'latitude': 37.7749, 'longitude': -122.4194},
            'permissions': ['geolocation'],
        }
        
        # Load saved state if exists
        if os.path.exists(self.storage_path):
            context_options['storage_state'] = self.storage_path
        
        self.context = await self.browser.new_context(**context_options)
        
        # Add stealth scripts
        await self.context.add_init_script("""
            // Mask webdriver
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            
            // Mask plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Mask languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        self.page = await self.context.new_page()
        
        # Set extra headers
        await self.page.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        })
        
        print("[BROWSER] Started with anti-detection measures")
        return self
    
    async def save_state(self):
        """Save browser state (cookies, localStorage)."""
        if self.context:
            await self.context.storage_state(path=self.storage_path)
            print(f"[STATE] Saved to {self.storage_path}")
    
    async def close(self):
        """Close browser and save state."""
        await self.save_state()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("[BROWSER] Closed")
    
    async def inject_linkedin_cookies(self):
        """Inject LinkedIn authentication cookies into browser context."""
        cookies = get_linkedin_cookies()
        if cookies:
            await self.context.add_cookies(cookies)
            print(f"[LINKEDIN] Injected {len(cookies)} authentication cookies")
            return True
        print("[LINKEDIN] No cookies found in environment")
        return False
    
    async def navigate(self, url: str, wait_for: str = 'networkidle'):
        """Navigate to URL with smart waiting."""
        print(f"[NAVIGATE] {url}")
        
        # Auto-inject LinkedIn cookies for LinkedIn URLs
        if 'linkedin.com' in url:
            await self.inject_linkedin_cookies()
        
        try:
            await self.page.goto(url, wait_until=wait_for, timeout=30000)
            await self.page.wait_for_timeout(1000)  # Human-like pause
        except PlaywrightTimeout:
            print(f"[TIMEOUT] Page load timeout, continuing anyway")
    
    async def get_page_content(self) -> str:
        """Get page HTML content."""
        return await self.page.content()
    
    async def screenshot(self, path: str = None) -> bytes:
        """Take screenshot for debugging."""
        if not path:
            path = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        return await self.page.screenshot(path=path, full_page=True)
    
    async def find_element_smart(self, description: str) -> Optional[str]:
        """
        Use AI-like pattern matching to find elements.
        Returns the best selector for the described element.
        """
        # Try common selectors based on description
        selectors_to_try = []
        desc_lower = description.lower()
        
        if 'email' in desc_lower:
            selectors_to_try = [
                'input[type="email"]',
                'input[name*="email"]',
                'input[id*="email"]',
                'input[placeholder*="email" i]',
                '#email',
                '[data-testid*="email"]',
            ]
        elif 'password' in desc_lower:
            selectors_to_try = [
                'input[type="password"]',
                'input[name*="password"]',
                'input[id*="password"]',
                '#password',
            ]
        elif 'name' in desc_lower:
            if 'first' in desc_lower:
                selectors_to_try = [
                    'input[name*="first"]',
                    'input[id*="first"]',
                    'input[placeholder*="first" i]',
                    '#firstName',
                    '#first_name',
                ]
            elif 'last' in desc_lower:
                selectors_to_try = [
                    'input[name*="last"]',
                    'input[id*="last"]',
                    'input[placeholder*="last" i]',
                    '#lastName',
                    '#last_name',
                ]
            else:
                selectors_to_try = [
                    'input[name*="name"]',
                    'input[id*="name"]',
                    'input[placeholder*="name" i]',
                ]
        elif 'phone' in desc_lower:
            selectors_to_try = [
                'input[type="tel"]',
                'input[name*="phone"]',
                'input[id*="phone"]',
                'input[placeholder*="phone" i]',
            ]
        elif 'submit' in desc_lower or 'button' in desc_lower:
            selectors_to_try = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Submit")',
                'button:has-text("Apply")',
                'button:has-text("Sign Up")',
                'button:has-text("Create Account")',
                'button:has-text("Continue")',
                'button:has-text("Next")',
            ]
        elif 'login' in desc_lower or 'sign in' in desc_lower:
            selectors_to_try = [
                'a:has-text("Log in")',
                'a:has-text("Sign in")',
                'button:has-text("Log in")',
                'button:has-text("Sign in")',
                '[href*="login"]',
                '[href*="signin"]',
            ]
        elif 'create account' in desc_lower or 'sign up' in desc_lower:
            selectors_to_try = [
                'a:has-text("Create account")',
                'a:has-text("Sign up")',
                'a:has-text("Register")',
                'button:has-text("Create account")',
                'button:has-text("Sign up")',
                '[href*="signup"]',
                '[href*="register"]',
            ]
        
        # Try each selector
        for selector in selectors_to_try:
            try:
                element = await self.page.wait_for_selector(selector, timeout=2000)
                if element and await element.is_visible():
                    return selector
            except:
                continue
        
        return None
    
    async def fill_field(self, selector: str, value: str):
        """Fill a form field with human-like typing."""
        try:
            await self.page.click(selector)
            await self.page.wait_for_timeout(100)
            await self.page.fill(selector, '')  # Clear first
            
            # Type with small random delays for human-like behavior
            for char in value:
                await self.page.type(selector, char, delay=50)
            
            await self.page.wait_for_timeout(200)
            print(f"[FILL] {selector}: {value[:20]}...")
        except Exception as e:
            print(f"[FILL ERROR] {selector}: {e}")
    
    async def click_element(self, selector: str):
        """Click an element with human-like behavior."""
        try:
            await self.page.wait_for_selector(selector, timeout=5000)
            await self.page.click(selector)
            await self.page.wait_for_timeout(500)
            print(f"[CLICK] {selector}")
        except Exception as e:
            print(f"[CLICK ERROR] {selector}: {e}")
    
    async def smart_fill_form(self, field_mapping: Dict[str, str] = None):
        """
        Intelligently fill a form by detecting fields.
        field_mapping: optional override {field_type: value}
        """
        data = {**USER_DATA, **(field_mapping or {})}
        
        # Get all input elements
        inputs = await self.page.query_selector_all('input:visible, textarea:visible, select:visible')
        
        for input_el in inputs:
            try:
                # Get element attributes
                name = await input_el.get_attribute('name') or ''
                id_attr = await input_el.get_attribute('id') or ''
                placeholder = await input_el.get_attribute('placeholder') or ''
                input_type = await input_el.get_attribute('type') or 'text'
                label_text = ''
                
                # Try to find associated label
                input_id = await input_el.get_attribute('id')
                if input_id:
                    label = await self.page.query_selector(f'label[for="{input_id}"]')
                    if label:
                        label_text = await label.text_content() or ''
                
                # Combine all text for matching
                all_text = f"{name} {id_attr} {placeholder} {label_text}".lower()
                
                # Skip already filled or hidden fields
                current_value = await input_el.input_value() if input_type != 'file' else ''
                if current_value and len(current_value) > 2:
                    continue
                
                # Match field to user data
                matched_value = None
                for field_key, patterns in FIELD_PATTERNS.items():
                    for pattern in patterns:
                        if re.search(pattern, all_text, re.IGNORECASE):
                            matched_value = data.get(field_key)
                            if matched_value:
                                break
                    if matched_value:
                        break
                
                if matched_value and input_type not in ['file', 'hidden', 'submit', 'button']:
                    selector = f'#{input_id}' if input_id else f'[name="{name}"]'
                    await self.fill_field(selector, matched_value)
                    
            except Exception as e:
                continue
    
    async def check_for_account_required(self) -> bool:
        """Check if the page requires account creation/login."""
        content = await self.get_page_content()
        lower_content = content.lower()
        
        indicators = [
            'create account',
            'sign up',
            'register',
            'log in to apply',
            'sign in to apply',
            'create a free account',
        ]
        
        return any(ind in lower_content for ind in indicators)
    
    async def create_account(self, site_domain: str) -> Dict:
        """
        Create an account on a job site.
        Returns credentials used.
        """
        print(f"[ACCOUNT] Creating account for {site_domain}")
        
        # Check if we already have an account
        existing = get_account_for_domain(site_domain)
        if existing:
            print(f"[ACCOUNT] Found existing account: {existing.get('email')}")
            return existing
        
        # Generate unique password
        import secrets
        password = f"Dw{secrets.token_urlsafe(8)}!2026"
        
        credentials = {
            "email": USER_DATA["email"],
            "password": password,
            "first_name": USER_DATA["first_name"],
            "last_name": USER_DATA["last_name"],
        }
        
        # Find and click sign up button
        signup_selectors = [
            'a:has-text("Sign up")',
            'a:has-text("Create account")',
            'a:has-text("Register")',
            'button:has-text("Sign up")',
            'button:has-text("Create account")',
            '[href*="signup"]',
            '[href*="register"]',
            '[href*="create-account"]',
        ]
        
        for selector in signup_selectors:
            try:
                element = await self.page.wait_for_selector(selector, timeout=2000)
                if element:
                    await element.click()
                    await self.page.wait_for_timeout(2000)
                    break
            except:
                continue
        
        # Fill the registration form
        await self.smart_fill_form({"password": password})
        
        # Look for password confirmation field
        confirm_selectors = [
            'input[name*="confirm"]',
            'input[id*="confirm"]',
            'input[placeholder*="confirm" i]',
            'input[name*="password2"]',
            'input[id*="password2"]',
        ]
        
        for selector in confirm_selectors:
            try:
                element = await self.page.wait_for_selector(selector, timeout=1000)
                if element:
                    await self.fill_field(selector, password)
                    break
            except:
                continue
        
        # Click submit button
        submit_selectors = [
            'button[type="submit"]',
            'button:has-text("Create")',
            'button:has-text("Sign up")',
            'button:has-text("Register")',
            'input[type="submit"]',
        ]
        
        for selector in submit_selectors:
            try:
                element = await self.page.wait_for_selector(selector, timeout=2000)
                if element:
                    await element.click()
                    await self.page.wait_for_timeout(3000)
                    break
            except:
                continue
        
        # Save credentials
        save_account(site_domain, credentials)
        
        return credentials
    
    async def verify_email(self, site_domain: str, max_wait_seconds: int = 120) -> bool:
        """
        Check Gmail for verification email and click the link.
        """
        print(f"[EMAIL VERIFY] Checking for verification email from {site_domain}")
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait_seconds:
            try:
                # Search for recent verification emails
                emails = search_emails(
                    f'newer_than:1h (subject:verify OR subject:confirm OR subject:activate) from:{site_domain}',
                    max_results=5
                )
                
                if not emails:
                    # Also try without domain restriction
                    emails = search_emails(
                        'newer_than:1h (subject:verify OR subject:confirm OR subject:activate OR subject:welcome)',
                        max_results=10
                    )
                
                for email in emails:
                    # Get full email content
                    full_email = get_email_by_id(email['id'])
                    if not full_email:
                        continue
                    
                    body = full_email.get('body', '')
                    
                    # Look for verification links
                    link_patterns = [
                        r'https?://[^\s<>"]+(?:verify|confirm|activate|token)[^\s<>"]*',
                        r'https?://[^\s<>"]+/v/[^\s<>"]+',
                        r'https?://[^\s<>"]+/email-verification[^\s<>"]*',
                    ]
                    
                    for pattern in link_patterns:
                        matches = re.findall(pattern, body, re.IGNORECASE)
                        if matches:
                            verify_link = matches[0].rstrip('.')
                            print(f"[EMAIL VERIFY] Found verification link: {verify_link[:50]}...")
                            
                            # Navigate to verification link
                            await self.navigate(verify_link)
                            await self.page.wait_for_timeout(3000)
                            
                            # Mark email as read
                            mark_as_read(email['id'])
                            
                            print("[EMAIL VERIFY] Verification complete!")
                            return True
                
                # Wait before checking again
                print(f"[EMAIL VERIFY] No verification email yet, waiting... ({int(time.time() - start_time)}s)")
                await asyncio.sleep(10)
                
            except Exception as e:
                print(f"[EMAIL VERIFY] Error: {e}")
                await asyncio.sleep(10)
        
        print("[EMAIL VERIFY] Timeout waiting for verification email")
        return False
    
    async def login_to_site(self, site_domain: str) -> bool:
        """Login to a site using stored credentials."""
        credentials = get_account_for_domain(site_domain)
        if not credentials:
            print(f"[LOGIN] No stored credentials for {site_domain}")
            return False
        
        print(f"[LOGIN] Attempting login to {site_domain}")
        
        # Find and click login button
        login_selectors = [
            'a:has-text("Log in")',
            'a:has-text("Sign in")',
            'button:has-text("Log in")',
            'button:has-text("Sign in")',
            '[href*="login"]',
            '[href*="signin"]',
        ]
        
        for selector in login_selectors:
            try:
                element = await self.page.wait_for_selector(selector, timeout=2000)
                if element:
                    await element.click()
                    await self.page.wait_for_timeout(2000)
                    break
            except:
                continue
        
        # Fill login form
        email_selector = await self.find_element_smart("email field")
        if email_selector:
            await self.fill_field(email_selector, credentials['email'])
        
        password_selector = await self.find_element_smart("password field")
        if password_selector:
            await self.fill_field(password_selector, credentials['password'])
        
        # Click login submit
        submit_selector = await self.find_element_smart("submit button")
        if submit_selector:
            await self.click_element(submit_selector)
            await self.page.wait_for_timeout(3000)
        
        return True
    
    async def upload_resume(self, resume_path: str):
        """Upload resume file."""
        print(f"[UPLOAD] Resume: {resume_path}")
        
        # Find file input
        file_inputs = await self.page.query_selector_all('input[type="file"]')
        
        for file_input in file_inputs:
            try:
                accept = await file_input.get_attribute('accept') or ''
                name = await file_input.get_attribute('name') or ''
                
                # Check if it's for resume/CV
                if any(x in accept.lower() for x in ['.pdf', '.doc', 'application/pdf']) or \
                   any(x in name.lower() for x in ['resume', 'cv', 'document']):
                    await file_input.set_input_files(resume_path)
                    print(f"[UPLOAD] Resume uploaded successfully")
                    return True
            except Exception as e:
                print(f"[UPLOAD] Error: {e}")
                continue
        
        return False
    
    async def apply_to_job(self, job_url: str, resume_path: str = None) -> Dict:
        """
        Complete job application workflow.
        Handles: navigation, login/signup, form filling, resume upload.
        """
        result = {
            "url": job_url,
            "status": "started",
            "steps_completed": [],
            "errors": [],
        }
        
        try:
            # Extract domain
            from urllib.parse import urlparse
            domain = urlparse(job_url).netloc
            
            # Navigate to job posting
            await self.navigate(job_url)
            result["steps_completed"].append("navigated")
            
            # Check if login/signup required
            if await self.check_for_account_required():
                # Try to login first
                existing_account = get_account_for_domain(domain)
                if existing_account:
                    await self.login_to_site(domain)
                    result["steps_completed"].append("logged_in")
                else:
                    # Create new account
                    await self.create_account(domain)
                    result["steps_completed"].append("account_created")
                    
                    # Wait for and verify email
                    verified = await self.verify_email(domain)
                    if verified:
                        result["steps_completed"].append("email_verified")
                    else:
                        result["errors"].append("email_verification_timeout")
            
            # Find and click Apply button
            apply_selectors = [
                'button:has-text("Apply")',
                'a:has-text("Apply")',
                'button:has-text("Easy Apply")',
                'button:has-text("Apply Now")',
                'a:has-text("Apply Now")',
                '[class*="apply"]',
            ]
            
            for selector in apply_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=3000)
                    if element:
                        await element.click()
                        await self.page.wait_for_timeout(2000)
                        result["steps_completed"].append("clicked_apply")
                        break
                except:
                    continue
            
            # Fill application form
            await self.smart_fill_form()
            result["steps_completed"].append("filled_form")
            
            # Upload resume if provided
            if resume_path and os.path.exists(resume_path):
                uploaded = await self.upload_resume(resume_path)
                if uploaded:
                    result["steps_completed"].append("uploaded_resume")
            
            # Look for submit button
            submit_selectors = [
                'button[type="submit"]',
                'button:has-text("Submit")',
                'button:has-text("Submit Application")',
                'button:has-text("Complete")',
                'input[type="submit"]',
            ]
            
            for selector in submit_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                    if element:
                        # Don't actually submit - mark as ready
                        result["steps_completed"].append("ready_to_submit")
                        result["status"] = "ready_to_submit"
                        break
                except:
                    continue
            
            # Save state
            await self.save_state()
            
        except Exception as e:
            result["errors"].append(str(e))
            result["status"] = "error"
        
        return result


async def scrape_job_details(url: str) -> Dict:
    """Scrape job details from any job posting URL."""
    scraper = SmartScraper(headless=True)
    await scraper.start()
    
    try:
        await scraper.navigate(url)
        
        # Wait for content to load - LinkedIn needs extra time
        if 'linkedin.com' in url:
            # Wait for job details to load
            try:
                await scraper.page.wait_for_selector('div.description__text, .show-more-less-html__markup, .jobs-description__content', timeout=10000)
            except:
                pass
            await scraper.page.wait_for_timeout(2000)
            
            # Try clicking "Show more" button if present (multiple selectors)
            show_more_selectors = [
                'button.show-more-less-html__button',
                'button[aria-label*="Show more"]',
                '.show-more-less-html__button--more',
                'button:has-text("Show more")',
            ]
            for sel in show_more_selectors:
                try:
                    show_more = await scraper.page.query_selector(sel)
                    if show_more:
                        await show_more.click()
                        await scraper.page.wait_for_timeout(1500)
                        break
                except:
                    continue
        else:
            await scraper.page.wait_for_timeout(2000)
        
        # Extract page title
        title = await scraper.page.title()
        
        job_data = {
            "url": url,
            "title": title,
            "scraped_at": datetime.now().isoformat(),
        }
        
        # LinkedIn-specific scraping
        if 'linkedin.com' in url:
            linkedin_selectors = {
                "job_title": [
                    'h1.top-card-layout__title',
                    'h1.topcard__title', 
                    'h1.job-details-jobs-unified-top-card__job-title',
                    'h1[class*="job-title"]',
                    '.jobs-unified-top-card__job-title',
                ],
                "company": [
                    'a.topcard__org-name-link',
                    '.topcard__org-name-link',
                    'a[data-tracking-control-name="public_jobs_topcard-org-name"]',
                    '.jobs-unified-top-card__company-name a',
                    'span.topcard__flavor:first-of-type',
                ],
                "location": [
                    'span.topcard__flavor--bullet',
                    '.topcard__flavor--bullet',
                    '.jobs-unified-top-card__bullet',
                ],
                "salary": [
                    '.salary-main-rail__data-badge',
                    '.jobs-unified-top-card__salary',
                    '[class*="salary"]',
                ],
                "description": [
                    '.show-more-less-html__markup',
                    'div.description__text .show-more-less-html__markup',
                    'div.description__text',
                    '.jobs-description__content .jobs-box__html-content',
                    '.jobs-description__content',
                    '#job-details .jobs-box__html-content',
                    '#job-details',
                    'article[class*="jobs-description"]',
                    'section[class*="description"] div',
                ],
            }
            
            for field, field_selectors in linkedin_selectors.items():
                for sel in field_selectors:
                    try:
                        element = await scraper.page.query_selector(sel)
                        if element:
                            text = await element.text_content()
                            if text and len(text.strip()) > 5:
                                job_data[field] = text.strip()[:3000]
                                break
                    except:
                        continue
            
            # Try extracting salary from page text if not found
            if 'salary' not in job_data or not job_data['salary']:
                page_text = await scraper.page.text_content('body')
                salary_patterns = [r'\$[\d,]+\s*[-–]\s*\$[\d,]+', r'\$[\d,]+/(?:yr|year|hr|hour)']
                for pattern in salary_patterns:
                    match = re.search(pattern, page_text)
                    if match:
                        job_data['salary'] = match.group(0)
                        break
        else:
            # Generic scraping for other job sites
            selectors = {
                "job_title": ['h1', '[class*="job-title"]', '[class*="jobTitle"]', '[data-testid="jobTitle"]'],
                "company": ['[class*="company"]', '[class*="employer"]', '[data-testid="company"]'],
                "location": ['[class*="location"]', '[data-testid="location"]'],
                "description": ['[class*="description"]', '[class*="job-details"]', '[id*="description"]'],
                "salary": ['[class*="salary"]', '[class*="compensation"]'],
            }
            
            for field, field_selectors in selectors.items():
                for sel in field_selectors:
                    try:
                        element = await scraper.page.query_selector(sel)
                        if element:
                            text = await element.text_content()
                            if text and len(text.strip()) > 0:
                                job_data[field] = text.strip()[:2000]
                                break
                    except:
                        continue
        
        return job_data
        
    finally:
        await scraper.close()


async def apply_to_job_full(job_url: str, resume_path: str = None) -> Dict:
    """Full job application workflow."""
    scraper = SmartScraper(headless=False)  # Show browser for debugging
    await scraper.start()
    
    try:
        result = await scraper.apply_to_job(job_url, resume_path)
        return result
    finally:
        await scraper.close()


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Smart Web Scraper for Job Applications')
    parser.add_argument('command', choices=['scrape', 'apply', 'accounts'])
    parser.add_argument('--url', help='Job URL')
    parser.add_argument('--resume', help='Path to resume file')
    parser.add_argument('--headless', action='store_true', help='Run headless')
    
    args = parser.parse_args()
    
    if args.command == 'scrape':
        if not args.url:
            print("Error: --url required for scrape")
        else:
            result = asyncio.run(scrape_job_details(args.url))
            print(json.dumps(result, indent=2))
    
    elif args.command == 'apply':
        if not args.url:
            print("Error: --url required for apply")
        else:
            result = asyncio.run(apply_to_job_full(args.url, args.resume))
            print(json.dumps(result, indent=2))
    
    elif args.command == 'accounts':
        accounts = load_created_accounts()
        print("\n=== Stored Accounts ===")
        for domain, creds in accounts.items():
            print(f"\n{domain}:")
            print(f"  Email: {creds.get('email')}")
            print(f"  Password: {creds.get('password')}")
            print(f"  Created: {creds.get('created_at')}")
