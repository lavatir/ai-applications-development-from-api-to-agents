---
name: unit-converter
description: >
  Use this skill when the user asks to convert a value between units of measurement — length, weight,
  temperature, volume, area, speed, time, data size, pressure, or energy. Triggers on requests like
  "convert 100 km to miles", "98.6°F in Celsius", "how many MB is 1.5 TB?", or "5 acres to hectares".
license: Apache-2.0
metadata:
  author: ai-powered-apps-development-expert
  version: "1.0"
allowed-tools: execute_code
---

# Unit Converter

This skill converts a value between two units using `scripts/convert.py`, executed via the `execute_code` tool.
See `references/how-code-execution-works.md` for how `execute_code` sessions work, and `examples.md` for
invocation examples and the full list of supported units per category.

## Workflow

### Step 1: Load the script (first call, session_id = "")
Call `execute_code` with `script_path` set to `unit-converter/scripts/convert.py`, no additional code needed yet,
and `session_id` = "". Save the returned `session_id` for reuse.

### Step 2: Write the conversion call
Pass as `code`: call `convert_units(value, from_unit, to_unit)` and print `Category`, `Input`, and `Result` in the
format shown in `examples.md`.

### Step 3: Return output
Return the printed output as-is.

### Step 4: Reuse session
On follow-up conversions skip Step 1 — pass only `code` + the saved `session_id` (no `script_path` needed since
the script is already loaded in that session).

### Step 5: Error handling
- **Unknown unit / incompatible categories**: report the error message and list the supported units for the
  relevant category from `examples.md`.
- **Invalid number**: ask the user to clarify the value.
- **Expired session**: silently restart from Step 1 with a new session.