---
name: technical-blog-writing
description: >-
  Write or rewrite technical security / malware-analysis blog posts in Nicole's
  personal voice, matching the exact language, grammar, punctuation, and
  structure of her published Intezer blogs. Use whenever the user asks to draft,
  write, or rewrite a blog post and provides the subject either as a description
  or as a source file (analysis notes, RE report, IOCs). Also use to ingest new
  sample blogs and refine the captured style.
---

# Technical Blog Writing (Nicole's voice)

Draft technical blogs that read as if Nicole wrote them. The voice is derived
from her published Intezer posts and captured in `references/style-guide.md`.
Read that file in full before writing. It is the source of truth for voice, and
it overrides any generic "blog writing" instincts.

## Absolute constraint: no dashes as punctuation

**Never write an em-dash (`—`) or a punctuation en-dash (`–`) in the blog. Never
use ` - ` as a dash substitute.** This is a standing instruction from Nicole and
it is the single most important rule in this skill. It applies to every draft,
every redraft, every heading, every table cell, and every image caption.

Use commas for appositives, a colon for explanation, parentheses for a gloss, a
semicolon for linked clauses, "to" for numeric ranges, or simply two sentences.
See the substitution table in §3 of the style guide. The only exemption is a
character that appears verbatim inside a malware artifact (a file name, command
line, or decoded string), reproduced exactly because it is evidence.

Regular hyphens in compound modifiers (`second-stage loader`) are correct and
expected. The ban is on dashes used as sentence punctuation.

## Workflow

1. **Load the voice.** Read `references/style-guide.md` completely. Do not skim.

2. **Get the content.** The blog subject comes from one of two places:
   - **A description** the user types in the prompt, or
   - **A source file** the user points to (analysis notes, an RE report, IOC
     lists, sandbox output). Read the whole file. Extract the technical facts,
     hashes, file names, addresses, and the narrative arc.

   If the content is thin or ambiguous (missing the threat context, the
   attribution stance, or the intended audience), ask before drafting. Do not
   invent technical facts. Fabricated hashes, CVEs, or attribution are the one
   unacceptable failure mode.

3. **Pick the structure.** Use the article skeleton in the style guide
   (Executive Summary / Intro → technical deep-dive → infrastructure →
   conclusion → IOCs). Adapt section headings to the actual content, the way
   the sample blogs use descriptive headers ("Infection Vector: Phishing
   Email") rather than generic ones ("Step 1").

4. **Draft in her voice.** Apply every rule in the style guide: American
   English, no contractions, no dashes as punctuation, defanged indicators, full
   hashes, strategic "we" for research claims, cautious attribution language, no
   sensationalism.

5. **Always write the blog to a file.** Never deliver the draft only in the
   chat. Use the Write tool to save clean Markdown to a `.md` file before
   presenting it. Default location and name: alongside the source file when the
   subject came from one (e.g. a source `notes/<name>.md` →
   `notes/<name>-blog.md`); otherwise a descriptively-named `.md` in the working
   directory (or the scratchpad if the working directory is not
   writable/appropriate). Then tell the user the file path. This is required on
   every run, including redrafts and edits. Re-save to the same path.

6. **Verify the dash ban mechanically.** After writing the file and before
   presenting anything, grep it. Do not rely on reading the draft, since these
   characters are easy to miss visually:

   ```bash
   grep -nP '\x{2014}|\x{2013}| - ' <path-to-blog.md>
   ```

   Every hit must be rewritten per the substitution table, unless it is a
   verbatim malware artifact. Re-save and re-run the grep until it returns
   nothing. If the grep is somehow unavailable, state that you could not verify
   mechanically rather than claiming the file is clean.

7. **Self-check against the style guide's checklist**, then deliver. Fix
   violations silently.

## Ingesting new sample blogs

When the user pastes or links a new blog they wrote, treat it as additional
ground truth for the voice:

1. Analyze it for the same ten dimensions listed in `references/style-guide.md`
   (sentence structure, tone/voice, punctuation, grammar/spelling, technical
   formatting, section structure, intro/conclusion, recurring phrases,
   lists-vs-prose, paragraph length).
2. Reconcile with the existing guide. If the new sample confirms an existing
   rule, leave it. If it reveals a new habit or contradicts a rule, update
   `references/style-guide.md` and note it in the "Sample corpus" list at the
   bottom of that file.
3. Prefer patterns that appear across multiple samples over one-off choices.
4. **Exception: never relax the dash ban.** A published post may contain
   em-dashes because an editor inserted them. Do not treat that as evidence
   about Nicole's voice, and do not weaken the rule.

## Output

Always write the blog to a `.md` file (step 5), verify with the grep (step 6),
and report the path. Do not deliver it only in the chat. Keep it clean Markdown.
Do not include meta-commentary about the style unless the user asks. When useful,
offer the IOC table and a short list of open questions (facts you could not
verify from the source) separately, so the user can fill gaps before publishing.
