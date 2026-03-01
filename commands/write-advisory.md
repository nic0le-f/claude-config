# Write Security Advisory

Generate a professional security advisory for a discovered vulnerability.

## Instructions

Create a formatted security advisory with the following sections:

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

$ARGUMENTS
