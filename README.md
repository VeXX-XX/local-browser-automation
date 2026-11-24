# Local Browser Automation

Run repetitive browser tasks from a JSON file. The Python runner opens pages, fills forms, clicks buttons, and uploads local files. It can reuse a saved sign-in and logs each run.

## Why use this skill?

Give an AI agent a workflow to configure once, then rerun it from your terminal without asking the agent to drive the browser step by step. This is useful for tasks you repeat, such as filling the same form or uploading files through the same page.

**100% less direct AI model usage during replay** when the alternative uses an AI model to drive the same browser steps. The standalone runner makes **zero AI model calls**. I verified the demo in Edge, including the selector fallback and saved profile. Setup, workflow design, and debugging with an AI agent can still consume credits. Overall savings depend on your baseline, how often you rerun the workflow, and how your plan counts usage.

## Quick setup

From the repository folder in PowerShell, with Python and Microsoft Edge installed:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_automation.py --demo --channel msedge --headless
```

Use `--channel chrome` for installed Chrome. To use Playwright Chromium, run `.\.venv\Scripts\python.exe -m playwright install chromium` and omit `--channel`. On macOS or Linux, use `./.venv/bin/python`.

## Run your workflow

Copy [workflow.example.json](workflow.example.json) and replace the URL and steps. Use `goto` with a `url`, `click` or `wait` with `selectors`, `fill` with `selectors` and a `value`, or `upload` with `selectors` and a local `path`. A selector needs `by` and `value`, for example `{"by":"label","value":"Email"}`. Role selectors also take a `name`. Use a final `wait` to confirm the result.

```powershell
.\.venv\Scripts\python.exe run_automation.py --config workflow.example.json --channel msedge
```

If the site requires sign-in, run the same script with `--login URL --channel msedge`, sign in in the opened window, and press Enter in the terminal. Later runs reuse the profile while the site keeps the session valid. Check `automation.log` for results.

For agent use, point your agent at [SKILL.md](SKILL.md). The skill helps configure and run the workflow. Python handles the browser actions during replay.
