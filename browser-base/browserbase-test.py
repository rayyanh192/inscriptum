import os
from playwright.sync_api import sync_playwright, Playwright
from browserbase import Browserbase
from dotenv import load_dotenv
load_dotenv()

bb = Browserbase(api_key=os.environ["BROWSERBASE_API_KEY"])

def run(playwright: Playwright):
    # Create a session on Browserbase
    session = bb.sessions.create(project_id=os.environ["BROWSERBASE_PROJECT_ID"])
    
    # Connect to the remote session
    browser = playwright.chromium.connect_over_cdp(session.connect_url)
    context = browser.contexts[0]
    page = context.pages[0]
    
    try:
        page.goto("https://www.google.com")
        page.screenshot(path="screenshot.png")
        print(f"Screenshot saved!")
    finally:
        page.close()
        browser.close()
    
    print(f"View replay at https://browserbase.com/sessions/{session.id}")

with sync_playwright() as playwright:
    run(playwright)