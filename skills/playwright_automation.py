"""
ClawdBot Playwright Automation Engine
=====================================
Production-grade browser automation with:
- Robust DOM analysis and form detection
- Intelligent field mapping with semantic understanding
- Proper CAPTCHA service integration
- State tracking and recovery mechanisms
"""

import asyncio
import os
import re
import json
import time
import base64
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import requests

from playwright.async_api import async_playwright, Page, Locator, Frame, ElementHandle, BrowserContext


class FieldType(Enum):
    TEXT = "text"
    EMAIL = "email"
    PHONE = "phone"
    NAME = "name"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    URL = "url"
    LINKEDIN = "linkedin"
    PORTFOLIO = "portfolio"
    TEXTAREA = "textarea"
    SELECT = "select"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    FILE = "file"
    DATE = "date"
    NUMBER = "number"
    UNKNOWN = "unknown"


class FormState(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    CAPTCHA_REQUIRED = "captcha_required"
    SUBMITTED = "submitted"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class FormField:
    """Represents a detected form field with semantic understanding."""
    element: Locator
    field_type: FieldType
    name: str
    label: str
    placeholder: str
    required: bool
    visible: bool
    value: str = ""
    options: List[str] = field(default_factory=list)
    confidence: float = 0.0
    
    
@dataclass
class FormAnalysis:
    """Complete analysis of a form's structure and fields."""
    form_locator: Optional[Locator]
    fields: List[FormField]
    submit_button: Optional[Locator]
    has_file_upload: bool
    has_captcha: bool
    captcha_type: Optional[str]
    page_title: str
    form_id: str


@dataclass
class ApplicationState:
    """Tracks progress through a multi-step application."""
    job_url: str
    company: str
    job_title: str
    current_step: int = 0
    total_steps: int = 1
    form_state: FormState = FormState.NOT_STARTED
    fields_filled: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    captcha_attempts: int = 0


class DOMAnalyzer:
    """
    Advanced DOM analysis for understanding page structure.
    Uses semantic selectors, accessibility attributes, and structural analysis.
    """
    
    FIELD_PATTERNS = {
        FieldType.EMAIL: [
            r'email', r'e-mail', r'mail'
        ],
        FieldType.PHONE: [
            r'phone', r'tel', r'mobile', r'cell'
        ],
        FieldType.FIRST_NAME: [
            r'first.?name', r'fname', r'given.?name', r'forename'
        ],
        FieldType.LAST_NAME: [
            r'last.?name', r'lname', r'surname', r'family.?name'
        ],
        FieldType.NAME: [
            r'^name$', r'full.?name', r'your.?name'
        ],
        FieldType.LINKEDIN: [
            r'linkedin', r'linked.?in'
        ],
        FieldType.PORTFOLIO: [
            r'portfolio', r'website', r'personal.?site', r'work.?samples'
        ],
        FieldType.URL: [
            r'url', r'link', r'website'
        ],
    }
    
    @staticmethod
    async def wait_for_stable_dom(page: Page, timeout: int = 10000) -> bool:
        """Wait for DOM to stabilize after dynamic content loads."""
        try:
            await page.wait_for_load_state('domcontentloaded', timeout=timeout)
            
            prev_height = 0
            stable_count = 0
            start = time.time()
            
            while (time.time() - start) < (timeout / 1000):
                current_height = await page.evaluate('document.body.scrollHeight')
                if current_height == prev_height:
                    stable_count += 1
                    if stable_count >= 3:
                        return True
                else:
                    stable_count = 0
                prev_height = current_height
                await asyncio.sleep(0.3)
            
            return True
        except Exception:
            return False
    
    @staticmethod
    async def find_form(page: Page) -> Optional[Locator]:
        """Find the primary application form on the page."""
        form_selectors = [
            'form[action*="apply"]',
            'form[id*="application"]',
            'form[class*="application"]',
            'form[data-qa*="application"]',
            '[role="form"]',
            'form',
        ]
        
        for selector in form_selectors:
            try:
                forms = page.locator(selector)
                count = await forms.count()
                if count > 0:
                    for i in range(count):
                        form = forms.nth(i)
                        if await form.is_visible():
                            inputs = form.locator('input, textarea, select')
                            if await inputs.count() >= 2:
                                return form
            except Exception:
                continue
        
        return None
    
    @staticmethod
    async def get_field_label(page: Page, element: Locator) -> str:
        """Extract the label for a form field using multiple strategies."""
        try:
            element_id = await element.get_attribute('id')
            if element_id:
                label = page.locator(f'label[for="{element_id}"]')
                if await label.count() > 0:
                    return (await label.first.inner_text()).strip()
            
            aria_label = await element.get_attribute('aria-label')
            if aria_label:
                return aria_label.strip()
            
            aria_labelledby = await element.get_attribute('aria-labelledby')
            if aria_labelledby:
                label_elem = page.locator(f'#{aria_labelledby}')
                if await label_elem.count() > 0:
                    return (await label_elem.first.inner_text()).strip()
            
            parent = element.locator('..')
            for _ in range(3):
                label = parent.locator('label')
                if await label.count() > 0:
                    return (await label.first.inner_text()).strip()
                parent = parent.locator('..')
            
            return ""
        except Exception:
            return ""
    
    @classmethod
    def classify_field(cls, name: str, label: str, placeholder: str, input_type: str) -> Tuple[FieldType, float]:
        """Classify a field based on its attributes with confidence score."""
        combined = f"{name} {label} {placeholder}".lower()
        
        if input_type == 'email':
            return FieldType.EMAIL, 1.0
        if input_type == 'tel':
            return FieldType.PHONE, 1.0
        if input_type == 'file':
            return FieldType.FILE, 1.0
        if input_type == 'date':
            return FieldType.DATE, 1.0
        if input_type == 'number':
            return FieldType.NUMBER, 1.0
        
        for field_type, patterns in cls.FIELD_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, combined, re.IGNORECASE):
                    confidence = 0.9 if re.search(pattern, name, re.IGNORECASE) else 0.7
                    return field_type, confidence
        
        if input_type == 'text':
            return FieldType.TEXT, 0.5
        
        return FieldType.UNKNOWN, 0.0
    
    @classmethod
    async def analyze_form(cls, page: Page) -> FormAnalysis:
        """Perform complete analysis of form structure and fields."""
        form = await cls.find_form(page)
        fields: List[FormField] = []
        submit_button = None
        has_file_upload = False
        has_captcha = False
        captcha_type = None
        
        search_context = form if form else page
        
        input_selectors = [
            'input:not([type="hidden"]):not([type="submit"]):not([type="button"])',
            'textarea',
            'select',
        ]
        
        for selector in input_selectors:
            elements = search_context.locator(selector)
            count = await elements.count()
            
            for i in range(count):
                element = elements.nth(i)
                
                try:
                    is_visible = await element.is_visible()
                    if not is_visible:
                        continue
                    
                    name = await element.get_attribute('name') or ''
                    placeholder = await element.get_attribute('placeholder') or ''
                    input_type = await element.get_attribute('type') or 'text'
                    required = await element.get_attribute('required') is not None
                    label = await cls.get_field_label(page, element)
                    current_value = await element.input_value() if input_type != 'file' else ''
                    
                    if input_type == 'file':
                        has_file_upload = True
                    
                    field_type, confidence = cls.classify_field(name, label, placeholder, input_type)
                    
                    options = []
                    tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
                    if tag_name == 'select':
                        option_elements = element.locator('option')
                        opt_count = await option_elements.count()
                        for j in range(opt_count):
                            opt = option_elements.nth(j)
                            opt_text = await opt.inner_text()
                            opt_value = await opt.get_attribute('value')
                            if opt_value:
                                options.append(f"{opt_value}:{opt_text}")
                    
                    fields.append(FormField(
                        element=element,
                        field_type=field_type,
                        name=name,
                        label=label,
                        placeholder=placeholder,
                        required=required,
                        visible=is_visible,
                        value=current_value,
                        options=options,
                        confidence=confidence,
                    ))
                except Exception:
                    continue
        
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Submit")',
            'button:has-text("Apply")',
            'button:has-text("Submit Application")',
            'button.postings-btn',
            '[data-qa="submit-button"]',
        ]
        
        for selector in submit_selectors:
            try:
                btn = search_context.locator(selector).first
                if await btn.count() > 0 and await btn.is_visible():
                    submit_button = btn
                    break
            except Exception:
                continue
        
        page_content = await page.content()
        captcha_patterns = [
            ('recaptcha', r'grecaptcha|recaptcha|g-recaptcha'),
            ('hcaptcha', r'hcaptcha|h-captcha'),
            ('funcaptcha', r'arkoselabs|funcaptcha|fc-token'),
            ('turnstile', r'cf-turnstile|turnstile'),
        ]
        
        for ctype, pattern in captcha_patterns:
            if re.search(pattern, page_content, re.IGNORECASE):
                has_captcha = True
                captcha_type = ctype
                break
        
        page_title = await page.title()
        form_id = hashlib.md5(f"{page.url}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        return FormAnalysis(
            form_locator=form,
            fields=fields,
            submit_button=submit_button,
            has_file_upload=has_file_upload,
            has_captcha=has_captcha,
            captcha_type=captcha_type,
            page_title=page_title,
            form_id=form_id,
        )


