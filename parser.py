import json

CARRIER_NAMES = {
    "6E": "IndiGo", "IX": "Air India Express", "QP": "AkasaAir",
    "AI": "Air India", "SG": "SpiceJet",
}


def extract_carrier_code(option: dict, valid_codes: set) -> str | None:
    """Carrier code is embedded inside the backtick-delimited BkKY string.
    Its position shifts depending on segment/baggage details, so we match
    against known valid codes (from the file's own 'm' summary) instead
    of relying on a fixed index."""
    try:
        bkky_str = option["b"][0]["BkKY"][0]
        for part in bkky_str.split("`"):
            if part in valid_codes:
                return part
    except (KeyError, IndexError):
        pass
    return None


def is_nonstop(option: dict) -> bool:
    """SD field looks like 'Non-Stop|6529|9|DEL-BOM||' or '1-Stop|...'."""
    sd = option.get("SD", "")
    return sd.startswith("Non-Stop")


def remove_outliers(records: list[dict], z_thresh: float = 2.5) -> list[dict]:
    """Drop fares that are statistical outliers within this batch
    (per requirement: ignore extreme outlier fares)."""
    fares = [r["total_fare"] for r in records if r["total_fare"] is not None]
    if len(fares) < 3:
        return records  # not enough data to judge outliers safely

    mean = sum(fares) / len(fares)
    variance = sum((f - mean) ** 2 for f in fares) / len(fares)
    std = variance ** 0.5 or 1  # avoid divide-by-zero if all fares identical

    return [
        r for r in records
        if r["total_fare"] is not None
        and abs((r["total_fare"] - mean) / std) <= z_thresh
    ]


def parse_easemytrip(raw_json: dict, origin: str, dest: str,
                      travel_date: str, advance_days: int,
                      scrape_date: str, source: str = "EaseMyTrip") -> list[dict]:
    """Extract non-stop flight fares with base fare / tax breakdown,
    filtered for outliers."""
    valid_codes = set(raw_json.get("m", {}).keys())
    options = raw_json.get("j", [{}])[0].get("s", [])

    records = []
    for option in options:
        if not is_nonstop(option):          # requirement 2: non-stop only
            continue

        carrier_code = extract_carrier_code(option, valid_codes)
        if not carrier_code:
            continue

        for fare_brand in option.get("lstFr", []):
            base_fare = fare_brand.get("BF")
            total_fare = fare_brand.get("TF")
            if base_fare is None or total_fare is None:
                continue

            taxes = round(total_fare - base_fare, 2)  # requirement 1: separate base & tax

            records.append({
                "origin": origin,
                "dest": dest,
                "carrier_code": carrier_code,
                "carrier_name": CARRIER_NAMES.get(carrier_code, carrier_code),
                "scrape_date": scrape_date,
                "travel_date": travel_date,
                "advance_days": advance_days,
                "fare_class": fare_brand.get("FN"),
                "base_fare": base_fare,
                "taxes": taxes,
                "total_fare": total_fare,
                "stops": 0,
                "source": source,
            })

    return remove_outliers(records)          # requirement 3: drop outlier fares


#if __name__ == "__main__":
#   with open("data/raw/DEL_BOM_05-09-2026_AirBus_New_20260904T202424.json") as f:
#        raw = json.load(f)
#    recs = parse_easemytrip(raw, "DEL", "BOM", "05/09/2026", 1, "2026-09-04")
#    print(f"{len(recs)} non-stop fare records after outlier removal")
#    for r in recs[:10]:
#        print(r)

if __name__ == "__main__":
    from pathlib import Path

    raw_dir = Path("data/raw")
    airbus_files = sorted(
        raw_dir.glob("*_AirBus_New_*.json"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    if not airbus_files:
        print("No AirBus_New files found in data/raw/")
    else:
        latest_file = airbus_files[0]
        print(f"Using: {latest_file.name}")

        # pull origin/dest/date straight from the filename instead of hardcoding
        parts = latest_file.stem.split("_")
        origin, dest, travel_date_str = parts[0], parts[1], parts[2]
        travel_date = travel_date_str.replace("-", "/")

        with open(latest_file, encoding="utf-8") as f:
            raw = json.load(f)

        recs = parse_easemytrip(raw, origin, dest, travel_date, advance_days=1, scrape_date="2026-09-04")
        print(f"{len(recs)} non-stop fare records after outlier removal")
        for r in recs[:10]:
            print(r)