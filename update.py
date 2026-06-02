import os
import sys
import time
import json
import shutil
import requests
from datetime import datetime, timezone
from charts_config import CATEGORIES

OUTPUT_DIR = "output"
CHARTS_DIR = os.path.join(OUTPUT_DIR, "charts")

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

session = requests.Session()
session.headers.update({"User-Agent": UA})


def download_chart(ticker: str) -> bool:
    path = os.path.join(CHARTS_DIR, f"{ticker}.png")
    if os.path.exists(path) and os.path.getsize(path) > 500:
        return True

    headers = {"Referer": f"https://finviz.com/quote.ashx?t={ticker}"}
    domains = ["charts2.finviz.com", "finviz.com"]

    for domain in domains:
        url = f"https://{domain}/chart.ashx?t={ticker}&ty=c&ta=1&p=d&s=l"
        for _ in range(2):
            try:
                r = session.get(url, headers=headers, timeout=15)
                ct = r.headers.get("Content-Type", "")
                if r.status_code == 200 and ct.startswith("image"):
                    with open(path, "wb") as f:
                        f.write(r.content)
                    time.sleep(0.4)
                    return True
            except Exception as e:
                print(f"    [{ticker}] {domain}: {e}", flush=True)
            time.sleep(0.5)

    print(f"  FAILED: {ticker}", flush=True)
    return False


def main():
    os.makedirs(CHARTS_DIR, exist_ok=True)

    # Deduplicate tickers but keep all category entries
    seen: set[str] = set()
    unique: list[str] = []
    for _, items in CATEGORIES:
        for ticker, _ in items:
            if ticker not in seen:
                seen.add(ticker)
                unique.append(ticker)

    total = len(unique)
    success = 0
    for i, ticker in enumerate(unique, 1):
        print(f"[{i}/{total}] {ticker}", flush=True)
        if download_chart(ticker):
            success += 1

    print(f"\nDownloaded {success}/{total} charts", flush=True)

    # charts_data.json
    updated_at = datetime.now(timezone.utc).isoformat()
    data = {
        "updated_at": updated_at,
        "categories": [
            {
                "name": cat,
                "id": "cat-" + str(idx),
                "items": [
                    {
                        "ticker": t,
                        "label": lbl,
                        "img": f"charts/{t}.png",
                        "exists": os.path.exists(os.path.join(CHARTS_DIR, f"{t}.png")),
                    }
                    for t, lbl in items
                ],
            }
            for idx, (cat, items) in enumerate(CATEGORIES)
        ],
    }

    with open(os.path.join(OUTPUT_DIR, "charts_data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    # Copy index.html → output/
    shutil.copy("index.html", os.path.join(OUTPUT_DIR, "index.html"))

    print(f"Done. {success}/{total} charts ready.", flush=True)
    if success < total * 0.5:
        print("WARNING: too many failures", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
