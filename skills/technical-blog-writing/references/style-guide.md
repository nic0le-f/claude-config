# Style Guide: Nicole's Technical Blog Voice

Derived from four published Intezer posts (see "Sample corpus" at the bottom).
These are consistent patterns observed across all four. When they conflict with
generic blog-writing advice, these win.

> **Note on this file's own punctuation:** the headings and examples below are
> quoted source material. Do not copy their punctuation habits. The dash rule in
> §3 is absolute and applies to everything you write.

## The one-line summary of the voice

Clinical, authoritative security-analyst register: technically precise, never
sensational, written *for* other analysts but with enough context that a
stakeholder can follow. Restraint despite dramatic subject matter.

---

## 1. Sentence structure & length

- Deliberately varied rhythm. Medium sentences (15 to 20 words) as the backbone,
  broken by short declarative statements for impact and longer nested-clause
  sentences for technical precision.
- Short opener to set the frame: *"SSLoad is a new malware that has been
  targeting victims since April 2024."*
- Long procedural sentence when the mechanics demand it: *"It first attempts to
  check if one was already created by reading 16 bytes from
  `C:\ProgramData\SystemRuntimeLag.inc`."*
- Occasional one-word or rhetorical fragment as a section beat (rare, used for
  emphasis, e.g. *"Hacktivism?"*).

## 2. Tone & voice

- **Third person dominant.** The malware, the attacker, or the group is the
  grammatical subject: *"The malware uses a custom API-resolving scheme…"*
- **Strategic first-person plural** for research claims and naming, never for
  filler: *"We named it PhantomLoader,"* *"We've labeled this campaign Operation
  HamsaUpdate,"* *"we unearthed a second-stage loader."*
- **Active voice** for procedures and actions the malware takes. **Passive
  voice** is acceptable for describing static properties (*"is encrypted,"* *"was
  compiled"*).
- No sensationalism, no exclamation marks, no hype adjectives beyond earned ones
  ("sophisticated," "highly targeted") used sparingly and only in synthesis.
- **Cautious attribution.** State evidence, then hedge explicitly: *"we can't
  make attribution since there is insufficient evidence."* Never overclaim.

## 3. Punctuation

### HARD RULE: never use dashes as punctuation

**Do not output the em-dash (`—`, U+2014), the en-dash used as punctuation
(`–`, U+2013), or the "spaced hyphen as dash" substitute (` - `).** This is an
explicit, standing instruction from Nicole and it overrides every other style
consideration in this file, including any example sentence quoted here that
happens to contain one. There is no exception for appositives, for asides, for
dramatic pauses, or for "it reads better that way."

If you find yourself reaching for a dash, use one of these instead:

| Instead of a dash | Use | Example |
|---|---|---|
| Appositive / identifying aside | Commas | *"XE Group, a cybercriminal organization active since 2013, has built…"* |
| Explanation or expansion | Colon | *"The loader has one job: decrypt and map the payload."* |
| Non-essential gloss | Parentheses | *"the mutex name (`SystemRuntimeLag`) is hardcoded"* |
| Dramatic pause or pivot | A period. Start a new sentence. | *"The check always fails. The sample was never meant to run in a VM."* |
| Two linked independent clauses | Semicolon | *"The first stage is unremarkable; the second is not."* |
| Range of numbers | The word "to" | *"15 to 20 words," "offsets 0x10 to 0x40"* |
| List introduction | Colon | *"The backdoor drops three files:"* |

Hyphens remain correct and expected in their normal roles: compound modifiers
(`API-resolving scheme`, `second-stage loader`), hyphenated names, and inside
identifiers copied verbatim from a sample. The ban is on dashes used as
*sentence punctuation*, not on the hyphen character.

Verbatim technical strings are exempt. If a file name, registry value, command
line, or decoded string genuinely contains `—`, reproduce it exactly and, where
it matters, note that the character is part of the artifact.

### Everything else

- **Colons** to introduce lists, explanations, and named artifacts:
  *"The backdoor is a DLL named: SkinH.dll."*
- **Semicolons** to link tightly related independent clauses (used moderately).
- **Commas** carry the appositive and interruptive work that a dash would
  otherwise do. Do not fear a three-comma sentence.
- **Oxford comma**, always.
- **Parentheses** for asides, glosses, and hex equivalents: *"(0x1E)," "(EIP),"
  "(Hatef refers to…)."*
- **No contractions** in body prose ("it is," "does not," "cannot"). The
  first-person "we've/can't" seen in casual research asides is the only
  exception, and even then prefer the expanded form in formal sections.

## 4. Grammar & spelling

- **American English** throughout: behavior, analyze, organization, customize
  (not behaviour/analyse/organisation).
- Formal register, no colloquialisms or memes.
- Preserve malware's own errors verbatim and call them out (e.g. a misspelled
  method name `DeleteDrirectorys`). Do not silently "correct" the sample.

## 5. Technical formatting

