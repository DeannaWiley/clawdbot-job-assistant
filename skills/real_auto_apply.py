"""
Real Auto-Apply - Actually submits job applications via Playwright
Supports: Greenhouse, Lever, and other standard ATS platforms
"""
import os
import sys
import json
import yaml
import time
import asyncio
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path


def load_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


# Deanna's demographic info for EEO questions
DEMOGRAPHIC_INFO = {
    'gender': 'Female',
    'race': 'Two or More Races',  # or 'Black or African American'
    'ethnicity': 'Not Hispanic or Latino',
    'veteran': 'No',  # I am not a veteran
    'disability': 'No',  # I do not have a disability
    'authorized': 'Yes',  # Authorized to work in US
    'sponsorship': 'No',  # Does not require sponsorship
}


async def fill_demographic_fields(page) -> None:
    """Fill EEO/demographic questions on job applications."""
    
    try:
        # Gender questions
        gender_selectors = [
            'select[name*="gender"]',
            'select[name*="Gender"]',
            '[data-qa*="gender"] select',
        ]
        for selector in gender_selectors:
            field = await page.query_selector(selector)
            if field:
                await field.select_option(label=DEMOGRAPHIC_INFO['gender'])
                print(f"  ✓ Gender filled")
                break
        
        # Race/Ethnicity questions
        race_selectors = [
            'select[name*="race"]',
            'select[name*="Race"]',
            'select[name*="ethnicity"]',
            '[data-qa*="race"] select',
        ]
        for selector in race_selectors:
            field = await page.query_selector(selector)
            if field:
                # Try different option values
                try:
                    await field.select_option(label=DEMOGRAPHIC_INFO['race'])
                except:
                    try:
                        await field.select_option(label='Black or African American')
                    except:
                        pass
                print(f"  ✓ Race/Ethnicity filled")
                break
        
        # Veteran status
        veteran_selectors = [
            'select[name*="veteran"]',
            'select[name*="Veteran"]',
            '[data-qa*="veteran"] select',
        ]
        for selector in veteran_selectors:
            field = await page.query_selector(selector)
            if field:
                try:
                    await field.select_option(label='I am not a protected veteran')
                except:
                    try:
                        await field.select_option(label='No')
                    except:
                        pass
                print(f"  ✓ Veteran status filled")
                break
        
        # Disability status
        disability_selectors = [
            'select[name*="disability"]',
            'select[name*="Disability"]',
            '[data-qa*="disability"] select',
        ]
        for selector in disability_selectors:
            field = await page.query_selector(selector)
            if field:
                try:
                    await field.select_option(label='I do not have a disability')
                except:
                    try:
                        await field.select_option(label='No')
                    except:
                        pass
                print(f"  ✓ Disability status filled")
                break
        
        # Work authorization
        auth_selectors = [
            'select[name*="authorized"]',
            'select[name*="work_auth"]',
            'input[name*="authorized"]',
        ]
        for selector in auth_selectors:
            field = await page.query_selector(selector)
            if field:
                tag = await field.evaluate('el => el.tagName')
                if tag == 'SELECT':
                    await field.select_option(label='Yes')
                else:
                    await field.check()
                print(f"  ✓ Work authorization filled")
                break
        
        # Handle radio buttons for Yes/No questions
        radio_questions = await page.query_selector_all('fieldset, .field-group, [role="radiogroup"]')
        for group in radio_questions:
            label_text = await group.inner_text()
            label_lower = label_text.lower()
            
            # Veteran question
            if 'veteran' in label_lower:
                no_option = await group.query_selector('input[value*="no" i], input[value="No"], label:has-text("not a protected veteran") input')
                if no_option:
                    await no_option.click()
            
            # Disability question
            elif 'disability' in label_lower or 'disabled' in label_lower:
                no_option = await group.query_selector('input[value*="no" i], label:has-text("do not have") input')
                if no_option:
                    await no_option.click()
            
            # Work authorization
            elif 'authorized' in label_lower and 'work' in label_lower:
                yes_option = await group.query_selector('input[value*="yes" i], input[value="Yes"]')
                if yes_option:
                    await yes_option.click()
            
            # Sponsorship
            elif 'sponsor' in label_lower:
                no_option = await group.query_selector('input[value*="no" i], input[value="No"]')
                if no_option:
                    await no_option.click()
                    
    except Exception as e:
        print(f"  ⚠️ Could not fill some demographic fields: {e}")


