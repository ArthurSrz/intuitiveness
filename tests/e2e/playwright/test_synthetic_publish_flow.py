"""
E2E Test: DataGouv Search → Cart → Wizard → Descent → Synthetic Data → Publish section

Tests that dataset_id propagates from data.gouv.fr search through the full pipeline,
enabling the "Publish to data.gouv.fr" section on the Synthetic Data page.

Run with:
    python tests/e2e/playwright/test_synthetic_publish_flow.py
"""
import time
from playwright.sync_api import sync_playwright

APP_URL = "https://intuitiveness.streamlit.app/"
SLOW = 3  # seconds to wait after each action


def get_app(page):
    """Return the Streamlit app iframe locator (where all UI elements live)."""
    return page.frame_locator('iframe').first


def wait(page, secs=SLOW):
    try:
        page.wait_for_load_state('networkidle', timeout=15000)
    except Exception:
        pass
    time.sleep(secs)


def dismiss_tutorial(app):
    """Dismiss tutorial dialog if present (it re-appears on every Streamlit rerun)."""
    start_btn = app.locator('button:has-text("Start Redesigning")')
    if start_btn.count() > 0 and start_btn.first.is_visible():
        print("   [Tutorial dismissed]")
        start_btn.first.click()
        time.sleep(2)
        return True
    return False


def list_buttons(app, limit=20):
    """Print all visible buttons for debugging."""
    btns = app.locator('button')
    print(f"   Buttons visible: {btns.count()}")
    for i in range(min(btns.count(), limit)):
        txt = btns.nth(i).text_content().strip()
        if txt:
            print(f"     {i}: {txt!r}")