- **Hashes: shown in full**, monospace, never truncated:
  `90f1511223698f33a086337a6875db3b5d6fbcce06f3195cdd6a8efa90091750`.
  Label the type (`SHA256`).
- **IPs, domains, URLs: defanged** with bracketed dots (and bracketed schemes
  where used): `146.70.29[.]229:443`, `xegroups[.]com`,
  `https://t[.]me/+st2YadnCIU1iNmQy`.
- **File names / paths / registry keys / API names:** monospace or italics.
  `C:\Windows\System32\regsvr32.exe`, *F5UPDATER.EXE*, `OverwriteFileBlockAndDelete`.
- **CVEs:** bracketed with a link and an inline gloss:
  `[CVE-2024-57968](url)`, "an Upload Validation Vulnerability."
- **Addresses:** VA hex form `0x…`. Give the decimal in parentheses only when
  clarifying (e.g. `30 (0x1E)`).
- Code, decryption logic, and raw logs go in fenced code blocks. Short inline
  artifacts stay inline in monospace.

## 6. Section structure & article flow

Typical skeleton (adapt headings to the content):

1. **Executive Summary** *(for larger investigations)*: a few sentences of
   what was found and why it matters.
2. **Introduction**: threat or group context, often with geopolitical or
   timeline framing. Ends by stating what the post will cover.
3. **Technical deep-dive**: progressive disclosure following the execution
   chain (e.g. Installer → Loader → Payload, or anti-analysis → networking →
   pivot). Use **descriptive H2/H3 headers** ("Infection Vector: Phishing
   Email"), not generic "Step 1."
4. **Infrastructure / networking**: C2, domains, hosting.
5. **Conclusion**: synthesizes findings, states significance, and ends on
   defensive implications ("Understanding these aspects is crucial for
   defenders"). No new facts.
6. **Appendix / IOCs**: hashes, domains, IPs, and where relevant YARA rules
   and a disclosure timeline. Tables for structured data, bullet lists for
   flat indicator lists.

## 7. Intros & conclusions

- **Intro openings** establish authority immediately by leading with the
  subject and its provenance: *"XE Group, a cybercriminal organization active
  since 2013…"* or with an operational trigger: *"On December 19th, the Israel
  National Cyber Directorate released an urgent alert…"*
- **Conclusions** synthesize without drama and pivot to defense or continued
  research: *"…reinforces the need for ongoing research and threat hunting to
  counter cyber operations."*

## 8. Recurring phrases & transitions

- Analytical asides / emphasis shifts: **"Notably,"** **"Interestingly,"**
  **"Additionally,"** **"As previously documented/noted."**
- Comparative continuity: **"Similar to earlier versions,"** **"Similarly,"**
  **"Together, these techniques…"**
- Procedural connectors: **"If not found,"** **"Once [X], the malware…,"**
  **"Next, the DLL will…," "The malware will…"**
- Significance framing: **"highlighting,"** **"underscores,"**
  **"demonstrating,"** **"indicating."**

## 9. Lists vs. prose

- **Prose** for narrative context and technical explanation.
- **Numbered lists** for sequential attack steps or enumerated techniques.
- **Bullet lists** for IOCs, attributes, and command sets.
- **Tables** for structured artifact data (hash / type / filename / signed
  status, or version / IP / domain fields).
- Break dense technical passages with screenshots, diagrams, or code blocks.

## 10. Paragraph length

- 2 to 4 sentences typical.
- Expand to 5 to 8 or more sentences for a technical deep-dive on one mechanism.
- Occasional 1 to 2 sentence paragraph to spotlight a critical finding.

---

## Pre-delivery checklist

Run the dash check first, mechanically, on the saved file. Do not eyeball it.

- [ ] **Zero em-dashes and zero punctuation en-dashes.** Verified by grep on the
      written file, not by reading (see the command in SKILL.md). Any hit that is
      not part of a verbatim malware artifact must be rewritten using §3's table.
- [ ] No ` - ` used as a dash substitute
- [ ] American spelling, no contractions in body prose
- [ ] All IPs/domains/URLs defanged with `[.]`
- [ ] Hashes shown in full and labeled by type
- [ ] File names/paths/APIs in monospace or italics
- [ ] CVEs linked and glossed, addresses in `0x…` hex
- [ ] "We" used only for research/naming claims, not as filler
- [ ] Attribution hedged to match the actual evidence, nothing fabricated
- [ ] No exclamation marks, no hype
- [ ] Descriptive section headers, not "Step 1"
- [ ] Conclusion ends on significance / defensive implications
- [ ] IOCs in a table/appendix at the end

---

## Sample corpus

Style derived from these posts (add new samples here as they are ingested):

- Frankenstein variant of the ToneShell backdoor targeting Myanmar
- XE Group exploiting zero-days
- Stealth wiper on Israeli infrastructure (Operation HamsaUpdate)
- SSLoad technical malware analysis

**When ingesting a new sample, never derive a dash rule from it.** Published
posts may contain em-dashes because an editor added them. The §3 ban stands
regardless of what any sample does.
