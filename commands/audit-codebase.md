# Security Audit Codebase

Perform a comprehensive security audit of source code in a folder.

## Instructions

When given a folder path, perform a systematic security audit:

### Phase 1: Reconnaissance
1. **Map the codebase structure**
   - Identify languages used (C/C++, Python, Go, Rust, JS, etc.)
   - Find build files to understand dependencies
   - Locate main entry points and configuration files

2. **Identify attack surface**
   - Network listeners and handlers
   - File parsers (especially for untrusted input)
   - IPC mechanisms
   - Command-line argument processing
   - Environment variable usage
   - Deserialization points

### Phase 2: Automated Pattern Search
Search for dangerous patterns based on language:

**C/C++:**
- `strcpy|strcat|sprintf|gets|scanf` - buffer overflows
- `malloc|realloc|free` - unchecked return values, double-free, use-after-free
- `system|popen|exec` - command injection
- `%s|%n` in printf-family - format strings
- Integer overflow leading to small allocations
- Off-by-one errors in loops

**Python:**
- `eval|exec|compile` - code injection
- `pickle|marshal|yaml.load` - deserialization
- `subprocess|os.system` with shell=True
- `__import__|importlib` with user input
- SQL queries with string formatting

**JavaScript/Node:**
- `eval|Function|setTimeout` with strings
- `child_process` usage
- `innerHTML|outerHTML` - XSS
- SQL/NoSQL query building
- Prototype pollution patterns

**Go:**
- `unsafe` package usage
- `cgo` boundary issues
- Command execution with user input
- SQL query building

**Rust:**
- `unsafe` blocks
- FFI boundaries
- `.unwrap()` on untrusted input

**Crypto Weaknesses (all languages):**
- Weak algorithms (MD5, SHA1 for security, DES, RC4)
- Hardcoded keys/IVs
- Predictable random number generation
- ECB mode usage

### Phase 3: Logic & Data Flow Analysis
1. Trace user input from entry points to sensitive operations
2. Identify missing or insufficient validation
3. Check for proper encoding/escaping at output boundaries
4. Look for trust boundary violations
5. Authentication bypass possibilities
6. Authorization check gaps (missing or inconsistent access controls)
7. TOCTOU race conditions
8. Improper error handling exposing sensitive information

### Phase 4: Configuration & Secrets
- Hardcoded credentials or API keys
- Weak crypto configurations
- Debug modes left enabled
- Overly permissive file/network access

### Phase 5: Report Generation

Generate a security audit report:

```markdown
# Security Audit Report
**Target:** [folder path]
**Date:** [date]
**Auditor:** [name]

## Executive Summary
[High-level findings and risk assessment]

## Scope
- Languages: [list]
- Files analyzed: [count]
- Lines of code: [approximate]

## Findings

### Critical
[List critical findings]

### High
[List high severity findings]

### Medium
[List medium severity findings]

### Low / Informational
[List low severity findings]

## Finding Details

### [FINDING-001]: [Title]
- **Severity:** [Critical/High/Medium/Low]
- **CWE:** [CWE-XXX]
- **Location:** [file:line]
- **Description:** [detailed description]
- **Impact:** [what an attacker could achieve]
- **Recommendation:** [how to fix]
- **Code:**
  ```
  [vulnerable code snippet]
  ```

[Repeat for each finding]

## Recommendations Summary
[Prioritized list of remediation actions]

## Appendix
- Tools used
- Files excluded
- Limitations of this audit
```

## Usage
```
/audit-codebase ./src
/audit-codebase /path/to/project --focus=network
/audit-codebase . --language=c
```

$ARGUMENTS
