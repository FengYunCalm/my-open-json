import os
import tempfile
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ModuleNotFoundError as exc:
    raise SystemExit(
        "This example requires the Python `playwright` package. "
        "Without Playwright, use the webapp-testing skill only for static inspection and selector planning."
    ) from exc

# Example: Automating interaction with static HTML files using file:// URLs

html_file_path = os.path.abspath("path/to/your/file.html")
file_url = f"file://{html_file_path}"
output_dir = Path(tempfile.gettempdir()) / "webapp-testing"
output_dir.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})

    # Navigate to local HTML file
    page.goto(file_url)

    # Take screenshot
    page.screenshot(path=str(output_dir / "static_page.png"), full_page=True)

    # Interact with elements
    page.click("text=Click Me")
    page.fill("#name", "John Doe")
    page.fill("#email", "john@example.com")

    # Submit form
    page.click('button[type="submit"]')
    page.wait_for_timeout(500)

    # Take final screenshot
    page.screenshot(path=str(output_dir / "after_submit.png"), full_page=True)

    browser.close()

print("Static HTML automation completed!")
