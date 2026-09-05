import json
import random
import re
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

from database import init_db, insert_fares
from index_calc import compute_index
from parser import parse_easemytrip

# ---- config: your route basket & advance-purchase windows ----
ROUTES = [
    ("DEL", "BOM"),
    ("DEL", "BLR"),
    # ("BOM", "BLR"),
    # ("DEL", "CCU"),
    # ("BLR", "HYD"),
    ("MAA", "DEL"),
]
ADVANCE_WINDOWS = [1, 7, 15, 30, 45]  # days ahead

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

IGNORE_SUBSTRINGS = [
    "moengage",
    "GetCoupons",
    "CheckSignIn",
    "UMS",
    "PSP",
    "google.com",
    "FareCalendarByDate",
    "flight-campaign",
    "FillCalendarDataByMonth",
]


def sanitize_filename(name: str) -> str:
    clean = re.sub(r"[^\w\-_.]", "_", name)
    return clean[:50]


def build_url(origin: str, dest: str, travel_date: str) -> str:
    return (
        f"https://www.easemytrip.com/flight-search/listing?"
        f"srch={origin}-{origin}-India%7C{dest}-{dest}-India%7C{travel_date}"
        f"&px=1-0-0&cbn=0&ar=undefined&isow=true&isdm=true&lang=en-us"
        f"&IsDoubleSeat=false&CCODE=IN&curr=INR&apptype=B2C"
    )


def make_response_handler(origin, dest, travel_date, scrape_ts):
    """Closure so each page navigation tags saved files with route/date/scrape time."""
    safe_date = travel_date.replace("/", "-")  # avoid path-separator bug in filenames

    def handle_response(response):
        if any(s in response.url for s in IGNORE_SUBSTRINGS):
            return  # skip known noise: coupons, session tokens, analytics SDKs

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                data = response.json()
                endpoint_name = response.url.split("?")[0].split("/")[-1] or "data"
                endpoint_clean = sanitize_filename(endpoint_name)
                filename = RAW_DIR / (
                    f"{origin}_{dest}_{safe_date}_{endpoint_clean}_{scrape_ts}.json"
                )
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"  [saved] {filename.name}")
            except Exception as e:
                print(f"  [skip] could not parse response from {response.url}: {e}")

    return handle_response


def scrape_route(playwright, origin: str, dest: str, travel_date: str):
    browser = playwright.firefox.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0"
    )
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)

    page = context.new_page()
    scrape_ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    page.on("response", make_response_handler(origin, dest, travel_date, scrape_ts))

    url = build_url(origin, dest, travel_date)
    print(f"Scraping {origin}->{dest} for {travel_date} ...")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(10000)
    except Exception as e:
        print(f"  [error] navigation failed: {e}")
    finally:
        browser.close()

    # --- NEW: find the AirBus_New file just saved, parse it, store it ---
    safe_date = travel_date.replace("/", "-")
    pattern = f"{origin}_{dest}_{safe_date}_AirBus_New_{scrape_ts}.json"
    matches = list(RAW_DIR.glob(pattern))
    if matches:
        with open(matches[0], encoding="utf-8") as f:
            raw = json.load(f)
        advance_days = (
            datetime.strptime(travel_date, "%d/%m/%Y") - datetime.now()
        ).days
        scrape_date_str = datetime.now().strftime("%Y-%m-%d")
        records = parse_easemytrip(
            raw, origin, dest, travel_date, advance_days, scrape_date_str
        )
        if records:
            insert_fares(records)
            print(f"  [db] inserted {len(records)} fare records")
        else:
            print("  [db] no records parsed (empty 'm' field?)")
    else:
        print(f"  [warn] no AirBus_New file found for {origin}->{dest} {travel_date}")


def main():
    init_db()

    # clear out old raw files so each run starts fresh
    if RAW_DIR.exists():
        shutil.rmtree(RAW_DIR)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        for origin, dest in ROUTES:
            for days_ahead in ADVANCE_WINDOWS:
                travel_date = (datetime.now() + timedelta(days=days_ahead)).strftime(
                    "%d/%m/%Y"
                )
                scrape_route(p, origin, dest, travel_date)
                time.sleep(random.uniform(3, 7))

    # --- NEW: Compute the index immediately after scraping ---
    # Set your permanent base date (the first day you gathered complete data)
    BASE_DATE = "2026-09-05"

    # Get today's date dynamically for the current scrape
    CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")

    print(f"\nComputing index for {CURRENT_DATE} against base {BASE_DATE}...")
    index_result = compute_index(current_date=CURRENT_DATE, base_date=BASE_DATE)

    # Save the output to a JSON file
    output_file = f"daily_index_{CURRENT_DATE}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(index_result, f, indent=2, default=str)

    print(f"Index successfully calculated and saved to {output_file}")


if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