class FieldMapper:
    """Maps user data to form fields with intelligent matching."""
    
    def __init__(self, user_data: Dict[str, Any]):
        self.user_data = user_data
        self.field_mapping = {
            FieldType.EMAIL: user_data.get('email', ''),
            FieldType.PHONE: user_data.get('phone', ''),
            FieldType.FIRST_NAME: user_data.get('first_name', ''),
            FieldType.LAST_NAME: user_data.get('last_name', ''),
            FieldType.NAME: f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip(),
            FieldType.LINKEDIN: user_data.get('linkedin', ''),
            FieldType.PORTFOLIO: user_data.get('portfolio', ''),
        }
        
        self.demographic_defaults = {
            'gender': 'female',
            'race': 'two or more',
            'ethnicity': 'not hispanic',
            'veteran': 'no',
            'disability': 'no',
            'authorized': 'yes',
            'sponsorship': 'no',
        }
    
    def get_value_for_field(self, field: FormField) -> Optional[str]:
        """Get the appropriate value for a form field."""
        if field.field_type in self.field_mapping:
            return self.field_mapping[field.field_type]
        
        combined = f"{field.name} {field.label}".lower()
        
        for demo_key, demo_value in self.demographic_defaults.items():
            if demo_key in combined:
                return demo_value
        
        return None
    
    def get_select_value(self, field: FormField) -> Optional[str]:
        """Get the appropriate value for a select dropdown."""
        combined = f"{field.name} {field.label}".lower()
        
        target_value = None
        for demo_key, demo_value in self.demographic_defaults.items():
            if demo_key in combined:
                target_value = demo_value
                break
        
        if not target_value:
            return None
        
        for option in field.options:
            parts = option.split(':', 1)
            if len(parts) == 2:
                value, text = parts
                if target_value in text.lower():
                    return value
        
        return None


