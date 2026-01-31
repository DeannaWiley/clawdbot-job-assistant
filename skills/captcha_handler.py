"""
CAPTCHA HANDLER - Multi-Tier Resolution System for ClawdBot
============================================================

Architecture:
  Tier 1: Auto-detection and simple bypass (cookie reuse, accessibility mode)
  Tier 2: Third-party CAPTCHA solving services (2Captcha, Anti-Captcha)
  Tier 3: Human-in-the-loop via Slack notification + desktop alert

Cost Model:
  - Free: Human-assisted only
  - $5-10/month: ~500-1000 CAPTCHAs via 2Captcha
  - $25/month: ~2500 CAPTCHAs + premium support

Design Principles:
  - Graceful degradation (never crash, always fallback)
  - Rate limiting to avoid abuse signals
  - Session persistence to minimize CAPTCHA encounters
  - Full logging for debugging and optimization
"""

import os
import sys
import json
import time
import asyncio
import hashlib
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Callable
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum


class CaptchaType(Enum):
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    FUNCAPTCHA = "funcaptcha"
    IMAGE_CAPTCHA = "image"
    TEXT_CAPTCHA = "text"
    TURNSTILE = "turnstile"
    UNKNOWN = "unknown"


class ResolutionTier(Enum):
    AUTO = 1          # Automatic bypass attempts
    SERVICE = 2       # Paid CAPTCHA solving services
    HUMAN = 3         # Human-in-the-loop
    FAILED = 4        # All tiers exhausted


@dataclass
class CaptchaChallenge:
    """Represents a detected CAPTCHA challenge."""
    challenge_id: str
    captcha_type: CaptchaType
    site_key: Optional[str]
    page_url: str
    detected_at: datetime
    screenshot_path: Optional[str] = None
    html_snippet: Optional[str] = None
    
    def to_dict(self):
        d = asdict(self)
        d['captcha_type'] = self.captcha_type.value
        d['detected_at'] = self.detected_at.isoformat()
        return d


@dataclass
class CaptchaResult:
    """Result of a CAPTCHA resolution attempt."""
    success: bool
    tier_used: ResolutionTier
    solution: Optional[str] = None
    token: Optional[str] = None
    time_taken: float = 0
    cost: float = 0
    error: Optional[str] = None
    
    def to_dict(self):
        d = asdict(self)
        d['tier_used'] = self.tier_used.value
        return d


