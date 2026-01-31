"""
Comprehensive Form Field Configuration for Job Applications
============================================================
Handles ALL common job application field types automatically.

Based on research of: Greenhouse, Lever, Workday, iCIMS, Taleo,
LinkedIn Easy Apply, and company career pages.
"""

import re
from typing import Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class UserProfile:
    """Complete user profile for form filling."""
    # Basic Info
    first_name: str = "Deanna"
    last_name: str = "Wiley"
    full_name: str = "Deanna Wiley"
    email: str = "DeannaWileyCareers@gmail.com"
    phone: str = "7082658734"  # Clean format
    phone_formatted: str = "(708) 265-8734"
    
    # Location
    address: str = ""
    city: str = "Alameda"
    state: str = "California"
    state_abbrev: str = "CA"
    zip_code: str = "94501"
    country: str = "United States"
    country_code: str = "US"
    
    # Online Presence
    linkedin: str = "https://www.linkedin.com/in/deannafwiley/"
    portfolio: str = "https://dwileydesign.myportfolio.com/"
    behance: str = "https://www.behance.net/deannawiley"
    website: str = "https://dwileydesign.myportfolio.com/"
    github: str = ""
    twitter: str = ""
    
    # Work Authorization
    authorized_to_work: str = "Yes"
    require_sponsorship: str = "No"
    us_citizen: str = "Yes"
    
    # Demographics (EEO - Optional, use "Prefer not to say" when available)
    gender: str = "Female"
    gender_identity: str = "Female"
    pronouns: str = "She/Her"
    race: str = "Two or More Races"
    ethnicity: str = "Not Hispanic or Latino"
    veteran_status: str = "I am not a protected veteran"
    disability_status: str = "No, I do not have a disability"
    
    # Education
    highest_degree: str = "Bachelor's Degree"
    degree_type: str = "Bachelor of Science"
    major: str = "Multimedia Design & Business Administration"
    school: str = "DeVry University"
    graduation_year: str = "2023"
    gpa: str = ""  # Leave blank if not required
    
    # Experience
    # 2 years Graphic Designer + 1 year freelance + 2 years budtender (cannabis only)
    years_experience: str = "3"  # Design experience (exclude cannabis unless relevant)
    years_in_field: str = "3"
    current_title: str = "Graphic Designer"
    current_company: str = ""
    
    # Cannabis industry experience (only include for cannabis jobs)
    cannabis_experience: str = "2 years as Budtender at Cannabist dispensary, Chicago"
    include_cannabis_exp: bool = False  # Set to True for cannabis industry jobs
    
    # Salary & Compensation
    salary_expectation: str = "80000"  # Target
    salary_min: str = "60000"
    salary_max: str = "100000"
    salary_currency: str = "USD"
    hourly_rate: str = "45"
    
    # Availability
    available_start: str = "Immediately"
    available_date: str = ""  # Leave blank for ASAP
    notice_period: str = "2 weeks"
    willing_to_relocate: str = "No"
    
    # Skills & Languages
    english_level: str = "Fluent"
    languages: str = "English (Native)"
    
    # Location-based Questions
    based_in_latin_america: str = "No"
    based_in_us: str = "Yes"
    based_in_europe: str = "No"
    timezone: str = "Pacific Time (PT)"
    
    # Age verification
    over_18: str = "Yes"
    over_21: str = "Yes"
    
    # References
    has_references: str = "Yes"
    
    # Additional
    hear_about_us: str = "Job Board"
    referred_by: str = ""