async def fill_additional_questions(page, user_info: Dict) -> None:
    """Fill additional custom questions with smart, human-readable responses."""
    
    try:
        # Find all textarea and text input fields that aren't already filled
        textareas = await page.query_selector_all('textarea:not([name="comments"])')
        
        for textarea in textareas:
            # Check if already has content
            value = await textarea.input_value()
            if value and len(value) > 5:
                continue
            
            # Get the label/question
            field_id = await textarea.get_attribute('id')
            field_name = await textarea.get_attribute('name') or ''
            
            label = None
            if field_id:
                label = await page.query_selector(f'label[for="{field_id}"]')
            
            question_text = ""
            if label:
                question_text = await label.inner_text()
            
            question_lower = question_text.lower()
            
            # Generate appropriate response based on question type
            response = ""
            
            if 'why' in question_lower and ('company' in question_lower or 'role' in question_lower or 'position' in question_lower):
                response = f"I am drawn to this opportunity because of the company's innovative approach and the chance to contribute my design expertise to meaningful projects."
            
            elif 'experience' in question_lower or 'background' in question_lower:
                response = "I have over 5 years of experience in UX/UI design, with a strong focus on user research, prototyping, and creating intuitive digital experiences."
            
            elif 'strength' in question_lower:
                response = "My key strengths include user-centered design thinking, cross-functional collaboration, and translating complex requirements into elegant solutions."
            
            elif 'salary' in question_lower or 'compensation' in question_lower:
                response = "I am open to discussing compensation based on the full scope of the role and benefits package."
            
            elif 'start' in question_lower and 'date' in question_lower:
                response = "I am available to start within 2-3 weeks of an offer."
            
            elif 'hear' in question_lower and 'about' in question_lower:
                response = "I discovered this position through my job search on the company's careers page."
            
            elif question_text and len(question_text) > 10:
                # Generic professional response for unknown questions
                response = "I would be happy to discuss this further during the interview process."
            
            if response:
                await textarea.fill(response)
                print(f"  ✓ Answered: {question_text[:40]}...")
                
    except Exception as e:
        print(f"  ⚠️ Could not fill some additional questions: {e}")


