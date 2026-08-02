"""Clean-browser smoke test for the static decision workspace.

Run through the webapp-testing helper so the helper owns the local server:

python3 /Users/amlfarhad/.agents/skills/webapp-testing/scripts/with_server.py \
  --server "python3 -m http.server 4176 --directory app" --port 4176 \
  -- .venv/bin/python tests/browser_smoke.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:4176")
CHROME_PATH = os.environ.get("CHROME_PATH")


def main() -> None:
    screenshot_dir = Path(os.environ.get("BROWSER_ARTIFACT_DIR", "/tmp/customer-health-browser"))
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    results: dict[str, object] = {}

    with sync_playwright() as playwright:
        launch_options = {"headless": True}
        if CHROME_PATH:
            launch_options["executable_path"] = CHROME_PATH
        browser = playwright.chromium.launch(**launch_options)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("console", lambda message: errors.append("console: " + message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: errors.append("pageerror: " + str(error)))
        page.goto(BASE_URL, wait_until="networkidle")
        page.screenshot(path=str(screenshot_dir / "desktop-overview.png"), full_page=True)

        assert page.get_by_role("heading", name="Make the next customer-health decision visible.").is_visible()
        initial_rows = page.locator("tbody#queue-body tr.queue-row").count()
        assert initial_rows == 30
        results["initial_queue_rows"] = initial_rows

        page.get_by_role("button", name="Show next 30").click()
        assert page.locator("tbody#queue-body tr.queue-row").count() == 60
        results["expanded_queue_rows"] = 60

        with page.expect_download() as queue_download_info:
            page.get_by_role("button", name="Export queue").click()
        queue_download = queue_download_info.value
        queue_path = screenshot_dir / "customer-health-queue.csv"
        queue_download.save_as(str(queue_path))
        assert len(queue_path.read_text().splitlines()) > 400
        results["queue_export"] = queue_download.suggested_filename

        page.locator("#queue-risk").select_option("high")
        high_rows = page.locator("tbody#queue-body tr.queue-row").count()
        assert high_rows > 0
        results["high_risk_rows"] = high_rows
        page.get_by_role("button", name="Clear filters").click()

        page.locator("#queue-search").fill("10388")
        assert page.locator("tbody#queue-body tr.queue-row").count() == 1
        page.get_by_role("button", name="Clear filters").click()
        page.locator("#queue-sort").select_option("revenue")
        page.wait_for_function("document.querySelectorAll('tbody#queue-body tr.queue-row td.number').length >= 2")
        revenues = page.locator("tbody#queue-body tr.queue-row td.number").all_text_contents()
        assert len(revenues) >= 2
        assert float(revenues[0].replace("$", "").replace(",", "")) >= float(revenues[1].replace("$", "").replace(",", ""))
        page.get_by_role("button", name="Clear filters").click()

        first_row = page.locator("tbody#queue-body tr.queue-row").first
        account_id = first_row.get_attribute("data-account-id")
        assert account_id
        first_row.click()
        page.wait_for_load_state("networkidle")
        assert page.get_by_role("heading", name="Observed facts").is_visible()
        assert page.get_by_role("heading", name="Why this account is in view").is_visible()
        results["account_id"] = account_id

        page.locator("#action-select").select_option(label="Follow up on support load")
        page.get_by_role("button", name="Save action").click()
        assert page.get_by_role("status").filter(has_text="Saved locally").is_visible()

        page.get_by_role("button", name="Back to queue").click()
        page.locator('tr.queue-row[data-account-id="' + account_id + '"]').click()
        assert page.locator("#action-select").input_value() == "Follow up on support load"
        page.reload(wait_until="networkidle")
        assert page.locator("#action-select").input_value() == "Follow up on support load"
        assert page.get_by_text("Model-derived signals: none in this demo pipeline.").is_visible()
        page.screenshot(path=str(screenshot_dir / "account-detail.png"), full_page=True)
        results["action_persists_after_reload"] = True

        with page.expect_download() as download_info:
            page.get_by_role("button", name="Export brief").click()
        download = download_info.value
        download.save_as(str(screenshot_dir / "account-brief.txt"))
        assert Path(screenshot_dir / "account-brief.txt").exists()
        results["account_export"] = download.suggested_filename

        page.get_by_role("button", name="Back to queue").click()
        page.get_by_role("link", name="Definitions & lineage").click()
        page.wait_for_load_state("networkidle")
        assert page.get_by_role("heading", name="Definitions with boundaries").is_visible()
        assert page.locator(".quality-row").count() == 10
        page.screenshot(path=str(screenshot_dir / "definitions.png"), full_page=True)
        unnamed_buttons = page.locator("button").evaluate_all(
            "buttons => buttons.filter(button => !(button.innerText || button.getAttribute('aria-label') || '').trim()).length"
        )
        assert unnamed_buttons == 0
        results["quality_checks"] = page.locator(".quality-row").count()
        results["accessible_button_names"] = True

        broken_page = browser.new_page()
        broken_page.route(
            "**/data/workspace.json",
            lambda route: route.fulfill(status=200, content_type="application/json", body="{}"),
        )
        broken_page.goto(BASE_URL, wait_until="networkidle")
        assert broken_page.get_by_role("heading", name="We couldn’t load the generated data.").is_visible()
        results["broken_data_state"] = True
        broken_page.close()

        mobile_page = browser.new_page(viewport={"width": 390, "height": 844})
        mobile_page.goto(BASE_URL, wait_until="networkidle")
        mobile_page.screenshot(path=str(screenshot_dir / "mobile-overview.png"), full_page=True)
        no_horizontal_overflow = mobile_page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
        assert no_horizontal_overflow
        results["mobile_no_horizontal_overflow"] = bool(no_horizontal_overflow)
        mobile_page.close()
        page.close()
        browser.close()

    if errors:
        raise AssertionError("Browser console errors: " + json.dumps(errors))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
