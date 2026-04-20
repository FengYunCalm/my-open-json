---
name: webapp-testing
description: Use when the user wants browser-level testing or debugging for a local web application, including Playwright interaction, UI verification, screenshots, and browser logs.
license: Complete terms in LICENSE.txt
---

# Web Application Testing

Use Python Playwright scripts only when Playwright is already available in the current environment. Without Playwright, limit this skill to static HTML inspection, selector planning, server startup help, and non-browser debugging guidance.

**Helper Scripts Available**:
- Use the bundled `scripts/with_server.py` helper from this skill's own directory.
- In this OpenCode checkout, the helper lives at `skills/webapp-testing/scripts/with_server.py` relative to the repo root. If the skill is installed elsewhere, locate that same path inside the skill directory and then call it by absolute path. Do not assume the current working directory is already there.
- Browser automation requires the Python `playwright` package and a working browser install. If either is missing, do not promise screenshots, console capture, or DOM inspection through a browser session.

**Always run scripts with `--help` first** to see usage. DO NOT read the source until you try running the script first and find that a customized solution is abslutely necessary. These scripts can be very large and thus pollute your context window. They exist to be called directly as black-box scripts rather than ingested into your context window.

## Decision Tree: Choosing Your Approach

```
User task -> Need browser-level behavior or rendered DOM?
    |- No -> Read HTML, templates, or frontend source directly
    |      and reason about selectors or event flow without a browser
    |
    `- Yes -> Is Playwright already available here?
        |- No -> Explain the limitation clearly
        |       Use static inspection, selector planning, and server guidance only
        |
        `- Yes -> Is the server already running?
            |- No -> Locate `skills/webapp-testing/scripts/with_server.py`
            |       or the installed equivalent, then run
            |       `python skills/webapp-testing/scripts/with_server.py --help`
            |       Then use the helper + write simplified Playwright script
            |
            `- Yes -> Reconnaissance-then-action:
                1. Navigate and wait for networkidle
                2. Take screenshot or inspect DOM
                3. Identify selectors from rendered state
                4. Execute actions with discovered selectors
```

## Example: Using with_server.py

To start a server, resolve the helper path once, run `--help` first, then use the helper:

**Single server:**
```bash
WITH_SERVER=skills/webapp-testing/scripts/with_server.py

python "$WITH_SERVER" --server "npm run dev" --port 5173 -- python your_automation.py
```

**Multiple servers (e.g., backend + frontend):**
```bash
WITH_SERVER=skills/webapp-testing/scripts/with_server.py

python "$WITH_SERVER" \
  --server "cd backend && python server.py" --port 3000 \
  --server "cd frontend && npm run dev" --port 5173 \
  -- python your_automation.py
```

To create an automation script, include only Playwright logic when Playwright is actually available (servers are managed automatically):
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True) # Always launch chromium in headless mode
    page = browser.new_page()
    page.goto('http://localhost:5173') # Server already running and ready
    page.wait_for_load_state('networkidle') # CRITICAL: Wait for JS to execute
    # ... your automation logic
    browser.close()
```

## Reconnaissance-Then-Action Pattern

1. **Inspect rendered DOM**:
   ```python
   page.screenshot(path='/tmp/inspect.png', full_page=True)
   content = page.content()
   page.locator('button').all()
   ```

2. **Identify selectors** from inspection results

3. **Execute actions** using discovered selectors

## Common Pitfall

❌ **Don't** inspect the DOM before waiting for `networkidle` on dynamic apps
✅ **Do** wait for `page.wait_for_load_state('networkidle')` before inspection

❌ **Don't** promise browser automation in an environment that cannot import `playwright`
✅ **Do** say that browser-level testing is unavailable and fall back to static inspection or server-side diagnosis

## Best Practices

- **Use bundled scripts as black boxes** - To accomplish a task, consider whether one of the scripts available in `scripts/` can help. These scripts handle common, complex workflows reliably without cluttering the context window. Use `--help` to see usage, then invoke directly.
- Prefer a resolved helper path over assuming the current working directory. Absolute paths are safest; the repo-relative path shown above is fine when you are already at the repo root.
- Use `sync_playwright()` for synchronous scripts only when Playwright is already installed and usable.
- Always close the browser when done
- Use descriptive selectors: `text=`, `role=`, CSS selectors, or IDs
- Add appropriate waits: `page.wait_for_selector()` or `page.wait_for_timeout()`

## Reference Files

- **Bundled examples in `examples/`** - Common patterns to consult when Playwright is available:
  - `element_discovery.py` - Discovering buttons, links, and inputs on a page
  - `static_html_automation.py` - Using file:// URLs for local HTML
  - `console_logging.py` - Capturing console logs during automation
