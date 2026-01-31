#!/usr/bin/env python3
"""Check for application confirmation emails."""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from gmail_handler import search_emails, get_email_summary

print("=" * 70)
print("📧 CHECKING FOR CONFIRMATION EMAILS")
print("=" * 70)

# Check email summary
summary = get_email_summary()
print(f"\nEmail Summary (last 14 days):")
print(f"  Total job emails: {summary.get('total_emails', 0)}")
print(f"  Interview requests: {summary.get('interview_requests', 0)}")
print(f"  Applications confirmed: {summary.get('applications_confirmed', 0)}")
print(f"  Rejections: {summary.get('rejections', 0)}")

# Search for confirmation emails
print("\n" + "-" * 50)
print("Recent emails with 'confirmation' or 'application':")
print("-" * 50)

emails = search_emails('subject:(application OR confirmation OR received OR thank) newer_than:1d', max_results=10)
print(f"Found {len(emails)} emails")

for e in emails:
    subject = e.get('subject', '?')
    sender = e.get('from', '?')
    date = e.get('date', '?')
    print(f"\n  Subject: {subject[:70]}")
    print(f"  From: {sender}")
    print(f"  Date: {date}")

# Specifically check for GoFasti/Greenhouse
print("\n" + "-" * 50)
print("Checking specifically for GoFasti/Greenhouse:")
print("-" * 50)

gofasti_emails = search_emails('from:gofasti OR from:greenhouse', max_results=5)
print(f"Found {len(gofasti_emails)} emails from GoFasti/Greenhouse")

for e in gofasti_emails:
    print(f"  - {e.get('subject', '?')}")

print("\n" + "=" * 70)
