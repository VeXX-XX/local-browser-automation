"""Run a JSON-defined Playwright workflow or a local smoke test."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from playwright.sync_api import Dialog, Error, Locator, Page, TimeoutError, sync_playwright


ROOT = Path(__file__).resolve().parent
DEMO_HTML = b"""<!doctype html><title>Automation test</title>
<label>Caption <input id="caption"></label>
<button onclick="result.textContent = caption.value; localStorage.setItem('checked', 'yes')">Preview</button>
<div id="result"></div><div id="session"></div>
<script>session.textContent = localStorage.getItem('checked') ? 'Profile restored' : 'New profile';</script>"""


class DemoHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(DEMO_HTML)

    def log_message(self, format: str, *args: Any) -> None:
        pass


def log(run_id: str, event: str, **fields: Any) -> None:
    record = {"time": datetime.now(timezone.utc).isoformat(), "run_id": run_id,
              "event": event, **fields}
    with (ROOT / "automation.log").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record) + "\n")


def locator_for(page: Page, selector: dict[str, str]) -> Locator:
    by = selector["by"]
    value = selector["value"]
    if by == "role":
        return page.get_by_role(value, name=selector["name"], exact=True)
    if by == "label":
        return page.get_by_label(value, exact=True)
    if by == "text":
        return page.get_by_text(value, exact=True)
    if by == "test_id":
        return page.get_by_test_id(value)
    if by == "css":
        return page.locator(value)
    raise ValueError(f"Unknown selector type: {by}")


def find_target(page: Page, selectors: list[dict[str, str]], timeout: int, action: str) -> Locator:
    if not selectors:
        raise ValueError("A step requires at least one selector")
    for selector in selectors:
        target = locator_for(page, selector)
        try:
            target.wait_for(state="attached" if action == "upload" else "visible", timeout=timeout / len(selectors))
            return target
        except TimeoutError:
            continue
    raise TimeoutError("No configured selector reached the required state")


def navigate(page: Page, url: str, timeout: int, run_id: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username:
        raise ValueError("Navigation requires an HTTP(S) URL without embedded credentials")
    for attempt in range(1, 4):
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        except Error:
            if attempt == 3:
                raise
        else:
            if response is None or response.status < 400:
                return
            if response.status not in {408, 500, 502, 503, 504} or attempt == 3:
                raise RuntimeError(f"Navigation failed with HTTP {response.status}")
        log(run_id, "navigation_retry", attempt=attempt)
        time.sleep(2 ** (attempt - 1))


def run(config: dict[str, Any], base: Path, profile: Path, headless: bool, channel: str | None) -> None:
    timeout = config.get("timeout_ms", 10000)
    steps = config["steps"]
    if type(timeout) is not int or timeout < 1 or not isinstance(steps, list) or not steps:
        raise ValueError("Provide a positive timeout and a nonempty steps array")
    run_id = uuid4().hex
    started = time.monotonic()
    completed = 0
    stats = {"popups_closed": 0, "dialogs_dismissed": 0}
    status = "failed"
    log(run_id, "run_started", steps=len(steps))
    try:
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(profile, headless=headless, channel=channel)
            try:
                page = context.pages[0] if context.pages else context.new_page()

                def close_popup(popup: Page) -> None:
                    popup.close()
                    stats["popups_closed"] += 1

                def dismiss_dialog(dialog: Dialog) -> None:
                    dialog.dismiss()
                    stats["dialogs_dismissed"] += 1

                page.on("popup", close_popup)
                context.on("dialog", dismiss_dialog)
                for step in steps:
                    action = step["action"]
                    if action == "goto":
                        navigate(page, step["url"], timeout, run_id)
                    elif action in {"click", "fill", "upload", "wait"}:
                        locator = find_target(page, step["selectors"], timeout, action)
                        if action == "click":
                            locator.click(timeout=timeout)
                        elif action == "fill":
                            locator.fill(step["value"], timeout=timeout)
                        elif action == "upload":
                            path = (base / step["path"]).resolve(strict=True)
                            if not path.is_file():
                                raise ValueError("Upload path must point to a file")
                            locator.set_input_files(path, timeout=timeout)
                    else:
                        raise ValueError(f"Unknown action: {action}")
                    completed += 1
                    log(run_id, "step_completed", step=completed, action=action)
            finally:
                context.close()
        status = "completed"
    except Exception as error:
        # Browser exceptions may contain form values, URLs and filenames.
        log(run_id, "run_error", step=min(completed + 1, len(steps)),
            error_type=type(error).__name__)
        raise RuntimeError(
            f"{type(error).__name__} after {completed}/{len(steps)} steps "
            f"(run {run_id}). See automation.log."
        ) from None
    finally:
        log(run_id, "run_finished", status=status, completed_steps=completed,
            duration_ms=round((time.monotonic() - started) * 1000), **stats)
    print(f"Completed {completed} steps (run {run_id}).")


def demo(headless: bool, channel: str | None) -> None:
    with ThreadingHTTPServer(("127.0.0.1", 18761), DemoHandler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            steps = [
                {"action": "goto", "url": "http://127.0.0.1:18761"},
                {"action": "fill", "value": "Local preview ready", "selectors": [
                    {"by": "label", "value": "Old caption label"},
                    {"by": "css", "value": "#caption"},
                ]},
                {"action": "click", "selectors": [
                    {"by": "role", "value": "button", "name": "Preview"},
                ]},
                {"action": "wait", "selectors": [
                    {"by": "text", "value": "Local preview ready"},
                ]},
            ]
            profile = ROOT / "demo_profile"
            run({"steps": steps, "timeout_ms": 3000}, ROOT, profile, headless, channel)
            run({"steps": [steps[0], {"action": "wait", "selectors": [
                {"by": "text", "value": "Profile restored"},
            ]}]}, ROOT, profile, headless, channel)
        finally:
            server.shutdown()
            thread.join()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--config", type=Path, help="JSON workflow path")
    source.add_argument("--demo", action="store_true", help="Run a local persistence test")
    source.add_argument("--login", metavar="URL", help="Open the workflow profile for manual sign-in")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--channel", choices=["chrome", "msedge"], help="Use an installed browser")
    args = parser.parse_args()
    try:
        if args.demo:
            demo(args.headless, args.channel)
        elif args.login:
            if args.headless:
                parser.error("--login requires a visible browser")
            with sync_playwright() as playwright:
                context = playwright.chromium.launch_persistent_context(ROOT / "user_data", headless=False, channel=args.channel)
                try:
                    page = context.pages[0] if context.pages else context.new_page()
                    navigate(page, args.login, 15000, uuid4().hex)
                    input("Finish signing in in Chromium, then press Enter here to save the profile. ")
                finally:
                    context.close()
        else:
            config = args.config.resolve()
            run(json.loads(config.read_text(encoding="utf-8")), config.parent,
                ROOT / "user_data", args.headless, args.channel)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, EOFError) as error:
        parser.exit(1, f"{error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
