'''import sqlite3
from database import get_conn

# Route weights - adjust based on DGCA traffic share; currently equal-weighted
ROUTE_WEIGHTS = {
    ("DEL", "BOM"): 0.25,
    ("DEL", "BLR"): 0.20,
    #("BOM", "BLR"): 0.15,
    #("DEL", "CCU"): 0.15,
    #("BLR", "HYD"): 0.15,
    ("MAA", "DEL"): 0.10,
}


def get_route_avg_fares(scrape_date: str) -> dict:
    """Average fare per route on a given scrape_date, across carriers and advance windows."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT origin, dest, AVG(total_fare)
        FROM fares
        WHERE scrape_date = ?
        GROUP BY origin, dest
    """, (scrape_date,)).fetchall()
    conn.close()
    return {(o, d): avg for o, d, avg in rows}


def compute_index(current_date: str, base_date: str) -> dict:
    """
    Computes a Laspeyres-style weighted airfare index.
    APIx = 100 on base_date by definition.
    Returns dict with overall index value + per-route breakdown.
    """
    base_fares = get_route_avg_fares(base_date)
    current_fares = get_route_avg_fares(current_date)

    weighted_sum = 0.0
    weight_total = 0.0
    route_breakdown = {}

    for route, weight in ROUTE_WEIGHTS.items():
        base_price = base_fares.get(route)
        current_price = current_fares.get(route)
        route_key = f"{route[0]}-{route[1]}"
        if base_price and current_price:
            relative = current_price / base_price
            weighted_sum += weight * relative
            weight_total += weight
            route_breakdown[route_key] = {
                "base_fare": round(base_price, 2),
                "current_fare": round(current_price, 2),
                "route_index": round(relative * 100, 2),
            }
        else:
            route_breakdown[route] = {"error": "missing data for this route/date"}

    overall_index = (weighted_sum / weight_total) * 100 if weight_total else None

    return {
        "base_date": base_date,
        "current_date": current_date,
        "overall_index": round(overall_index, 2) if overall_index else None,
        "routes": route_breakdown,
    }


if __name__ == "__main__":
    # On day 1, base_date == current_date -> index will show 100.0 for every route
    # Once you scrape on a second day, change current_date to that new scrape_date
    result = compute_index(current_date="2026-09-04", base_date="2026-09-04")
    import json
    print(json.dumps(result, indent=2, default=str))'''

from database import get_conn

ROUTE_WEIGHTS = {
    ("DEL", "BOM"): 0.25,
    ("DEL", "BLR"): 0.20,
    ("BOM", "BLR"): 0.15,
    ("DEL", "CCU"): 0.15,
    ("BLR", "HYD"): 0.15,
    ("MAA", "DEL"): 0.10,
}


def get_route_avg_fares(scrape_date: str) -> dict:
    """Average base fare, tax, and total fare per route on a given scrape_date."""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT origin, dest, AVG(base_fare), AVG(taxes), AVG(total_fare)
        FROM fares
        WHERE scrape_date = ?
        GROUP BY origin, dest
    """,
        (scrape_date,),
    ).fetchall()
    conn.close()
    return {
        (o, d): {"base_fare": bf, "taxes": tx, "total_fare": tf}
        for o, d, bf, tx, tf in rows
    }


def compute_index(current_date: str, base_date: str) -> dict:
    base_fares = get_route_avg_fares(base_date)
    current_fares = get_route_avg_fares(current_date)

    weighted_sum = 0.0
    weight_total = 0.0
    route_breakdown = {}

    for route, weight in ROUTE_WEIGHTS.items():
        route_key = f"{route[0]}-{route[1]}"
        base = base_fares.get(route)
        current = current_fares.get(route)

        if base and current and base["total_fare"] and current["total_fare"]:
            relative = current["total_fare"] / base["total_fare"]
            weighted_sum += weight * relative
            weight_total += weight
            route_breakdown[route_key] = {
                "base_fare": round(current["base_fare"], 2),
                "taxes": round(current["taxes"], 2),
                "total_fare": round(current["total_fare"], 2),
                "route_index": round(relative * 100, 2),
            }
        else:
            route_breakdown[route_key] = {"error": "missing data for this route/date"}

    overall_index = (weighted_sum / weight_total) * 100 if weight_total else None

    return {
        "base_date": base_date,
        "current_date": current_date,
        "overall_index": round(overall_index, 2) if overall_index else None,
        "routes": route_breakdown,
    }


if __name__ == "__main__":
    import json

    result = compute_index(current_date="2026-09-04", base_date="2026-09-04")
    print(json.dumps(result, indent=2, default=str))
