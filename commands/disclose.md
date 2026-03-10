# Prepare Disclosure

Generate materials for responsible vulnerability disclosure.

## Instructions

Based on the argument or conversation context, produce one or both outputs below.

---

## Output 1: Security Advisory

A full technical advisory document for public or coordinated release.

```
# Security Advisory: [TITLE]

## Overview
- **CVE ID**: [CVE-YYYY-XXXXX or "Pending"]
- **Vendor**: [Vendor Name]
- **Product**: [Product Name]
- **Affected Versions**: [Version range]
- **Fixed Version**: [Version or "Not yet patched"]
- **Severity**: [Critical/High/Medium/Low] (CVSS: X.X)
- **Discovered by**: [Researcher name]
- **Disclosure Date**: [Date]

## Summary
[One paragraph description of the vulnerability]

## Technical Details
[Detailed technical explanation including:]
- Root cause analysis
- Affected component/function
- Attack vector
- Code snippets or pseudocode showing the issue

## Impact
[What an attacker can achieve by exploiting this vulnerability]

## Proof of Concept
[Steps to reproduce - non-weaponized]

## Remediation
[How to fix the vulnerability]

## Workarounds
[Temporary mitigations if patch not available]

## Timeline
- [Date]: Vulnerability discovered
- [Date]: Vendor notified
- [Date]: Vendor acknowledged
- [Date]: Patch released
- [Date]: Public disclosure

## References
- [Relevant links]
```

---

## Output 2: Vendor Notification Email

An initial disclosure email for sending to the vendor's security team.

```
Subject: Security Vulnerability in [Product Name] - Responsible Disclosure

Dear [Vendor] Security Team,

I am a security researcher and I have discovered a vulnerability in [Product Name]
that I would like to report through your responsible disclosure program.

**Summary**
- Product: [Product Name]
- Affected Versions: [Versions]
- Vulnerability Type: [Type] (CWE-XXX)
- Severity: [Critical/High/Medium/Low]
- Attack Vector: [Network/Local/etc.]

**Brief Description**
[2-3 sentence description of the vulnerability and its impact]

**Disclosure Timeline**
I follow a 90-day disclosure policy. I am prepared to:
- Work with your team to verify and understand the issue
- Coordinate on patch timeline
- Delay public disclosure if patch is imminent
- Provide credit in any public advisory if desired

**Next Steps**
Please confirm receipt of this report. I am happy to provide:
- Detailed technical write-up
- Proof-of-concept code
- Remediation suggestions

I can be reached at [email] and am available for a call if helpful.

Best regards,
[Your Name]
```

---

## Pre-Disclosure Checklist
- [ ] Verified vulnerability is reproducible
- [ ] Confirmed affected versions
- [ ] Checked for existing CVE
- [ ] Found correct security contact (security.txt, security@vendor, bug bounty)
- [ ] Prepared detailed write-up
- [ ] Created non-weaponized PoC
- [ ] Saved all evidence and communications

$ARGUMENTS
