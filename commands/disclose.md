# Prepare Disclosure

Generate materials for responsible disclosure to a vendor.

## Instructions

Create a professional disclosure report for sending to the vendor:

## Initial Disclosure Email Template

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

## Checklist Before Sending
- [ ] Verified vulnerability is reproducible
- [ ] Confirmed affected versions
- [ ] Checked for existing CVE
- [ ] Found correct security contact (security.txt, security@vendor, bug bounty)
- [ ] Prepared detailed write-up
- [ ] Created non-weaponized PoC
- [ ] Saved all evidence and communications

$ARGUMENTS