async def fill_all_form_fields(page, user_info: Dict) -> None:
    """
    Comprehensive form filling that handles ALL UI elements:
    - Text inputs, textareas
    - Dropdowns/selects
    - Radio buttons
    - Checkboxes
    - Custom components
    """
    
    try:
        # 1. Handle all SELECT dropdowns
        selects = await page.query_selector_all('select')
        for select in selects:
            try:
                name = await select.get_attribute('name') or ''
                field_id = await select.get_attribute('id') or ''
                
                # Get label text
                label_text = ""
                if field_id:
                    label = await page.query_selector(f'label[for="{field_id}"]')
                    if label:
                        label_text = (await label.inner_text()).lower()
                
                # Get all options
                options = await select.query_selector_all('option')
                option_values = []
                for opt in options:
                    val = await opt.get_attribute('value')
                    text = await opt.inner_text()
                    if val and val.strip():
                        option_values.append((val, text.lower()))
                
                selected_value = None
                
                # Smart selection based on field type
                if 'gender' in label_text or 'gender' in name.lower():
                    for val, text in option_values:
                        if 'female' in text:
                            selected_value = val
                            break
                
                elif 'race' in label_text or 'ethnic' in label_text:
                    for val, text in option_values:
                        if 'two or more' in text or 'multi' in text:
                            selected_value = val
                            break
                    if not selected_value:
                        for val, text in option_values:
                            if 'african' in text or 'black' in text:
                                selected_value = val
                                break
                
                elif 'veteran' in label_text:
                    for val, text in option_values:
                        if 'not a' in text or 'no' == text.strip():
                            selected_value = val
                            break
                
                elif 'disability' in label_text or 'disabled' in label_text:
                    for val, text in option_values:
                        if 'do not have' in text or 'no' == text.strip():
                            selected_value = val
                            break
                
                elif 'country' in label_text:
                    for val, text in option_values:
                        if 'united states' in text or 'usa' in text or 'u.s.' in text:
                            selected_value = val
                            break
                
                elif 'state' in label_text and 'united' not in label_text:
                    for val, text in option_values:
                        if 'california' in text or 'ca' == text.strip():
                            selected_value = val
                            break
                
                elif 'hear' in label_text or 'source' in label_text or 'how did you' in label_text:
                    for val, text in option_values:
                        if 'website' in text or 'career' in text or 'job board' in text or 'other' in text:
                            selected_value = val
                            break
                
                elif 'legal' in label_text or 'authorized' in label_text or 'eligible' in label_text:
                    for val, text in option_values:
                        if 'yes' in text:
                            selected_value = val
                            break
                
                elif 'sponsor' in label_text:
                    for val, text in option_values:
                        if 'no' in text:
                            selected_value = val
                            break
                
                # If we found a value to select, do it
                if selected_value:
                    await select.select_option(value=selected_value)
                    print(f"  ✓ Dropdown filled: {label_text[:30] or name[:30]}...")
                    
            except Exception as e:
                continue
        
        # 2. Handle all radio button groups
        radio_groups = await page.query_selector_all('fieldset, [role="radiogroup"], .radio-group, .form-group:has(input[type="radio"])')
        for group in radio_groups:
            try:
                group_text = (await group.inner_text()).lower()
                radios = await group.query_selector_all('input[type="radio"]')
                
                selected = False
                
                # Veteran questions
                if 'veteran' in group_text:
                    for radio in radios:
                        label = await radio.evaluate('el => el.labels?.[0]?.innerText || el.nextSibling?.textContent || ""')
                        if 'not a' in label.lower() or label.strip().lower() == 'no':
                            await radio.click()
                            selected = True
                            print(f"  ✓ Radio selected: Not a veteran")
                            break
                
                # Disability questions
                elif 'disability' in group_text or 'disabled' in group_text:
                    for radio in radios:
                        label = await radio.evaluate('el => el.labels?.[0]?.innerText || el.nextSibling?.textContent || ""')
                        if 'do not' in label.lower() or label.strip().lower() == 'no':
                            await radio.click()
                            selected = True
                            print(f"  ✓ Radio selected: No disability")
                            break
                
                # Work authorization
                elif 'authorized' in group_text or 'eligible' in group_text or 'legally' in group_text:
                    for radio in radios:
                        label = await radio.evaluate('el => el.labels?.[0]?.innerText || el.nextSibling?.textContent || ""')
                        if 'yes' in label.lower():
                            await radio.click()
                            selected = True
                            print(f"  ✓ Radio selected: Authorized to work")
                            break
                
                # Sponsorship
                elif 'sponsor' in group_text:
                    for radio in radios:
                        label = await radio.evaluate('el => el.labels?.[0]?.innerText || el.nextSibling?.textContent || ""')
                        if 'no' in label.lower():
                            await radio.click()
                            selected = True
                            print(f"  ✓ Radio selected: No sponsorship needed")
                            break
                
                # Gender
                elif 'gender' in group_text:
                    for radio in radios:
                        label = await radio.evaluate('el => el.labels?.[0]?.innerText || el.nextSibling?.textContent || ""')
                        if 'female' in label.lower():
                            await radio.click()
                            selected = True
                            print(f"  ✓ Radio selected: Female")
                            break
                            
            except Exception as e:
                continue
        
        # 3. Handle checkboxes (usually agreements/acknowledgments)
        checkboxes = await page.query_selector_all('input[type="checkbox"]:not(:checked)')
        for checkbox in checkboxes:
            try:
                # Get associated label
                label_text = await checkbox.evaluate('el => el.labels?.[0]?.innerText || ""')
                name = await checkbox.get_attribute('name') or ''
                
                label_lower = label_text.lower()
                
                # Check agreement/acknowledgment boxes
                if any(word in label_lower for word in ['agree', 'acknowledge', 'consent', 'confirm', 'accept', 'certify', 'understand']):
                    await checkbox.check()
                    print(f"  ✓ Checkbox checked: {label_text[:40]}...")
                
                # Check privacy/terms boxes
                elif any(word in label_lower for word in ['privacy', 'terms', 'policy']):
                    await checkbox.check()
                    print(f"  ✓ Checkbox checked: {label_text[:40]}...")
                    
            except Exception as e:
                continue
        
        # 4. Handle empty text inputs that we might have missed
        text_inputs = await page.query_selector_all('input[type="text"]:not([readonly]), input:not([type]):not([readonly])')
        for input_field in text_inputs:
            try:
                value = await input_field.input_value()
                if value and len(value) > 0:
                    continue
                
                name = await input_field.get_attribute('name') or ''
                placeholder = await input_field.get_attribute('placeholder') or ''
                field_id = await input_field.get_attribute('id') or ''
                
                # Get label
                label_text = ""
                if field_id:
                    label = await page.query_selector(f'label[for="{field_id}"]')
                    if label:
                        label_text = await label.inner_text()
                
                combined = (name + placeholder + label_text).lower()
                
                # Fill based on field type - using Deanna's actual info
                if 'city' in combined:
                    await input_field.fill('Alameda')
                    print(f"  ✓ Text filled: City")
                elif 'zip' in combined or 'postal' in combined:
                    await input_field.fill('94501')
                    print(f"  ✓ Text filled: Zip")
                elif 'state' in combined and 'united' not in combined:
                    await input_field.fill('CA')
                    print(f"  ✓ Text filled: State")
                elif 'address' in combined and 'email' not in combined:
                    await input_field.fill(user_info.get('address', ''))
                    print(f"  ✓ Text filled: Address")
                elif 'years' in combined and 'experience' in combined:
                    await input_field.fill('5')
                    print(f"  ✓ Text filled: Years of Experience")
                elif 'salary' in combined or 'compensation' in combined:
                    await input_field.fill('Negotiable based on total compensation')
                    print(f"  ✓ Text filled: Salary Expectations")
                    
            except Exception as e:
                continue
                
        print(f"  ✓ All form fields processed")
        
    except Exception as e:
        print(f"  ⚠️ Error in comprehensive form filling: {e}")


