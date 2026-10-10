"""Malaysia fuel price dashboard: reads the dbt Gold tables in Supabase."""
import os

import pandas as pd
import psycopg
import streamlit as st
from dotenv import load_dotenv

load_dotenv()  # local: reads .env
st.set_page_config(page_title="Malaysia Fuel Prices", page_icon="⛽", layout="wide")

KEYS = ["PGHOST", "PGPORT", "PGUSER", "PGPASSWORD", "PGDATABASE"]


def database_config():
    """Read login details from Streamlit secrets (cloud) or .env (laptop)."""
    try:
        secrets = {k: st.secrets[k] for k in KEYS if k in st.secrets}
    except Exception:  # no secrets file when running locally
        secrets = {}
    cfg = {k: secrets.get(k) or os.getenv(k) for k in KEYS}
    return {
        "host": cfg["PGHOST"],
        "port": cfg["PGPORT"] or "5432",
        "user": cfg["PGUSER"],
        "password": cfg["PGPASSWORD"],
        "dbname": cfg["PGDATABASE"] or "postgres",
    }


@st.cache_data(ttl=3600)  # re-query at most once an hour
def query(sql: str) -> pd.DataFrame:
    with psycopg.connect(**database_config(), sslmode="require") as conn, conn.cursor() as cur:
        cur.execute(sql)
        cols = [c.name for c in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)


weekly = query("""
    select price_date, ron95::float as ron95, ron95_budi95::float as ron95_budi95,
           ron97::float as ron97, diesel::float as diesel,
           ron97_change::float as ron97_change, diesel_change::float as diesel_change
    from analytics_marts.fct_fuel_prices_weekly
    order by price_date
""")
monthly = query("""
    select month, avg_ron97::float as avg_ron97, avg_diesel::float as avg_diesel
    from analytics_marts.mart_fuel_monthly
    order by month
""")
weekly["price_date"] = pd.to_datetime(weekly["price_date"])
monthly["month"] = pd.to_datetime(monthly["month"])

# ── Header ───────────────────────────────────────────────
st.title("⛽ Malaysia Fuel Prices")
latest, prev = weekly.iloc[-1], weekly.iloc[-2]
st.caption(f"Official weekly prices from data.gov.my · latest week: {latest.price_date:%d %b %Y} · "
           "pipeline runs daily on GitHub Actions")


def delta(col):
    if pd.isna(latest[col]) or pd.isna(prev[col]):
        return None
    return f"{latest[col] - prev[col]:+.2f}"


# ── This week's prices ───────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("RON95 (market)", f"RM {latest.ron95:.2f}", delta("ron95"), delta_color="inverse")
if pd.notna(latest.ron95_budi95):
    c2.metric("RON95 (BUDI95)", f"RM {latest.ron95_budi95:.2f}", delta("ron95_budi95"), delta_color="inverse")
c3.metric("RON97", f"RM {latest.ron97:.2f}", delta("ron97"), delta_color="inverse")
c4.metric("Diesel", f"RM {latest.diesel:.2f}", delta("diesel"), delta_color="inverse")

# ── Price trend ──────────────────────────────────────────
st.subheader("Weekly prices over time")
period = st.radio("Period", ["1 year", "3 years", "All"], index=2, horizontal=True)
start = {"1 year": latest.price_date - pd.DateOffset(years=1),
         "3 years": latest.price_date - pd.DateOffset(years=3),
         "All": weekly.price_date.min()}[period]
trend = weekly[weekly.price_date >= start].set_index("price_date")
st.line_chart(trend[["ron95", "ron97", "diesel"]], y_label="RM per litre")

# ── Subsidy gap + monthly view ───────────────────────────
left, right = st.columns(2)
with left:
    st.subheader("RON95: market price vs BUDI95")
    gap = weekly.dropna(subset=["ron95_budi95"]).set_index("price_date")
    if gap.empty:
        st.info("No BUDI95 prices in the data yet.")
    else:
        st.line_chart(gap[["ron95", "ron95_budi95"]], y_label="RM per litre")
        st.caption(f"Current gap: RM {latest.ron95 - latest.ron95_budi95:.2f} per litre")
with right:
    st.subheader("Monthly average")
    st.bar_chart(monthly.set_index("month")[["avg_ron97", "avg_diesel"]], y_label="RM per litre")

# ── Latest weeks ─────────────────────────────────────────
st.subheader("Latest 10 weeks")
st.dataframe(
    weekly.sort_values("price_date", ascending=False).head(10)
          [["price_date", "ron97", "ron97_change", "diesel", "diesel_change"]],
    hide_index=True, use_container_width=True,
)
st.caption("Source: data.gov.my · Built by Ain Nurnabila · github.com/bellaazharr/Malaysia-Open-Data-Pipeline")