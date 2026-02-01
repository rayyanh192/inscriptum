import os
from dotenv import load_dotenv
load_dotenv()

from playwright.sync_api import sync_playwright, Playwright
from browserbase import Browserbase

bb = Browserbase(api_key=os.environ["BROWSERBASE_API_KEY"])

def run(playwright: Playwright):
    session = bb.sessions.create(project_id=os.environ["BROWSERBASE_PROJECT_ID"])
    
    browser = playwright.chromium.connect_over_cdp(session.connect_url)
    context = browser.contexts[0]
    page = context.pages[0]
    
    try:
        # Go to a test form
        page.goto("https://www.google.com")
        
        # Type in the search box
        page.fill('textarea[name="q"]', 'browserbase automation')
        
        # Screenshot before clicking
        page.screenshot(path="before_search.png")
        
        # Press enter to search
        page.keyboard.press("Enter")
        
        # Wait for results to load
        page.wait_for_timeout(2000)
        
        # Screenshot the results
        page.screenshot(path="after_search.png")
        
        print("Done! Check before_search.png and after_search.png")
        
    finally:
        page.close()
        browser.close()
    
    print(f"Replay: https://browserbase.com/sessions/{session.id}")

with sync_playwright() as playwright:
    run(playwright)