class CaptchaResolver:
    """Handles CAPTCHA detection and resolution via external services."""
    
    def __init__(self, api_key: str, daily_budget: float = 1.0):
        self.api_key = api_key
        self.daily_budget = daily_budget
        self.daily_spent = 0.0
        self.costs = {
            'recaptcha': 0.003,
            'hcaptcha': 0.003,
            'funcaptcha': 0.005,
            'turnstile': 0.003,
            'image': 0.002,
        }
    
    async def detect_captcha(self, page: Page) -> Tuple[bool, Optional[str], Optional[str], Optional[dict]]:
        """
        Detect CAPTCHA presence and extract all necessary parameters.
        Returns: (has_captcha, captcha_type, sitekey, extra_params)
        
        URL Patterns for CAPTCHA types:
        - FunCaptcha/Arkose: arkoselabs.com, funcaptcha.com, client-api.arkoselabs.com
        - reCAPTCHA: google.com/recaptcha, recaptcha.net
        - hCaptcha: hcaptcha.com, js.hcaptcha.com
        - Turnstile: challenges.cloudflare.com
        """
        page_content = await page.content()
        page_url = page.url
        extra_params = {}
        
        # FunCaptcha / Arkose Labs detection
        if re.search(r'arkoselabs|funcaptcha|arkose', page_content, re.IGNORECASE):
            sitekey = None
            surl = None
            
            # Method 1: data-pkey attribute
            pkey_match = re.search(r'data-pkey=["\']([^"\']+)["\']', page_content)
            if pkey_match:
                sitekey = pkey_match.group(1)
            
            # Method 2: Extract from fc-token input value (pk= parameter)
            fc_token_match = re.search(r'pk=([A-F0-9-]{36})', page_content, re.IGNORECASE)
            if fc_token_match and not sitekey:
                sitekey = fc_token_match.group(1)
            
            # Method 3: Look in script tags for public key
            script_pk_match = re.search(r'publicKey["\s:]+["\']([A-F0-9-]{36})["\']', page_content, re.IGNORECASE)
            if script_pk_match and not sitekey:
                sitekey = script_pk_match.group(1)
            
            # Extract service URL (surl) - critical for FunCaptcha
            surl_patterns = [
                r'surl=([^&"\'\s]+)',
                r'service_url["\s:]+["\']([^"\']+)["\']',
                r'(https://[^"\']*arkoselabs\.com[^"\']*)',
                r'(https://[^"\']*funcaptcha\.com[^"\']*)',
            ]
            for pattern in surl_patterns:
                surl_match = re.search(pattern, page_content, re.IGNORECASE)
                if surl_match:
                    surl = surl_match.group(1)
                    break
            
            if not surl:
                surl = "https://client-api.arkoselabs.com"
            
            extra_params['surl'] = surl
            print(f"   🔍 FunCaptcha detected - Key: {sitekey[:20] if sitekey else 'None'}..., sURL: {surl}")
            return True, 'funcaptcha', sitekey, extra_params
        
        # reCAPTCHA v2/v3 detection
        if re.search(r'g-recaptcha|grecaptcha|recaptcha', page_content, re.IGNORECASE):
            sitekey = None
            is_v3 = False
            is_enterprise = False
            action = None
            
            # Check for Enterprise version
            if re.search(r'enterprise\.js|grecaptcha\.enterprise', page_content, re.IGNORECASE):
                is_enterprise = True
            
            # Check for v3 (render parameter in script URL)
            v3_match = re.search(r'api\.js\?render=([^&"\'\s]+)', page_content)
            if v3_match:
                sitekey = v3_match.group(1)
                is_v3 = True
            
            # Standard sitekey extraction
            if not sitekey:
                sitekey_match = re.search(r'data-sitekey=["\']([^"\']+)["\']', page_content)
                if sitekey_match:
                    sitekey = sitekey_match.group(1)
            
            # Extract action for v3
            action_match = re.search(r'action["\s:]+["\']([^"\']+)["\']', page_content)
            if action_match:
                action = action_match.group(1)
            
            extra_params['is_v3'] = is_v3
            extra_params['is_enterprise'] = is_enterprise
            extra_params['action'] = action or 'verify'
            
            version = "Enterprise" if is_enterprise else ("v3" if is_v3 else "v2")
            print(f"   🔍 reCAPTCHA {version} detected - Key: {sitekey[:20] if sitekey else 'None'}...")
            return True, 'recaptcha', sitekey, extra_params
        
        # hCaptcha detection
        if re.search(r'h-captcha|hcaptcha', page_content, re.IGNORECASE):
            sitekey_match = re.search(r'data-sitekey=["\']([^"\']+)["\']', page_content)
            sitekey = sitekey_match.group(1) if sitekey_match else None
            print(f"   🔍 hCaptcha detected - Key: {sitekey[:20] if sitekey else 'None'}...")
            return True, 'hcaptcha', sitekey, extra_params
        
        # Cloudflare Turnstile detection
        if re.search(r'cf-turnstile|turnstile|challenges\.cloudflare', page_content, re.IGNORECASE):
            sitekey_match = re.search(r'data-sitekey=["\']([^"\']+)["\']', page_content)
            sitekey = sitekey_match.group(1) if sitekey_match else None
            print(f"   🔍 Turnstile detected - Key: {sitekey[:20] if sitekey else 'None'}...")
            return True, 'turnstile', sitekey, extra_params
        
        # Geetest detection
        if re.search(r'geetest|gt\.js|initGeetest', page_content, re.IGNORECASE):
            gt_match = re.search(r'gt["\s:]+["\']([^"\']+)["\']', page_content)
            challenge_match = re.search(r'challenge["\s:]+["\']([^"\']+)["\']', page_content)
            extra_params['gt'] = gt_match.group(1) if gt_match else None
            extra_params['challenge'] = challenge_match.group(1) if challenge_match else None
            print(f"   🔍 Geetest detected")
            return True, 'geetest', extra_params.get('gt'), extra_params
        
        return False, None, None, {}
    
    async def solve_via_screenshot(self, page: Page, instruction: str = "Solve the CAPTCHA") -> Optional[str]:
        """Solve CAPTCHA using screenshot-based approach for visual puzzles."""
        if self.daily_spent >= self.daily_budget:
            print("   ⚠️ Daily CAPTCHA budget exhausted")
            return None
        
        try:
            captcha_selectors = [
                'iframe[src*="arkoselabs"]',
                'iframe[src*="recaptcha"]',
                'iframe[src*="hcaptcha"]',
                '.captcha-container',
                '[class*="challenge"]',
                '[role="dialog"]',
            ]
            
            captcha_element = None
            for selector in captcha_selectors:
                try:
                    elem = page.locator(selector).first
                    if await elem.count() > 0 and await elem.is_visible():
                        captcha_element = elem
                        break
                except:
                    continue
            
            if not captcha_element:
                screenshot = await page.screenshot()
            else:
                screenshot = await captcha_element.screenshot()
            
            screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
            
            response = requests.post(
                'https://api.2captcha.com/createTask',
                json={
                    'clientKey': self.api_key,
                    'task': {
                        'type': 'ImageToTextTask',
                        'body': screenshot_b64,
                        'phrase': False,
                        'case': False,
                        'numeric': 0,
                        'math': False,
                        'minLength': 0,
                        'maxLength': 0,
                        'comment': instruction,
                    }
                },
                timeout=30
            )
            
            result = response.json()
            if result.get('errorId') != 0:
                return None
            
            task_id = result.get('taskId')
            if not task_id:
                return None
            
            for _ in range(30):
                await asyncio.sleep(5)
                
                response = requests.post(
                    'https://api.2captcha.com/getTaskResult',
                    json={
                        'clientKey': self.api_key,
                        'taskId': task_id
                    },
                    timeout=30
                )
                
                result = response.json()
                if result.get('status') == 'ready':
                    solution = result.get('solution', {}).get('text')
                    if solution:
                        self.daily_spent += self.costs.get('image', 0.002)
                        return solution
                
                if result.get('errorId') != 0:
                    return None
            
            return None
            
        except Exception as e:
            print(f"   ❌ Screenshot CAPTCHA solve error: {e}")
            return None
    
    async def wait_for_human_solve(self, page: Page, timeout: int = 300) -> bool:
        """Wait for human to solve CAPTCHA manually."""
        print(f"\n{'='*60}")
        print(f"🔐 HUMAN ASSISTANCE REQUIRED")
        print(f"   Please solve the CAPTCHA in the browser window...")
        print(f"   Timeout: {timeout} seconds")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        check_interval = 3
        
        while (time.time() - start_time) < timeout:
            elapsed = int(time.time() - start_time)
            remaining = timeout - elapsed
            
            if elapsed % 30 == 0 and elapsed > 0:
                print(f"   ⏳ Waiting for human... {remaining}s remaining")
            
            page_content = await page.content()
            
            success_indicators = ['thank you', 'application received', 'successfully', 'confirmation']
            if any(ind in page_content.lower() for ind in success_indicators):
                print("   ✅ CAPTCHA solved - success page detected")
                return True
            
            captcha_indicators = ['captcha', 'verify', 'challenge', 'arkoselabs']
            if not any(ind in page_content.lower() for ind in captcha_indicators):
                print("   ✅ CAPTCHA appears to be solved")
                return True
            
            await asyncio.sleep(check_interval)
        
        print("   ❌ CAPTCHA solve timeout")
        return False