class CaptchaMetrics:
    """Tracks CAPTCHA resolution metrics for optimization."""
    
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.data_dir / "captcha_metrics.json"
        self.load()
    
    def load(self):
        if self.metrics_file.exists():
            with open(self.metrics_file, 'r') as f:
                self.data = json.load(f)
        else:
            self.data = {
                "total_challenges": 0,
                "tier1_success": 0,
                "tier2_success": 0,
                "tier3_success": 0,
                "failures": 0,
                "total_cost": 0.0,
                "daily_stats": {},
                "by_type": {},
                "by_site": {}
            }
    
    def save(self):
        with open(self.metrics_file, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def record(self, challenge: CaptchaChallenge, result: CaptchaResult):
        today = datetime.now().strftime("%Y-%m-%d")
        
        self.data["total_challenges"] += 1
        
        if result.success:
            tier_key = f"tier{result.tier_used.value}_success"
            self.data[tier_key] = self.data.get(tier_key, 0) + 1
        else:
            self.data["failures"] += 1
        
        self.data["total_cost"] += result.cost
        
        # Daily stats
        if today not in self.data["daily_stats"]:
            self.data["daily_stats"][today] = {"attempts": 0, "success": 0, "cost": 0}
        self.data["daily_stats"][today]["attempts"] += 1
        if result.success:
            self.data["daily_stats"][today]["success"] += 1
        self.data["daily_stats"][today]["cost"] += result.cost
        
        # By type
        ctype = challenge.captcha_type.value
        if ctype not in self.data["by_type"]:
            self.data["by_type"][ctype] = {"attempts": 0, "success": 0}
        self.data["by_type"][ctype]["attempts"] += 1
        if result.success:
            self.data["by_type"][ctype]["success"] += 1
        
        self.save()
    
    def get_success_rate(self) -> float:
        total = self.data["total_challenges"]
        if total == 0:
            return 0
        successes = (
            self.data.get("tier1_success", 0) +
            self.data.get("tier2_success", 0) +
            self.data.get("tier3_success", 0)
        )
        return (successes / total) * 100
    
    def get_daily_cost(self) -> float:
        today = datetime.now().strftime("%Y-%m-%d")
        return self.data["daily_stats"].get(today, {}).get("cost", 0)
    
    def get_summary(self) -> str:
        return f"""
CAPTCHA Metrics Summary
=======================
Total Challenges: {self.data['total_challenges']}
Success Rate: {self.get_success_rate():.1f}%
  - Tier 1 (Auto): {self.data.get('tier1_success', 0)}
  - Tier 2 (Service): {self.data.get('tier2_success', 0)}
  - Tier 3 (Human): {self.data.get('tier3_success', 0)}
  - Failed: {self.data['failures']}
Total Cost: ${self.data['total_cost']:.2f}
Today's Cost: ${self.get_daily_cost():.2f}
"""


class CaptchaSolvingService:
    """Integration with CAPTCHA solving services (2Captcha, Anti-Captcha)."""
    
    # Pricing (approximate, 2024-2025 rates)
    PRICING = {
        "2captcha": {
            "recaptcha_v2": 0.003,      # $2.99 per 1000
            "recaptcha_v3": 0.004,      # $3.99 per 1000
            "hcaptcha": 0.003,          # $2.99 per 1000
            "funcaptcha": 0.004,        # $3.99 per 1000
            "image": 0.001,             # $0.99 per 1000
            "turnstile": 0.003,         # $2.99 per 1000
        },
        "anti-captcha": {
            "recaptcha_v2": 0.002,
            "recaptcha_v3": 0.003,
            "hcaptcha": 0.002,
            "funcaptcha": 0.003,
            "image": 0.001,
            "turnstile": 0.002,
        }
    }
    
    def __init__(self):
        # Check multiple env var names for compatibility
        self.api_key_2captcha = (
            os.environ.get("CAPTCHA_2CAPTCHA_KEY") or 
            os.environ.get("CaptchaKey") or
            os.environ.get("TWOCAPTCHA_KEY")
        )
        self.api_key_anticaptcha = os.environ.get("CAPTCHA_ANTICAPTCHA_KEY")
        self.preferred_service = "2captcha" if self.api_key_2captcha else "anti-captcha"
        self.daily_budget = float(
            os.environ.get("CAPTCHA_DAILY_BUDGET") or 
            os.environ.get("CaptchaBudget") or 
            "1.0"
        )
        self.daily_spent = 0.0
        self.last_reset = datetime.now().date()
        
        if self.api_key_2captcha:
            print(f"✅ 2Captcha API key loaded (budget: ${self.daily_budget}/day)")
    
    def _reset_daily_if_needed(self):
        today = datetime.now().date()
        if today > self.last_reset:
            self.daily_spent = 0.0
            self.last_reset = today
    
    def _check_budget(self, estimated_cost: float) -> bool:
        self._reset_daily_if_needed()
        return (self.daily_spent + estimated_cost) <= self.daily_budget
    
    def get_estimated_cost(self, captcha_type: CaptchaType) -> float:
        type_key = captcha_type.value.replace("_v2", "_v2").replace("_v3", "_v3")
        return self.PRICING.get(self.preferred_service, {}).get(type_key, 0.005)
    
    def is_available(self) -> bool:
        return bool(self.api_key_2captcha or self.api_key_anticaptcha)
    
    async def solve_recaptcha_v2(
        self,
        site_key: str,
        page_url: str,
        invisible: bool = False
    ) -> Tuple[Optional[str], float]:
        """Solve reCAPTCHA v2 using 2Captcha API."""
        
        if not self.api_key_2captcha:
            return None, 0
        
        cost = self.get_estimated_cost(CaptchaType.RECAPTCHA_V2)
        if not self._check_budget(cost):
            print(f"⚠️ Daily CAPTCHA budget (${self.daily_budget}) reached")
            return None, 0
        
        try:
            # Submit task
            submit_url = "http://2captcha.com/in.php"
            params = {
                "key": self.api_key_2captcha,
                "method": "userrecaptcha",
                "googlekey": site_key,
                "pageurl": page_url,
                "invisible": 1 if invisible else 0,
                "json": 1
            }
            
            response = requests.post(submit_url, data=params, timeout=30)
            result = response.json()
            
            if result.get("status") != 1:
                print(f"❌ 2Captcha submit error: {result.get('request')}")
                return None, 0
            
            task_id = result["request"]
            print(f"📤 CAPTCHA submitted to 2Captcha (ID: {task_id})")
            
            # Poll for result (max 120 seconds)
            result_url = "http://2captcha.com/res.php"
            for attempt in range(24):  # 24 * 5s = 120s max
                await asyncio.sleep(5)
                
                response = requests.get(result_url, params={
                    "key": self.api_key_2captcha,
                    "action": "get",
                    "id": task_id,
                    "json": 1
                }, timeout=30)
                
                result = response.json()
                
                if result.get("status") == 1:
                    self.daily_spent += cost
                    print(f"✅ CAPTCHA solved (cost: ${cost:.4f})")
                    return result["request"], cost
                
                if result.get("request") != "CAPCHA_NOT_READY":
                    print(f"❌ 2Captcha error: {result.get('request')}")
                    return None, 0
                
                print(f"   ⏳ Waiting for solution... ({attempt + 1}/24)")
            
            print("❌ CAPTCHA solve timeout (120s)")
            return None, 0
            
        except Exception as e:
            print(f"❌ 2Captcha error: {e}")
            return None, 0
    
    async def solve_hcaptcha(
        self,
        site_key: str,
        page_url: str
    ) -> Tuple[Optional[str], float]:
        """Solve hCaptcha using 2Captcha API."""
        
        if not self.api_key_2captcha:
            return None, 0
        
        cost = self.get_estimated_cost(CaptchaType.HCAPTCHA)
        if not self._check_budget(cost):
            return None, 0
        
        try:
            submit_url = "http://2captcha.com/in.php"
            params = {
                "key": self.api_key_2captcha,
                "method": "hcaptcha",
                "sitekey": site_key,
                "pageurl": page_url,
                "json": 1
            }
            
            response = requests.post(submit_url, data=params, timeout=30)
            result = response.json()
            
            if result.get("status") != 1:
                return None, 0
            
            task_id = result["request"]
            
            result_url = "http://2captcha.com/res.php"
            for _ in range(24):
                await asyncio.sleep(5)
                
                response = requests.get(result_url, params={
                    "key": self.api_key_2captcha,
                    "action": "get",
                    "id": task_id,
                    "json": 1
                }, timeout=30)
                
                result = response.json()
                
                if result.get("status") == 1:
                    self.daily_spent += cost
                    return result["request"], cost
                
                if result.get("request") != "CAPCHA_NOT_READY":
                    return None, 0
            
            return None, 0
            
        except Exception as e:
            print(f"❌ hCaptcha solve error: {e}")
            return None, 0
    
    async def solve_funcaptcha(
        self,
        public_key: str,
        page_url: str,
        service_url: str = None
    ) -> Tuple[Optional[str], float]:
        """Solve FunCaptcha (Arkose Labs) using 2Captcha API with multiple methods."""
        
        if not self.api_key_2captcha:
            return None, 0
        
        cost = self.get_estimated_cost(CaptchaType.FUNCAPTCHA)
        if not self._check_budget(cost):
            print(f"⚠️ Daily CAPTCHA budget (${self.daily_budget}) reached")
            return None, 0
        
        # Try the legacy API first (more reliable for some implementations)
        try:
            print(f"📤 Submitting FunCaptcha to 2Captcha...")
            print(f"   Public Key: {public_key[:20]}...")
            print(f"   Service URL: {service_url or 'default'}")
            
            # Use legacy API which works better for some FunCaptcha implementations
            submit_url = "http://2captcha.com/in.php"
            params = {
                "key": self.api_key_2captcha,
                "method": "funcaptcha",
                "publickey": public_key,
                "pageurl": page_url,
                "json": 1
            }
            
            if service_url:
                params["surl"] = service_url
            
            response = requests.post(submit_url, data=params, timeout=30)
            result = response.json()
            
            if result.get("status") != 1:
                error_msg = result.get("request", "Unknown error")
                print(f"   Legacy API error: {error_msg}")
                
                # If legacy fails, try createTask API
                print(f"   Trying createTask API...")
                return await self._solve_funcaptcha_v2(public_key, page_url, service_url, cost)
            
            task_id = result["request"]
            print(f"   Task ID: {task_id}")
            
            # Poll for result
            result_url = "http://2captcha.com/res.php"
            for attempt in range(36):  # 36 * 5s = 180s max
                await asyncio.sleep(5)
                
                response = requests.get(result_url, params={
                    "key": self.api_key_2captcha,
                    "action": "get",
                    "id": task_id,
                    "json": 1
                }, timeout=30)
                
                result = response.json()
                
                if result.get("status") == 1:
                    self.daily_spent += cost
                    print(f"✅ FunCaptcha solved (cost: ${cost:.4f})")
                    return result["request"], cost
                
                if result.get("request") != "CAPCHA_NOT_READY":
                    print(f"❌ 2Captcha error: {result.get('request')}")
                    break
                
                if attempt % 6 == 0:
                    print(f"   ⏳ Waiting for solution... ({attempt * 5}s)")
            
            return None, 0
            
        except Exception as e:
            print(f"❌ FunCaptcha solve error: {e}")
            return None, 0
    
    async def _solve_funcaptcha_v2(
        self,
        public_key: str,
        page_url: str,
        service_url: str,
        cost: float
    ) -> Tuple[Optional[str], float]:
        """Fallback: Solve FunCaptcha using createTask API."""
        
        try:
            create_url = "https://api.2captcha.com/createTask"
            
            task_data = {
                "clientKey": self.api_key_2captcha,
                "task": {
                    "type": "FunCaptchaTaskProxyless",
                    "websiteURL": page_url,
                    "websitePublicKey": public_key,
                    "funcaptchaApiJSSubdomain": service_url or "client-api.arkoselabs.com",
                    "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            }
            
            response = requests.post(create_url, json=task_data, timeout=30)
            result = response.json()
            
            if result.get("errorId") != 0:
                error_code = result.get("errorCode", "Unknown")
                print(f"   createTask error: {error_code}")
                return None, 0
            
            task_id = result.get("taskId")
            if not task_id:
                return None, 0
                
            print(f"   Task ID: {task_id}")
            
            result_url = "https://api.2captcha.com/getTaskResult"
            for attempt in range(36):
                await asyncio.sleep(5)
                
                response = requests.post(result_url, json={
                    "clientKey": self.api_key_2captcha,
                    "taskId": task_id
                }, timeout=30)
                
                result = response.json()
                
                if result.get("status") == "ready":
                    solution = result.get("solution", {}).get("token")
                    if solution:
                        self.daily_spent += cost
                        print(f"✅ FunCaptcha solved via v2 (cost: ${cost:.4f})")
                        return solution, cost
                
                if result.get("errorId") != 0:
                    return None, 0
                
                if attempt % 6 == 0:
                    print(f"   ⏳ Waiting... ({attempt * 5}s)")
            
            return None, 0
            
        except Exception as e:
            print(f"❌ FunCaptcha v2 error: {e}")
            return None, 0
    
    async def solve_funcaptcha_image(
        self,
        page,
        cost: float
    ) -> Tuple[Optional[str], float]:
        """Solve FunCaptcha using image-based approach (GridTask API)."""
        
        try:
            import base64
            
            # Find the CAPTCHA element - try multiple selectors
            captcha_selectors = [
                'iframe[src*="arkoselabs"]',
                'iframe[src*="funcaptcha"]',
                'iframe[id*="fc-iframe"]',
                '.fc-iframe-wrap iframe',
                '[id*="arkose"]',
                '[class*="arkose"]',
                '.captcha-container',
                '[data-callback*="arkose"]',
                'div[style*="arkoselabs"]',
            ]
            
            captcha_element = None
            for selector in captcha_selectors:
                try:
                    captcha_element = await page.query_selector(selector)
                    if captcha_element:
                        break
                except:
                    continue
            
            # If no specific element found, take screenshot of visible CAPTCHA area
            if not captcha_element:
                # Try to find any modal or overlay that might contain the CAPTCHA
                modal_selectors = [
                    '.modal',
                    '[role="dialog"]',
                    '.overlay',
                    '.captcha',
                    '[class*="challenge"]',
                ]
                for selector in modal_selectors:
                    try:
                        captcha_element = await page.query_selector(selector)
                        if captcha_element:
                            break
                    except:
                        continue
            
            if not captcha_element:
                print("   ⚠️ No CAPTCHA element found for image capture")
                return None, 0
            
            # Take screenshot of the CAPTCHA
            screenshot_bytes = await captcha_element.screenshot()
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            # Try to extract instruction text from the page
            instruction = ""
            instruction_selectors = [
                '.sc-1io4bok-0',
                '.fc-button-header',
                '[class*="instruction"]',
                '[class*="prompt"]',
            ]
            
            for selector in instruction_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        instruction = await elem.inner_text()
                        if instruction:
                            break
                except:
                    continue
            
            if not instruction:
                instruction = "Solve the image puzzle"
            
            print(f"   📸 Captured CAPTCHA screenshot")
            print(f"   📝 Instruction: {instruction[:50]}...")
            
            # Submit to 2Captcha GridTask API
            submit_url = "https://api.2captcha.com/createTask"
            
            task_data = {
                "clientKey": self.api_key_2captcha,
                "task": {
                    "type": "GridTask",
                    "body": screenshot_b64,
                    "comment": instruction,
                    "imgType": "funcaptcha"
                }
            }
            
            response = requests.post(submit_url, json=task_data, timeout=30)
            result = response.json()
            
            if result.get("errorId") != 0:
                error_code = result.get("errorCode", "Unknown")
                print(f"   ❌ GridTask error: {error_code}")
                return None, 0
            
            task_id = result.get("taskId")
            if not task_id:
                return None, 0
            
            print(f"   Task ID: {task_id}")
            
            # Poll for result
            result_url = "https://api.2captcha.com/getTaskResult"
            for attempt in range(24):  # 24 * 5s = 120s max
                await asyncio.sleep(5)
                
                response = requests.post(result_url, json={
                    "clientKey": self.api_key_2captcha,
                    "taskId": task_id
                }, timeout=30)
                
                result = response.json()
                
                if result.get("status") == "ready":
                    solution = result.get("solution", {})
                    # GridTask returns click coordinates or selected indices
                    click_data = solution.get("click", [])
                    if click_data:
                        self.daily_spent += cost
                        print(f"   ✅ CAPTCHA solved via image (cost: ${cost:.4f})")
                        return str(click_data), cost
                
                if result.get("errorId") != 0:
                    return None, 0
                
                if attempt % 4 == 0:
                    print(f"   ⏳ Waiting for image solution... ({attempt * 5}s)")
            
            return None, 0
            
        except Exception as e:
            print(f"   ❌ Image-based solving error: {e}")
            return None, 0

    async def solve_turnstile(
        self,
        site_key: str,
        page_url: str
    ) -> Tuple[Optional[str], float]:
        """Solve Cloudflare Turnstile using 2Captcha API."""
        
        if not self.api_key_2captcha:
            return None, 0
        
        cost = self.get_estimated_cost(CaptchaType.TURNSTILE)
        if not self._check_budget(cost):
            return None, 0
        
        try:
            submit_url = "http://2captcha.com/in.php"
            params = {
                "key": self.api_key_2captcha,
                "method": "turnstile",
                "sitekey": site_key,
                "pageurl": page_url,
                "json": 1
            }
            
            response = requests.post(submit_url, data=params, timeout=30)
            result = response.json()
            
            if result.get("status") != 1:
                return None, 0
            
            task_id = result["request"]
            
            result_url = "http://2captcha.com/res.php"
            for _ in range(24):
                await asyncio.sleep(5)
                
                response = requests.get(result_url, params={
                    "key": self.api_key_2captcha,
                    "action": "get",
                    "id": task_id,
                    "json": 1
                }, timeout=30)
                
                result = response.json()
                
                if result.get("status") == 1:
                    self.daily_spent += cost
                    return result["request"], cost
                
                if result.get("request") != "CAPCHA_NOT_READY":
                    return None, 0
            
            return None, 0
            
        except Exception as e:
            print(f"❌ Turnstile solve error: {e}")
            return None, 0


class HumanAssistant:
    """Human-in-the-loop CAPTCHA resolution via Slack with screenshot upload."""
    
    def __init__(self, slack_channel: str = None):
        self.slack_channel = slack_channel or os.environ.get("SLACK_CAPTCHA_CHANNEL", "C0ABG9NGNTZ")
        self.timeout_seconds = 300  # 5 minute timeout for human response
        self.screenshot_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'captcha_screenshots')
        os.makedirs(self.screenshot_dir, exist_ok=True)
    
    async def _capture_captcha_screenshot(self, page, challenge_id: str) -> Optional[str]:
        """Capture screenshot of the CAPTCHA for Slack display."""
        try:
            screenshot_path = os.path.join(self.screenshot_dir, f"captcha_{challenge_id}.png")
            
            # Try to capture just the CAPTCHA element
            captcha_selectors = [
                'iframe[src*="recaptcha"]',
                'iframe[src*="hcaptcha"]',
                'iframe[src*="arkoselabs"]',
                '.captcha-container',
                '[class*="captcha"]',
                '[class*="challenge"]',
                '[role="dialog"]',
            ]
            
            captured = False
            for selector in captcha_selectors:
                try:
                    elem = page.locator(selector).first
                    if await elem.count() > 0 and await elem.is_visible():
                        await elem.screenshot(path=screenshot_path)
                        captured = True
                        print(f"   📸 Captured CAPTCHA element: {selector}")
                        break
                except:
                    continue
            
            # Fallback to full page screenshot
            if not captured:
                await page.screenshot(path=screenshot_path, full_page=False)
                print(f"   📸 Captured full page screenshot")
            
            return screenshot_path
        except Exception as e:
            print(f"   ⚠️ Screenshot capture failed: {e}")
            return None
    
    async def _send_slack_notification_with_screenshot(
        self,
        challenge: CaptchaChallenge,
        page,
        job_title: str = "",
        company: str = ""
    ) -> bool:
        """Send Slack notification with CAPTCHA screenshot for remote solving."""
        
        try:
            from slack_sdk import WebClient
            
            bot_token = os.environ.get("SLACK_BOT_TOKEN")
            if not bot_token:
                print("⚠️ SLACK_BOT_TOKEN not set, cannot notify")
                return False
            
            client = WebClient(token=bot_token)
            
            # Capture screenshot
            screenshot_path = await self._capture_captcha_screenshot(page, challenge.challenge_id)
            
            message = f"""🔐 *CAPTCHA Assistance Needed*

*Job:* {job_title} at {company}
*Type:* {challenge.captcha_type.value}
*URL:* <{challenge.page_url}|Open Application>

📱 *Remote Solving Options:*
1. Open the URL above on your phone/computer
2. Or use the browser window on your desktop

⏱️ *Timeout:* {self.timeout_seconds // 60} minutes

_The CAPTCHA screenshot is attached below. Solve it in the browser window._
"""
            
            # Upload screenshot first if available
            file_id = None
            if screenshot_path and os.path.exists(screenshot_path):
                try:
                    upload_result = client.files_upload_v2(
                        channel=self.slack_channel,
                        file=screenshot_path,
                        title=f"CAPTCHA for {company}",
                        initial_comment=message
                    )
                    file_id = upload_result.get('file', {}).get('id')
                    print(f"   📤 Screenshot uploaded to Slack")
                except Exception as e:
                    print(f"   ⚠️ Screenshot upload failed: {e}")
                    # Fall back to text-only message
                    client.chat_postMessage(
                        channel=self.slack_channel,
                        text=message,
                        blocks=[
                            {"type": "section", "text": {"type": "mrkdwn", "text": message}},
                            {
                                "type": "actions",
                                "elements": [
                                    {
                                        "type": "button",
                                        "text": {"type": "plain_text", "text": "✅ I Solved It"},
                                        "style": "primary",
                                        "action_id": "captcha_solved",
                                        "value": challenge.challenge_id
                                    },
                                    {
                                        "type": "button",
                                        "text": {"type": "plain_text", "text": "❌ Skip Job"},
                                        "style": "danger",
                                        "action_id": "captcha_skip",
                                        "value": challenge.challenge_id
                                    }
                                ]
                            }
                        ]
                    )
            else:
                # No screenshot, send text message
                client.chat_postMessage(
                    channel=self.slack_channel,
                    text=message,
                    blocks=[
                        {"type": "section", "text": {"type": "mrkdwn", "text": message}},
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "✅ I Solved It"},
                                    "style": "primary",
                                    "action_id": "captcha_solved",
                                    "value": challenge.challenge_id
                                },
                                {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "❌ Skip Job"},
                                    "style": "danger",
                                    "action_id": "captcha_skip",
                                    "value": challenge.challenge_id
                                }
                            ]
                        }
                    ]
                )
            
            return True
            
        except Exception as e:
            print(f"⚠️ Slack notification failed: {e}")
            return False
    
    def _send_slack_notification(
        self,
        challenge: CaptchaChallenge,
        job_title: str = "",
        company: str = ""
    ) -> bool:
        """Send basic Slack notification (sync version for backward compatibility)."""
        
        try:
            from slack_sdk import WebClient
            
            bot_token = os.environ.get("SLACK_BOT_TOKEN")
            if not bot_token:
                print("⚠️ SLACK_BOT_TOKEN not set, cannot notify")
                return False
            
            client = WebClient(token=bot_token)
            
            message = f"""🔐 *CAPTCHA Assistance Needed*

*Job:* {job_title} at {company}
*Type:* {challenge.captcha_type.value}
*URL:* <{challenge.page_url}|Open Application>

The browser window is open and waiting for you to solve the CAPTCHA.

⏱️ *Timeout:* {self.timeout_seconds // 60} minutes
"""
            
            client.chat_postMessage(
                channel=self.slack_channel,
                text=message,
                blocks=[
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": message}
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "✅ Solved"},
                                "style": "primary",
                                "action_id": "captcha_solved",
                                "value": challenge.challenge_id
                            },
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "❌ Skip This Job"},
                                "style": "danger",
                                "action_id": "captcha_skip",
                                "value": challenge.challenge_id
                            }
                        ]
                    }
                ]
            )
            
            return True
            
        except Exception as e:
            print(f"⚠️ Slack notification failed: {e}")
            return False
    
    def _send_desktop_notification(self, challenge: CaptchaChallenge, job_title: str = ""):
        """Send desktop notification (Windows toast)."""
        
        if sys.platform == "win32":
            try:
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                toaster.show_toast(
                    "ClawdBot - CAPTCHA Help Needed",
                    f"Please solve CAPTCHA for: {job_title}\nCheck the browser window.",
                    duration=10,
                    threaded=True
                )
            except ImportError:
                # Fallback to PowerShell notification
                import subprocess
                subprocess.run([
                    "powershell", "-Command",
                    f'[System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms"); '
                    f'[System.Windows.Forms.MessageBox]::Show("CAPTCHA help needed for {job_title}. Check browser window.", "ClawdBot")'
                ], capture_output=True)
    
    async def request_human_help(
        self,
        challenge: CaptchaChallenge,
        page,  # Playwright page object
        job_title: str = "",
        company: str = ""
    ) -> bool:
        """
        Request human assistance for CAPTCHA solving.
        
        Returns True if human solved it, False if timeout/skipped.
        """
        
        print(f"\n{'='*60}")
        print(f"🔐 HUMAN ASSISTANCE REQUIRED")
        print(f"   Job: {job_title} at {company}")
        print(f"   CAPTCHA Type: {challenge.captcha_type.value}")
        print(f"   Please solve the CAPTCHA in the browser window...")
        print(f"   Timeout: {self.timeout_seconds} seconds")
        print(f"{'='*60}\n")
        
        # Send notifications with screenshot
        await self._send_slack_notification_with_screenshot(challenge, page, job_title, company)
        self._send_desktop_notification(challenge, job_title)
        
        # Play sound to get attention
        if sys.platform == "win32":
            import winsound
            winsound.Beep(1000, 500)  # 1000Hz for 500ms
        
        # Wait for human to solve, checking page state periodically
        start_time = time.time()
        check_interval = 3  # Check every 3 seconds
        
        while (time.time() - start_time) < self.timeout_seconds:
            await asyncio.sleep(check_interval)
            
            # Check if CAPTCHA was solved (page changed)
            try:
                page_content = await page.content()
                page_url = page.url
                
                # Success indicators
                success_indicators = [
                    "thank you" in page_content.lower(),
                    "application received" in page_content.lower(),
                    "successfully submitted" in page_content.lower(),
                    "/confirmation" in page_url.lower(),
                    "/success" in page_url.lower(),
                    "/thank" in page_url.lower(),
                ]
                
                # CAPTCHA gone indicators
                captcha_gone = not any([
                    "captcha" in page_content.lower(),
                    "recaptcha" in page_content.lower(),
                    "hcaptcha" in page_content.lower(),
                    "verify you" in page_content.lower(),
                    "pick all" in page_content.lower(),
                ])
                
                if any(success_indicators):
                    print("✅ Application submitted successfully!")
                    return True
                
                if captcha_gone:
                    # CAPTCHA might be solved, check if we can proceed
                    print("✅ CAPTCHA appears to be solved")
                    return True
                
            except Exception as e:
                # Page might have navigated
                print(f"   Checking... (error: {e})")
            
            elapsed = int(time.time() - start_time)
            remaining = self.timeout_seconds - elapsed
            if elapsed % 30 == 0:  # Log every 30 seconds
                print(f"   ⏳ Waiting for human... {remaining}s remaining")
        
        print("❌ Human assistance timeout")
        return False


