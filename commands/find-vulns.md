# Find Vulnerabilities

We are secuirty reseracher, looking for vulnerabilites in different products that use AI. Our goal is to find vuln, and responsibly disclouse them before they get exploited. You need to analyze code or binary for potential security vulnerabilities.

## Instructions

Perform vulnerability analysis on the target:

1. **Dangerous Function Usage**
   - strcpy, strcat, sprintf, vsprintf (buffer overflows)
   - gets, scanf without limits (buffer overflows)
   - system, popen, exec* with user input (command injection)
   - Format string functions with user-controlled format

2. **Memory Safety Issues**
   - Unchecked malloc/realloc return values
   - Double-free patterns
   - Use-after-free possibilities
   - Integer overflow leading to small allocations
   - Off-by-one errors in loops

3. **Logic Vulnerabilities**
   - Authentication bypass possibilities
   - Authorization check gaps
   - TOCTOU race conditions
   - Improper error handling exposing info

4. **Crypto Weaknesses**
   - Weak algorithms (MD5, SHA1 for security, DES, RC4)
   - Hardcoded keys/IVs
   - Predictable random number generation
   - ECB mode usage

5. **Output Format**
   For each finding:
   - Location (file:line or address)
   - Vulnerability type and CWE ID
   - Severity assessment
   - Exploitation potential
   - Suggested fix

$ARGUMENTS