class ApplicationEngine:
    """Main engine for executing job applications with full state management."""
    
    def __init__(self, user_data: Dict[str, Any], captcha_api_key: str = None):
        self.user_data = user_data
        self.field_mapper = FieldMapper(user_data)
        self.captcha_resolver = CaptchaResolver(captcha_api_key) if captcha_api_key else None
        self.state: Optional[ApplicationState] = None
        self.page: Optional[Page] = None
        self.context: Optional[BrowserContext] = None
    
    async def fill_field(self, field: FormField) -> bool:
        """Fill a single form field with appropriate value."""
        try:
            if not await field.element.is_visible():
                return False
            
            tag_name = await field.element.evaluate('el => el.tagName.toLowerCase()')
            input_type = await field.element.get_attribute('type') or 'text'
            
            if tag_name == 'select':
                value = self.field_mapper.get_select_value(field)
                if value:
                    await field.element.select_option(value=value)
                    return True
                return False
            
            if input_type == 'checkbox':
                combined = f"{field.name} {field.label}".lower()
                if any(kw in combined for kw in ['agree', 'consent', 'acknowledge', 'terms', 'privacy']):
                    await field.element.check()
                    return True
                return False
            
            if input_type == 'radio':
                return False
            
            if input_type == 'file':
                resume_path = self.user_data.get('resume_path', '')
                if resume_path and os.path.exists(resume_path):
                    await field.element.set_input_files(resume_path)
                    return True
                return False
            
            value = self.field_mapper.get_value_for_field(field)
            if value:
                await field.element.click()
                await field.element.fill('')
                await field.element.fill(value)
                return True
            
            return False
            
        except Exception as e:
            print(f"   ⚠️ Error filling field {field.name}: {e}")
            return False
    
    async def fill_form(self, analysis: FormAnalysis) -> int:
        """Fill all detected form fields. Returns count of fields filled."""
        filled_count = 0
        
        for field in analysis.fields:
            if not field.visible:
                continue
            
            if field.value and len(field.value) > 0:
                continue
            
            if await self.fill_field(field):
                filled_count += 1
                self.state.fields_filled.append(field.name)
                print(f"   ✓ Filled: {field.label or field.name}")
        
        # Handle Greenhouse-specific file upload (click-to-attach style)
        await self._handle_greenhouse_file_upload()
        
        # Handle any unfilled dropdowns
        await self._handle_unfilled_dropdowns()
        
        # Handle radio button groups
        await self._handle_radio_buttons()
        
        # Direct click approach for common radio questions
        await self._click_common_radio_answers()
        
        # Handle ALL remaining form fields with comprehensive config
        await self._fill_remaining_fields()
        
        return filled_count
    
    async def _fill_remaining_fields(self):
        """Fill any remaining unfilled fields using comprehensive field config."""
        try:
            from form_field_config import get_field_value, get_select_value, get_radio_answer, UserProfile
            profile = UserProfile()
            
            # Find all input fields that might still be empty
            all_inputs = await self.page.query_selector_all('input:not([type="hidden"]):not([type="submit"]):not([type="button"]), textarea, select')
            
            for inp in all_inputs:
                try:
                    # Skip already filled fields
                    tag = await inp.evaluate('el => el.tagName.toLowerCase()')
                    input_type = await inp.get_attribute('type') or 'text'
                    
                    if tag == 'select':
                        current = await inp.input_value()
                        if current and current.strip():
                            continue
                    elif tag in ['input', 'textarea']:
                        if input_type in ['checkbox', 'radio', 'file', 'submit', 'button']:
                            continue
                        current = await inp.input_value()
                        if current and current.strip():
                            continue
                    
                    # Get field identifiers
                    name = await inp.get_attribute('name') or ''
                    field_id = await inp.get_attribute('id') or ''
                    placeholder = await inp.get_attribute('placeholder') or ''
                    
                    # Try to get label text
                    label = await inp.evaluate('''el => {
                        const label = document.querySelector(`label[for="${el.id}"]`);
                        if (label) return label.innerText;
                        const parent = el.closest('label, .field, .form-group');
                        return parent ? parent.innerText : "";
                    }''')
                    
                    combined = f"{name} {field_id} {placeholder} {label}".lower()
                    
                    if tag == 'select':
                        # Get options
                        options = await inp.query_selector_all('option')
                        option_texts = []
                        for opt in options:
                            text = await opt.inner_text()
                            option_texts.append(text.strip())
                        
                        best_option = get_select_value(name, label, option_texts, profile)
                        if best_option:
                            for opt in options:
                                text = await opt.inner_text()
                                if text.strip() == best_option:
                                    val = await opt.get_attribute('value')
                                    if val:
                                        await inp.select_option(value=val)
                                        print(f"   ✓ Auto-filled select: {name or field_id}")
                                        break
                    else:
                        # Text input
                        value = get_field_value(name, label, profile)
                        if value:
                            await inp.fill(value)
                            print(f"   ✓ Auto-filled: {name or field_id}")
                        
                except Exception as e:
                    continue
                    
        except ImportError:
            pass  # form_field_config not available
        except Exception as e:
            print(f"   ⚠️ Error in _fill_remaining_fields: {e}")
    
    async def _click_common_radio_answers(self):
        """Directly click common radio button answers using Playwright locators."""
        try:
            # Use Playwright's powerful text-based locator to find and click "No" near Latin America text
            # First try to click the "No" text/label directly
            try:
                # Find the specific "No" option for Latin America question
                no_locator = self.page.locator('text=No').first
                if await no_locator.count() > 0:
                    await no_locator.click()
                    print(f"   ✓ Clicked 'No' option")
            except:
                pass
            
            # Alternative: Use JavaScript to click the radio button
            try:
                clicked = await self.page.evaluate('''() => {
                    // Find all radio inputs
                    const radios = document.querySelectorAll('input[type="radio"]');
                    for (const radio of radios) {
                        // Get the label text
                        const label = radio.nextElementSibling || radio.parentElement;
                        const labelText = label ? label.innerText.toLowerCase().trim() : '';
                        
                        // Check if this is the "No" option
                        if (labelText === 'no') {
                            radio.click();
                            return true;
                        }
                    }
                    return false;
                }''')
                if clicked:
                    print(f"   ✓ Clicked 'No' radio via JavaScript")
            except Exception as e:
                print(f"   ⚠️ JS radio click failed: {e}")
                    
        except Exception as e:
            print(f"   ⚠️ Direct radio click error: {e}")
    
    async def _handle_greenhouse_file_upload(self):
        """Handle Greenhouse's click-to-attach file upload style."""
        resume_path = self.user_data.get('resume_path', '')
        if not resume_path or not os.path.exists(resume_path):
            return
        
        try:
            # Find the hidden file input
            file_inputs = await self.page.query_selector_all('input[type="file"]')
            for file_input in file_inputs:
                try:
                    await file_input.set_input_files(resume_path)
                    print(f"   ✓ Resume file attached")
                    return
                except:
                    continue
            
            # Alternative: Click the attach button and use file chooser
            attach_selectors = [
                '[data-field="resume"] button',
                'button:has-text("attach")',
                'span:has-text("Click here to attach")',
                '.attach-or-paste button',
            ]
            for selector in attach_selectors:
                try:
                    attach_btn = await self.page.query_selector(selector)
                    if attach_btn:
                        async with self.page.expect_file_chooser() as fc_info:
                            await attach_btn.click()
                        file_chooser = await fc_info.value
                        await file_chooser.set_files(resume_path)
                        print(f"   ✓ Resume uploaded via file chooser")
                        return
                except:
                    continue
        except Exception as e:
            print(f"   ⚠️ File upload failed: {e}")
    
    async def _handle_unfilled_dropdowns(self):
        """Fill any unfilled dropdown/select fields."""
        try:
            selects = await self.page.query_selector_all('select')
            for select in selects:
                try:
                    # Check if already has a non-empty value
                    current_val = await select.input_value()
                    if current_val and current_val.strip() != '':
                        continue
                    
                    # Get all options and select the first non-placeholder one
                    options = await select.query_selector_all('option')
                    for i, opt in enumerate(options):
                        text = (await opt.inner_text()).strip().lower()
                        val = await opt.get_attribute('value')
                        
                        # Skip empty/placeholder options
                        if i == 0 or not val or val == '' or 'select' in text or 'choose' in text or text == '':
                            continue
                        
                        # For English level, prefer fluent/advanced
                        if 'fluent' in text or 'native' in text or 'advanced' in text or 'c1' in text or 'c2' in text:
                            await select.select_option(value=val)
                            print(f"   ✓ Dropdown selected: {text}")
                            break
                    else:
                        # If no preferred option found, select the second option (first real choice)
                        if len(options) > 1:
                            val = await options[1].get_attribute('value')
                            text = await options[1].inner_text()
                            if val:
                                await select.select_option(value=val)
                                print(f"   ✓ Dropdown selected (first available): {text.strip()}")
                except Exception as e:
                    print(f"   ⚠️ Dropdown error: {e}")
                    continue
        except Exception as e:
            print(f"   ⚠️ Dropdown handling error: {e}")
    
    async def _handle_radio_buttons(self):
        """Handle radio button groups with common questions."""
        try:
            # Find all radio button groups by finding unchecked radio buttons
            all_radios = await self.page.query_selector_all('input[type="radio"]:not(:checked)')
            
            # Track which groups we've handled
            handled_groups = set()
            
            for radio in all_radios:
                try:
                    name = await radio.get_attribute('name')
                    if not name or name in handled_groups:
                        continue
                    
                    # Get the question text by looking at parent elements
                    question_text = await radio.evaluate('''el => {
                        let parent = el.closest("fieldset, .field, .form-group, div.field");
                        if (!parent) parent = el.parentElement?.parentElement;
                        return parent ? parent.innerText : "";
                    }''')
                    question_lower = question_text.lower()
                    
                    # Get the label for this specific radio
                    label = await radio.evaluate('''el => {
                        let lbl = el.nextElementSibling || el.parentElement;
                        return lbl ? lbl.innerText : "";
                    }''')
                    label_lower = label.lower().strip()
                    
                    # Determine what answer to give based on question
                    should_click = False
                    
                    # Latin America / location questions - answer No (Deanna is in US)
                    if 'latin america' in question_lower or 'latam' in question_lower or 'based in' in question_lower:
                        if 'no' in label_lower:
                            should_click = True
                            print(f"   ✓ Latin America question: No")
                    
                    # Work authorization - answer Yes
                    elif 'authorized' in question_lower or 'legally' in question_lower or 'eligible to work' in question_lower:
                        if 'yes' in label_lower:
                            should_click = True
                            print(f"   ✓ Work authorization: Yes")
                    
                    # Sponsorship - answer No
                    elif 'sponsor' in question_lower or 'visa' in question_lower:
                        if 'no' in label_lower:
                            should_click = True
                            print(f"   ✓ Sponsorship: No")
                    
                    # 18+ / legal age - answer Yes
                    elif '18' in question_lower or 'legal age' in question_lower:
                        if 'yes' in label_lower:
                            should_click = True
                            print(f"   ✓ Age requirement: Yes")
                    
                    if should_click:
                        await radio.click()
                        handled_groups.add(name)
                        
                except Exception as e:
                    continue
        except Exception as e:
            print(f"   ⚠️ Radio button handling error: {e}")
    
    async def handle_captcha(self) -> bool:
        """Handle CAPTCHA if present on page using 2Captcha auto-solve."""
        has_captcha, captcha_type, sitekey, extra_params = await self.captcha_resolver.detect_captcha(self.page)
        
        if not has_captcha:
            return True
        
        print(f"\n🔐 CAPTCHA Detected: {captcha_type}")
        self.state.form_state = FormState.CAPTCHA_REQUIRED
        self.state.captcha_attempts += 1
        
        if self.state.captcha_attempts > 3:
            print("   ❌ Too many CAPTCHA attempts, aborting")
            return False
        
        page_url = self.page.url
        token = None
        
        # Try 2Captcha auto-solve first
        try:
            from captcha_handler import CaptchaSolverService
            solver = CaptchaSolverService()
            
            if solver.is_available():
                print(f"   🤖 Attempting 2Captcha auto-solve...")
                
                if captcha_type == 'funcaptcha' and sitekey:
                    surl = extra_params.get('surl', 'https://client-api.arkoselabs.com')
                    token, cost = await solver.solve_funcaptcha(sitekey, page_url, surl)
                    
                elif captcha_type == 'recaptcha' and sitekey:
                    is_v3 = extra_params.get('is_v3', False)
                    if is_v3:
                        action = extra_params.get('action', 'verify')
                        token, cost = await solver.solve_recaptcha_v3(sitekey, page_url, action)
                    else:
                        token, cost = await solver.solve_recaptcha_v2(sitekey, page_url)
                        
                elif captcha_type == 'hcaptcha' and sitekey:
                    token, cost = await solver.solve_hcaptcha(sitekey, page_url)
                
                if token:
                    # Inject the token into the page
                    await self._inject_captcha_token(captcha_type, token)
                    self.state.form_state = FormState.IN_PROGRESS
                    return True
                else:
                    print(f"   ⚠️ 2Captcha auto-solve failed, falling back to human")
        except Exception as e:
            print(f"   ⚠️ 2Captcha error: {e}, falling back to human")
        
        # Fallback to human solve
        solved = await self.captcha_resolver.wait_for_human_solve(self.page)
        
        if solved:
            self.state.form_state = FormState.IN_PROGRESS
            return True
        
        return False
    
    async def _inject_captcha_token(self, captcha_type: str, token: str) -> bool:
        """Inject solved CAPTCHA token into the page."""
        try:
            if captcha_type == 'funcaptcha':
                # FunCaptcha: Set fc-token input value
                await self.page.evaluate(f'''() => {{
                    const fcToken = document.querySelector('input[name="fc-token"]');
                    if (fcToken) fcToken.value = "{token}";
                    
                    // Also try setting via callback
                    if (window.ArkoseEnforcement) {{
                        window.ArkoseEnforcement.setConfig({{ onCompleted: () => {{}} }});
                    }}
                }}''')
                print(f"   ✅ FunCaptcha token injected")
                
            elif captcha_type == 'recaptcha':
                # reCAPTCHA: Set g-recaptcha-response textarea
                await self.page.evaluate(f'''() => {{
                    const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                    if (textarea) {{
                        textarea.value = "{token}";
                        textarea.style.display = "block";
                    }}
                    
                    // Also try calling callback
                    if (window.grecaptcha && window.grecaptcha.getResponse) {{
                        // Trigger any registered callbacks
                    }}
                }}''')
                print(f"   ✅ reCAPTCHA token injected")
                
            elif captcha_type == 'hcaptcha':
                # hCaptcha: Set h-captcha-response textarea
                await self.page.evaluate(f'''() => {{
                    const textarea = document.querySelector('textarea[name="h-captcha-response"]');
                    if (textarea) textarea.value = "{token}";
                    
                    const gResponse = document.querySelector('textarea[name="g-recaptcha-response"]');
                    if (gResponse) gResponse.value = "{token}";
                }}''')
                print(f"   ✅ hCaptcha token injected")
            
            return True
        except Exception as e:
            print(f"   ⚠️ Token injection error: {e}")
            return False
    
    async def _check_required_fields_filled(self) -> Tuple[bool, List[str]]:
        """Check if all required fields have values. Returns (all_filled, list of empty required fields)."""
        empty_fields = []
        
        try:
            # Check all inputs with required attribute or aria-required
            required_inputs = await self.page.query_selector_all('input[required], input[aria-required="true"], select[required], textarea[required]')
            
            for inp in required_inputs:
                try:
                    value = await inp.input_value()
                    if not value or value.strip() == '':
                        name = await inp.get_attribute('name') or await inp.get_attribute('id') or 'unknown'
                        empty_fields.append(name)
                except:
                    continue
            
            # Also check for "This field is required" error messages
            error_messages = await self.page.query_selector_all('[class*="error"], [class*="required"], .field-error')
            for err in error_messages:
                try:
                    text = await err.inner_text()
                    if 'required' in text.lower() or 'this field' in text.lower():
                        # Try to get the field name from parent
                        parent_text = await err.evaluate('el => el.closest(".field, .form-group, label")?.innerText || ""')
                        if parent_text:
                            empty_fields.append(parent_text[:30])
                except:
                    continue
            
            return len(empty_fields) == 0, empty_fields
        except Exception as e:
            print(f"   ⚠️ Error checking required fields: {e}")
            return True, []  # Assume OK if check fails
    
    async def submit_form(self, analysis: FormAnalysis) -> bool:
        """Submit the form and verify submission."""
        if not analysis.submit_button:
            print("   ⚠️ No submit button found")
            return False
        
        # Check all required fields are filled BEFORE submitting
        all_filled, empty_fields = await self._check_required_fields_filled()
        if not all_filled:
            print(f"   ⚠️ Required fields still empty: {empty_fields[:5]}")
            # Try to fill them one more time
            await self._handle_unfilled_dropdowns()
            await self._handle_radio_buttons()
            await asyncio.sleep(1)
            
            # Check again
            all_filled, empty_fields = await self._check_required_fields_filled()
            if not all_filled:
                print(f"   ❌ Cannot submit - required fields empty: {empty_fields}")
                return False
        
        # Record URL before submit to detect redirect
        url_before = self.page.url
        
        try:
            await analysis.submit_button.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            await analysis.submit_button.click()
            print("   ✓ Submit button clicked")
            
            # Wait for potential redirect or page change
            await asyncio.sleep(3)
            
            # Check for URL change (strong indicator of success)
            url_after = self.page.url
            if url_after != url_before:
                print(f"   ✓ Page redirected: {url_after[:60]}...")
            
            page_content = await self.page.content()
            
            captcha_indicators = ['captcha', 'verify', 'challenge', 'arkoselabs', 'recaptcha', 'hcaptcha']
            if any(ind in page_content.lower() for ind in captcha_indicators):
                if not await self.handle_captcha():
                    return False
            
            await asyncio.sleep(2)
            page_content = await self.page.content()
            
            # More specific success indicators to avoid FAQ false positives
            success_indicators = [
                'thank you for applying',
                'application has been received',
                'application has been submitted',
                'we have received your application',
                'successfully submitted',
                'thank you for your interest',
                'application complete',
            ]
            page_lower = page_content.lower()
            if any(ind in page_lower for ind in success_indicators):
                self.state.form_state = FormState.SUCCESS
                print("   ✅ SUCCESS: Found confirmation on page")
                return True
            
            error_indicators = ['error', 'invalid', 'required', 'please fill', 'missing', 'complete all']
            if any(ind in page_content.lower() for ind in error_indicators):
                self.state.form_state = FormState.FAILED
                print("   ❌ FAILED: Error indicators found on page")
                return False
            
            # Check if we're still on the same page (form not submitted)
            form_still_present = await self.page.query_selector('form input, button[type="submit"]')
            if form_still_present:
                self.state.form_state = FormState.FAILED
                print("   ⚠️ WARNING: Form still present - submission may have failed")
                return False
            
            # Only mark as submitted (not success) if no clear indicators
            self.state.form_state = FormState.SUBMITTED
            print("   ⚠️ UNCERTAIN: No clear success/failure indicators - marking as submitted but unverified")
            return True
            
        except Exception as e:
            print(f"   ❌ Submit error: {e}")
            self.state.errors.append(str(e))
            return False
    
    async def take_screenshot(self, name: str) -> str:
        """Take a screenshot for debugging/verification."""
        screenshots_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'applications')
        os.makedirs(screenshots_dir, exist_ok=True)
        
        path = os.path.join(screenshots_dir, f'{name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
        await self.page.screenshot(path=path)
        self.state.screenshots.append(path)
        return path
    
    async def apply(self, job_url: str, job_title: str, company: str, resume_path: str, cover_letter: str = "") -> Dict:
        """Execute the full application flow."""
        self.user_data['resume_path'] = resume_path
        self.user_data['cover_letter'] = cover_letter
        
        self.state = ApplicationState(
            job_url=job_url,
            company=company,
            job_title=job_title,
        )
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=200)
            self.context = await browser.new_context()
            self.page = await self.context.new_page()
            
            try:
                print(f"\n🌐 Navigating to: {job_url}")
                await self.page.goto(job_url, wait_until='domcontentloaded', timeout=60000)
                
                await DOMAnalyzer.wait_for_stable_dom(self.page)
                
                page_content = await self.page.content()
                page_title = await self.page.title()
                current_url = self.page.url
                
                # Check for 404/invalid page indicators
                invalid_page_indicators = [
                    'no longer open', 'position has been filled', 'no longer accepting', 
                    'position is closed', 'couldn\'t find anything', '404 error',
                    'has been removed', 'job has closed', 'posting has expired',
                    'sorry, we couldn\'t find', 'page not found', 'this page doesn\'t exist',
                    'oops! we can\'t find', 'the page you requested', 'job not found',
                    'this job is no longer available', 'error 404', 'not found',
                    'we can\'t find that page', 'sorry, but we can\'t find'
                ]
                
                # Also check page title for 404
                page_check = (page_content + ' ' + page_title).lower()
                
                if any(ind in page_check for ind in invalid_page_indicators):
                    print(f"   ❌ Invalid/closed job page detected")
                    await browser.close()
                    return {"success": False, "error": "Job posting is no longer open"}
                
                # Check if page loaded but has minimal content (likely error page)
                if len(page_content) < 1000 and ('404' in current_url or 'error' in current_url.lower()):
                    print(f"   ❌ Error page detected (minimal content)")
                    await browser.close()
                    return {"success": False, "error": "Job page returned error"}
                
                # Navigate to apply page if needed
                current_url = self.page.url
                if '/apply' not in current_url.lower():
                    # Try clicking Apply button or navigating directly
                    apply_selectors = [
                        'a:has-text("Apply for this job")',
                        'a:has-text("Apply now")',
                        'a:has-text("Apply")',
                        'button:has-text("Apply")',
                        'a.postings-btn',
                        '[data-qa="show-page-apply"]',
                    ]
                    clicked = False
                    for selector in apply_selectors:
                        try:
                            btn = self.page.locator(selector).first
                            if await btn.count() > 0 and await btn.is_visible():
                                await btn.click()
                                print("   ✓ Clicked Apply button")
                                clicked = True
                                await asyncio.sleep(3)
                                break
                        except:
                            continue
                    
                    # If no button found, try direct URL navigation
                    if not clicked:
                        apply_url = job_url.rstrip('/') + '/apply'
                        print(f"   Navigating to: {apply_url}")
                        await self.page.goto(apply_url, wait_until='domcontentloaded', timeout=30000)
                
                await DOMAnalyzer.wait_for_stable_dom(self.page)
                
                # Wait for form elements to appear
                form_wait_selectors = [
                    'input[name="name"]',
                    'input[name="email"]',
                    'input[type="email"]',
                    'form input',
                    '.application-form',
                ]
                form_found = False
                for selector in form_wait_selectors:
                    try:
                        await self.page.wait_for_selector(selector, timeout=5000)
                        form_found = True
                        break
                    except:
                        continue
                
                if not form_found:
                    # Take debug screenshot
                    await self.take_screenshot(f'{company}_debug_noform')
                    print("   ⚠️ Form elements not immediately visible, waiting longer...")
                    await asyncio.sleep(3)
                
                print("\n📋 Analyzing form structure...")
                analysis = await DOMAnalyzer.analyze_form(self.page)
                print(f"   Found {len(analysis.fields)} form fields")
                print(f"   Submit button: {'Yes' if analysis.submit_button else 'No'}")
                print(f"   File upload: {'Yes' if analysis.has_file_upload else 'No'}")
                print(f"   CAPTCHA detected: {analysis.captcha_type or 'No'}")
                
                self.state.form_state = FormState.IN_PROGRESS
                
                print("\n📝 Filling form fields...")
                filled = await self.fill_form(analysis)
                print(f"   Filled {filled} fields")
                
                await self.take_screenshot(f'{company}_prefill')
                
                print("\n⏳ Waiting before submit...")
                await asyncio.sleep(3)
                
                print("\n🚀 Submitting application...")
                success = await self.submit_form(analysis)
                
                await self.take_screenshot(f'{company}_result')
                
                await browser.close()
                
                return {
                    "success": success,
                    "state": self.state.form_state.value,
                    "fields_filled": len(self.state.fields_filled),
                    "screenshots": self.state.screenshots,
                    "errors": self.state.errors,
                    "captcha_attempts": self.state.captcha_attempts,
                    "message": "Application submitted successfully!" if success else "Application may have issues",
                }
                
            except Exception as e:
                await self.take_screenshot(f'{company}_error')
                await browser.close()
                return {
                    "success": False,
                    "error": str(e),
                    "state": self.state.form_state.value if self.state else "unknown",
                    "screenshots": self.state.screenshots if self.state else [],
                }


async def apply_with_engine(
    job_url: str,
    job_title: str,
    company: str,
    resume_path: str,
    cover_letter: str,
    user_info: Dict,
) -> Dict:
    """Main entry point for applying to jobs using the new engine."""
    
    captcha_key = os.environ.get('CaptchaKey') or os.environ.get('CAPTCHA_2CAPTCHA_KEY')
    
    engine = ApplicationEngine(user_info, captcha_key)
    
    return await engine.apply(job_url, job_title, company, resume_path, cover_letter)