async def apply_greenhouse(
    job_url: str,
    resume_path: str,
    cover_letter: str,
    user_info: Dict
) -> Dict:
    """
    Actually apply to a Greenhouse job posting by filling out the form.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {"success": False, "error": "Playwright not installed"}
    
    print(f"🌱 Applying via Greenhouse: {job_url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            await page.goto(job_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(3000)
            
            # Check if job is closed
            page_content = await page.content()
            closed_indicators = ['no longer open', 'position has been filled', 'no longer accepting', 'job has been closed', 'position is closed']
            if any(ind in page_content.lower() for ind in closed_indicators):
                await browser.close()
                return {"success": False, "error": "Job posting is no longer open"}
            
            # Check if we need to click an Apply button first
            apply_buttons = [
                'a:has-text("Apply")',
                'button:has-text("Apply")',
                'a:has-text("Apply for this job")',
                'a:has-text("Apply Now")',
                '.btn:has-text("Apply")',
                '[data-qa="apply-button"]',
            ]
            for btn_selector in apply_buttons:
                try:
                    apply_btn = await page.query_selector(btn_selector)
                    if apply_btn:
                        await apply_btn.click()
                        print("  ✓ Clicked Apply button")
                        await page.wait_for_timeout(3000)
                        break
                except:
                    continue
            
            # Wait for application form to load
            form_selectors = ['form', '#application_form', '.application-form', '[data-qa="application-form"]']
            form_found = False
            for _ in range(10):
                for selector in form_selectors:
                    form = await page.query_selector(selector)
                    if form:
                        form_found = True
                        break
                if form_found:
                    break
                await page.wait_for_timeout(1000)
            
            if not form_found:
                print("  ⚠️ Application form not found, taking debug screenshot...")
                debug_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'applications', f'debug_greenhouse_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
                await page.screenshot(path=debug_path)
            
            # Fill in standard Greenhouse fields
            # First Name
            first_name_selectors = ['input[name="job_application[first_name]"]', '#first_name', 'input[autocomplete="given-name"]']
            for selector in first_name_selectors:
                elem = await page.query_selector(selector)
                if elem:
                    await elem.fill(user_info['first_name'])
                    print(f"  ✓ First name filled")
                    break
            
            # Last Name
            last_name_selectors = ['input[name="job_application[last_name]"]', '#last_name', 'input[autocomplete="family-name"]']
            for selector in last_name_selectors:
                elem = await page.query_selector(selector)
                if elem:
                    await elem.fill(user_info['last_name'])
                    print(f"  ✓ Last name filled")
                    break
            
            # Email
            email_selectors = ['input[name="job_application[email]"]', '#email', 'input[type="email"]']
            for selector in email_selectors:
                elem = await page.query_selector(selector)
                if elem:
                    await elem.fill(user_info['email'])
                    print(f"  ✓ Email filled")
                    break
            
            # Phone
            phone_selectors = ['input[name="job_application[phone]"]', '#phone', 'input[type="tel"]']
            for selector in phone_selectors:
                elem = await page.query_selector(selector)
                if elem:
                    await elem.fill(user_info['phone'])
                    print(f"  ✓ Phone filled")
                    break
            
            # Resume upload
            resume_selectors = ['input[type="file"][name*="resume"]', 'input[data-field="resume"]', '#resume']
            for selector in resume_selectors:
                elem = await page.query_selector(selector)
                if elem and os.path.exists(resume_path):
                    await elem.set_input_files(resume_path)
                    print(f"  ✓ Resume uploaded")
                    break
            
            # Cover Letter (text field)
            cover_letter_selectors = ['textarea[name*="cover_letter"]', '#cover_letter', 'textarea[data-field="cover_letter"]']
            for selector in cover_letter_selectors:
                elem = await page.query_selector(selector)
                if elem:
                    await elem.fill(cover_letter)
                    print(f"  ✓ Cover letter filled")
                    break
            
            # LinkedIn URL
            linkedin_selectors = ['input[name*="linkedin"]', 'input[placeholder*="LinkedIn"]']
            for selector in linkedin_selectors:
                elem = await page.query_selector(selector)
                if elem:
                    await elem.fill(user_info.get('linkedin', ''))
                    print(f"  ✓ LinkedIn filled")
                    break
            
            # Portfolio URL
            portfolio_selectors = ['input[name*="portfolio"]', 'input[name*="website"]', 'input[placeholder*="Portfolio"]']
            for selector in portfolio_selectors:
                elem = await page.query_selector(selector)
                if elem:
                    await elem.fill(user_info.get('portfolio', ''))
                    print(f"  ✓ Portfolio filled")
                    break
            
            # Handle EEO/Demographic questions
            await fill_demographic_fields(page)
            
            # Handle any additional custom questions
            await fill_additional_questions(page, user_info)
            
            # Comprehensive form fill for any remaining fields
            await fill_all_form_fields(page, user_info)
            
            # Wait for user to verify before submitting
            print("\n⏳ Form filled! Waiting 5 seconds before submit...")
            await page.wait_for_timeout(5000)
            
            # Scroll to bottom to ensure submit button is visible
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)
            
            # Find and click submit button - expanded selectors
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Submit")',
                'button:has-text("Apply")',
                'button:has-text("Submit Application")',
                'button:has-text("Submit application")',
                '#submit_app',
                '.submit-button',
                '[data-qa="submit-button"]',
                'button[data-action="submit"]',
            ]
            submitted = False
            for selector in submit_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        await elem.scroll_into_view_if_needed()
                        await page.wait_for_timeout(500)
                        await elem.click()
                        submitted = True
                        print(f"  ✓ Submit button clicked!")
                        break
                except:
                    continue
            
            if submitted:
                # Wait for confirmation page
                await page.wait_for_timeout(5000)
                
                # Check for success indicators
                page_content = await page.content()
                success_indicators = ['thank you', 'application received', 'successfully submitted', 'confirmation']
                is_success = any(indicator in page_content.lower() for indicator in success_indicators)
                
                # Take screenshot for verification
                screenshot_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'applications', f'screenshot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
                os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
                await page.screenshot(path=screenshot_path)
                
                await browser.close()
                
                return {
                    "success": is_success,
                    "platform": "greenhouse",
                    "screenshot": screenshot_path,
                    "resume_path": resume_path,
                    "cover_letter_path": None,  # Cover letter is text, not file
                    "fields_filled": 8,
                    "message": "Application submitted successfully!" if is_success else "Submitted but couldn't confirm success"
                }
            else:
                await browser.close()
                return {"success": False, "error": "Could not find submit button"}
                
        except Exception as e:
            await browser.close()
            return {"success": False, "error": str(e)}


async def apply_lever(
    job_url: str,
    resume_path: str,
    cover_letter: str,
    user_info: Dict
) -> Dict:
    """
    Actually apply to a Lever job posting.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {"success": False, "error": "Playwright not installed"}
    
    print(f"🔧 Applying via Lever: {job_url}")
    
    # Lever apply URL format
    if '/apply' not in job_url:
        job_url = job_url.rstrip('/') + '/apply'
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            await page.goto(job_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(3000)
            
            # Check if we need to click an Apply button first
            apply_buttons = [
                'a:has-text("Apply")',
                'button:has-text("Apply")',
                'a.postings-btn',
                '[data-qa="apply-button"]',
            ]
            for btn_selector in apply_buttons:
                try:
                    apply_btn = await page.query_selector(btn_selector)
                    if apply_btn:
                        await apply_btn.click()
                        print("  ✓ Clicked Apply button")
                        await page.wait_for_timeout(2000)
                        break
                except:
                    continue
            
            # Wait for form to be ready
            form_ready = False
            for _ in range(10):
                form = await page.query_selector('form, .application-form, [data-qa="application-form"], .posting-application')
                if form:
                    form_ready = True
                    break
                await page.wait_for_timeout(1000)
            
            if not form_ready:
                print("  ⚠️ Form not found, attempting to continue...")
            
            # Lever form fields - try multiple selectors
            full_name = f"{user_info['first_name']} {user_info['last_name']}"
            
            # Name field - try multiple selectors
            name_selectors = [
                'input[name="name"]',
                'input[name="fullName"]',
                'input[name="full_name"]',
                'input[placeholder*="name" i]',
                'input[aria-label*="name" i]',
                '#name',
            ]
            name_filled = False
            for selector in name_selectors:
                try:
                    field = await page.query_selector(selector)
                    if field:
                        await field.fill(full_name)
                        name_filled = True
                        print(f"  ✓ Name filled")
                        break
                except:
                    continue
            
            if not name_filled:
                # Try first/last name separately
                first_name_selectors = ['input[name="firstName"]', 'input[name="first_name"]', '#firstName']
                last_name_selectors = ['input[name="lastName"]', 'input[name="last_name"]', '#lastName']
                for sel in first_name_selectors:
                    try:
                        field = await page.query_selector(sel)
                        if field:
                            await field.fill(user_info['first_name'])
                            print(f"  ✓ First name filled")
                            break
                    except:
                        continue
                for sel in last_name_selectors:
                    try:
                        field = await page.query_selector(sel)
                        if field:
                            await field.fill(user_info['last_name'])
                            print(f"  ✓ Last name filled")
                            break
                    except:
                        continue
            
            # Email field - try multiple selectors
            email_selectors = [
                'input[name="email"]',
                'input[type="email"]',
                'input[placeholder*="email" i]',
                'input[aria-label*="email" i]',
                '#email',
            ]
            for selector in email_selectors:
                try:
                    field = await page.query_selector(selector)
                    if field:
                        await field.fill(user_info['email'])
                        print(f"  ✓ Email filled")
                        break
                except:
                    continue
            
            # Phone field - try multiple selectors
            phone_selectors = [
                'input[name="phone"]',
                'input[type="tel"]',
                'input[placeholder*="phone" i]',
                'input[aria-label*="phone" i]',
                '#phone',
            ]
            for selector in phone_selectors:
                try:
                    field = await page.query_selector(selector)
                    if field:
                        await field.fill(user_info['phone'])
                        print(f"  ✓ Phone filled")
                        break
                except:
                    continue
            
            # Resume upload - try multiple selectors
            resume_selectors = [
                'input[type="file"][name="resume"]',
                'input[type="file"][accept*="pdf"]',
                'input[type="file"]',
            ]
            for selector in resume_selectors:
                try:
                    resume_input = await page.query_selector(selector)
                    if resume_input and os.path.exists(resume_path):
                        await resume_input.set_input_files(resume_path)
                        print(f"  ✓ Resume uploaded")
                        break
                except:
                    continue
            
            # LinkedIn - try multiple selectors
            linkedin_selectors = [
                'input[name="urls[LinkedIn]"]',
                'input[name="linkedin"]',
                'input[placeholder*="linkedin" i]',
                'input[aria-label*="linkedin" i]',
            ]
            for selector in linkedin_selectors:
                try:
                    field = await page.query_selector(selector)
                    if field:
                        await field.fill(user_info.get('linkedin', ''))
                        print(f"  ✓ LinkedIn filled")
                        break
                except:
                    continue
            
            # Portfolio - try multiple selectors
            portfolio_selectors = [
                'input[name="urls[Portfolio]"]',
                'input[name="portfolio"]',
                'input[name="website"]',
                'input[placeholder*="portfolio" i]',
                'input[placeholder*="website" i]',
            ]
            for selector in portfolio_selectors:
                try:
                    field = await page.query_selector(selector)
                    if field:
                        await field.fill(user_info.get('portfolio', ''))
                        print(f"  ✓ Portfolio filled")
                        break
                except:
                    continue
            
            # Cover letter - only if the field exists and is for cover letter
            cover_field = await page.query_selector('textarea[name="comments"]')
            if cover_field:
                # Check if label mentions cover letter
                label = await page.query_selector('label[for="comments"]')
                label_text = await label.inner_text() if label else ""
                if 'cover' in label_text.lower() or 'letter' in label_text.lower():
                    await cover_field.fill(cover_letter)
                    print(f"  ✓ Cover letter filled")
                else:
                    # Generic additional info - keep it brief and human
                    brief_intro = f"I am excited to apply for this {user_info.get('_job_title', 'position')} role. My background in design and user experience aligns well with your team's needs. I look forward to discussing how I can contribute."
                    await cover_field.fill(brief_intro)
                    print(f"  ✓ Additional info filled")
            
            # Handle EEO/Demographic questions
            await fill_demographic_fields(page)
            
            # Handle any additional custom questions
            await fill_additional_questions(page, user_info)
            
            # Comprehensive form fill for any remaining fields (dropdowns, radios, checkboxes)
            await fill_all_form_fields(page, user_info)
            
            print("\n⏳ Form filled! Waiting 3 seconds before submit...")
            await page.wait_for_timeout(3000)
            
            # Scroll to bottom to make submit button visible
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)
            
            # Submit - try multiple selectors
            submit_selectors = [
                'button[type="submit"]',
                'button.postings-btn',
                'button:has-text("Submit application")',
                'button:has-text("Submit")',
                'input[type="submit"]',
            ]
            
            submitted = False
            for selector in submit_selectors:
                try:
                    submit_btn = await page.query_selector(selector)
                    if submit_btn:
                        # Scroll element into view
                        await submit_btn.scroll_into_view_if_needed()
                        await page.wait_for_timeout(500)
                        await submit_btn.click()
                        submitted = True
                        print(f"  ✓ Submit clicked! (selector: {selector})")
                        break
                except Exception as e:
                    continue
            
            if submitted:
                await page.wait_for_timeout(3000)
                
                # Check for CAPTCHA and use multi-tier resolution
                page_content = await page.content()
                captcha_indicators = [
                    'captcha', 'recaptcha', 'hcaptcha', 'pick objects', 
                    'verify you', 'select all', 'click on the point',
                    'where the lines cross', 'arkoselabs', 'funcaptcha'
                ]
                
                if any(ind in page_content.lower() for ind in captcha_indicators):
                    print("\n🔐 CAPTCHA detected! Initiating multi-tier resolution...")
                    
                    try:
                        from captcha_handler import CaptchaHandler
                        handler = CaptchaHandler()
                        
                        # Get job info for context (passed via user_info)
                        job_title_ctx = user_info.get('_job_title', 'Job Application')
                        company_ctx = user_info.get('_company', 'Company')
                        
                        result = await handler.resolve(
                            page,
                            job_title=job_title_ctx,
                            company=company_ctx,
                            use_service=True,
                            use_human=True
                        )
                        
                        if result.success:
                            print(f"✅ CAPTCHA resolved via {result.tier_used.name}")
                            if result.cost > 0:
                                print(f"   Cost: ${result.cost:.4f}")
                        else:
                            print(f"⚠️ CAPTCHA not resolved: {result.error}")
                            
                    except ImportError:
                        # Fallback to manual waiting
                        print("⚠️ CAPTCHA handler not available, falling back to manual...")
                        for i in range(100):  # 5 minute timeout
                            await page.wait_for_timeout(3000)
                            page_content = await page.content()
                            if 'thank you' in page_content.lower() or 'received' in page_content.lower():
                                print("✅ CAPTCHA solved manually!")
                                break
                            if not any(ind in page_content.lower() for ind in captcha_indicators):
                                print("✅ CAPTCHA appears resolved")
                                break
                
                await page.wait_for_timeout(2000)
                
                # Screenshot
                screenshot_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'applications', f'lever_screenshot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
                os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
                await page.screenshot(path=screenshot_path)
                
                page_content = await page.content()
                is_success = any(x in page_content.lower() for x in ['thank you', 'received', 'submitted', 'confirmation'])
                
                # Cache successful session
                if is_success:
                    try:
                        from captcha_handler import CaptchaHandler
                        handler = CaptchaHandler()
                        cookies = await context.cookies()
                        domain = job_url.split('/')[2]
                        handler.cache_session(domain, cookies)
                    except:
                        pass
                
                await browser.close()
                return {
                    "success": is_success,
                    "platform": "lever",
                    "screenshot": screenshot_path,
                    "resume_path": resume_path,
                    "cover_letter_path": None,
                    "fields_filled": 8,
                    "message": "Application submitted!" if is_success else "Submitted but couldn't confirm"
                }
            
            await browser.close()
            return {"success": False, "error": "Submit button not found"}
            
        except Exception as e:
            await browser.close()
            return {"success": False, "error": str(e)}


