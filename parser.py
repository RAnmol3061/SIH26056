import json

def parse_easemytrip(raw_json: dict, origin: str, dest: str,
                      travel_date: str, advance_days: int,
                      scrape_date: str, source="EaseMyTrip") -> list[dict]:
    """Extract per-carrier cheapest-fare records from EaseMyTrip's AirBus_New response."""
    records = []
    carrier_summary = raw_json.get("m", {})

    for carrier_code, info in carrier_summary.items():
        parts = info.split("|")
        if len(parts) < 2:
            continue
        carrier_name = parts[0]
        try:
            cheapest_fare = float(parts[1])
        except ValueError:
            continue
        flight_count = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None

        records.append({
            "origin": origin,
            "dest": dest,
            "carrier_code": carrier_code,
            "carrier_name": carrier_name,
            "scrape_date": scrape_date,
            "travel_date": travel_date,
            "advance_days": advance_days,
            "total_fare": cheapest_fare,
            "flight_count": flight_count,
            "source": source,
        })
    return records


if __name__ == "__main__":
    with open("data/raw/DEL_BOM_05-09-2026_AirBus_New_20260904T143608.json") as f:
        raw = json.load(f)
    recs = parse_easemytrip(raw, "DEL", "BOM", "05/09/2026", 1, "2026-09-04")
    for r in recs:
        print(r)