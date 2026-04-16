import sys
import json
import time
import os
from playwright.sync_api import sync_playwright

def scrape_questions(url):
    with sync_playwright() as p:
        # Launch with persistent context to save login state
        browser = p.chromium.launch_persistent_context(
            user_data_dir="./playwright_session",
            headless=False,
            channel="chrome" 
        )
        
        page = browser.pages[0]
        print(f"Navigating to {url}")
        page.goto(url)
        
        print("Please log in to the website if you haven't already.")
        
        # Save incrementally to the subject data directory.
        db_dir = os.path.join("data", "subjects")
        os.makedirs(db_dir, exist_ok=True)
        db_file = os.path.join(db_dir, "affective_computing.json")
        
        if os.path.exists(db_file):
            with open(db_file, "r") as f:
                try:
                    all_data = json.load(f)
                except:
                    all_data = {}
        else:
            all_data = {}

        # Ensure all_data is a dictionary, not a list (cleaning up old format if present)
        if isinstance(all_data, list):
            all_data = {"Legacy Scrape": all_data}

        print("\n" + "="*50)
        print("       INTERACTIVE SCRAPING MODE")
        print("="*50)
        print("1. Open an assessment page in the browser.")
        print("2. Return to this terminal and press ENTER to extract.")
        print("3. Type 'q' and press ENTER when finished.")
        print("="*50 + "\n")

        while True:
            cmd = input("Ready? Press ENTER to extract this assessment (or 'q' to quit): ")
            if cmd.strip().lower() == 'q':
                break
                
            heading = extract_questions_from_page(page, all_data)
            
            # Save incrementally
            with open(db_file, "w") as f:
                json.dump(all_data, f, indent=4)
            print(f"Saved to {db_file}")

        print("\nAll Scraping completed! Browser is closing...")
        browser.close()

def extract_questions_from_page(page, all_data):
    # Try to grab the heading from div.gcb-assessment-contents h1
    heading_loc = page.locator('div.gcb-assessment-contents h1')
    if heading_loc.count() > 0:
        heading = heading_loc.first.inner_text().strip()
    else:
        # Fallback if the element structure is slightly different
        heading = f"Unknown Assessment - {int(time.time())}"
        
    print(f"\nExtracting: '{heading}'")
    
    if heading not in all_data:
        all_data[heading] = []

    questions = page.locator('.qt-mc-question')
    q_count = questions.count()
    if q_count > 0:
        print(f"Found {q_count} questions.")
        for i in range(q_count):
            q_loc = questions.nth(i)
            try:
                # Get question text
                q_text_loc = q_loc.locator('.qt-question')
                q_text = q_text_loc.inner_text().strip() if q_text_loc.count() > 0 else "Unknown Question"
                
                # Get choices
                lbl_loc = q_loc.locator('.qt-choices label')
                c_count = lbl_loc.count()
                choices = []
                for j in range(c_count):
                    choices.append(lbl_loc.nth(j).inner_text().strip())
                
                # Get answer (must be the div, not the h3 header)
                ans_loc = q_loc.locator('div.faculty-answer')
                if ans_loc.count() > 0:
                    ans_text = ans_loc.first.inner_text().strip()
                else:
                    ans_text = "Unknown Answer"
                
                # Clean up "Accepted Answers:" if it's there
                if "Accepted Answers:" in ans_text:
                    ans_text = ans_text.replace("Accepted Answers:", "").strip()
                
                # IMPORTANT: For multiple choice (multiple selections), answers are often separated by \n
                # We save the answers as an array of strings to accurately reflect multiple options
                ans_list = [a.strip() for a in ans_text.split('\n') if a.strip()]

                all_data[heading].append({
                    "question": q_text,
                    "choices": choices,
                    "answer": ans_list # Now saved as a list
                })
            except Exception as e:
                print(f"Error parsing question {i}: {e}")
                
        # Deduplicate strictly within this heading
        unique_q = {}
        for q in all_data[heading]:
            unique_q[q['question']] = q
        all_data[heading] = list(unique_q.values())
        print(f"Unique questions saved for '{heading}': {len(all_data[heading])}")
        
    else:
        print("No .qt-mc-question classes found on this visible page.")
        
    return heading

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scraper.py <url>")
        sys.exit(1)
    
    target_url = sys.argv[1]
    scrape_questions(target_url)