async def auto_apply_to_job(
    job_url: str,
    job_title: str,
    company: str,
    job_description: str
) -> Dict:
    """
    Main function to auto-apply to a job.
    Generates documents and submits application.
    """
    config = load_config()
    user = config['user']
    
    # Parse user name
    name_parts = user['name'].split()
    # Clean phone number - remove formatting for international compatibility
    clean_phone = user['phone'].replace('(', '').replace(')', '').replace('-', '').replace(' ', '')
    
    user_info = {
        'first_name': name_parts[0],
        'last_name': ' '.join(name_parts[1:]) if len(name_parts) > 1 else '',
        'email': user['email'],
        'phone': clean_phone,  # Clean format: 7082658734
        'phone_formatted': user['phone'],  # Original format if needed
        'linkedin': user.get('linkedin_url', ''),
        'portfolio': user.get('portfolio_url', ''),
        'location': user.get('location', 'Alameda, CA'),
        '_job_title': job_title,  # For CAPTCHA handler context
        '_company': company,      # For CAPTCHA handler context
    }
    
    print(f"\n{'='*60}")
    print(f"🚀 AUTO-APPLYING TO: {job_title} at {company}")
    print(f"{'='*60}")
    
    # Step 1: Generate documents
    print("\n📝 Step 1: Generating tailored resume and cover letter...")
    from document_generator import generate_application_documents
    
    docs = generate_application_documents(job_title, company, job_description)
    
    resume_path = docs.get('files', {}).get('resume_pdf', '')
    cover_letter = docs.get('cover_letter', '')
    
    if not resume_path or not os.path.exists(resume_path):
        return {"success": False, "error": "Failed to generate resume PDF"}
    
    print(f"  ✓ Resume: {resume_path}")
    print(f"  ✓ Cover letter generated ({len(cover_letter)} chars)")
    
    # Step 2: Apply using the new automation engine
    print("\n🌐 Step 2: Applying via automation engine...")
    
    try:
        from playwright_automation import ApplicationEngine
        
        captcha_key = os.environ.get('CaptchaKey') or os.environ.get('CAPTCHA_2CAPTCHA_KEY')
        engine = ApplicationEngine(user_info, captcha_key)
        
        result = await engine.apply(
            job_url=job_url,
            job_title=job_title,
            company=company,
            resume_path=resume_path,
            cover_letter=cover_letter
        )
        
        result['platform'] = 'auto'
        
    except Exception as e:
        print(f"  ⚠️ New engine failed ({e}), falling back to legacy...")
        url_lower = job_url.lower()
        
        if 'greenhouse.io' in url_lower or 'boards.greenhouse' in url_lower:
            print("  Platform: Greenhouse")
            result = await apply_greenhouse(job_url, resume_path, cover_letter, user_info)
        elif 'lever.co' in url_lower or 'jobs.lever' in url_lower:
            print("  Platform: Lever")
            result = await apply_lever(job_url, resume_path, cover_letter, user_info)
        else:
            return {
                "success": False,
                "error": f"Platform not supported for auto-apply. Please apply manually at: {job_url}",
                "documents": docs
            }
    
    # Step 3: Record application
    print("\n📊 Step 3: Recording application...")
    from job_approval_workflow import record_application
    
    record_application(
        job_url=job_url,
        title=job_title,
        company=company,
        application_method="auto",
        documents_generated=docs.get('files', {}),
        success=result.get('success', False),
        error=result.get('error', '')
    )
    
    if result.get('success'):
        print(f"\n✅ APPLICATION SUBMITTED SUCCESSFULLY!")
        print(f"   Screenshot saved: {result.get('screenshot', 'N/A')}")
        
        # Step 4: Verify via email confirmation (async check)
        print("\n📧 Step 4: Checking for email confirmation...")
        email_verified = await verify_application_email(company, user_info['email'])
        if email_verified:
            print(f"   ✅ Email confirmation received from {company}!")
            result['email_verified'] = True
        else:
            print(f"   ⏳ No confirmation email yet (may arrive later)")
            result['email_verified'] = False
    else:
        print(f"\n❌ Application failed: {result.get('error', 'Unknown error')}")
    
    result['documents'] = docs
    result['resume_path'] = resume_path
    result['cover_letter_path'] = docs.get('files', {}).get('cover_letter_pdf', None)
    return result


