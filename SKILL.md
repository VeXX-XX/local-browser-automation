---
name: local-browser-automation
description: Execute repeatable browser workflows locally using JSON and Python Playwright. Use for known sequences of navigation, form entry, file uploads, and completion checks.
---

# Local browser automation

Read [README.md](README.md) for setup and the workflow schema. Prefer unique role or label selectors and finish with a wait that proves the requested result. Run the demo on a new installation. If authentication is required, use the runner's dedicated sign-in profile.

Report the exit status and check the matching run ID in the JSON Lines log. If a run fails after a submission, inspect the site's state before replaying it.
