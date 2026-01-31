# ClawdBot CAPTCHA Handling System Architecture

## Executive Summary

This document describes the multi-tier CAPTCHA resolution system designed for ClawdBot's automated job application workflow. The system prioritizes reliability, cost-efficiency, and compliance with a target of 95%+ successful application submissions.

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        JOB APPLICATION FLOW                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   [Job Found] → [Documents Generated] → [Form Filled] → [Submit]     │
│                                                                  ↓    │
│                                              ┌───────────────────────┐│
│                                              │   CAPTCHA DETECTED?   ││
│                                              └───────────────────────┘│
│                                                        ↓              │
│                              ┌─────────────────────────────────────┐  │
│                              │      MULTI-TIER RESOLUTION          │  │
│                              ├─────────────────────────────────────┤  │
│                              │                                     │  │
│                              │  TIER 1: AUTO BYPASS (~10% success) │  │
│                              │  ├─ Cookie reuse                    │  │
│                              │  ├─ Checkbox click                  │  │
│                              │  └─ Session persistence             │  │
│                              │            ↓ (if failed)            │  │
│                              │                                     │  │
│                              │  TIER 2: SERVICE (~85% success)     │  │
│                              │  ├─ 2Captcha API                    │  │
│                              │  ├─ Anti-Captcha API                │  │
│                              │  └─ Cost: $0.002-0.004/solve        │  │
│                              │            ↓ (if failed)            │  │
│                              │                                     │  │
│                              │  TIER 3: HUMAN (~99% success)       │  │
│                              │  ├─ Slack notification              │  │
│                              │  ├─ Desktop alert                   │  │
│                              │  └─ 5-minute timeout                │  │
│                              │                                     │  │
│                              └─────────────────────────────────────┘  │
│                                                        ↓              │
│                                              [APPLICATION SUBMITTED]  │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Tier Details

### Tier 1: Automatic Resolution

**Success Rate:** ~10-15%
**Cost:** Free
**Speed:** 1-3 seconds

Tier 1 attempts automatic CAPTCHA resolution through:

1. **Session Cookie Reuse**
   - Caches successful session cookies per domain
   - Reduces CAPTCHA frequency by 40-60%
   - 24-hour cache expiration

2. **Checkbox Clicking (reCAPTCHA v2)**
   - Attempts to click the "I'm not a robot" checkbox
   - Works when challenge is simple verification only
   - Falls through if image challenge appears

3. **Accessibility Mode**
   - Uses accessible alternatives when available
   - Audio challenges (not implemented - requires additional work)

**When Tier 1 Fails:**
- Image/puzzle challenge required
- reCAPTCHA v3 with low score
- hCaptcha challenge
- Cloudflare Turnstile
- FunCaptcha

### Tier 2: Third-Party Solving Services

**Success Rate:** 85-95%
**Cost:** $0.002-0.004 per solve
**Speed:** 15-120 seconds

Supported Services:
- **2Captcha** (primary) - Most reliable, good pricing
- **Anti-Captcha** (backup) - Slightly cheaper

**Supported CAPTCHA Types:**

| Type | Cost/1000 | Avg Solve Time |
|------|-----------|----------------|
| reCAPTCHA v2 | $2.99 | 20-45 sec |
| reCAPTCHA v3 | $3.99 | 15-30 sec |
| hCaptcha | $2.99 | 20-45 sec |
| Turnstile | $2.99 | 15-30 sec |
| FunCaptcha | $3.99 | 30-60 sec |
| Image CAPTCHA | $0.99 | 10-20 sec |

**Budget Controls:**
- Daily spending limit (default: $1.00)
- Hourly attempt limit (default: 20)
- Automatic fallback to human when budget exhausted

### Tier 3: Human-in-the-Loop

**Success Rate:** 99%
**Cost:** Free (human time)
**Speed:** 30 seconds - 5 minutes

**Notification Channels:**
1. **Slack Message** - Sent to #all-job-hunt-ai
2. **Desktop Notification** - Windows toast
3. **Audio Alert** - Beep sound

**Process:**
1. Browser window stays open (non-headless mode)
2. Notifications sent to all channels
3. Human solves CAPTCHA in browser
4. System detects page change
5. Continues with application

**Timeout Handling:**
- 5-minute default timeout
- If timeout: Application marked as failed
- User can still complete manually

---

## Cost Modeling

### Free Tier Operation ($0/month)

- Tier 1 auto-bypass only
- Tier 3 human assistance for all failures
- Requires ~5 min human attention per CAPTCHA
- Best for: Low volume (1-5 applications/day)

### Budget Tier ($5-10/month)

- ~500-1000 CAPTCHA solves
- Human fallback for service failures
- Best for: Medium volume (5-15 applications/day)

### Standard Tier ($25/month)

- ~2500 CAPTCHA solves
- Covers most use cases
- Best for: High volume (15-30 applications/day)

