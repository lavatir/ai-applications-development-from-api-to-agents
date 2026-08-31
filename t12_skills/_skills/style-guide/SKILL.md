---
name: style-guide
description: >
  Use this skill when the user asks to write, rewrite, review, or check content against the brand style guide.
  Covers emails, blog posts, social media posts (LinkedIn, Twitter/X), and support/help content. Triggers on
  requests like "rewrite this in our brand voice", "does this follow our style guide", "write a LinkedIn post
  about...", or "what are the rules for writing [content type]".
---

# Style Guide Skill

This skill teaches the agent how to write and rewrite content in the brand's voice and tone, using the rules in
REFERENCE.md and the before/after rewrites in EXAMPLES.md.

## File Map
- `REFERENCE.md` — type-specific rules (emails, blog posts, social media, support content) plus grammar/mechanics.
- `EXAMPLES.md` — before (❌) / after (✅) rewrites for each content type, used as a model for new rewrites.

## Workflow
1. Identify the content type (email, blog post, social media post, support reply, or general text).
2. Apply the Core Principles and Instant Rules below to the draft.
3. Open REFERENCE.md and apply the rules for that specific content type.
4. Open EXAMPLES.md and use the matching before/after pair as a model for tone and structure.
5. Return the polished text, followed by a short changelog listing the key changes made (e.g. "Removed passive
   voice, shortened subject line, added a clear CTA").

## Core Principles
- **Voice**: confident, friendly, and human — write like a knowledgeable colleague, not a corporate memo.
- **Tone**: warm and direct; adjust formality per content type (see REFERENCE.md's tone dial).
- **Length**: as short as the message allows — cut filler words and redundant qualifiers.
- **Person**: address the reader directly as "you"; refer to the company as "we".

## Instant Rules
Quick checklist to apply to every rewrite:
- [ ] No jargon or corporate-speak (see EXAMPLES.md's Jargon → Plain English table)
- [ ] No passive voice — use active voice with a clear subject
- [ ] Use contractions (e.g. "we're", "you'll") to sound natural
- [ ] Spell out numbers one through nine; use digits for 10+
- [ ] Use the Oxford comma in lists of three or more items
- [ ] Avoid exclamation marks and excessive punctuation