class CaptchaHandler:
    """
    Main CAPTCHA handling orchestrator.
    
    Implements multi-tier resolution:
      Tier 1: Automatic detection and simple bypasses
      Tier 2: Third-party CAPTCHA solving services
      Tier 3: Human-in-the-loop assistance
    """
    
    def __init__(self, data_dir: str = None):
        if not data_dir:
            data_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'captcha')
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.metrics = CaptchaMetrics(str(self.data_dir))
        self.solving_service = CaptchaSolvingService()
        self.human_assistant = HumanAssistant()
        
        # Session cookie cache for reducing CAPTCHA frequency
        self.session_cache_file = self.data_dir / "session_cache.json"
        self.session_cache = self._load_session_cache()
        
        # Rate limiting
        self.max_attempts_per_hour = 20
        self.attempts_this_hour = 0
        self.hour_start = datetime.now()
    
    def _load_session_cache(self) -> Dict:
        if self.session_cache_file.exists():
            with open(self.session_cache_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_session_cache(self):
        with open(self.session_cache_file, 'w') as f:
            json.dump(self.session_cache, f)
    
    def cache_session(self, domain: str, cookies: list):
        """Cache successful session cookies to reduce future CAPTCHAs."""
        self.session_cache[domain] = {
            "cookies": cookies,
            "cached_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat()
        }
        self._save_session_cache()
    
    def get_cached_session(self, domain: str) -> Optional[list]:
        """Get cached session cookies if valid."""
        if domain in self.session_cache:
            entry = self.session_cache[domain]
            expires = datetime.fromisoformat(entry["expires_at"])
            if datetime.now() < expires:
                return entry["cookies"]
            else:
                del self.session_cache[domain]
                self._save_session_cache()
        return None
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        now = datetime.now()
        if (now - self.hour_start).total_seconds() > 3600:
            self.attempts_this_hour = 0
            self.hour_start = now
        
        return self.attempts_this_hour < self.max_attempts_per_hour
    
    async def extract_arkose_params(self, page) -> Dict:
        """Extract Arkose Labs parameters from fc-token or page content."""
        
        params = {"public_key": None, "surl": None}
        
        try:
            page_content = await page.content()
            import re
            
            # Try to find fc-token input which contains both pk and surl
            fc_token_match = re.search(r'name=["\']fc-token["\'][^>]*value=["\']([^"\']+)["\']', page_content, re.IGNORECASE)
            if not fc_token_match:
                fc_token_match = re.search(r'value=["\']([^"\']*\|pk=[^"\']+)["\']', page_content)
            
            if fc_token_match:
                fc_token = fc_token_match.group(1)
                
                # Extract pk (public key)
                pk_match = re.search(r'pk=([^|&"\']+)', fc_token)
                if pk_match:
                    params["public_key"] = pk_match.group(1)
                
                # Extract surl (service URL)
                surl_match = re.search(r'surl=([^|&"\']+)', fc_token)
                if surl_match:
                    params["surl"] = surl_match.group(1)
            
            # Try to find surl in script tags or iframes
            if not params["surl"]:
                surl_patterns = [
                    r'https://([a-zA-Z0-9-]+\.arkoselabs\.com)',
                    r'https://([a-zA-Z0-9-]+)-api\.arkoselabs\.com',
                    r'surl["\s:=]+["\']?(https://[^"\'>\s]+arkoselabs[^"\'>\s]*)',
                ]
                for pattern in surl_patterns:
                    match = re.search(pattern, page_content, re.IGNORECASE)
                    if match:
                        if 'http' in match.group(0):
                            params["surl"] = match.group(0).split('"')[0].split("'")[0]
                        else:
                            params["surl"] = f"https://{match.group(1)}"
                        break
            
            # Common known subdomains for different sites
            if not params["surl"]:
                page_url = page.url.lower()
                if 'lever.co' in page_url:
                    params["surl"] = "https://lever-api.arkoselabs.com"
                elif 'spotify' in page_url:
                    params["surl"] = "https://spotify-api.arkoselabs.com"
                elif 'linkedin' in page_url:
                    params["surl"] = "https://linkedin-api.arkoselabs.com"
                else:
                    params["surl"] = "https://client-api.arkoselabs.com"
            
            if params["public_key"] or params["surl"]:
                print(f"   Arkose params: pk={params['public_key'][:20] if params['public_key'] else 'N/A'}..., surl={params['surl']}")
                
        except Exception as e:
            print(f"   ⚠️ Could not extract Arkose params: {e}")
        
        return params

    async def detect_captcha(self, page) -> Optional[CaptchaChallenge]:
        """Detect CAPTCHA type on the current page."""
        
        try:
            page_content = await page.content()
            page_url = page.url
            
            # Detection patterns - ORDER MATTERS! More specific patterns first
            # Check FunCaptcha FIRST as it can appear alongside other CAPTCHA indicators
            detections = [
                (CaptchaType.FUNCAPTCHA, [
                    'funcaptcha',
                    'arkoselabs',
                    'click on the point',
                    'where the lines cross',
                    'enforcement.arkoselabs',
                    'drag the correct image',
                    'complete the corresponding image',
                    'please drag',
                ]),
                (CaptchaType.HCAPTCHA, [
                    'class="h-captcha"',
                    'hcaptcha.com/1/',
                    'data-hcaptcha-sitekey',
                ]),
                (CaptchaType.TURNSTILE, [
                    'challenges.cloudflare.com/turnstile',
                    'cf-turnstile',
                ]),
                (CaptchaType.RECAPTCHA_V3, [
                    'grecaptcha.execute',
                    'recaptcha/api.js?render=',
                ]),
                (CaptchaType.RECAPTCHA_V2, [
                    'class="g-recaptcha"',
                    'grecaptcha.render',
                    'www.google.com/recaptcha',
                ]),
                (CaptchaType.IMAGE_CAPTCHA, [
                    'pick all squares',
                    'select all images',
                    'verify you are human',
                ]),
            ]
            
            detected_type = CaptchaType.UNKNOWN
            site_key = None
            
            for ctype, patterns in detections:
                if any(p.lower() in page_content.lower() for p in patterns):
                    detected_type = ctype
                    break
            
            if detected_type == CaptchaType.UNKNOWN:
                # Check for generic CAPTCHA indicators
                generic_indicators = ['captcha', 'verify', 'robot', 'human']
                if any(ind in page_content.lower() for ind in generic_indicators):
                    # Check if there's a UUID-format sitekey (indicates FunCaptcha)
                    import re
                    uuid_match = re.search(r'data-sitekey=["\']([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})["\']', page_content, re.IGNORECASE)
                    if uuid_match:
                        detected_type = CaptchaType.FUNCAPTCHA
                        site_key = uuid_match.group(1)
                        print(f"   Detected UUID key format -> treating as FunCaptcha")
                    else:
                        detected_type = CaptchaType.IMAGE_CAPTCHA
                else:
                    return None  # No CAPTCHA detected
            
            # Extract site key if possible
            import re
            
            if detected_type in [CaptchaType.RECAPTCHA_V2, CaptchaType.RECAPTCHA_V3]:
                match = re.search(r'data-sitekey=["\']([^"\']+)["\']', page_content)
                if match:
                    site_key = match.group(1)
            elif detected_type == CaptchaType.HCAPTCHA:
                match = re.search(r'data-sitekey=["\']([^"\']+)["\']', page_content)
                if match:
                    site_key = match.group(1)
                    # Check if this is actually a UUID (FunCaptcha) not hCaptcha
                    # FunCaptcha uses UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
                    if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', site_key, re.IGNORECASE):
                        print(f"   UUID key detected -> reclassifying as FunCaptcha")
                        detected_type = CaptchaType.FUNCAPTCHA
            elif detected_type == CaptchaType.TURNSTILE:
                match = re.search(r'data-sitekey=["\']([^"\']+)["\']', page_content)
                if match:
                    site_key = match.group(1)
            elif detected_type == CaptchaType.FUNCAPTCHA:
                # FunCaptcha public key extraction - multiple patterns
                patterns = [
                    r'data-pkey=["\']([^"\']+)["\']',
                    r'publicKey["\s:]+["\']([^"\']+)["\']',
                    r'public_key["\s:]+["\']([^"\']+)["\']',
                    r'arkoselabs\.com/fc/gc/\?pk=([^&"\']+)',
                    r'data-sitekey=["\']([0-9a-f-]{36})["\']',
                ]
                for pattern in patterns:
                    match = re.search(pattern, page_content, re.IGNORECASE)
                    if match:
                        site_key = match.group(1)
                        break
            
            # Create challenge object
            challenge_id = hashlib.md5(f"{page_url}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
            
            # Take screenshot for debugging
            screenshot_path = str(self.data_dir / f"captcha_{challenge_id}.png")
            try:
                await page.screenshot(path=screenshot_path)
            except:
                screenshot_path = None
            
            return CaptchaChallenge(
                challenge_id=challenge_id,
                captcha_type=detected_type,
                site_key=site_key,
                page_url=page_url,
                detected_at=datetime.now(),
                screenshot_path=screenshot_path
            )
            
        except Exception as e:
            print(f"❌ CAPTCHA detection error: {e}")
            return None
    
    async def resolve(
        self,
        page,  # Playwright page object
        job_title: str = "",
        company: str = "",
        use_service: bool = True,
        use_human: bool = True
    ) -> CaptchaResult:
        """
        Attempt to resolve CAPTCHA using multi-tier approach.
        
        Args:
            page: Playwright page object
            job_title: Job title for context
            company: Company name for context
            use_service: Whether to use paid CAPTCHA services
            use_human: Whether to fall back to human assistance
        
        Returns:
            CaptchaResult with resolution details
        """
        
        start_time = time.time()
        
        # Rate limit check
        if not self._check_rate_limit():
            return CaptchaResult(
                success=False,
                tier_used=ResolutionTier.FAILED,
                error="Rate limit reached (20/hour). Please wait."
            )
        
        self.attempts_this_hour += 1
        
        # Detect CAPTCHA
        challenge = await self.detect_captcha(page)
        
        if not challenge:
            return CaptchaResult(
                success=True,
                tier_used=ResolutionTier.AUTO,
                time_taken=time.time() - start_time
            )
        
        print(f"\n🔐 CAPTCHA Detected: {challenge.captcha_type.value}")
        print(f"   Site Key: {challenge.site_key or 'Not found'}")
        
        # ==== TIER 1: Automatic Resolution ====
        # Try clicking through simple challenges
        tier1_result = await self._try_tier1_auto(page, challenge)
        if tier1_result.success:
            self.metrics.record(challenge, tier1_result)
            return tier1_result
        
        # ==== TIER 2: Solving Service ====
        if use_service and self.solving_service.is_available():
            tier2_result = await self._try_tier2_service(page, challenge)
            if tier2_result.success:
                self.metrics.record(challenge, tier2_result)
                return tier2_result
        
        # ==== TIER 3: Human Assistance ====
        if use_human:
            tier3_result = await self._try_tier3_human(page, challenge, job_title, company)
            self.metrics.record(challenge, tier3_result)
            return tier3_result
        
        # All tiers exhausted
        result = CaptchaResult(
            success=False,
            tier_used=ResolutionTier.FAILED,
            time_taken=time.time() - start_time,
            error="All resolution tiers exhausted"
        )
        self.metrics.record(challenge, result)
        return result
    
    async def _try_tier1_auto(self, page, challenge: CaptchaChallenge) -> CaptchaResult:
        """Tier 1: Automatic simple bypasses."""
        
        start_time = time.time()
        
        try:
            # Try clicking the checkbox (reCAPTCHA v2)
            if challenge.captcha_type == CaptchaType.RECAPTCHA_V2:
                # Try to find and click the checkbox
                checkbox_selectors = [
                    'iframe[title*="reCAPTCHA"]',
                    '.g-recaptcha iframe',
                    '#recaptcha-anchor',
                ]
                
                for selector in checkbox_selectors:
                    try:
                        frame = page.frame_locator(selector)
                        checkbox = frame.locator('.recaptcha-checkbox-border')
                        if await checkbox.count() > 0:
                            await checkbox.click()
                            await asyncio.sleep(3)
                            
                            # Check if solved
                            page_content = await page.content()
                            if 'captcha' not in page_content.lower():
                                return CaptchaResult(
                                    success=True,
                                    tier_used=ResolutionTier.AUTO,
                                    time_taken=time.time() - start_time
                                )
                    except:
                        continue
            
            # For other types, Tier 1 fails
            return CaptchaResult(
                success=False,
                tier_used=ResolutionTier.AUTO,
                time_taken=time.time() - start_time
            )
            
        except Exception as e:
            return CaptchaResult(
                success=False,
                tier_used=ResolutionTier.AUTO,
                time_taken=time.time() - start_time,
                error=str(e)
            )
    
    async def _try_tier2_service(self, page, challenge: CaptchaChallenge) -> CaptchaResult:
        """Tier 2: Third-party CAPTCHA solving service."""
        
        start_time = time.time()
        
        if not challenge.site_key:
            return CaptchaResult(
                success=False,
                tier_used=ResolutionTier.SERVICE,
                time_taken=time.time() - start_time,
                error="No site key found for CAPTCHA service"
            )
        
        solution = None
        cost = 0
        
        try:
            if challenge.captcha_type == CaptchaType.RECAPTCHA_V2:
                solution, cost = await self.solving_service.solve_recaptcha_v2(
                    challenge.site_key,
                    challenge.page_url
                )
            elif challenge.captcha_type == CaptchaType.HCAPTCHA:
                solution, cost = await self.solving_service.solve_hcaptcha(
                    challenge.site_key,
                    challenge.page_url
                )
            elif challenge.captcha_type == CaptchaType.TURNSTILE:
                solution, cost = await self.solving_service.solve_turnstile(
                    challenge.site_key,
                    challenge.page_url
                )
            elif challenge.captcha_type == CaptchaType.FUNCAPTCHA:
                # FunCaptcha (Arkose Labs) - used by Lever, Spotify, etc.
                # Extract Arkose params including surl
                arkose_params = await self.extract_arkose_params(page)
                public_key = arkose_params.get("public_key") or challenge.site_key
                surl = arkose_params.get("surl")
                
                if public_key:
                    solution, cost = await self.solving_service.solve_funcaptcha(
                        public_key,
                        challenge.page_url,
                        service_url=surl
                    )
                
                # If token-based failed, try image-based approach
                if not solution:
                    print("   Trying image-based FunCaptcha solving...")
                    solution, cost = await self.solving_service.solve_funcaptcha_image(
                        page,
                        self.solving_service.get_estimated_cost(CaptchaType.FUNCAPTCHA)
                    )
            elif challenge.captcha_type == CaptchaType.IMAGE_CAPTCHA:
                # Generic image CAPTCHAs need human assistance
                print("⚠️ Image CAPTCHA detected - requires human assistance")
                return CaptchaResult(
                    success=False,
                    tier_used=ResolutionTier.SERVICE,
                    time_taken=time.time() - start_time,
                    error="Image CAPTCHA requires human assistance"
                )
            
            if solution:
                # Inject the solution token
                injected = await self._inject_captcha_solution(page, challenge, solution)
                
                if injected:
                    return CaptchaResult(
                        success=True,
                        tier_used=ResolutionTier.SERVICE,
                        solution=solution,
                        token=solution,
                        time_taken=time.time() - start_time,
                        cost=cost
                    )
            
            return CaptchaResult(
                success=False,
                tier_used=ResolutionTier.SERVICE,
                time_taken=time.time() - start_time,
                cost=cost,
                error="Service failed to solve CAPTCHA"
            )
            
        except Exception as e:
            return CaptchaResult(
                success=False,
                tier_used=ResolutionTier.SERVICE,
                time_taken=time.time() - start_time,
                error=str(e)
            )
    
    async def _inject_captcha_solution(self, page, challenge: CaptchaChallenge, solution: str) -> bool:
        """Inject CAPTCHA solution token into the page."""
        
        try:
            if challenge.captcha_type in [CaptchaType.RECAPTCHA_V2, CaptchaType.RECAPTCHA_V3]:
                # Inject into g-recaptcha-response textarea
                await page.evaluate(f'''
                    document.getElementById("g-recaptcha-response").innerHTML = "{solution}";
                    document.getElementById("g-recaptcha-response").value = "{solution}";
                ''')
                
                # Also try callback if exists
                await page.evaluate(f'''
                    if (typeof grecaptcha !== 'undefined' && grecaptcha.getResponse) {{
                        // Trigger callback if registered
                        var callbacks = document.querySelectorAll('[data-callback]');
                        callbacks.forEach(function(el) {{
                            var callbackName = el.getAttribute('data-callback');
                            if (window[callbackName]) {{
                                window[callbackName]("{solution}");
                            }}
                        }});
                    }}
                ''')
                
            elif challenge.captcha_type == CaptchaType.HCAPTCHA:
                await page.evaluate(f'''
                    document.querySelector('[name="h-captcha-response"]').value = "{solution}";
                    document.querySelector('[name="g-recaptcha-response"]').value = "{solution}";
                ''')
                
            elif challenge.captcha_type == CaptchaType.TURNSTILE:
                await page.evaluate(f'''
                    document.querySelector('[name="cf-turnstile-response"]').value = "{solution}";
                ''')
            
            elif challenge.captcha_type == CaptchaType.FUNCAPTCHA:
                # FunCaptcha token injection - set fc-token input and trigger verification
                await page.evaluate(f'''
                    // Try to find and set fc-token input
                    var fcToken = document.querySelector('input[name="fc-token"]');
                    if (fcToken) {{
                        fcToken.value = "{solution}";
                    }}
                    
                    // Also try setting via ArkoseEnforcement callback
                    if (window.ArkoseEnforcement && window.ArkoseEnforcement.setSessionToken) {{
                        window.ArkoseEnforcement.setSessionToken("{solution}");
                    }}
                    
                    // Try triggering form validation
                    var forms = document.querySelectorAll('form');
                    forms.forEach(function(form) {{
                        var hiddenInput = document.createElement('input');
                        hiddenInput.type = 'hidden';
                        hiddenInput.name = 'fc-token';
                        hiddenInput.value = "{solution}";
                        form.appendChild(hiddenInput);
                    }});
                ''')
                
                # Click any verify/submit buttons that might be present
                verify_selectors = [
                    'button:has-text("Verify")',
                    'button[type="submit"]',
                    '.verify-button',
                ]
                for selector in verify_selectors:
                    try:
                        btn = await page.query_selector(selector)
                        if btn:
                            await btn.click()
                            break
                    except:
                        pass
            
            await asyncio.sleep(2)
            return True
            
        except Exception as e:
            print(f"⚠️ Solution injection failed: {e}")
            return False
    
    async def _try_tier3_human(
        self,
        page,
        challenge: CaptchaChallenge,
        job_title: str,
        company: str
    ) -> CaptchaResult:
        """Tier 3: Human-in-the-loop assistance."""
        
        start_time = time.time()
        
        success = await self.human_assistant.request_human_help(
            challenge,
            page,
            job_title,
            company
        )
        
        return CaptchaResult(
            success=success,
            tier_used=ResolutionTier.HUMAN,
            time_taken=time.time() - start_time
        )
    
    def get_metrics_summary(self) -> str:
        """Get metrics summary for dashboard."""
        return self.metrics.get_summary()


# ============== INTEGRATION HELPER ==============

async def handle_captcha_for_application(
    page,
    job_title: str,
    company: str,
    use_paid_service: bool = True
) -> bool:
    """
    Convenience function to handle CAPTCHA during job application.
    
    Returns True if CAPTCHA was resolved (or none detected), False otherwise.
    """
    
    handler = CaptchaHandler()
    result = await handler.resolve(
        page,
        job_title=job_title,
        company=company,
        use_service=use_paid_service,
        use_human=True
    )
    
    if result.success:
        print(f"✅ CAPTCHA resolved via {result.tier_used.name}")
        if result.cost > 0:
            print(f"   Cost: ${result.cost:.4f}")
    else:
        print(f"❌ CAPTCHA resolution failed: {result.error}")
    
    return result.success


if __name__ == "__main__":
    # Test metrics display
    handler = CaptchaHandler()
    print(handler.get_metrics_summary())
    
    print("\n" + "="*60)
    print("CAPTCHA HANDLER READY")
    print("="*60)
    print(f"2Captcha API Key: {'✅ Set' if handler.solving_service.api_key_2captcha else '❌ Not set'}")
    print(f"Anti-Captcha Key: {'✅ Set' if handler.solving_service.api_key_anticaptcha else '❌ Not set'}")
    print(f"Daily Budget: ${handler.solving_service.daily_budget}")
    print(f"Hourly Limit: {handler.max_attempts_per_hour} attempts")