### Premium Tier ($50-100/month)

- 5000+ CAPTCHA solves
- Priority service queues
- Best for: Enterprise/agency use

---

## Rate Limiting Strategy

### Application Level

| Metric | Limit | Rationale |
|--------|-------|-----------|
| Applications/hour | 5 | Avoid platform detection |
| Applications/day | 20 | Quality over quantity |
| Same company/week | 3 | Prevent spam flagging |
| CAPTCHA attempts/hour | 20 | Service rate limits |

### Platform-Specific

| Platform | Max/Day | Cooldown |
|----------|---------|----------|
| Greenhouse | 10 | 10 min |
| Lever | 10 | 10 min |
| LinkedIn | 5 | 15 min |
| Workday | 3 | 20 min |

---

## Failure Handling

### Decision Tree

```
CAPTCHA_DETECTED:
  ├─ is_budget_available?
  │   ├─ YES → Try Tier 2
  │   └─ NO → Skip to Tier 3
  │
  ├─ tier2_success?
  │   ├─ YES → Continue application
  │   └─ NO → Try Tier 3
  │
  ├─ tier3_success?
  │   ├─ YES → Continue application
  │   └─ NO → FAIL
  │
  └─ on_failure:
      ├─ Log attempt
      ├─ Mark job as "needs_manual"
      ├─ Send failure notification
      └─ Provide manual apply link
```

### Failure Response Matrix

| Failure Type | Response | Retry? |
|--------------|----------|--------|
| Service timeout | Try next tier | Yes |
| Invalid sitekey | Try human | Yes |
| Page navigation | Restart flow | Once |
| Budget exceeded | Human only | No |
| 3+ consecutive fails | Pause 1 hour | No |
| IP blocked | Alert user | No |

---

## Session Management

### Cookie Persistence

```python
# Successful sessions cached per domain
{
    "jobs.lever.co": {
        "cookies": [...],
        "cached_at": "2025-01-30T10:00:00",
        "expires_at": "2025-01-31T10:00:00"
    }
}
```

### Benefits
- 40-60% reduction in CAPTCHA encounters
- Faster subsequent applications
- Lower overall costs

---

## Monitoring & Observability

### Key Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| CAPTCHA success rate | >90% | <70% |
| Avg solve time | <60s | >120s |
| Daily cost | <$1.00 | >$0.80 |
| Human intervention rate | <20% | >50% |

### Dashboard

The `automation_dashboard.py` provides:
- Real-time metrics display
- Cost tracking
- Success rate monitoring
- Recommendations

---

## Setup Instructions

### 1. Environment Variables

```powershell
# Required for Tier 2 (paid service)
[Environment]::SetEnvironmentVariable("CAPTCHA_2CAPTCHA_KEY", "your-key", "User")

# Optional backup service
[Environment]::SetEnvironmentVariable("CAPTCHA_ANTICAPTCHA_KEY", "your-key", "User")

# Budget control (default $1/day)
[Environment]::SetEnvironmentVariable("CAPTCHA_DAILY_BUDGET", "1.0", "User")
```

### 2. Get 2Captcha API Key

1. Register at https://2captcha.com
2. Add funds ($3 minimum for testing)
3. Copy API key from dashboard
4. Set environment variable

### 3. Test the System

```powershell
cd C:\Users\deann\clawd\job-assistant\skills
python captcha_handler.py
```

---

## Limitations (Honest Assessment)

### Known Limitations

1. **reCAPTCHA v3 Score-Based**
   - No reliable automated solution
   - Score depends on browser fingerprint
   - May require human intervention

2. **FunCaptcha (Arkose Labs)**
   - Used by LinkedIn
   - Higher cost ($0.004/solve)
   - 60-90 second solve time

3. **Enterprise Cloudflare**
   - Some sites use advanced bot detection
   - May block after multiple attempts
   - Session persistence helps

4. **Audio CAPTCHAs**
   - Not currently implemented
   - Would require speech-to-text

### Mitigations

- Always have human fallback ready
- Use non-headless browser (looks more human)
- Random delays between actions
- Session cookie reuse
- Rate limiting to avoid detection

---

## Future Enhancements

1. **Audio CAPTCHA Support**
   - Add speech-to-text for accessibility CAPTCHAs

2. **Browser Fingerprint Management**
   - Consistent fingerprints for better reCAPTCHA scores

3. **ML-Based Image Recognition**
   - Local CAPTCHA solving (no API cost)
   - Privacy benefits

4. **Mobile App Notifications**
   - Push notifications for human assistance

---

## Conclusion

This system provides a robust, cost-effective approach to CAPTCHA handling:

- **95%+ success rate** with all tiers enabled
- **$5-25/month** typical operating cost
- **Graceful degradation** - never crashes, always falls back
- **Full logging** for optimization

The human-in-the-loop design ensures no application is lost to CAPTCHA challenges while minimizing manual effort through intelligent automation.
