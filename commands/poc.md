# Generate Proof of Concept

Create a proof-of-concept for demonstrating a vulnerability.

## Instructions

Generate a PoC that:

1. **Purpose**: Demonstrate the vulnerability exists without causing harm
2. **Minimal**: Only include what's necessary to trigger the bug
3. **Documented**: Clearly explain each step
4. **Safe**: Include safeguards and warnings

## PoC Structure

```python
#!/usr/bin/env python3
"""
Proof of Concept: [Vulnerability Name]
CVE: [CVE-ID if assigned]
Target: [Product/Version]
Author: [Researcher]
Date: [Date]

Description:
[Brief description of what this PoC demonstrates]

DISCLAIMER: This PoC is for authorized security research only.
Do not use against systems without explicit permission.
"""

import argparse
# ... imports

def check_vulnerable(target):
    """Check if target is vulnerable without exploitation."""
    pass

def demonstrate_bug(target):
    """Trigger the vulnerability in a safe manner."""
    pass

def main():
    parser = argparse.ArgumentParser(description='PoC for [Vuln Name]')
    parser.add_argument('target', help='Target to test')
    parser.add_argument('--check-only', action='store_true',
                       help='Only check if vulnerable, do not exploit')
    args = parser.parse_args()

    print("[*] PoC for [Vulnerability Name]")
    print("[!] For authorized testing only\n")

    if args.check_only:
        vulnerable = check_vulnerable(args.target)
        print(f"[{'!' if vulnerable else '-'}] Target is {'VULNERABLE' if vulnerable else 'not vulnerable'}")
    else:
        demonstrate_bug(args.target)

if __name__ == '__main__':
    main()
```

$ARGUMENTS
