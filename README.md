# Local Browser Automation

Run repeatable browser workflows from JSON with Python Playwright. Once an agent writes the workflow, each execution runs locally without LLM API calls.

## Setup

From this folder in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_automation.py --demo --channel msedge
```

Use `--channel chrome` for installed Chrome or run `python -m playwright install chromium` from the virtual environment and omit the channel. Add `--headless` for background execution. On macOS and Linux use `./.venv/bin/python`.

## Workflows

Copy [workflow.example.json](workflow.example.json), edit its ordered steps, and pass the file with `--config workflow.example.json`.

| Action | Required fields |
| --- | --- |
| `goto` | `url` |
| `fill` | `selectors` and text `value` |
| `upload` | `selectors` for a file input and a local file `path`, relative to the config or absolute |
| `click` | `selectors` |
| `wait` | `selectors` for a visible completion indicator |

Each selector has `by` and `value`. Use `label`, `text`, `test_id`, `css`, or `role`. A role also needs a `name`, such as `{"by":"role","value":"button","name":"Preview"}`. Selectors are tried in order and must match one element. The top-level `timeout_ms` defaults to 10000.

For authenticated workflows, run `run_automation.py --login URL --channel msedge` with the virtual environment's Python, complete sign-in, and press Enter in the terminal. Use the same channel on subsequent runs. The runner keeps its own persistent `user_data/` profile. Sites can expire sessions, and the Codex browser pane uses a separate profile.

The runner retries transient navigation failures, dismisses JavaScript dialogs, and closes popups. Handle known HTML modals with configured steps. It writes JSON Lines to `automation.log` with run IDs, step counts, durations, and error types. A failed run exits nonzero. Inspect the destination before rerunning a workflow that reached a submit click.

## Agent skill

Install this folder according to your agent's skill-directory convention, or point the agent at [SKILL.md](SKILL.md). Keep the runner and example config beside it.

## Push from a secondary GitHub account

Use `gh auth login --hostname github.com --web` and sign in with the secondary account. If both accounts are already configured, use `gh auth switch --hostname github.com --user SECONDARY_USER`. Check `gh api user --jq .login` before pushing. Run `gh auth setup-git` to configure GitHub CLI as Git's credential helper.

For an empty remote repository, run the following in the project folder. Substitute the secondary account's GitHub noreply address from **Settings > Emails** and the repository's HTTPS clone URL.

```powershell
git init -b main
git config --local user.name SECONDARY_USER
git config --local user.email SECONDARY_NOREPLY_EMAIL
git add -- .gitignore README.md SKILL.md requirements.txt run_automation.py workflow.example.json
git diff --cached --stat
git commit -m "Add local browser automation skill"
git remote add origin https://github.com/SECONDARY_USER/REPOSITORY.git
git push -u origin main
```

For a repository with existing commits, clone it first and add the project files to the clone. Commit identity comes from Git configuration. Push authorization comes from the signed-in account. Keep browser profiles, private workflow inputs, and logs out of Git.
