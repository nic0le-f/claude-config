# Analyze Binary

Perform initial triage and analysis of a binary file.

## Instructions

When given a binary file path, perform the following analysis:

1. **File Identification**
   - Run `file` command to identify type
   - Check for architecture (x86, x64, ARM, etc.)
   - Identify format (ELF, PE, Mach-O)

2. **Security Protections**
   - Check for ASLR/PIE
   - Stack canaries
   - NX/DEP
   - RELRO (for ELF)
   - Use `checksec` if available, otherwise parse headers

3. **Strings Analysis**
   - Extract interesting strings (URLs, paths, error messages, crypto constants)
   - Look for version info, debug strings, hardcoded credentials

4. **Import/Export Analysis**
   - List interesting imports (crypto, network, file I/O, dangerous functions)
   - Flag unsafe functions: strcpy, sprintf, gets, system, etc.

5. **Summary**
   - Provide overview of what the binary likely does
   - Highlight areas of interest for further analysis
   - Suggest next steps

$ARGUMENTS