# Field pattern matching - maps field identifiers to profile values
FIELD_PATTERNS = {
    # ===== BASIC CONTACT INFO =====
    'first_name': {
        'patterns': ['first.?name', 'given.?name', 'fname', 'first$'],
        'value_key': 'first_name',
        'type': 'text'
    },
    'last_name': {
        'patterns': ['last.?name', 'sur.?name', 'family.?name', 'lname', 'last$'],
        'value_key': 'last_name',
        'type': 'text'
    },
    'full_name': {
        'patterns': ['full.?name', '^name$', 'your.?name', 'applicant.?name'],
        'value_key': 'full_name',
        'type': 'text'
    },
    'email': {
        'patterns': ['email', 'e-mail', 'mail'],
        'value_key': 'email',
        'type': 'email'
    },
    'phone': {
        'patterns': ['phone', 'tel', 'mobile', 'cell', 'contact.?number'],
        'value_key': 'phone',
        'type': 'tel'
    },
    
    # ===== LOCATION =====
    'address': {
        'patterns': ['address', 'street'],
        'value_key': 'address',
        'type': 'text'
    },
    'city': {
        'patterns': ['city', 'town'],
        'value_key': 'city',
        'type': 'text'
    },
    'state': {
        'patterns': ['state', 'province', 'region'],
        'value_key': 'state',
        'type': 'select',
        'alternatives': ['state_abbrev']
    },
    'zip': {
        'patterns': ['zip', 'postal', 'postcode'],
        'value_key': 'zip_code',
        'type': 'text'
    },
    'country': {
        'patterns': ['country', 'nation'],
        'value_key': 'country',
        'type': 'select',
        'alternatives': ['country_code']
    },
    
    # ===== ONLINE PRESENCE =====
    'linkedin': {
        'patterns': ['linkedin', 'linked.?in'],
        'value_key': 'linkedin',
        'type': 'url'
    },
    'portfolio': {
        'patterns': ['portfolio', 'work.?samples', 'creative.?work'],
        'value_key': 'portfolio',
        'type': 'url'
    },
    'website': {
        'patterns': ['website', 'personal.?site', 'url', 'web.?page'],
        'value_key': 'website',
        'type': 'url'
    },
    'behance': {
        'patterns': ['behance'],
        'value_key': 'behance',
        'type': 'url'
    },
    'github': {
        'patterns': ['github', 'git.?hub'],
        'value_key': 'github',
        'type': 'url'
    },
    'twitter': {
        'patterns': ['twitter', 'x.com'],
        'value_key': 'twitter',
        'type': 'url'
    },
    
    # ===== WORK AUTHORIZATION =====
    'authorized': {
        'patterns': ['authorized', 'eligible.?to.?work', 'legally.?work', 'work.?authorization', 'right.?to.?work'],
        'value_key': 'authorized_to_work',
        'type': 'radio',
        'answer': 'Yes'
    },
    'sponsorship': {
        'patterns': ['sponsor', 'visa', 'immigration', 'require.?sponsor'],
        'value_key': 'require_sponsorship',
        'type': 'radio',
        'answer': 'No'
    },
    'citizen': {
        'patterns': ['citizen', 'citizenship', 'nationality'],
        'value_key': 'us_citizen',
        'type': 'radio',
        'answer': 'Yes'
    },
    
    # ===== DEMOGRAPHICS / EEO =====
    'gender': {
        'patterns': ['gender', 'sex'],
        'value_key': 'gender',
        'type': 'select',
        'prefer_not_to_say': True
    },
    'pronouns': {
        'patterns': ['pronoun'],
        'value_key': 'pronouns',
        'type': 'select'
    },
    'race': {
        'patterns': ['race', 'racial'],
        'value_key': 'race',
        'type': 'select',
        'prefer_not_to_say': True
    },
    'ethnicity': {
        'patterns': ['ethnicity', 'ethnic', 'hispanic', 'latino'],
        'value_key': 'ethnicity',
        'type': 'select',
        'prefer_not_to_say': True
    },
    'veteran': {
        'patterns': ['veteran', 'military', 'armed.?forces', 'served'],
        'value_key': 'veteran_status',
        'type': 'select',
        'prefer_not_to_say': True
    },
    'disability': {
        'patterns': ['disability', 'disabled', 'handicap', 'impairment'],
        'value_key': 'disability_status',
        'type': 'select',
        'prefer_not_to_say': True
    },
    
    # ===== EDUCATION =====
    'degree': {
        'patterns': ['degree', 'education.?level', 'highest.?education'],
        'value_key': 'highest_degree',
        'type': 'select'
    },
    'major': {
        'patterns': ['major', 'field.?of.?study', 'concentration', 'discipline'],
        'value_key': 'major',
        'type': 'text'
    },
    'school': {
        'patterns': ['school', 'university', 'college', 'institution'],
        'value_key': 'school',
        'type': 'text'
    },
    'graduation': {
        'patterns': ['graduat', 'grad.?year', 'completion'],
        'value_key': 'graduation_year',
        'type': 'text'
    },
    'gpa': {
        'patterns': ['gpa', 'grade.?point'],
        'value_key': 'gpa',
        'type': 'text'
    },
    
    # ===== EXPERIENCE =====
    'years_experience': {
        'patterns': ['years?.?experience', 'years?.?of.?experience', 'experience.?years', 'how.?many.?years'],
        'value_key': 'years_experience',
        'type': 'text'
    },
    'current_title': {
        'patterns': ['current.?title', 'job.?title', 'position', 'role'],
        'value_key': 'current_title',
        'type': 'text'
    },
    'current_company': {
        'patterns': ['current.?company', 'current.?employer', 'employer'],
        'value_key': 'current_company',
        'type': 'text'
    },
    
    # ===== SALARY & COMPENSATION =====
    'salary': {
        'patterns': ['salary', 'compensation', 'pay.?expectation', 'desired.?salary', 'expected.?salary'],
        'value_key': 'salary_expectation',
        'type': 'text'
    },
    'salary_min': {
        'patterns': ['minimum.?salary', 'min.?salary', 'lowest.?salary'],
        'value_key': 'salary_min',
        'type': 'text'
    },
    'hourly': {
        'patterns': ['hourly', 'rate.?per.?hour', 'hour.?rate'],
        'value_key': 'hourly_rate',
        'type': 'text'
    },
    
    # ===== AVAILABILITY =====
    'start_date': {
        'patterns': ['start.?date', 'available.?date', 'when.?can.?you.?start', 'earliest.?start'],
        'value_key': 'available_start',
        'type': 'text'
    },
    'notice_period': {
        'patterns': ['notice.?period', 'notice.?required', 'days?.?notice'],
        'value_key': 'notice_period',
        'type': 'text'
    },
    'relocate': {
        'patterns': ['relocat', 'willing.?to.?move', 'open.?to.?relocation'],
        'value_key': 'willing_to_relocate',
        'type': 'radio',
        'answer': 'No'
    },
    
    # ===== LANGUAGE & SKILLS =====
    'english': {
        'patterns': ['english', 'language.?level', 'fluency'],
        'value_key': 'english_level',
        'type': 'select'
    },
    'languages': {
        'patterns': ['language', 'speak', 'multilingual'],
        'value_key': 'languages',
        'type': 'text'
    },
    
    # ===== LOCATION-BASED QUESTIONS =====
    'latin_america': {
        'patterns': ['latin.?america', 'latam', 'south.?america', 'central.?america'],
        'value_key': 'based_in_latin_america',
        'type': 'radio',
        'answer': 'No'
    },
    'europe': {
        'patterns': ['europe', 'eu', 'european'],
        'value_key': 'based_in_europe',
        'type': 'radio',
        'answer': 'No'
    },
    'timezone': {
        'patterns': ['timezone', 'time.?zone'],
        'value_key': 'timezone',
        'type': 'select'
    },
    
    # ===== AGE VERIFICATION =====
    'age_18': {
        'patterns': ['18.?years', 'over.?18', '18.?or.?older', 'at.?least.?18'],
        'value_key': 'over_18',
        'type': 'radio',
        'answer': 'Yes'
    },
    'age_21': {
        'patterns': ['21.?years', 'over.?21', '21.?or.?older', 'at.?least.?21'],
        'value_key': 'over_21',
        'type': 'radio',
        'answer': 'Yes'
    },
    
    # ===== REFERRAL / SOURCE =====
    'hear_about': {
        'patterns': ['hear.?about', 'how.?did.?you.?find', 'source', 'referred'],
        'value_key': 'hear_about_us',
        'type': 'select'
    },
    'referral': {
        'patterns': ['referral', 'referred.?by', 'employee.?referral'],
        'value_key': 'referred_by',
        'type': 'text'
    },
}


