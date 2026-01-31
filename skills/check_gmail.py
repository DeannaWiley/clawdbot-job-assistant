from gmail_handler import search_emails, get_email_by_id

print('Checking Gmail for Spotify application confirmation...')

# Search for recent emails from Spotify or Lever
emails = search_emails('from:spotify OR from:lever OR subject:spotify OR subject:application', max_results=10)

print(f'Found {len(emails)} matching emails')
for email in emails[:5]:
    print(f'  - {email["date"]}: {email["subject"]}')
    print(f'    From: {email["from"]}')
    print(f'    Snippet: {email["snippet"][:100]}...')
    print()

# Also check for very recent emails (last hour)
print('\nChecking for any emails in last hour...')
recent = search_emails('newer_than:1h', max_results=5)
print(f'Found {len(recent)} emails in last hour')
for email in recent:
    print(f'  - {email["subject"]}')
    print(f'    From: {email["from"]}')
