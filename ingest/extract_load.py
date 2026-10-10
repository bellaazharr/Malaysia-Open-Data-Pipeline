"""Extract weekly fuel prices from data.gov.my and load them, unchanged, into raw.fuelprice."""
import time

import psycopg
import requests
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

API = "https://api.data.gov.my/data-catalogue"
DATASET = "fuelprice"


def extract():
    # data.gov.my allows 4 requests/minute, so back off politely on a 429
    for attempt in range(3):
        resp = requests.get(API, params={"id": DATASET, "limit": 10000}, timeout=60)
        if resp.status_code == 429:
            time.sleep(20)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError("Rate limited by data.gov.my, try again in a minute")


def load(rows):
    # psycopg reads PGHOST, PGUSER, PGPASSWORD etc. from the environment
    with psycopg.connect(sslmode="require") as conn, conn.cursor() as cur:
        cur.execute("create schema if not exists raw")
        cur.execute("""
            create table if not exists raw.fuelprice (
                record_date  date        not null,
                series_type  text        not null,
                payload      jsonb       not null,
                loaded_at    timestamptz not null default now(),
                primary key (record_date, series_type)
            )
        """)
        # upsert: re-running never creates duplicates
        cur.executemany(
            """
            insert into raw.fuelprice (record_date, series_type, payload, loaded_at)
            values (%s, %s, %s, now())
            on conflict (record_date, series_type)
            do update set payload = excluded.payload, loaded_at = excluded.loaded_at
            """,
            [(r["date"], r["series_type"], Jsonb(r)) for r in rows],
        )
    return len(rows)


if __name__ == "__main__":
    load_dotenv()
    rows = extract()
    print(f"Extracted {len(rows)} rows from data.gov.my")
    print(f"Loaded {load(rows)} rows into raw.fuelprice")