def get_field_value(field_name: str, field_label: str, profile: UserProfile = None) -> Optional[str]:
    """
    Determine the value to fill for a given form field.
    
    Args:
        field_name: The field's name/id attribute
        field_label: The field's label text
        profile: User profile (defaults to Deanna's info)
    
    Returns:
        The value to fill, or None if no match found
    """
    if profile is None:
        profile = UserProfile()
    
    combined = f"{field_name} {field_label}".lower()
    
    for field_type, config in FIELD_PATTERNS.items():
        for pattern in config['patterns']:
            if re.search(pattern, combined, re.IGNORECASE):
                value_key = config['value_key']
                return getattr(profile, value_key, None)
    
    return None


def get_select_value(field_name: str, field_label: str, options: list, profile: UserProfile = None) -> Optional[str]:
    """
    Determine the best option to select for a dropdown/select field.
    
    Args:
        field_name: The field's name/id
        field_label: The field's label
        options: List of available options
        profile: User profile
    
    Returns:
        The option value to select
    """
    if profile is None:
        profile = UserProfile()
    
    combined = f"{field_name} {field_label}".lower()
    
    # Check for "Prefer not to say" questions (EEO)
    prefer_not_patterns = ['gender', 'race', 'ethnicity', 'veteran', 'disability']
    for pattern in prefer_not_patterns:
        if pattern in combined:
            # Look for prefer not to say option
            for opt in options:
                if 'prefer' in opt.lower() or 'decline' in opt.lower() or 'not.?disclose' in opt.lower():
                    return opt
    
    # Get target value from profile
    target_value = get_field_value(field_name, field_label, profile)
    if target_value:
        target_lower = target_value.lower()
        
        # Find best matching option
        for opt in options:
            if target_lower in opt.lower() or opt.lower() in target_lower:
                return opt
    
    # English level special handling
    if 'english' in combined or 'language' in combined or 'level' in combined:
        for opt in options:
            opt_lower = opt.lower()
            if any(word in opt_lower for word in ['fluent', 'native', 'advanced', 'c2', 'c1']):
                return opt
    
    # Experience level
    if 'experience' in combined and 'year' in combined:
        for opt in options:
            if '5' in opt or '4-6' in opt or '3-5' in opt:
                return opt
    
    # Education level
    if 'education' in combined or 'degree' in combined:
        for opt in options:
            if 'bachelor' in opt.lower():
                return opt
    
    return None


