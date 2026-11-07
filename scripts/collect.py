"""Download every open job from each company's public Greenhouse job board.

Each board is saved to data/raw/<slug>.json so it only has to be pulled once.
Run it again and any board that's already saved is skipped.

Usage:
    uv run scripts/collect.py
"""

import json
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
API_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
HEADERS = {"User-Agent": "STAT 386 class project (BYU) - pm-job-postings-dataset"}
PAUSE_SECONDS = 1  # wait between requests so we don't load the API


def fetch_board(slug: str) -> dict:
    """Return the full job list for one board, including each job's description."""
    response = requests.get(
        API_URL.format(slug=slug),
        params={"content": "true"},
        headers=HEADERS,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    companies = pd.read_csv(ROOT / "data" / "companies.csv")

    for slug in companies["slug"]:
        out_path = RAW_DIR / f"{slug}.json"
        if out_path.exists():
            print(f"{slug}: already saved, skipping")
            continue

        try:
            board = fetch_board(slug)
        except requests.RequestException as err:
            print(f"{slug}: failed ({err})")
        else:
            out_path.write_text(json.dumps(board))
            print(f"{slug}: saved {len(board.get('jobs', []))} jobs")
        time.sleep(PAUSE_SECONDS)


if __name__ == "__main__":
    main()
