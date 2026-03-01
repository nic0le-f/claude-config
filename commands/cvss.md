# Calculate CVSS Score

Calculate CVSS 3.1 score for a vulnerability.

## Instructions

Guide through CVSS 3.1 scoring based on the vulnerability details:

### Attack Vector (AV)
- **Network (N)**: Exploitable over network (0.85)
- **Adjacent (A)**: Requires adjacent network (0.62)
- **Local (L)**: Requires local access (0.55)
- **Physical (P)**: Requires physical access (0.20)

### Attack Complexity (AC)
- **Low (L)**: No special conditions (0.77)
- **High (H)**: Requires specific conditions (0.44)

### Privileges Required (PR)
- **None (N)**: No authentication (0.85/0.85)
- **Low (L)**: Basic user privileges (0.62/0.68)
- **High (H)**: Admin privileges (0.27/0.50)

### User Interaction (UI)
- **None (N)**: No user action (0.85)
- **Required (R)**: User must perform action (0.62)

### Scope (S)
- **Unchanged (U)**: Stays in vulnerable component
- **Changed (C)**: Impacts other components

### Confidentiality Impact (C)
- **High (H)**: Total information disclosure
- **Low (L)**: Limited disclosure
- **None (N)**: No impact

### Integrity Impact (I)
- **High (H)**: Total system modification
- **Low (L)**: Limited modification
- **None (N)**: No impact

### Availability Impact (A)
- **High (H)**: Total denial of service
- **Low (L)**: Reduced performance
- **None (N)**: No impact

## Output
- CVSS Vector String: CVSS:3.1/AV:X/AC:X/PR:X/UI:X/S:X/C:X/I:X/A:X
- Base Score: X.X
- Severity: Critical (9.0-10.0) / High (7.0-8.9) / Medium (4.0-6.9) / Low (0.1-3.9)

$ARGUMENTS
