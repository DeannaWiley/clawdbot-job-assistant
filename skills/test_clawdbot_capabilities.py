#!/usr/bin/env python3
"""Test ClawdBot capabilities - email check and document generation"""
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("🦞 CLAWDBOT CAPABILITY TEST")
print("=" * 60)

# Test 1: Gmail Integration
print("\n📧 TEST 1: Email Integration")
print("-" * 40)
try:
    from gmail_handler import search_emails, get_email_summary
    
    # Search for recent application confirmations
    emails = search_emails('subject:(application OR confirmation OR received) newer_than:7d', max_results=10)
    
    if emails:
        print(f"Found {len(emails)} potential confirmations:")
        for e in emails[:5]:
            print(f"  • {e['subject'][:50]}")
            print(f"    From: {e['from'][:40]}")
    else:
        print("No recent application confirmations found")
    
    summary = get_email_summary()
    print(f"\n📊 Email Summary (14 days):")
    print(f"   Total job emails: {summary['total']}")
    print(f"   Confirmations: {summary['applications_confirmed']}")
    print(f"   Interview requests: {summary['interview_requests']}")
    print("✅ Gmail: WORKING")
except Exception as e:
    print(f"❌ Gmail: FAILED - {e}")

# Test 2: Document Generation
print("\n📄 TEST 2: Document Generation")
print("-" * 40)
try:
    from tailor_resume import tailor_resume
    
    test_job = {
        'title': 'Senior Product Designer',
        'company': 'Spotify',
        'description': 'We are looking for a Senior Product Designer to join our team. You will design user experiences for our music streaming platform.'
    }
    
    # Load base resume
    with open('../data/base_resume.txt', 'r') as f:
        resume_text = f.read()
    
    print(f"Generating tailored content for {test_job['title']} at {test_job['company']}...")
    result = tailor_resume(resume_text, test_job['title'], test_job['company'], test_job['description'])
    
    if result and 'tailored_summary' in result:
        print(f"✅ Summary generated: {result['tailored_summary'][:100]}...")
        print(f"✅ Match score: {result.get('match_score', 'N/A')}")
        print("✅ Document Generation: WORKING")
    else:
        print("⚠️ Document Generation: Partial result")
except Exception as e:
    print(f"❌ Document Generation: FAILED - {e}")

# Test 3: LLM Fallback
print("\n🤖 TEST 3: LLM Fallback Chain")
print("-" * 40)
try:
    from test_llm_fallback import load_env
    import requests
    
    groq_key = load_env('GROQ_API_KEY')
    if groq_key:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_key}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": "Say OK"}],
                "max_tokens": 10
            },
            timeout=10
        )
        if resp.status_code == 200:
            print("✅ Groq Fallback: WORKING")
        else:
            print(f"⚠️ Groq: {resp.status_code}")
    else:
        print("⏭️ Groq: No key")
except Exception as e:
    print(f"❌ LLM Fallback: {e}")

print("\n" + "=" * 60)
print("✅ CAPABILITY TEST COMPLETE")
print("=" * 60)