def get_radio_answer(field_name: str, field_label: str, question_text: str, profile: UserProfile = None) -> str:
    """
    Determine Yes/No answer for radio button questions.
    
    Returns: 'Yes', 'No', or None
    """
    if profile is None:
        profile = UserProfile()
    
    combined = f"{field_name} {field_label} {question_text}".lower()
    
    # Work authorization - Yes
    if any(word in combined for word in ['authorized', 'eligible to work', 'legally work', 'right to work']):
        return 'Yes'
    
    # Sponsorship - No
    if any(word in combined for word in ['sponsor', 'visa', 'immigration support']):
        return 'No'
    
    # Location questions - based on actual location
    if any(word in combined for word in ['latin america', 'latam', 'south america']):
        return 'No'
    if any(word in combined for word in ['europe', 'eu ', 'european union']):
        return 'No'
    if any(word in combined for word in ['united states', 'u.s.', 'usa', 'us-based']):
        return 'Yes'
    
    # Age verification - Yes
    if any(word in combined for word in ['18 years', 'over 18', '18 or older', '21 years', 'over 21']):
        return 'Yes'
    
    # Relocation - No (based on config)
    if 'relocat' in combined:
        return 'No'
    
    # Background check consent - Yes
    if 'background check' in combined or 'consent' in combined:
        return 'Yes'
    
    # References available - Yes
    if 'reference' in combined:
        return 'Yes'
    
    # Currently employed
    if 'currently employed' in combined:
        return 'No'  # Looking for work
    
    return None


# Common dropdown option mappings
SELECT_MAPPINGS = {
    'gender': ['Female', 'Woman', 'Prefer not to say'],
    'race': ['Two or More Races', 'Prefer not to say', 'Decline to self-identify'],
    'ethnicity': ['Not Hispanic or Latino', 'Prefer not to say'],
    'veteran': ['I am not a protected veteran', 'No', 'Prefer not to say'],
    'disability': ['No, I do not have a disability', 'No', 'Prefer not to say'],
    'degree': ["Bachelor's Degree", "Bachelor's", "BA", "4-year degree"],
    'english': ['Fluent', 'Native', 'Advanced', 'C2', 'C1'],
    'experience': ['5+ years', '4-6 years', '3-5 years', '5'],
    'start': ['Immediately', 'ASAP', '2 weeks', 'Available now'],
    'hear_about': ['Job Board', 'Online Search', 'LinkedIn', 'Indeed'],
    'country': ['United States', 'USA', 'US'],
    'state': ['California', 'CA'],
}


def print_field_coverage():
    """Print all supported field types for documentation."""
    print("=" * 70)
    print("SUPPORTED FORM FIELD TYPES")
    print("=" * 70)
    
    categories = {
        'Contact Info': ['first_name', 'last_name', 'full_name', 'email', 'phone'],
        'Location': ['address', 'city', 'state', 'zip', 'country'],
        'Online Presence': ['linkedin', 'portfolio', 'website', 'behance', 'github', 'twitter'],
        'Work Authorization': ['authorized', 'sponsorship', 'citizen'],
        'Demographics (EEO)': ['gender', 'pronouns', 'race', 'ethnicity', 'veteran', 'disability'],
        'Education': ['degree', 'major', 'school', 'graduation', 'gpa'],
        'Experience': ['years_experience', 'current_title', 'current_company'],
        'Compensation': ['salary', 'salary_min', 'hourly'],
        'Availability': ['start_date', 'notice_period', 'relocate'],
        'Language': ['english', 'languages'],
        'Location-based': ['latin_america', 'europe', 'timezone'],
        'Age Verification': ['age_18', 'age_21'],
        'Referral': ['hear_about', 'referral'],
    }
    
    for category, fields in categories.items():
        print(f"\n{category}:")
        for field in fields:
            if field in FIELD_PATTERNS:
                config = FIELD_PATTERNS[field]
                patterns = ', '.join(config['patterns'][:3])
                print(f"  - {field}: {patterns}")
    
    print("\n" + "=" * 70)
    print(f"Total field types: {len(FIELD_PATTERNS)}")
    print("=" * 70)


if __name__ == "__main__":
    print_field_coverage()
