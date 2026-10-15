
import statistics
from collections import defaultdict
from typing import Dict, Iterable, List

LEVEL_RANK = {"none": 0, "weak": 1, "moderate": 2, "strong": 3}


def daily_counts(events: Iterable[dict], min_signal: str = "weak") -> Dict[tuple, Dict[str, int]]:
    """events: {date:'YYYY-MM-DD', zone:str, syndromes:[{syndrome,signal}]} -> {(zone,syndrome): {date: count}}"""
    out: Dict[tuple, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for e in events:
        for s in e["syndromes"]:
            if LEVEL_RANK[s["signal"]] >= LEVEL_RANK[min_signal]:
                out[(e["zone"], s["syndrome"])][e["date"]] += 1
    return out


def ears_c2(series: List[float], baseline: int = 7, guard: int = 2, k: float = 3.0, sd_floor: float = 1.0):
    """Returns per-day dicts with expected, threshold, z and alert flag (None until baseline is available)."""
    res = []
    for t, x in enumerate(series):
        lo, hi = t - guard - baseline, t - guard
        if lo < 0:
            res.append({"count": x, "expected": None, "threshold": None, "z": None, "alert": False})
            continue
        base = series[lo:hi]
        mu, sd = statistics.mean(base), max(statistics.pstdev(base), sd_floor)
        res.append({"count": x, "expected": round(mu, 2), "threshold": round(mu + k * sd, 2),
                    "z": round((x - mu) / sd, 2), "alert": x > mu + k * sd})
    return res


def detect(counts: Dict[tuple, Dict[str, int]], dates: List[str], **kw) -> List[dict]:
    alerts = []
    for (zone, syndrome), by_day in counts.items():
        series = [by_day.get(d, 0) for d in dates]
        for d, r in zip(dates, ears_c2(series, **kw)):
            if r["alert"]:
                alerts.append({"date": d, "zone": zone, "syndrome": syndrome, **r})
    return sorted(alerts, key=lambda a: (a["date"], -a["z"]))