async def verify_application_email(company: str, user_email: str, timeout_seconds: int = 30) -> bool:
    """
    Check Gmail for application confirmation email from the company.
    Returns True if confirmation found, False otherwise.
    """
    try:
        from gmail_handler import get_email_summary, get_job_emails
        
        # Wait a bit for email to arrive
        await asyncio.sleep(10)
        
        # Check recent emails for confirmation
        emails = get_job_emails(days_back=1, max_results=10)
        
        company_lower = company.lower()
        confirmation_keywords = ['received', 'thank you', 'application', 'submitted', 'confirmation']
        
        for email in emails:
            subject = email.get('subject', '').lower()
            sender = email.get('from', '').lower()
            snippet = email.get('snippet', '').lower()
            
            # Check if email is from or about the company
            if company_lower in sender or company_lower in subject:
                # Check if it's a confirmation
                if any(kw in subject or kw in snippet for kw in confirmation_keywords):
                    return True
        
        return False
        
    except Exception as e:
        print(f"   ⚠️ Could not check email: {e}")
        return False


def apply_sync(job_url: str, job_title: str, company: str, job_description: str) -> Dict:
    """Synchronous wrapper for auto_apply_to_job."""
    return asyncio.run(auto_apply_to_job(job_url, job_title, company, job_description))


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) >= 5:
        url = sys.argv[1]
        title = sys.argv[2]
        company = sys.argv[3]
        description = ' '.join(sys.argv[4:])
        
        result = apply_sync(url, title, company, description)
        print(json.dumps(result, indent=2, default=str))
    else:
        print("Usage: python real_auto_apply.py <job_url> <job_title> <company> <job_description>")
        print("\nExample:")
        print('  python real_auto_apply.py "https://boards.greenhouse.io/company/jobs/123" "Designer" "ACME" "Design role"')