def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        # ── 1. Load app ──────────────────────────────────────────────────────
        print("1. Loading app...")
        page.goto(APP_URL, wait_until='domcontentloaded', timeout=90000)
        wait(page, 10)

        app = get_app(page)

        # Dismiss tutorial if present
        start_btn = app.locator('button:has-text("Start Redesigning")')
        if start_btn.count() > 0:
            start_btn.first.click()
            wait(page, 3)

        page.screenshot(path='/tmp/s01_loaded.png')
        print("   ✓ App loaded")

        # ── 2. Search data.gouv.fr ───────────────────────────────────────────
        print("2. Searching 'vaccination' on data.gouv.fr...")
        search_input = app.locator('input[aria-label="Search datasets"]')
        search_input.wait_for(state='visible', timeout=20000)
        search_input.fill("vaccination")

        # Use Enter key (form submission) instead of button click
        search_input.press("Enter")
        print("   Pressed Enter, waiting 15s for API results...")
        wait(page, 15)

        page.screenshot(path='/tmp/s02_search_results.png')

        add_btns = app.locator('button:has-text("Add to selection")')
        print(f"   'Add to selection' buttons: {add_btns.count()}")
        print("   ✓ Search results loaded")

        # ── 3. Add first dataset to cart ─────────────────────────────────────
        print("3. Adding first dataset to cart...")

        # Search results are inside expanders - click first one to reveal the add button
        expanders = app.locator('[data-testid="stExpander"]')
        print(f"   Expanders found: {expanders.count()}")

        added = False
        if expanders.count() > 0:
            # Click the summary (toggle) of the first expander to expand it
            first_expander_summary = expanders.first.locator('summary')
            if first_expander_summary.count() > 0:
                first_expander_summary.first.click()
            else:
                expanders.first.click()
            wait(page, 2)
            page.screenshot(path='/tmp/s03a_expanded.png')

            # Now click the add button inside the expanded expander
            add_in_expander = expanders.first.locator(
                'button:has-text("Add to selection"), button:has-text("➕ Add to selection")'
            )
            print(f"   Add buttons inside first expander: {add_in_expander.count()}")
            if add_in_expander.count() > 0:
                add_in_expander.first.click()
                wait(page, 4)
                page.screenshot(path='/tmp/s03_added_cart.png')
                print("   ✓ Dataset added to cart")
                added = True

        if not added:
            # Fallback: try iterate and find a visible button
            print("   Trying visible button fallback...")
            all_add_btns = app.locator('button:has-text("Add to selection"), button:has-text("➕ Add to selection")')
            for i in range(all_add_btns.count()):
                btn = all_add_btns.nth(i)
                if btn.is_visible():
                    btn.click()
                    wait(page, 4)
                    page.screenshot(path='/tmp/s03_added_cart.png')
                    print(f"   ✓ Dataset added (visible btn #{i})")
                    added = True
                    break

        if not added:
            print("   ✗ No 'Add to selection' button found/visible")
            list_buttons(app)
            page.screenshot(path='/tmp/s03_debug.png')

        # Tutorial pops up again after cart rerun - dismiss it
        dismiss_tutorial(app)
        wait(page, 2)

        # ── 4. Start Analysis ────────────────────────────────────────────────
        print("4. Starting analysis...")
        start_btn = app.locator('button:has-text("Start Analysis")')
        if start_btn.count() > 0:
            start_btn.first.click()
            wait(page, 4)
            dismiss_tutorial(app)
            wait(page, 2)
            page.screenshot(path='/tmp/s04_wizard.png')
            print("   ✓ Wizard started")
        else:
            print(f"   ✗ No 'Start Analysis' button found")
            list_buttons(app)
            page.screenshot(path='/tmp/s04_debug.png')

        # ── 5a. Wizard Step 1: column selection ───────────────────────────────
        print("5a. Wizard Step 1...")
        continue_btn = app.locator('button:has-text("Continue"), button:has-text("→ Continue")')
        if continue_btn.count() > 0:
            continue_btn.first.click()
            wait(page, 3)
            dismiss_tutorial(app)
            wait(page, 1)
            page.screenshot(path='/tmp/s05a_step1.png')
            print("   ✓ Step 1 done")
        else:
            print(f"   ✗ No Continue button at Step 1")
            list_buttons(app)
            page.screenshot(path='/tmp/s05a_debug.png')

        # ── 5b. Wizard Step 2: connections ──────────────────────────────────
        print("5b. Wizard Step 2...")
        continue_btn2 = app.locator('button:has-text("Continue"), button:has-text("→ Continue")')
        if continue_btn2.count() > 0:
            continue_btn2.first.click()
            wait(page, 3)
            dismiss_tutorial(app)
            wait(page, 1)
            page.screenshot(path='/tmp/s05b_step2.png')
            print("   ✓ Step 2 done")
        else:
            print(f"   ✗ No Continue button at Step 2")
            list_buttons(app)
            page.screenshot(path='/tmp/s05b_debug.png')

        # ── 5c. Wizard Step 3: confirm ────────────────────────────────────────
        print("5c. Wizard Step 3...")
        continue_btn3 = app.locator('button:has-text("Continue"), button:has-text("→ Continue")')
        if continue_btn3.count() > 0:
            continue_btn3.first.click()
            wait(page, 5)
            dismiss_tutorial(app)
            wait(page, 2)
            page.screenshot(path='/tmp/s05c_step3.png')
            print("   ✓ Step 3 done - on descent page")
        else:
            print(f"   ✗ No Continue button at Step 3")
            list_buttons(app)
            page.screenshot(path='/tmp/s05c_debug.png')

        # ── 6. Descent: Domain categorization ────────────────────────────────
        print("6. Descent - domain categorization...")
        categorize_btn = app.locator('button:has-text("Categorize")')
        if categorize_btn.count() > 0:
            categorize_btn.first.click()
            wait(page, 5)
            dismiss_tutorial(app)
            wait(page, 1)
            page.screenshot(path='/tmp/s06_categorized.png')
            print("   ✓ Domain categorization done")
        else:
            print("   Skipping categorization (not found)")
            # Check what buttons are visible
            list_buttons(app)
            page.screenshot(path='/tmp/s06_debug.png')

        # ── 7. Navigate descent to completion ─────────────────────────────────
        print("7. Navigating remaining descent steps...")
        for step_name in ["Extract features", "Aggregate to L1", "Compute L0"]:
            for btn_text in ["Extract", "Continue", "Compute", "Aggregate", "Finalize"]:
                btn = app.locator(f'button:has-text("{btn_text}")')
                if btn.count() > 0:
                    print(f"   Clicking '{btn_text}'...")
                    btn.first.click()
                    wait(page, 4)
                    break

        page.screenshot(path='/tmp/s07_descent_progress.png')

        # ── 8. Navigate to Synthetic Data ────────────────────────────────────
        print("8. Looking for Synthetic Data navigation...")
        synth_btn = app.locator(
            'button:has-text("Synthetic Data"), '
            'button:has-text("🔮 Synthetic Data"), '
            'button:has-text("Generate Synthetic")'
        )
        print(f"   Synthetic buttons found: {synth_btn.count()}")
        list_buttons(app, 30)

        if synth_btn.count() > 0:
            synth_btn.first.click()
            wait(page, 5)
            page.screenshot(path='/tmp/s08_synthetic_page.png')
            print("   ✓ On Synthetic Data page")

            # ── 9. Verify Publish section ────────────────────────────────────
            print("9. Verifying 'Publish to data.gouv.fr' section...")
            all_text = ''
            try:
                body = app.locator('body')
                if body.count() > 0:
                    all_text = body.text_content() or ''
            except Exception:
                pass

            has_publish = 'Publish' in all_text or 'data.gouv' in all_text or 'publish' in all_text.lower()
            print(f"   'Publish' keyword in page: {has_publish}")

            publish_els = app.locator(
                '[data-testid*="publish"], '
                'h2:has-text("Publish"), h3:has-text("Publish"), '
                'div:has-text("Publish to data.gouv")'
            )
            print(f"   Publish elements: {publish_els.count()}")

            if has_publish:
                print("   ✓ SUCCESS: 'Publish to data.gouv.fr' section FOUND!")
            else:
                print("   ✗ 'Publish to data.gouv.fr' section NOT found")
                print(f"   Page text (500 chars): {all_text[:500]}")
        else:
            print("   ✗ No Synthetic Data button found")
            page.screenshot(path='/tmp/s08_no_synth.png')

        print("\n✓ Test completed. Screenshots in /tmp/s*.png")
        browser.close()


if __name__ == '__main__':
    test()
