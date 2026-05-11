# ═════════════════════════════════════════════════════════════════════════════
# ALPHA DASHBOARD — generate_dashboard.py
# ═════════════════════════════════════════════════════════════════════════════
#   VERSION   : 3.0.0
#   DATE      : 2026-05-11
#   PAIRS WITH: refresh.yml v2.3.1+
#   STRATEGY  : Bogle/Buffett anchored, Mag6-dominant, Active vs Legacy split
#   CHANGELOG :
#     3.0.6 — Full-deploy allocation (May 11):
#             • Removed gap-cap on allocation: input always fully deployed.
#             • Each open sleeve gets its renormalized matrix share of input,
#                even if that pushes the sleeve slightly past target.
#             • No more "Unallocated $X" leftover from capped sleeves.
#             • Per user request: prefer slight overshoot over leftover cash.
#             • Self-correcting: overshot sleeves go GREEN, get $0 next cycle.
#     3.0.5 — SGOV restructured as parent + sub-rows (May 11):
#             • Single SGOV parent row at TOP of allocation table (8% target)
#                aggregates Cash Dry Powder + SpaceX + Anthropic earmarks.
#             • Three indented sub-rows (├─ Cash Dry Powder, ├─ SpaceX,
#                └─ Anthropic) show the breakdown at 4%/2%/2% sub-targets.
#             • Tree characters + smaller/grayer styling on sub-rows.
#             • Allocation math uses sub-rows (real matrix sleeves);
#                parent's Allocation $ is the sum (display-only aggregate).
#             • SpaceX/Anthropic removed from previous separate positions —
#                now only appear nested under SGOV.
#             • Stack order: SGOV block first, then equities below.
#     3.0.4 — SGOV allocation restored (May 11):
#             • SGOV re-included in matrix-weight deployment pool.
#             • SGOV gets its proportional share (4%/64.8% renorm = ~$3K).
#             • Visual separation at bottom of table maintained.
#             • Corrects v3.0.3 over-correction that excluded SGOV entirely.
#     3.0.3 — Allocation table refinements (May 11):
#             • SGOV excluded from deployment pool — funded separately from
#                cash float, not pre-deducted from monthly allocation input.
#             • SGOV row pinned to bottom of table with visual separator.
#             • Removed parenthetical breakdown "($X monthly + $Y plain cash)"
#                from TOTAL DEPLOYED row. Just shows total.
#             • SGOV row shows "—" in Allocation $ column; gap stays red to
#                signal SGOV needs to be funded externally.
#     3.0.2 — Monthly Allocation Table refinements (May 11):
#             • SGOV gap calculated from actual SGOV ETF position ($0), not
#               plain IBKR cash. Now shows real BUY target.
#             • Plain IBKR cash treated as "deployment pool" (added to monthly
#                input). Default deploy = $12,820 + plain cash.
#             • Matrix-weight allocation: renormalized to under-target sleeves
#                only (replaces gap-proportional pro-rata).
#             • Added "Allocation $" column showing $ to deploy per row.
#             • Added totals row at bottom of allocation table.
#             • COLOR SWAP: RED gap = action needed; GREEN = at-target/over.
#             • Caption updated to explain matrix-weight logic.
#     3.0.1 — Monthly Allocation Table fixes per user review (May 11):
#             • Whole-portfolio gap calculation (Active + Legacy combined,
#               BTC excluded as legacy hold) — replaces old active-only math.
#             • Citi-locked overweights display "OVER (locked)" with 0 shares.
#             • SGOV gets its zone-matrix allocation share like any other sleeve
#               — no "excess cash to redeploy" override logic.
#             • Pro-rata deployment includes ALL positive gaps (SPYL, Mag6,
#               earmarks, SGOV). Total monthly input fully distributed.
#             • Removed priority-tier override that was skipping SPYL when
#               active-overweight; now strict zone matrix at whole-portfolio.
#     3.0.0 — MAJOR REFACTOR per canonical strategy.md (May 11, 2026):
#             • New strategy structure: SPYL anchor + Mag6 alpha + SpaceX & 
#               Anthropic earmarks + Cash. TSLA dropped. BTC moved to Legacy.
#             • Mag6 internal weights unified: NVDA25/MSFT20/META20/GOOGL15/
#               AMZN12/AAPL8 — single source of truth.
#             • Zone matrix per strategy doc:
#               Z1: SPYL31 Mag656 SpX2 Anth2 Cash9
#               Z2: SPYL29 Mag661 SpX2 Anth2 Cash6
#               Z3: SPYL28 Mag664 SpX2 Anth2 Cash4   <-- current
#               Z4: SPYL25 Mag668 SpX2 Anth2 Cash3
#               Z5: SPYL23 Mag671 SpX2 Anth2 Cash2
#             • Active vs Legacy holdings separation in display.
#             • Monthly Allocation Table replaces Monday Action Table.
#             • Portfolio Performance: SPYL vs Mag6 vs Total Portfolio.
#             • VOO merged conceptually into SPYL Anchor sleeve.
#             • Removed TSLA fair value card and projection.
#             • Removed PHP cash and emergency reserve concepts.
#             • Fixed: data-source labels say "Twelve Data + FRED" everywhere.
#             • Fixed: SPYL gap calculation (no more "+$0 OVER" bug).
#             • Fixed: GOOGL shows in gap tracker.
#             • Fixed: Dip Trigger uses 52w peak, not cost basis.
#     2.3.5 — BTC holdings update (0.18486736 @ $91760 effective). ETH removed.
#     2.3.4 — Fixed GOOG/GOOGL aggregation for deployment gap.
#     2.3.3 — Pre-populated FV_OVERLAY with May 2026 consensus.
#     2.3.0 — Twelve Data + FRED migration.
# ═════════════════════════════════════════════════════════════════════════════
SCRIPT_VERSION = "3.0.6"
SCRIPT_DATE    = "2026-05-11"  # v3.0.6 patch

"""
generate_dashboard.py — Alpha Dashboard v3
==========================================
Generates index.html with five major sections (in display order):
  1. Monthly Allocation Table — replaces Monday Action Table; driven by zone matrix
  2. Holdings Snapshot — Active / Legacy / Total breakdown
  3. Portfolio Performance — SPYL vs Mag6 vs Total Portfolio (with YTD/1Y/5Y views)
  4. Fair Value Assessment — Mag6 + SPYL + BTC (no TSLA)
  5. Macro Overlay — yield curve, OU projection, zone bands

    pip install pandas numpy requests
    python generate_dashboard.py
"""

import json, webbrowser, os, time, io
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# ── DATA SOURCE ARCHITECTURE ─────────────────────────────────────────────────
# Twelve Data — stocks/crypto/ETFs (free: 800/day, 8/min — we use ~14 calls/day)
# FRED         — Treasury yields (DGS10, DGS3MO)
# Stooq        — last-resort fallback if both APIs fail
import requests

# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║   PASTE YOUR FREE API KEYS BETWEEN THE QUOTES BELOW                       ║
# ║                                                                           ║
# ║   1. Twelve Data:  https://twelvedata.com/register                        ║
# ║                    Login → "API Keys" tab → copy 32-char key              ║
# ║                                                                           ║
# ║   2. FRED:         https://fredaccount.stlouisfed.org/apikey              ║
# ║                    Request key → confirm email → copy 32-char key         ║
# ║                                                                           ║
# ║   If your dashboard ever shows "rate limit exceeded", rotate the          ║
# ║   Twelve Data key (30 sec at twelvedata.com → API Keys → revoke + new).   ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
TWELVEDATA_API_KEY = ""   # ← paste your Twelve Data key between the quotes
FRED_API_KEY       = ""   # ← paste your FRED key between the quotes

# Allow env-variable override:
TWELVEDATA_KEY = os.environ.get("TWELVEDATA_API_KEY", TWELVEDATA_API_KEY).strip()
FRED_KEY       = os.environ.get("FRED_API_KEY",       FRED_API_KEY).strip()
TD_BASE        = "https://api.twelvedata.com"
FRED_BASE      = "https://api.stlouisfed.org/fred"

if not TWELVEDATA_KEY:
    print("⚠ TWELVEDATA_API_KEY not set — Twelve Data disabled, will use Stooq only")
else:
    print(f"✓ Twelve Data key loaded (length: {len(TWELVEDATA_KEY)} chars)")
if not FRED_KEY:
    print("⚠ FRED_API_KEY not set — Treasury fetch will fall back to Stooq or placeholder")
else:
    print(f"✓ FRED key loaded (length: {len(FRED_KEY)} chars)")

USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/120.0.0.0 Safari/537.36")

HTTP_SESSION = requests.Session()
HTTP_SESSION.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
})

# ── Twelve Data symbol mapping ───────────────────────────────────────────────
def td_symbol(yf_ticker):
    t = yf_ticker.upper()
    if t == "BTC-USD": return "BTC/USD"
    if t == "SPYL.L":  return None    # Premium-only on Twelve Data; synthesized from SPY × 0.0241
    if t in ("^TNX", "^IRX"): return None
    return t   # AAPL, MSFT, NVDA, GOOGL, GOOG, META, AMZN, SPY, VOO

def td_quote(yf_ticker):
    """Live quote via Twelve Data /price. Returns float price or None."""
    if not TWELVEDATA_KEY: return None
    sym = td_symbol(yf_ticker)
    if not sym: return None
    try:
        r = HTTP_SESSION.get(f"{TD_BASE}/price",
                             params={"symbol": sym, "apikey": TWELVEDATA_KEY},
                             timeout=10)
        if r.status_code != 200:
            print(f"  TD quote {yf_ticker} ({sym}): HTTP {r.status_code}")
            return None
        data = r.json()
        if "price" in data:
            return float(data["price"])
        if data.get("status") == "error":
            print(f"  TD quote {yf_ticker} ({sym}): {data.get('message', 'error')}")
        return None
    except Exception as e:
        print(f"  TD quote {yf_ticker} ({sym}) failed: {e}")
        return None

def td_candles(yf_ticker, days=400):
    """Daily candles via Twelve Data /time_series. Returns Series of close prices."""
    if not TWELVEDATA_KEY: return None
    sym = td_symbol(yf_ticker)
    if not sym: return None
    try:
        r = HTTP_SESSION.get(f"{TD_BASE}/time_series",
                             params={"symbol": sym, "interval": "1day",
                                     "outputsize": min(days, 5000),
                                     "apikey": TWELVEDATA_KEY,
                                     "format": "JSON"},
                             timeout=15)
        if r.status_code != 200:
            print(f"  TD candles {yf_ticker} ({sym}): HTTP {r.status_code}")
            return None
        data = r.json()
        if data.get("status") == "error":
            print(f"  TD candles {yf_ticker} ({sym}): {data.get('message', 'error')}")
            return None
        vals = data.get("values", [])
        if not vals:
            return None
        rows = []
        for v in vals:
            try:
                rows.append((pd.Timestamp(v["datetime"]), float(v["close"])))
            except Exception:
                continue
        if not rows: return None
        s = pd.Series(dict(rows)).sort_index()
        return s
    except Exception as e:
        print(f"  TD candles {yf_ticker} ({sym}) failed: {e}")
        return None

# ── FRED for Treasury yields ─────────────────────────────────────────────────
FRED_SERIES = {"^TNX": "DGS10", "^IRX": "DGS3MO"}

def fred_series(yf_ticker, days=400):
    if not FRED_KEY: return None
    sid = FRED_SERIES.get(yf_ticker)
    if not sid: return None
    start = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        r = HTTP_SESSION.get(f"{FRED_BASE}/series/observations",
                             params={"series_id": sid, "api_key": FRED_KEY,
                                     "file_type": "json",
                                     "observation_start": start},
                             timeout=15)
        if r.status_code != 200:
            print(f"  FRED {yf_ticker} ({sid}): HTTP {r.status_code}")
            return None
        data = r.json()
        obs = data.get("observations", [])
        if not obs: return None
        rows = []
        for o in obs:
            v = o.get("value", ".")
            if v in (".", ""): continue
            try:
                rows.append((pd.Timestamp(o["date"]), float(v)))
            except Exception:
                continue
        if not rows: return None
        s = pd.Series(dict(rows)).sort_index()
        return s
    except Exception as e:
        print(f"  FRED {yf_ticker} ({sid}) failed: {e}")
        return None

# ── Stooq last-resort fallback ───────────────────────────────────────────────
def stooq_symbol(yf_ticker):
    t = yf_ticker.upper()
    if t == "BTC-USD": return "btcusd"
    if t == "^TNX":    return "10usy.b"
    if t == "^IRX":    return "3muy.b"
    if t == "SPYL.L":  return None
    return f"{t.lower()}.us"

def stooq_history(yf_ticker, years=1):
    sym = stooq_symbol(yf_ticker)
    if not sym: return None
    url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
    try:
        r = HTTP_SESSION.get(url, timeout=10)
        if r.status_code != 200 or len(r.text) < 50: return None
        df = pd.read_csv(io.StringIO(r.text))
        if "Date" not in df.columns or "Close" not in df.columns: return None
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()
        cutoff = datetime.today() - timedelta(days=years*365)
        df = df[df.index >= cutoff]
        return df["Close"].astype(float) if len(df) > 0 else None
    except Exception:
        return None

# ── MAIN HISTORICAL FETCHER ──────────────────────────────────────────────────
print("Initializing data fetch...")

def fetch_history(ticker_list, start_date, end_date, max_attempts=3):
    """Fetch close-price history for tickers. Returns dict {ticker: pd.Series}."""
    days = (end_date - start_date).days + 30
    out = {}

    # Phase 1: split
    fred_tickers = [t for t in ticker_list if t in FRED_SERIES]
    other_tickers = [t for t in ticker_list if t not in FRED_SERIES and t != "SPYL.L"]

    # Phase 2: FRED for yields
    for t in fred_tickers:
        s = fred_series(t, days=days)
        if s is not None and len(s) > 5:
            out[t] = s.loc[(s.index >= start_date) & (s.index <= end_date)]
            print(f"  ✓ {t}: FRED ({len(out[t])} rows)")
        else:
            print(f"  ✗ {t}: FRED failed")

    # Phase 3: Twelve Data for stocks/crypto/ETFs
    for t in other_tickers:
        s = td_candles(t, days=days)
        if s is not None and len(s) > 5:
            out[t] = s.loc[(s.index >= start_date) & (s.index <= end_date)]
            print(f"  ✓ {t}: Twelve Data ({len(out[t])} rows)")
        else:
            print(f"  ✗ {t}: Twelve Data failed, trying Stooq")
            years = max(1, (end_date - start_date).days // 365 + 1)
            s = stooq_history(t, years=years)
            if s is not None and len(s) > 5:
                out[t] = s.loc[(s.index >= start_date) & (s.index <= end_date)]
                print(f"  ✓ {t}: Stooq ({len(out[t])} rows)")
        time.sleep(8)  # respect 8/min limit

    return out

# ─────────────────────────────────────────────────────────────────────────────
# STRATEGY CONFIG — from canonical strategy.md (v3.0.0)
# ─────────────────────────────────────────────────────────────────────────────

# ── HOLDINGS — CURRENT POSITIONS ──────────────────────────────────────────────
# Edit this when you execute trades. Format:
#   ACCOUNT: { TICKER: {"shares": N, "avg_cost": price}, "CASH": amount }
#
# CLASSIFICATION (per strategy doc):
#   ACTIVE  = IBKR  → drives zone matrix, receives monthly contributions
#   LEGACY  = Citi* (frozen) + CRYPTO (BTC, never add)
#
# Note: VOO in IBKR is conceptually merged with SPYL (same exposure).
HOLDINGS = {
    "IBKR": {
        "META": {"shares": 18,   "avg_cost": 612.04},
        "MSFT": {"shares": 25,   "avg_cost": 419.18},
        "NVDA": {"shares": 50,   "avg_cost": 202.57},
        "SPYL": {"shares": 2065, "avg_cost": 17.72},
        "VOO":  {"shares": 28,   "avg_cost": 605.89},
        "CASH": 31144.43,
    },
    "CITI_401K": {
        "AMZN": {"shares": 100, "avg_cost": 163.51},
        "GOOG": {"shares": 141, "avg_cost": 122.71},
        "META": {"shares": 25,  "avg_cost": 329.06},
        "CASH": 59.06,
    },
    "CITI_ROTH": {
        "AAPL": {"shares": 134, "avg_cost": 127.05},
        "META": {"shares": 25,  "avg_cost": 339.97},
        "CASH": 179.42,
    },
    "CITI_BROK": {
        "META": {"shares": 12, "avg_cost": 154.14},
        "VOO":  {"shares": 7,  "avg_cost": 388.45},
        "CASH": 737.30,
    },
    "CRYPTO": {
        # BTC: avg cost is effective USD-equivalent including cryptoback rewards.
        # Updated 2026-05-10. Held indefinitely; never add per strategy.
        "BTC": {"shares": 0.18486736, "avg_cost": 91760},
    },
}

# Account classification: which accounts are ACTIVE vs LEGACY
ACTIVE_ACCOUNTS = ["IBKR"]
LEGACY_ACCOUNTS = ["CITI_401K", "CITI_ROTH", "CITI_BROK", "CRYPTO"]

ACCOUNT_LABELS = {
    "IBKR":      "IBKR",
    "CITI_401K": "Citi 401k",
    "CITI_ROTH": "Citi Roth",
    "CITI_BROK": "Citi Brokerage",
    "CRYPTO":    "Crypto (BTC)",
}

# ── ZONE MATRIX — ACTIVE SLEEVES ──────────────────────────────────────────────
# Per strategy doc Section 3. Percentages apply to ACTIVE capital (IBKR).
# Sleeves: SPYL (anchor), MAG6 (alpha), SPACEX (earmark), ANTHROPIC (earmark), CASH
# Note: SPACEX and ANTHROPIC earmarks physically held in SGOV.
#       CASH dry powder also held in SGOV.
ZONE_ALLOCATION = {
    1: {"SPYL": 0.31, "MAG6": 0.56, "SPACEX": 0.02, "ANTHROPIC": 0.02, "CASH": 0.09},
    2: {"SPYL": 0.29, "MAG6": 0.61, "SPACEX": 0.02, "ANTHROPIC": 0.02, "CASH": 0.06},
    3: {"SPYL": 0.28, "MAG6": 0.64, "SPACEX": 0.02, "ANTHROPIC": 0.02, "CASH": 0.04},
    4: {"SPYL": 0.25, "MAG6": 0.68, "SPACEX": 0.02, "ANTHROPIC": 0.02, "CASH": 0.03},
    5: {"SPYL": 0.23, "MAG6": 0.71, "SPACEX": 0.02, "ANTHROPIC": 0.02, "CASH": 0.02},
}

# Verify all sum to 1.0
for z, a in ZONE_ALLOCATION.items():
    assert abs(sum(a.values()) - 1.0) < 1e-9, f"Zone {z} sums to {sum(a.values())}"

# ── MAG6 INTERNAL WEIGHTS ─────────────────────────────────────────────────────
# Per strategy doc Section 4 — fixed across all zones.
# Single source of truth — all UI/calcs derive from this.
MAG6_INTERNAL = {
    "NVDA":  0.25,
    "MSFT":  0.20,
    "META":  0.20,
    "GOOGL": 0.15,
    "AMZN":  0.12,
    "AAPL":  0.08,
}
assert abs(sum(MAG6_INTERNAL.values()) - 1.0) < 1e-9, "Mag6 must sum to 100%"

# Ordered list for consistent display
MAG6_ORDER = ["NVDA", "MSFT", "META", "GOOGL", "AMZN", "AAPL"]

# ── ZONE METADATA ─────────────────────────────────────────────────────────────
ZONE_META = {
    1: {"label":"ZONE 1 — INVERTED",  "color":"#dc2626","bg":"#fef2f2","desc":"Recession signal · maximum defense"},
    2: {"label":"ZONE 2 — CAUTION",   "color":"#ea580c","bg":"#fff7ed","desc":"Curve uninverting · building dry powder"},
    3: {"label":"ZONE 3 — NEUTRAL",   "color":"#d97706","bg":"#fffbeb","desc":"Base operating zone"},
    4: {"label":"ZONE 4 — HEALTHY",   "color":"#16a34a","bg":"#f0fdf4","desc":"Mid-cycle expansion · lean offense"},
    5: {"label":"ZONE 5 — BULL",      "color":"#15803d","bg":"#dcfce7","desc":"Steep curve · maximum offense"},
}
ZONE_BOUNDARIES = [0.0, 0.5, 1.21, 2.0]   # spread thresholds in %

def get_zone(spread):
    if spread is None: return 3
    if spread < 0:    return 1
    if spread < 0.5:  return 2
    if spread < 1.21: return 3
    if spread < 2.0:  return 4
    return 5

# ── FAIR VALUE OVERLAY — manually-maintained fundamentals ────────────────────
# UPDATE FREQUENCY: ~Monthly. Sources:
#   - Targets, analyst count: stockanalysis.com/stocks/{ticker}/forecast/
#   - Fwd P/E, Rev Growth:    finance.yahoo.com/quote/{ticker}/key-statistics
# LAST UPDATED: 2026-05-10
#
# Per strategy v3.0.0: TSLA removed (no longer held).
# Zone actions reflect strategy doc operational rules.
FV_OVERLAY = {
    "NVDA": {
        "hist_pe": 50, "mag6_weight": 0.25, "in_mag6": True,
        "zone_action": {1:"Trim — Defensive",2:"Hold — Building Cash",3:"Buy Aggressively",4:"Buy Aggressively",5:"Max Deploy"},
        "target_mean": 270.73,  "target_low": 195.00,  "target_high": 360.00,
        "fwd_pe": 25.87,        "rev_growth": 0.732,   "analysts": 37,
        "recommendation": "strong_buy",
    },
    "MSFT": {
        "hist_pe": 33, "mag6_weight": 0.20, "in_mag6": True,
        "zone_action": {1:"Trim — Defensive",2:"Hold",3:"Buy Aggressively",4:"Buy Aggressively",5:"Max Deploy"},
        "target_mean": 569.46,  "target_low": 415.00,  "target_high": 680.00,
        "fwd_pe": 22.0,         "rev_growth": 0.180,   "analysts": 37,
        "recommendation": "strong_buy",
    },
    "META": {
        "hist_pe": 25, "mag6_weight": 0.20, "in_mag6": True,
        "zone_action": {1:"Trim — Defensive",2:"Hold",3:"Buy Aggressively",4:"Buy Aggressively",5:"Max Deploy"},
        "target_mean": 836.39,  "target_low": 700.00,  "target_high": 1015.00,
        "fwd_pe": 19.5,         "rev_growth": 0.331,   "analysts": 36,
        "recommendation": "strong_buy",
    },
    "GOOGL": {
        "hist_pe": 25, "mag6_weight": 0.15, "in_mag6": True,
        "zone_action": {1:"Trim — Defensive",2:"Hold",3:"Hold — At Consensus",4:"Buy Systematically",5:"Buy Systematically"},
        "target_mean": 427.00,  "target_low": 190.00,  "target_high": 515.00,
        "fwd_pe": 27.8,         "rev_growth": 0.218,   "analysts": 45,
        "recommendation": "strong_buy",
    },
    "AMZN": {
        "hist_pe": 22, "mag6_weight": 0.12, "in_mag6": True,
        "zone_action": {1:"Trim — Defensive",2:"Hold",3:"Buy Systematically",4:"Buy Systematically",5:"Buy Aggressively"},
        "target_mean": 306.00,  "target_low": 250.00,  "target_high": 370.00,
        "fwd_pe": 31.7,         "rev_growth": 0.166,   "analysts": 41,
        "recommendation": "strong_buy",
    },
    "AAPL": {
        "hist_pe": 32, "mag6_weight": 0.08, "in_mag6": True,
        "zone_action": {1:"Trim — Defensive",2:"Hold",3:"Accumulate Slowly",4:"Buy Systematically",5:"Buy Aggressively"},
        "target_mean": 304.16,  "target_low": 215.00,  "target_high": 400.00,
        "fwd_pe": 30.0,         "rev_growth": 0.166,   "analysts": 30,
        "recommendation": "buy",
    },
    "SPYL": {
        "hist_pe": None, "mag6_weight": 0.0, "in_mag6": False,
        "is_anchor": True,
        "spyl_target": 18.0,
        "spyl_target_hi": 18.50,
        "zone_action": {1:"DCA Buy Fixed",2:"DCA Buy Fixed",3:"DCA Buy Fixed",4:"DCA Buy Fixed",5:"DCA Buy Fixed"},
    },
    "BTC": {
        "hist_pe": None, "mag6_weight": 0.0, "in_mag6": False,
        "is_legacy": True,
        "s2f_low": 100000, "s2f_high": 150000,
        "zone_action": {1:"Hold (Legacy)",2:"Hold (Legacy)",3:"Hold (Legacy)",4:"Hold (Legacy)",5:"Hold (Legacy)"},
    },
}

# ── STOCK CHART CONFIG ────────────────────────────────────────────────────────
# Performance chart compares: SPYL · Mag6 · Total Portfolio
# Mag6 basket weights = MAG6_INTERNAL (conviction-weighted per strategy)
FWD_CAGR = {"SPYL": 0.09, "MAG6": 0.12, "PORTFOLIO": 0.105}
VOLS     = {"SPYL": 0.16, "MAG6": 0.25, "PORTFOLIO": 0.20}

# Tickers fetched for chart history + holdings valuation
# Note: TSLA dropped from active strategy; not fetched.
ALL_TICKERS = ["NVDA","MSFT","META","GOOGL","AMZN","AAPL","SPY","VOO","GOOG","BTC-USD"]
# ─────────────────────────────────────────────────────────────────────────────
# DATA FETCH
# ─────────────────────────────────────────────────────────────────────────────

print("\nFetching equity prices...")
today = datetime.today()
start = today - timedelta(days=365*11)

raw_prices = fetch_history(ALL_TICKERS, start, today)

prices = {}
for col, s in raw_prices.items():
    if col == "BTC-USD":
        key = "BTC"
    else:
        key = str(col)
    prices[key] = s
    print(f"  {key}: {len(s)} rows  ${s.iloc[0]:.2f} → ${s.iloc[-1]:.2f}")

if not prices:
    print("  ⚠ NO PRICE DATA — using synthetic fallback so dashboard still renders")
    fb_dates = pd.bdate_range(end=pd.Timestamp.today(), periods=300)
    for t in ["SPY","MSFT","NVDA","META","GOOGL","AMZN","AAPL","VOO","GOOG","BTC"]:
        base = {"SPY":500,"MSFT":480,"NVDA":220,"META":700,"GOOGL":175,"AMZN":230,
                "AAPL":220,"VOO":620,"GOOG":175,"BTC":95000}.get(t, 100)
        prices[t] = pd.Series([base * (1 + 0.0003*i) for i in range(len(fb_dates))], index=fb_dates)

# ── SPYL Proxy: SPYL = SPY × 0.0241 ──────────────────────────────────────────
# SPYL.L (London-listed SPDR S&P 500 UCITS ETF) is Twelve Data Grow-tier only.
SPYL_RATIO = 0.0241
if "SPY" in prices and "SPYL" not in prices:
    prices["SPYL"] = prices["SPY"] * SPYL_RATIO
    print(f"  SPYL: synthesized from SPY × {SPYL_RATIO} → ${prices['SPYL'].iloc[-1]:.2f}")

# ── MAG6 basket — conviction-weighted per strategy ────────────────────────────
components = []
for t, w in MAG6_INTERNAL.items():
    s = prices.get(t)
    if s is not None and len(s) > 20:
        components.append((s / s.iloc[0] * 100) * w)
if components:
    basket = pd.concat(components, axis=1).sum(axis=1)
    prices["MAG6"] = basket / basket.iloc[0] * 100
    print(f"  MAG6 basket: built from {len(components)} components")
else:
    print("  ⚠ MAG6 basket: no components — using SPY as proxy")
    prices["MAG6"] = prices.get("SPY", pd.Series(dtype=float))

# ── FETCH TREASURY YIELDS ─────────────────────────────────────────────────────
print("\nFetching Treasury yields (^TNX, ^IRX)...")
yld = fetch_history(["^TNX","^IRX"], today - timedelta(days=365*6), today)
tnx = yld.get("^TNX")
irx = yld.get("^IRX")
if tnx is not None and irx is not None and len(tnx) > 5 and len(irx) > 5:
    spread_series = (tnx - irx).dropna()
    current_spread = float(spread_series.iloc[-1])
    print(f"  10yr: {float(tnx.iloc[-1]):.3f}%  3mo: {float(irx.iloc[-1]):.3f}%  spread: {current_spread:+.3f}%")
else:
    print("  Treasury fetch failed — using fallback spread 0.64 (Zone 3)")
    spread_series = pd.Series(dtype=float)
    current_spread = 0.64

current_zone = get_zone(current_spread)
print(f"  → {ZONE_META[current_zone]['label']}")

# ── OU MEAN-REVERSION PROJECTION ──────────────────────────────────────────────
OU_MU    = 1.5
OU_THETA = 0.35
OU_SIGMA = 0.80

def proj_ou(last_spread, last_date, end_date):
    dates = pd.bdate_range(start=last_date + timedelta(days=1), end=end_date)
    if len(dates) == 0: return [], [], []
    dt = 1/252
    pts, upper, lower = [], [], []
    x = last_spread
    for i, d in enumerate(dates):
        t = (i+1) * dt
        e_x = OU_MU + (last_spread - OU_MU) * np.exp(-OU_THETA * t)
        var_x = (OU_SIGMA**2 / (2*OU_THETA)) * (1 - np.exp(-2*OU_THETA*t))
        sd = np.sqrt(var_x)
        pts.append((str(d.date()), round(float(e_x), 4)))
        upper.append((str(d.date()), round(float(e_x + 1.0*sd), 4)))
        lower.append((str(d.date()), round(float(e_x - 1.0*sd), 4)))
    return pts, upper, lower

# ── BUILD YIELD CURVE HORIZON DATA ───────────────────────────────────────────
yc_horizons = {"30D":30, "6M":180, "1Y":365, "5Y":1825}
yc_data = {}
if len(spread_series) > 0:
    for hkey, days in yc_horizons.items():
        hist_start = today - timedelta(days=days)
        hist = spread_series.loc[spread_series.index >= hist_start]
        proj_end = today + timedelta(days=days)
        last_d   = spread_series.index[-1].to_pydatetime()
        proj, up, lo = proj_ou(current_spread, last_d, proj_end)
        yc_data[hkey] = {
            "hist": [(str(d.date()), round(float(v), 4)) for d, v in hist.items()],
            "proj": proj, "upper": up, "lower": lo,
        }
else:
    for hkey in yc_horizons:
        yc_data[hkey] = {"hist": [], "proj": [], "upper": [], "lower": []}

# ── PERFORMANCE CHART HORIZON DATA ───────────────────────────────────────────
# Compares: SPYL · MAG6 · PORTFOLIO (total)
def biz_range(s, e):
    return pd.bdate_range(start=s, end=e)

def proj_cagr(lv, ld, ed, rate):
    dates = biz_range(ld + timedelta(days=1), ed)
    if len(dates) == 0: return []
    pts = []
    daily = (1 + rate) ** (1/252) - 1
    cur = lv
    for d in dates:
        cur *= (1 + daily)
        pts.append((str(d.date()), round(float(cur), 2)))
    return pts

def proj_gbm(lv, ld, ed, rate, vol, seed):
    dates = biz_range(ld + timedelta(days=1), ed)
    if len(dates) == 0: return []
    rng = np.random.default_rng(seed)
    daily_drift = (rate - 0.5*vol*vol) / 252
    daily_vol   = vol / np.sqrt(252)
    pts = []
    cur = lv
    for d in dates:
        z = rng.standard_normal()
        cur *= np.exp(daily_drift + daily_vol*z)
        pts.append((str(d.date()), round(float(cur), 2)))
    return pts

def vol_bands(proj_pts, vol):
    upper, lower = [], []
    for i, (d, v) in enumerate(proj_pts):
        t = (i+1)/252
        f = np.exp(1.645 * vol * np.sqrt(t))
        upper.append((d, round(v*f, 2)))
        lower.append((d, round(v/f, 2)))
    return upper, lower

# ─────────────────────────────────────────────────────────────────────────────
# HOLDINGS VALUATION — split Active vs Legacy
# ─────────────────────────────────────────────────────────────────────────────

# Fetch live prices for all FV-card tickers (these populate during FV card build)
live_prices = {}

# ── FAIR VALUE CARDS ──────────────────────────────────────────────────────────
print("\nFetching fair value data...")

# FV_CONFIG: (yfinance_ticker, display_ticker, company_name, asset_class)
# Per v3.0.0 strategy: TSLA removed.
FV_CONFIG = [
    ("NVDA",    "NVDA",  "NVIDIA Corporation",      "stock"),
    ("MSFT",    "MSFT",  "Microsoft Corporation",   "stock"),
    ("META",    "META",  "Meta Platforms Inc.",     "stock"),
    ("GOOGL",   "GOOGL", "Alphabet Inc.",           "stock"),
    ("AMZN",    "AMZN",  "Amazon.com Inc.",         "stock"),
    ("AAPL",    "AAPL",  "Apple Inc.",              "stock"),
    ("SPYL.L",  "SPYL",  "SPDR S&P 500 UCITS ETF",  "etf"),
    ("BTC-USD", "BTC",   "Bitcoin (Legacy Hold)",   "crypto"),
]

def _fetch_fv(yt):
    """Fair value info — Twelve Data primary, history-derived fallback."""
    info = {}
    # Phase 1: Twelve Data /price
    if yt == "SPYL.L":
        spy_price = td_quote("SPY")
        if spy_price:
            info["regularMarketPrice"] = round(spy_price * SPYL_RATIO, 4)
    elif yt == "BTC-USD":
        p = td_quote("BTC-USD")
        if p: info["regularMarketPrice"] = round(p, 2)
    else:
        p = td_quote(yt)
        if p: info["regularMarketPrice"] = round(p, 2)
    time.sleep(8)  # respect rate limit

    # Phase 2: derive from chart history if Twelve Data didn't give us price
    if "regularMarketPrice" not in info:
        key = yt.replace(".L", "").replace("-USD", "")
        if key == "SPYL" and "SPYL" in prices:
            info["regularMarketPrice"] = float(prices["SPYL"].iloc[-1])
        elif key in prices:
            info["regularMarketPrice"] = float(prices[key].iloc[-1])

    return info

def _fmt(v, dec=2):
    if v is None: return "—"
    if isinstance(v, str): return v
    try:
        if dec == 0: return f"${int(round(v)):,}"
        return f"${v:,.{dec}f}"
    except Exception:
        return "—"

def _badge(rec, upside, disp):
    if disp == "BTC": return ("Legacy Hold", "fv-hold")
    if disp == "SPYL": return ("DCA BUY", "fv-dca")
    r = (rec or "").lower()
    if r == "strong_buy": return ("Strong Buy", "fv-buy")
    if r == "buy":        return ("Buy", "fv-buy")
    if r == "hold":       return ("Hold", "fv-hold")
    if r == "sell":       return ("Sell", "fv-cau")
    if upside is not None and upside > 0.10: return ("Buy", "fv-buy")
    return ("Hold", "fv-hold")

def _deploy_color(action):
    a = (action or "").lower()
    if "max" in a or "aggressively" in a: return "dep-green"
    if "systematic" in a or "dca" in a or "accumulate" in a: return "dep-amber"
    if "do not" in a or "trim" in a or "overvalued" in a: return "dep-red"
    if "hold" in a or "consensus" in a: return "dep-neutral"
    if "strategic" in a or "legacy" in a: return "dep-neutral"
    return "dep-neutral"

def _build_card(yt, disp, co, cls):
    info = _fetch_fv(yt)
    ov   = FV_OVERLAY.get(disp, {})
    # Layer overlay analyst fields onto info
    for k in ("target_mean","target_low","target_high","fwd_pe","rev_growth","analysts","recommendation"):
        if k in ov: info[k] = ov[k]

    price = info.get("regularMarketPrice")
    if price is None: return ""
    live_prices[disp] = price

    target_mean = info.get("target_mean")
    target_low  = info.get("target_low")
    target_high = info.get("target_high")
    fwd_pe      = info.get("fwd_pe")
    rev_growth  = info.get("rev_growth")
    analysts    = info.get("analysts")
    rec         = info.get("recommendation")

    upside = None
    if target_mean and price > 0:
        upside = (target_mean - price) / price

    badge_text, badge_cls = _badge(rec, upside, disp)

    # Core metrics row
    metrics_html = ""
    if disp == "SPYL":
        s52w_high = float(prices["SPYL"].iloc[-252:].max()) if "SPYL" in prices and len(prices["SPYL"]) > 0 else price
        s52w_low  = float(prices["SPYL"].iloc[-252:].min()) if "SPYL" in prices and len(prices["SPYL"]) > 0 else price
        spyl_tgt  = ov.get("spyl_target", 18.0)
        spyl_upd  = (spyl_tgt - price) / price if price > 0 else 0
        target_str  = f"${spyl_tgt:.2f}"
        upside_str  = f"{spyl_upd*100:+.1f}%"
        low_str     = f"${s52w_low:.2f}"
        high_str    = f"${s52w_high:.2f}"
        metrics_html = f"""
          <div class="fv-met"><div class="fv-met-lbl">Div Yield</div><div class="fv-met-val">—</div></div>
          <div class="fv-met"><div class="fv-met-lbl">52w High</div><div class="fv-met-val">${s52w_high:.2f}</div></div>
          <div class="fv-met"><div class="fv-met-lbl">52w Low</div><div class="fv-met-val">${s52w_low:.2f}</div></div>"""
    elif disp == "BTC":
        s52w_high = float(prices["BTC"].iloc[-252:].max()) if "BTC" in prices and len(prices["BTC"]) > 0 else price
        s52w_low  = float(prices["BTC"].iloc[-252:].min()) if "BTC" in prices and len(prices["BTC"]) > 0 else price
        s2f_low  = ov.get("s2f_low", 100000)
        s2f_high = ov.get("s2f_high", 150000)
        target_str  = f"${s2f_low:,.0f}"
        target_high_str = f"${s2f_high:,.0f}"
        upside_str = f"{((s2f_low-price)/price*100):+.1f}%" if price > 0 else "—"
        low_str    = f"${s52w_low:,.0f}"
        high_str   = f"${s52w_high:,.0f}"
        metrics_html = f"""
          <div class="fv-met"><div class="fv-met-lbl">Market Cap</div><div class="fv-met-val">~$1.6T</div></div>
          <div class="fv-met"><div class="fv-met-lbl">52w High</div><div class="fv-met-val">${s52w_high:,.0f}</div></div>
          <div class="fv-met"><div class="fv-met-lbl">52w Low</div><div class="fv-met-val">${s52w_low:,.0f}</div></div>"""
    else:
        target_str = _fmt(target_mean)
        upside_str = f"{upside*100:+.1f}%" if upside is not None else "—"
        low_str    = _fmt(target_low)
        high_str   = _fmt(target_high)
        peg = None
        if fwd_pe is not None and rev_growth and rev_growth > 0.01:
            peg = fwd_pe / (rev_growth * 100)
        peg_str = f"{peg:.2f}x" if peg is not None else "—"
        rev_str = f"{rev_growth*100:+.1f}%" if rev_growth is not None else "—"
        metrics_html = f"""
          <div class="fv-met"><div class="fv-met-lbl">Fwd P/E</div><div class="fv-met-val">{fwd_pe:.1f}x</div></div>
          <div class="fv-met"><div class="fv-met-lbl">Rev Growth</div><div class="fv-met-val">{rev_str}</div></div>
          <div class="fv-met"><div class="fv-met-lbl">Analysts</div><div class="fv-met-val">{analysts or '—'}</div></div>"""

    # Zone-aware deployment
    action = ov.get("zone_action", {}).get(current_zone, "Hold")
    dep_cls = _deploy_color(action)

    # Allocation footer
    if disp == "SPYL":
        weight_str = "28% Anchor (Z3)"
        alloc_str  = "DCA fixed monthly"
    elif disp == "BTC":
        weight_str = "Legacy hold"
        alloc_str  = "No new capital"
    else:
        mag6_w = ov.get("mag6_weight", 0)
        z3_w   = mag6_w * ZONE_ALLOCATION[3]["MAG6"]
        weight_str = f"{int(mag6_w*100)}% of Mag6 ({z3_w*100:.2f}% of active)"
        alloc_str  = f"Buy per zone matrix"

    # SPYL-specific dip trigger
    spyl_dip_html = ""
    if disp == "SPYL":
        if "SPYL" in prices and len(prices["SPYL"]) > 0:
            peak_52w = float(prices["SPYL"].iloc[-252:].max())
            drawdown = (price - peak_52w) / peak_52w if peak_52w > 0 else 0
            dd_pct = drawdown * 100
            if dd_pct > -5:    dd_class, dd_msg = "fv-met-val pos", "Within normal range"
            elif dd_pct > -10: dd_class, dd_msg = "fv-met-val", "Approaching T1 trigger"
            elif dd_pct > -20: dd_class, dd_msg = "fv-met-val", "T1 ACTIVE — buy 2x"
            elif dd_pct > -30: dd_class, dd_msg = "fv-met-val", "T2 ACTIVE — buy 4x"
            else:              dd_class, dd_msg = "fv-met-val neg", "T3 ACTIVE — max deploy"
            spyl_dip_html = f"""
              <div class="fv-dip">
                <div class="fv-dip-hd">DIP TRIGGER (vs 52w peak ${peak_52w:.2f})</div>
                <div class="fv-dip-val {dd_class}">{dd_pct:+.1f}%</div>
                <div class="fv-dip-msg">{dd_msg}</div>
                <div class="fv-dip-scale"><span>0%</span><span>-10% T1</span><span>-20% T2</span><span>-30% T3</span></div>
              </div>"""

    btc_cycle_html = ""
    if disp == "BTC":
        if "BTC" in prices and len(prices["BTC"]) > 0:
            peak_52w = float(prices["BTC"].iloc[-252:].max())
            drawdown = (price - peak_52w) / peak_52w if peak_52w > 0 else 0
            dd_pct = drawdown * 100
            btc_cycle_html = f"""
              <div class="fv-dip">
                <div class="fv-dip-hd">CYCLE DRAWDOWN (vs 52w peak ${peak_52w:,.0f})</div>
                <div class="fv-dip-val">{dd_pct:+.1f}%</div>
                <div class="fv-dip-msg">Strategy: legacy hold — never add</div>
              </div>"""

    return f"""
      <div class="fv-card" data-ticker="{disp}" data-price="{price}">
        <div class="fv-head">
          <div>
            <div class="fv-tk">{disp}</div>
            <div class="fv-co">{co}</div>
          </div>
          <div class="fv-bdg {badge_cls}">{badge_text}</div>
        </div>
        <div class="fv-price-row">
          <div class="fv-price-block">
            <div class="fv-price-lbl">PRICE</div>
            <div class="fv-price-val">{_fmt(price, 2 if price < 100 else 0)}</div>
          </div>
          <div class="fv-price-block">
            <div class="fv-price-lbl">TARGET</div>
            <div class="fv-price-val">{target_str}</div>
          </div>
          <div class="fv-price-block">
            <div class="fv-price-lbl">UPSIDE</div>
            <div class="fv-price-val">{upside_str}</div>
          </div>
        </div>
        <div class="fv-range">
          <span>Low {low_str}</span><span>Current</span><span>High {high_str}</span>
        </div>
        <div class="fv-met-grid">{metrics_html}
        </div>
        <div class="fv-action">
          <div class="fv-action-lbl">Zone {current_zone} Action</div>
          <div class="fv-action-val {dep_cls}">{action}</div>
        </div>
        <div class="fv-meta">
          <div><span>Target Weight</span><strong>{weight_str}</strong></div>
          <div><span>Deployment</span><strong>{alloc_str}</strong></div>
        </div>{spyl_dip_html}{btc_cycle_html}
      </div>"""

fv_cards_html = ""
for yt, disp, co, cls in FV_CONFIG:
    fv_cards_html += _build_card(yt, disp, co, cls)

print(f"  Built {len(FV_CONFIG)} FV cards")
# ─────────────────────────────────────────────────────────────────────────────
# HOLDINGS VALUATION — Active vs Legacy classification
# ─────────────────────────────────────────────────────────────────────────────

def _holding_price(ticker):
    if ticker in live_prices: return live_prices[ticker]
    if ticker == "GOOG" and "GOOG" in prices: return float(prices["GOOG"].iloc[-1])
    if ticker == "GOOG" and "GOOGL" in live_prices: return live_prices["GOOGL"]
    if ticker in prices: return float(prices[ticker].iloc[-1])
    return None

def _price_on(ticker, target_date):
    """Price for a ticker as of a given date (or nearest prior trading day).
    Used for YTD performance baselines."""
    if ticker == "GOOG": ticker = "GOOG" if "GOOG" in prices else "GOOGL"
    s = prices.get(ticker)
    if s is None or len(s) == 0: return None
    sub = s.loc[s.index <= pd.Timestamp(target_date)]
    if len(sub) == 0: return None
    return float(sub.iloc[-1])

# YTD baseline date
ytd_start = pd.Timestamp(today.year, 1, 1)

# Build holding rows with classification
holdings_rows = []
for account, positions in HOLDINGS.items():
    is_active = account in ACTIVE_ACCOUNTS
    classification = "ACTIVE" if is_active else "LEGACY"
    for ticker, holding in positions.items():
        if ticker == "CASH":
            holdings_rows.append({
                "account": account, "classification": classification, "ticker": "CASH",
                "shares": None, "avg_cost": None, "price": None,
                "cost_basis": holding, "value": holding,
                "pnl_ltd": 0.0, "pnl_ltd_pct": 0.0,
                "ytd_value": holding, "ytd_pct": 0.0,
            })
            continue
        shares   = holding["shares"]
        avg_cost = holding["avg_cost"]
        price    = _holding_price(ticker)
        if price is None:
            print(f"  ⚠ no price for {ticker} ({account}) — using avg cost as placeholder")
            price = avg_cost
        cost_basis = shares * avg_cost
        value      = shares * price
        pnl_ltd    = value - cost_basis
        pnl_ltd_pct = (pnl_ltd / cost_basis * 100) if cost_basis > 0 else 0.0

        # YTD: price on Jan 1, 2026 (or nearest prior trading day)
        ytd_base_price = _price_on(ticker, ytd_start)
        if ytd_base_price is None or ytd_base_price <= 0:
            ytd_base_price = avg_cost  # safety fallback
        ytd_value_at_start = shares * ytd_base_price
        ytd_pct = ((value - ytd_value_at_start) / ytd_value_at_start * 100) if ytd_value_at_start > 0 else 0.0

        holdings_rows.append({
            "account": account, "classification": classification, "ticker": ticker,
            "shares": shares, "avg_cost": avg_cost, "price": price,
            "cost_basis": cost_basis, "value": value,
            "pnl_ltd": pnl_ltd, "pnl_ltd_pct": pnl_ltd_pct,
            "ytd_base_price": ytd_base_price, "ytd_value_at_start": ytd_value_at_start,
            "ytd_pct": ytd_pct,
        })

# Aggregate totals by classification
def _agg(rows, predicate):
    sub = [r for r in rows if predicate(r)]
    total_value = sum(r["value"] for r in sub)
    total_cost  = sum(r["cost_basis"] for r in sub if r["ticker"] != "CASH")
    total_pnl_ltd = sum(r["pnl_ltd"] for r in sub)
    total_ytd_start = sum(r["ytd_value_at_start"] for r in sub if r["ticker"] != "CASH") \
                    + sum(r["value"] for r in sub if r["ticker"] == "CASH")
    total_ytd_pct = ((total_value - total_ytd_start) / total_ytd_start * 100) if total_ytd_start > 0 else 0.0
    return {
        "value": total_value, "cost": total_cost,
        "pnl_ltd": total_pnl_ltd,
        "pnl_ltd_pct": (total_pnl_ltd / total_cost * 100) if total_cost > 0 else 0.0,
        "ytd_value_start": total_ytd_start,
        "ytd_pct": total_ytd_pct,
        "n_positions": len(sub),
    }

active_agg = _agg(holdings_rows, lambda r: r["classification"] == "ACTIVE")
legacy_agg = _agg(holdings_rows, lambda r: r["classification"] == "LEGACY")
total_agg  = _agg(holdings_rows, lambda r: True)

active_cash  = sum(r["value"] for r in holdings_rows if r["classification"] == "ACTIVE" and r["ticker"] == "CASH")
legacy_cash  = sum(r["value"] for r in holdings_rows if r["classification"] == "LEGACY" and r["ticker"] == "CASH")

print(f"\n── Portfolio Snapshot ──")
print(f"  ACTIVE  : ${active_agg['value']:>11,.0f} | LTD {active_agg['pnl_ltd']:+,.0f} ({active_agg['pnl_ltd_pct']:+.1f}%) | YTD {active_agg['ytd_pct']:+.2f}%")
print(f"  LEGACY  : ${legacy_agg['value']:>11,.0f} | LTD {legacy_agg['pnl_ltd']:+,.0f} ({legacy_agg['pnl_ltd_pct']:+.1f}%) | YTD {legacy_agg['ytd_pct']:+.2f}%")
print(f"  TOTAL   : ${total_agg['value']:>11,.0f} | LTD {total_agg['pnl_ltd']:+,.0f} ({total_agg['pnl_ltd_pct']:+.1f}%) | YTD {total_agg['ytd_pct']:+.2f}%")

# ─────────────────────────────────────────────────────────────────────────────
# MONTHLY ALLOCATION TABLE — WHOLE-PORTFOLIO matrix (strict, no overrides)
# ─────────────────────────────────────────────────────────────────────────────
# Logic:
#   1. Compute current $ for each sleeve at WHOLE-PORTFOLIO level (Active + Legacy)
#   2. BTC tracked separately, excluded from deployable universe
#   3. Target $ = zone_matrix_% × deployable_total
#   4. Gap = target − current. Positive = buy. Negative = over (display "OVER (locked)")
#   5. Monthly deployment input gets pro-rata distributed across positive gaps ONLY
#   6. SGOV gets allocated per its zone target % like any other sleeve
#   7. No "excess cash to redeploy" logic — the matrix budget is the truth

def _whole_portfolio_sleeve_value(sleeve):
    """Sum the current $ value for a sleeve across both Active + Legacy holdings."""
    v = 0.0
    if sleeve == "SPYL":
        # SPYL (IBKR) + VOO (IBKR active + Citi legacy)
        for r in holdings_rows:
            if r["ticker"] in ("SPYL", "VOO"):
                v += r["value"]
        return v
    if sleeve in MAG6_INTERNAL:  # NVDA, MSFT, META, GOOGL, AMZN, AAPL
        for r in holdings_rows:
            t = r["ticker"]
            if t == "GOOG": t = "GOOGL"  # GOOG = Class C of GOOGL; same sleeve
            if t == sleeve:
                v += r["value"]
        return v
    if sleeve == "SGOV":
        # Only the actual SGOV ETF position counts, not plain cash.
        # Per operational rule, plain cash is "uncommitted" and gets deployed
        # across all sleeves (including SGOV) via the matrix.
        for r in holdings_rows:
            if r["ticker"] == "SGOV":
                v += r["value"]
        return v
    if sleeve in ("SPACEX", "ANTHROPIC"):
        # Earmarks not yet allocated as tagged SGOV positions
        return 0.0
    return 0.0

# Whole-portfolio totals
active_capital = active_agg["value"]   # display only
legacy_capital = legacy_agg["value"]   # display only
total_portfolio = total_agg["value"]

# BTC is tracked but excluded from the deployable universe (legacy hold)
btc_value = sum(r["value"] for r in holdings_rows if r["ticker"] == "BTC")
deployable_total = total_portfolio - btc_value

# Plain cash sitting in IBKR (uncommitted — will be deployed via matrix).
# This is separate from the SGOV ETF position. Per Angelo's operational rule,
# all IBKR cash should be in SGOV, so plain cash is a transitional state.
plain_cash_ibkr = sum(r["value"] for r in holdings_rows
                      if r["ticker"] == "CASH" and r["classification"] == "ACTIVE")

zone_alloc = ZONE_ALLOCATION[current_zone]

# Build allocation rows — strict matrix, no priority overrides
alloc_rows = []

# 1. SPYL anchor
spyl_current = _whole_portfolio_sleeve_value("SPYL")
spyl_target_pct = zone_alloc["SPYL"]
spyl_target_dollar = deployable_total * spyl_target_pct
alloc_rows.append({
    "ticker": "SPYL",
    "sleeve": "Anchor",
    "current_dollar": spyl_current,
    "target_pct": spyl_target_pct,
    "target_dollar": spyl_target_dollar,
    "gap_dollar": spyl_target_dollar - spyl_current,
    "live_price": _holding_price("SPYL"),
    "notes": "Includes all VOO holdings (legacy + active) at whole-portfolio level",
    "action": FV_OVERLAY["SPYL"]["zone_action"][current_zone],
    "row_type": "equity",
})

# 2. Mag6 — one row per ticker, target at whole-portfolio level
mag6_envelope = zone_alloc["MAG6"]
for ticker in MAG6_ORDER:
    internal_w = MAG6_INTERNAL[ticker]
    target_pct = mag6_envelope * internal_w
    target_dollar = deployable_total * target_pct
    current_dollar = _whole_portfolio_sleeve_value(ticker)
    gap = target_dollar - current_dollar

    # Citi covers some Mag6 names — note for context, not for action override
    citi_overlay = ticker in ("AAPL", "GOOGL", "AMZN", "META")
    note = "Citi legacy overlay — whole-portfolio basis" if citi_overlay else ""

    alloc_rows.append({
        "ticker": ticker,
        "sleeve": "Mag6 Alpha",
        "current_dollar": current_dollar,
        "target_pct": target_pct,
        "target_dollar": target_dollar,
        "gap_dollar": gap,
        "live_price": _holding_price(ticker),
        "notes": note,
        "action": FV_OVERLAY[ticker]["zone_action"][current_zone],
        "row_type": "equity",
    })

# 3. SGOV parent + sub-rows (Cash Dry Powder, SpaceX, Anthropic)
# All three are held in SGOV ETF — parent row sums them, sub-rows show the breakdown.
sgov_current_etf = _whole_portfolio_sleeve_value("SGOV")  # actual SGOV ETF position
cash_dp_pct = zone_alloc["CASH"]
spx_pct     = zone_alloc["SPACEX"]
ant_pct     = zone_alloc["ANTHROPIC"]
sgov_parent_pct = cash_dp_pct + spx_pct + ant_pct  # combined target (e.g., 8% in Z3)

cash_dp_target = deployable_total * cash_dp_pct
spx_target     = deployable_total * spx_pct
ant_target     = deployable_total * ant_pct
sgov_parent_target = deployable_total * sgov_parent_pct

# SGOV ETF currently holds nothing — all three sub-allocations are at $0 current
cash_dp_current = sgov_current_etf  # all SGOV ETF treated as cash dry powder for now
spx_current     = 0.0
ant_current     = 0.0
sgov_parent_current = cash_dp_current + spx_current + ant_current

# SGOV PARENT row
alloc_rows.append({
    "ticker": "SGOV",
    "sleeve": "Cash + Earmarks (3 sub-allocations)",
    "current_dollar": sgov_parent_current,
    "target_pct": sgov_parent_pct,
    "target_dollar": sgov_parent_target,
    "gap_dollar": sgov_parent_target - sgov_parent_current,
    "live_price": None,
    "notes": f"Zone {current_zone} SGOV vehicle: {cash_dp_pct*100:.0f}% dry powder + {spx_pct*100:.0f}% SpaceX + {ant_pct*100:.0f}% Anthropic",
    "action": "Allocate per matrix",
    "row_type": "sgov_parent",
})
# Sub-row 1: Cash Dry Powder
alloc_rows.append({
    "ticker": "Cash Dry Powder",
    "sleeve": "SGOV sub-allocation",
    "current_dollar": cash_dp_current,
    "target_pct": cash_dp_pct,
    "target_dollar": cash_dp_target,
    "gap_dollar": cash_dp_target - cash_dp_current,
    "live_price": None,
    "notes": "Reserve for dip triggers and zone transitions",
    "action": "Allocate per matrix",
    "row_type": "sgov_sub",
})
# Sub-row 2: SpaceX Earmark
alloc_rows.append({
    "ticker": "SpaceX",
    "sleeve": "SGOV sub-allocation",
    "current_dollar": spx_current,
    "target_pct": spx_pct,
    "target_dollar": spx_target,
    "gap_dollar": spx_target - spx_current,
    "live_price": None,
    "notes": "Hold as tagged SGOV until SpaceX IPO",
    "action": "Hold in SGOV",
    "row_type": "sgov_sub",
})
# Sub-row 3: Anthropic Earmark
alloc_rows.append({
    "ticker": "Anthropic",
    "sleeve": "SGOV sub-allocation",
    "current_dollar": ant_current,
    "target_pct": ant_pct,
    "target_dollar": ant_target,
    "gap_dollar": ant_target - ant_current,
    "live_price": None,
    "notes": "Hold as tagged SGOV until Anthropic IPO",
    "action": "Hold in SGOV",
    "row_type": "sgov_sub",
})

# Sort order (top to bottom):
#   1. SGOV parent row
#   2. SGOV sub-rows (Cash Dry Powder, SpaceX, Anthropic) in that fixed order
#   3. Equity rows: positive gaps (BUY) first by size descending, then OVER by size ascending
SGOV_SUB_ORDER = {"Cash Dry Powder": 1, "SpaceX": 2, "Anthropic": 3}

def _sort_key(r):
    rt = r.get("row_type", "equity")
    if rt == "sgov_parent":
        return (0, 0, 0)        # very first
    if rt == "sgov_sub":
        return (1, SGOV_SUB_ORDER.get(r["ticker"], 99), 0)  # parent's subs in fixed order
    # Equity rows
    has_gap = -(r["gap_dollar"] > 100)   # positive gaps first within equity group
    return (2, has_gap, -r["gap_dollar"])

alloc_rows.sort(key=_sort_key)

# ─────────────────────────────────────────────────────────────────────────────
# PERFORMANCE CHART DATA — SPYL · MAG6 · PORTFOLIO
# ─────────────────────────────────────────────────────────────────────────────

# Build PORTFOLIO synthetic price series (active + legacy combined, indexed to 100)
def _build_portfolio_series():
    """Construct a synthetic 'My Portfolio' series weighted by current holdings."""
    # Use current value weights across all holdings as the constant weighting
    weights = {}
    for r in holdings_rows:
        if r["ticker"] == "CASH": continue
        t = r["ticker"]
        if t == "GOOG": t = "GOOGL"  # use GOOGL price series for GOOG
        if t == "VOO":  t = "SPY"    # use SPY price series for VOO (parallel)
        weights[t] = weights.get(t, 0) + r["value"]
    total_w = sum(weights.values())
    if total_w == 0: return None
    for t in weights:
        weights[t] /= total_w

    # Build weighted index
    components = []
    for t, w in weights.items():
        s = prices.get(t)
        if s is None or len(s) < 20: continue
        components.append((s / s.iloc[0] * 100) * w)
    if not components: return None
    basket = pd.concat(components, axis=1).sum(axis=1)
    return basket / basket.iloc[0] * 100

prices["PORTFOLIO"] = _build_portfolio_series()
if prices["PORTFOLIO"] is None:
    print("  ⚠ Portfolio synthetic series failed — using MAG6 as proxy")
    prices["PORTFOLIO"] = prices.get("MAG6")

horizons_cfg = {
    "7D":  {"back": pd.DateOffset(days=7),   "fwd": pd.DateOffset(days=7),   "kind":"gbm"},
    "30D": {"back": pd.DateOffset(days=30),  "fwd": pd.DateOffset(days=30),  "kind":"gbm"},
    "6M":  {"back": pd.DateOffset(months=6), "fwd": pd.DateOffset(months=6), "kind":"gbm"},
    "YTD": {"back": None,                    "fwd": pd.DateOffset(months=6), "kind":"cagr"},
    "1Y":  {"back": pd.DateOffset(years=1),  "fwd": pd.DateOffset(years=1),  "kind":"cagr"},
    "5Y":  {"back": pd.DateOffset(years=5),  "fwd": pd.DateOffset(years=5),  "kind":"cagr"},
}

all_data = {}
for hkey, hcfg in horizons_cfg.items():
    hist_start = (pd.Timestamp(today.year, 1, 1)
                  if hkey == "YTD"
                  else today - hcfg["back"])
    proj_end = today + hcfg["fwd"]
    kind     = hcfg["kind"]
    h_data   = {}

    for key in ["SPYL", "MAG6", "PORTFOLIO"]:
        raw_s = prices.get(key)
        if raw_s is None: continue

        sliced = raw_s.loc[(raw_s.index >= hist_start) & (raw_s.index <= today)].dropna()
        if len(sliced) < 2: continue

        normed   = sliced / sliced.iloc[0] * 100
        hist_pts = [(str(d.date()), round(float(v), 2)) for d, v in normed.items()]

        lv    = float(normed.iloc[-1])
        lp    = float(sliced.iloc[-1])
        ld    = normed.index[-1].to_pydatetime()
        rate  = FWD_CAGR[key]
        vol   = VOLS[key]
        seed  = abs(hash(f"{key}:{hkey}")) % (2**31)

        if kind == "cagr":
            proj_pts = proj_cagr(lv, ld, proj_end, rate)
        else:
            proj_pts = proj_gbm(lv, ld, proj_end, rate, vol, seed)

        entry = {
            "hist": hist_pts, "proj": proj_pts,
            "ret":  round(lv - 100, 2),
            "base_price": round(float(sliced.iloc[0]), 2),
            "base_date":  str(sliced.index[0].date()),
            "last_price": round(lp, 2),
        }
        yrs = (normed.index[-1] - normed.index[0]).days / 365.25
        entry["cagr"] = round((float(normed.iloc[-1]/normed.iloc[0])**(1/yrs)-1)*100, 1) if yrs > 0.1 else None

        h_data[key] = entry

    all_data[hkey] = h_data

# ── TIMESTAMP ─────────────────────────────────────────────────────────────────
now_manila    = datetime.utcnow() + timedelta(hours=8)
next_manila   = (now_manila + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0)
fetched_at    = now_manila.strftime("%b %d, %Y %H:%M PHT")
next_refresh  = next_manila.strftime("%b %d, %Y 14:00 PHT")

# ── JSON PAYLOAD ──────────────────────────────────────────────────────────────
payload = json.dumps({
    "horizons":     all_data,
    "yc":           {"horizons": yc_data, "current_spread": round(current_spread, 4),
                     "current_zone": current_zone, "ou_mu": OU_MU,
                     "zone_boundaries": ZONE_BOUNDARIES},
    "zone_alloc":   {str(k): v for k, v in ZONE_ALLOCATION.items()},
    "zone_meta":    {str(k): v for k, v in ZONE_META.items()},
    "alloc_rows":   alloc_rows,
    "active_capital": active_capital,
    "plain_cash":   plain_cash_ibkr,
    "monthly_input": 12820,
    "fetched_at":   fetched_at,
}, separators=(",",":"))

print(f"\nGenerating index.html...")
# ─────────────────────────────────────────────────────────────────────────────
# HTML RENDERING
# ─────────────────────────────────────────────────────────────────────────────

zone_color  = ZONE_META[current_zone]["color"]
zone_bg     = ZONE_META[current_zone]["bg"]
zone_label  = ZONE_META[current_zone]["label"]
zone_desc   = ZONE_META[current_zone]["desc"]
spread_fmt  = f"{current_spread:+.2f}%"

# ── HTML formatters ──
def _fmt_usd(v, dec=0):
    if v is None: return "—"
    try:
        if dec == 0: return f"${int(round(v)):,}"
        return f"${v:,.{dec}f}"
    except Exception:
        return "—"

def _fmt_shares(s):
    if s is None: return "—"
    if s < 1: return f"{s:.4f}"
    return f"{int(s):,}" if s == int(s) else f"{s:,.2f}"

def _fmt_pct(v, dec=1):
    if v is None: return "—"
    return f"{v:+.{dec}f}%"

# ── Build allocation table rows HTML (initial render — JS re-renders on input change) ──
# LOGIC: Matrix-weight allocation renormalized to under-target ("open") sleeves only.
#
# Special handling for SGOV parent + sub-rows:
#   - The SGOV "parent" row (row_type=sgov_parent) is a display-only aggregator.
#   - The 3 sub-rows (row_type=sgov_sub) are the actual matrix sleeves at 4%/2%/2%.
#   - Renormalization uses SUB-rows + equity rows (NOT the parent — would double-count).
#   - Parent's Allocation $ = sum of its 3 sub-rows' allocations (computed after).
#
# Default deployment = monthly input ($12,820) + plain IBKR cash (deployed in full).
default_monthly = 12820.0
default_deploy = default_monthly + plain_cash_ibkr   # full pool

# Identify open sleeves (positive gap) — EXCLUDING sgov_parent (sub-rows carry the math)
_open_rows = [r for r in alloc_rows
              if r["gap_dollar"] > 100 and r.get("row_type") != "sgov_parent"]
_closed_rows = [r for r in alloc_rows if r["gap_dollar"] <= 100 and r.get("row_type") != "sgov_parent"]

# Sum of matrix target percentages for OPEN sleeves (used for renormalization)
_open_matrix_total = sum(r["target_pct"] for r in _open_rows)

# Compute allocation $ per row by pure matrix weight (no gap cap).
# Per user preference: always deploy the full input, allow slight overshoot
# of individual sleeves rather than leaving cash unallocated.
_alloc_amts = {}
for r in _open_rows:
    if _open_matrix_total > 0:
        renorm_share = r["target_pct"] / _open_matrix_total
        amt = default_deploy * renorm_share
        _alloc_amts[r["ticker"]] = amt
    else:
        _alloc_amts[r["ticker"]] = 0.0

# Aggregate sub-row allocations into the SGOV parent (display only)
_sgov_parent_alloc = sum(_alloc_amts.get(t, 0.0) for t in ("Cash Dry Powder", "SpaceX", "Anthropic"))
_alloc_amts["SGOV"] = _sgov_parent_alloc   # for display in the parent row

# Total: sum unique sleeves only (don't double-count parent)
_total_allocated = sum(amt for t, amt in _alloc_amts.items() if t != "SGOV")
_unallocated = max(0.0, default_deploy - _total_allocated)

# Tree characters for sub-rows
SGOV_SUB_TREE = {"Cash Dry Powder": "├─", "SpaceX": "├─", "Anthropic": "└─"}

alloc_rows_html = ""
for r in alloc_rows:
    gap = r["gap_dollar"]
    gap_sign = "+" if gap > 0 else ""
    row_type = r.get("row_type", "equity")
    is_parent = row_type == "sgov_parent"
    is_sub = row_type == "sgov_sub"

    if gap > 100:
        gap_cls = "alloc-red"
        alloc_amt = _alloc_amts.get(r["ticker"], 0.0)
        alloc_str = f"${alloc_amt:,.0f}" if alloc_amt > 0 else "—"
        # Shares column
        if r["ticker"] in ("SpaceX", "Anthropic", "SGOV", "Cash Dry Powder"):
            shares_str = "—"
        elif r["live_price"] and r["live_price"] > 0 and alloc_amt > 0:
            n = int(alloc_amt / r["live_price"])
            shares_str = str(n) if n > 0 else "<1"
        else:
            shares_str = "—"
    elif gap < -100:
        gap_cls = "alloc-green"
        alloc_str = "—"
        shares_str = "OVER (locked)"
    else:
        gap_cls = "alloc-ok"
        alloc_str = "—"
        shares_str = "—"

    # Row class + ticker display formatting
    if is_parent:
        row_cls = "alloc-sgov-parent"
        ticker_display = f"<strong>{r['ticker']}</strong><div class='alloc-sleeve'>{r['sleeve']}</div>"
    elif is_sub:
        row_cls = "alloc-sgov-sub"
        tree = SGOV_SUB_TREE.get(r["ticker"], "├─")
        ticker_display = f"<span class='alloc-tree'>{tree}</span> {r['ticker']}<div class='alloc-sleeve alloc-sub-sleeve'>{r['sleeve']}</div>"
    else:
        row_cls = ""
        ticker_display = f"<strong>{r['ticker']}</strong><div class='alloc-sleeve'>{r['sleeve']}</div>"

    price_str = _fmt_usd(r["live_price"], 2) if r["live_price"] else "—"
    action_str = r["action"] or "—"
    notes_str = r["notes"] or ""
    alloc_rows_html += f"""
        <tr class="{row_cls}">
          <td>{ticker_display}</td>
          <td class="alloc-num">{r['target_pct']*100:.2f}%</td>
          <td class="alloc-num">{_fmt_usd(r['current_dollar'])}</td>
          <td class="alloc-num">{_fmt_usd(r['target_dollar'])}</td>
          <td class="alloc-num {gap_cls}">{gap_sign}{_fmt_usd(gap)}</td>
          <td class="alloc-num">{price_str}</td>
          <td class="alloc-num"><strong>{alloc_str}</strong></td>
          <td class="alloc-num">{shares_str}</td>
          <td><span class="alloc-act">{action_str}</span><div class="alloc-note">{notes_str}</div></td>
        </tr>"""

# Totals row — clean, no parenthetical breakdown
alloc_rows_html += f"""
        <tr class="alloc-totals">
          <td colspan="6"><strong>TOTAL DEPLOYED</strong></td>
          <td class="alloc-num"><strong>${_total_allocated:,.0f}</strong></td>
          <td class="alloc-num">—</td>
          <td><span class="alloc-note">{'Unallocated $'+f'{_unallocated:,.0f}' if _unallocated > 10 else 'Fully deployed'}</span></td>
        </tr>"""

# ── Build holdings tables (Active + Legacy) ──
def _build_holdings_table(predicate, title):
    rows_html = ""
    for r in [hr for hr in holdings_rows if predicate(hr)]:
        is_cash = r["ticker"] == "CASH"
        ltd_cls = "pos" if r["pnl_ltd"] >= 0 else "neg"
        ytd_cls = "pos" if r["ytd_pct"] >= 0 else "neg"
        ltd_sign = "+" if r["pnl_ltd"] >= 0 else ""
        ytd_sign = "+" if r["ytd_pct"] >= 0 else ""
        acc_lbl = ACCOUNT_LABELS.get(r["account"], r["account"])
        rows_html += f"""
            <tr class="hold-row{' hold-cash' if is_cash else ''}">
              <td>{acc_lbl}</td>
              <td><strong>{r['ticker']}</strong></td>
              <td class="hold-num">{_fmt_shares(r['shares'])}</td>
              <td class="hold-num">{_fmt_usd(r['price'], 2) if r['price'] else '—'}</td>
              <td class="hold-num"><strong>{_fmt_usd(r['value'])}</strong></td>
              <td class="hold-num {ytd_cls}">{ytd_sign}{r['ytd_pct']:.1f}%</td>
              <td class="hold-num {ltd_cls}">{ltd_sign}{_fmt_usd(r['pnl_ltd']) if not is_cash else '—'}</td>
              <td class="hold-num {ltd_cls}">{(ltd_sign + f"{r['pnl_ltd_pct']:.1f}%") if not is_cash else '—'}</td>
            </tr>"""
    return rows_html

active_rows_html = _build_holdings_table(lambda r: r["classification"] == "ACTIVE", "ACTIVE")
legacy_rows_html = _build_holdings_table(lambda r: r["classification"] == "LEGACY", "LEGACY")

# ── Mag6 internal weight footer string ──
mag6_footer = " / ".join([f"{t} {int(w*100)}%" for t, w in MAG6_INTERNAL.items()])

# ── Zone-allocation chip row for header ──
z_chip = ZONE_ALLOCATION[current_zone]
zone_chip_html = f"""
      <div class="zone-alloc-chip"><span>{z_chip['SPYL']*100:.0f}%</span><small>SPYL Anchor</small></div>
      <div class="zone-alloc-chip"><span>{z_chip['MAG6']*100:.0f}%</span><small>Mag6 Alpha</small></div>
      <div class="zone-alloc-chip"><span>{z_chip['SPACEX']*100:.0f}%</span><small>SpaceX</small></div>
      <div class="zone-alloc-chip"><span>{z_chip['ANTHROPIC']*100:.0f}%</span><small>Anthropic</small></div>
      <div class="zone-alloc-chip"><span>{z_chip['CASH']*100:.0f}%</span><small>SGOV Cash</small></div>"""

# ─────────────────────────────────────────────────────────────────────────────
# HTML STRING
# ─────────────────────────────────────────────────────────────────────────────

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Investment Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@700;800&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet"/>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#f8f7f4;--surf:#ffffff;--surf2:#f3f2ef;
  --bdr:#e2e0db;--bdr2:#ccc9c2;
  --txt:#1a1814;--mut:#7c7970;--dim:#f0efe9;
  --grn:#15803d;--red:#b91c1c;--amb:#b45309;
  --spyl:#16a34a;--mag6:#1d4ed8;--port:#7c3aed;
  --zone:{zone_color};
}}
html,body{{background:var(--bg);color:var(--txt);font-family:'DM Mono',monospace;font-size:13px;min-height:100vh}}
.page{{max-width:1280px;margin:0 auto;padding:32px 24px 64px}}

/* ── HEADER ── */
.hdr{{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:8px;flex-wrap:wrap;gap:12px;border-bottom:1.5px solid var(--txt);padding-bottom:14px}}
.hdr-left h1{{font-family:'Syne',sans-serif;font-size:28px;font-weight:800;letter-spacing:-1px;line-height:1}}
.hdr-left h1 em{{font-family:'Instrument Serif',serif;font-style:italic;font-weight:400;color:var(--mut)}}
.hdr-sub{{font-size:9px;color:var(--mut);letter-spacing:.15em;text-transform:uppercase;margin-top:4px}}
.src{{font-size:9px;color:var(--mut);margin-bottom:24px;display:flex;align-items:center;gap:6px}}
.src-dot{{width:6px;height:6px;border-radius:50%;background:#22c55e;flex-shrink:0;animation:pulse 2s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.4}}}}

/* ── SECTION LABELS ── */
.section-hd{{font-size:9px;letter-spacing:.18em;text-transform:uppercase;color:var(--mut);margin-bottom:14px;padding-bottom:6px;border-bottom:.5px solid var(--bdr);display:flex;justify-content:space-between;align-items:center}}

/* ── ZONE BANNER ── */
.zone-banner{{background:{zone_bg};border:1px solid {zone_color}33;border-radius:8px;padding:14px 18px;margin-bottom:24px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}}
.zone-pill{{background:{zone_color};color:#fff;font-family:'Syne',sans-serif;font-size:13px;font-weight:700;padding:5px 14px;border-radius:20px;letter-spacing:.03em;white-space:nowrap}}
.zone-spread{{font-size:22px;font-family:'Syne',sans-serif;font-weight:700;color:{zone_color}}}
.zone-desc{{font-size:11px;color:var(--mut)}}
.zone-alloc-row{{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;width:100%}}
.zone-alloc-chip{{background:var(--surf);border:.5px solid var(--bdr);border-radius:4px;padding:4px 10px;font-size:10px;text-align:center}}
.zone-alloc-chip span{{display:block;font-size:16px;font-weight:600;color:var(--txt);line-height:1.2}}
.zone-alloc-chip small{{color:var(--mut)}}

/* ── MONTHLY ALLOCATION TABLE ── */
.alloc-section{{margin-bottom:32px}}
.alloc-input-row{{display:flex;align-items:center;gap:12px;margin-bottom:16px;flex-wrap:wrap}}
.alloc-input-lbl{{font-size:10px;color:var(--mut);white-space:nowrap}}
.alloc-input{{font-family:'DM Mono',monospace;font-size:18px;font-weight:500;color:var(--txt);border:1.5px solid var(--zone);border-radius:6px;padding:7px 14px;width:180px;background:var(--surf);outline:none}}
.alloc-input:focus{{border-color:var(--txt);box-shadow:0 0 0 3px rgba(0,0,0,.06)}}
.alloc-hint{{font-size:9px;color:var(--mut)}}
.alloc-cap{{font-size:11px;color:var(--mut);margin-bottom:12px}}
.alloc-cap strong{{color:var(--txt);font-weight:600}}
.alloc-table{{width:100%;border-collapse:collapse;font-size:11px;background:var(--surf);border:.5px solid var(--bdr);border-radius:6px;overflow:hidden}}
.alloc-table th{{font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:var(--mut);padding:8px 10px;text-align:left;border-bottom:1px solid var(--bdr);white-space:nowrap;background:var(--surf2)}}
.alloc-table td{{padding:10px;border-bottom:.5px solid var(--bdr);vertical-align:middle}}
.alloc-table tr:last-child td{{border-bottom:none}}
.alloc-table tr:hover td{{background:var(--dim)}}
.alloc-num{{text-align:right;font-variant-numeric:tabular-nums}}
.alloc-sleeve{{font-size:9px;color:var(--mut);margin-top:1px}}
.alloc-act{{font-size:10px;font-weight:600}}
.alloc-note{{font-size:9px;color:var(--mut);margin-top:2px;font-style:italic}}
.alloc-red{{color:var(--red);font-weight:600}}      /* needs action (gap) */
.alloc-green{{color:var(--grn);font-weight:600}}    /* at-target / done */
.alloc-ok{{color:var(--mut)}}
/* Backward compat aliases — older classes redirect to new semantics */
.alloc-buy{{color:var(--red);font-weight:600}}      /* legacy: buy = action = red */
.alloc-sell{{color:var(--grn);font-weight:600}}     /* legacy: over/sell = done = green */
.alloc-totals{{background:var(--surf2);border-top:1.5px solid var(--bdr2);font-weight:600}}
.alloc-totals td{{padding:11px 10px}}
/* SGOV parent row — slightly emphasized */
.alloc-sgov-parent{{background:var(--surf2);border-top:.5px solid var(--bdr2);border-bottom:.5px solid var(--bdr)}}
.alloc-sgov-parent td{{padding-top:11px;padding-bottom:6px;font-weight:500}}
/* SGOV sub-rows — indented, smaller, muted */
.alloc-sgov-sub{{background:#fafaf7}}
.alloc-sgov-sub td{{padding-top:6px;padding-bottom:6px;font-size:10.5px;color:#7c7970}}
.alloc-sgov-sub td:first-child{{padding-left:22px}}
.alloc-sgov-sub .alloc-num{{color:#7c7970}}
.alloc-tree{{color:#a8a59c;font-family:monospace;margin-right:4px;font-size:10px}}
.alloc-sub-sleeve{{opacity:.7}}
/* SGOV block ends before equities — border separator */
.alloc-sgov-sub:last-of-type{{border-bottom:1px solid var(--bdr2)}}

/* ── HOLDINGS — ACTIVE / LEGACY / TOTAL ── */
.hold-section{{margin-bottom:32px}}
.hold-trio{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:16px}}
@media(max-width:780px){{.hold-trio{{grid-template-columns:1fr}}}}
.hold-summary-card{{background:var(--surf);border:.5px solid var(--bdr);border-radius:6px;padding:14px 16px}}
.hold-summary-card.active{{border-left:3px solid var(--mag6)}}
.hold-summary-card.legacy{{border-left:3px solid var(--mut)}}
.hold-summary-card.total{{border-left:3px solid var(--zone)}}
.hold-card-lbl{{font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:var(--mut);margin-bottom:6px}}
.hold-card-val{{font-family:'Syne',sans-serif;font-size:22px;font-weight:700;color:var(--txt);margin-bottom:6px}}
.hold-card-row{{display:flex;justify-content:space-between;font-size:10px;color:var(--mut);padding:3px 0}}
.hold-card-row strong{{font-family:'DM Mono',monospace;font-weight:500;color:var(--txt)}}
.hold-subhd{{font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:var(--mut);margin:18px 0 8px;padding-bottom:4px;border-bottom:.5px solid var(--bdr)}}
.hold-table{{width:100%;border-collapse:collapse;font-size:11px;background:var(--surf);border:.5px solid var(--bdr);border-radius:6px;overflow:hidden}}
.hold-table th{{font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:var(--mut);padding:7px 10px;text-align:left;border-bottom:1px solid var(--bdr);background:var(--surf2);white-space:nowrap}}
.hold-table td{{padding:8px 10px;border-bottom:.5px solid var(--bdr);vertical-align:middle}}
.hold-table tr:last-child td{{border-bottom:none}}
.hold-num{{text-align:right;font-variant-numeric:tabular-nums}}
.hold-cash{{background:var(--dim);font-style:italic;opacity:.85}}
.pos{{color:var(--grn)}} .neg{{color:var(--red)}}

/* ── PERFORMANCE CHART ── */
.chart-section{{margin-bottom:32px}}
.ctrls{{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:12px}}
.cl{{font-size:9px;color:var(--mut);letter-spacing:.06em}}
.tog{{font-size:10px;padding:4px 11px;border-radius:4px;border:.5px solid var(--bdr2);background:transparent;color:var(--mut);cursor:pointer;font-family:'DM Mono',monospace}}
.tog.on{{background:var(--txt);color:#fff;border-color:var(--txt)}}
.vsep{{width:1px;height:18px;background:var(--bdr);margin:0 4px}}
.tabs{{display:flex;border-bottom:1px solid var(--bdr);margin-bottom:12px}}
.tab{{font-size:10px;padding:7px 16px;border:none;background:transparent;color:var(--mut);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;font-family:'DM Mono',monospace;letter-spacing:.04em}}
.tab.on{{color:var(--txt);border-bottom-color:var(--txt)}}
.cards{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-bottom:12px}}
.card{{background:var(--surf);border-radius:6px;border:.5px solid var(--bdr);border-top:2px solid transparent;padding:11px 13px}}
.card-lbl{{font-size:9px;color:var(--mut);letter-spacing:.1em;margin-bottom:4px}}
.card-val{{font-size:20px;font-weight:500;margin-bottom:2px}}
.card-sub{{font-size:9px;color:var(--mut)}}
.card-base{{font-size:9px;color:var(--mut);opacity:.5;margin-top:2px}}
.legend{{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:8px;font-size:9px;color:var(--mut)}}
.li{{display:flex;align-items:center;gap:5px}}
.ln{{width:18px;height:2px;flex-shrink:0}}
.ld{{width:18px;height:2px;background-image:repeating-linear-gradient(90deg,currentColor 0,currentColor 4px,transparent 4px,transparent 8px)}}
.note{{font-size:9px;color:var(--mut);opacity:.6;margin-bottom:6px;line-height:1.5}}
.chart-wrap{{position:relative;width:100%;height:400px}}
.outperf{{display:flex;gap:14px;flex-wrap:wrap;margin-top:8px;min-height:18px;font-size:10px;color:var(--mut)}}
.op span{{font-size:10px}}

/* ── FAIR VALUE CARDS ── */
.fv-section{{margin-bottom:32px}}
.fv-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:12px}}
.fv-card{{background:var(--surf);border:.5px solid var(--bdr);border-radius:8px;padding:14px 16px}}
.fv-head{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px}}
.fv-tk{{font-family:'Syne',sans-serif;font-size:18px;font-weight:800;color:var(--txt)}}
.fv-co{{font-size:10px;color:var(--mut);margin-top:1px}}
.fv-bdg{{font-size:9px;padding:3px 8px;border-radius:3px;font-weight:600;letter-spacing:.04em;white-space:nowrap}}
.fv-buy{{background:#dcfce7;color:#166534}}
.fv-hold{{background:#fef3c7;color:#92400e}}
.fv-cau{{background:#fee2e2;color:#991b1b}}
.fv-dca{{background:#dbeafe;color:#1e40af}}
.fv-price-row{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:8px}}
.fv-price-block{{padding:8px 0}}
.fv-price-lbl{{font-size:8px;letter-spacing:.1em;color:var(--mut);margin-bottom:3px}}
.fv-price-val{{font-family:'Syne',sans-serif;font-size:16px;font-weight:700;color:var(--txt)}}
.fv-range{{display:flex;justify-content:space-between;font-size:9px;color:var(--mut);padding:6px 0;border-top:.5px solid var(--bdr);border-bottom:.5px solid var(--bdr);margin-bottom:10px}}
.fv-met-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin-bottom:10px}}
.fv-met{{background:var(--surf2);border-radius:4px;padding:6px 8px}}
.fv-met-lbl{{font-size:8px;color:var(--mut);letter-spacing:.05em;margin-bottom:2px}}
.fv-met-val{{font-size:13px;font-weight:600;color:var(--txt)}}
.fv-action{{background:var(--surf2);border-radius:4px;padding:8px 10px;margin-bottom:8px}}
.fv-action-lbl{{font-size:8px;color:var(--mut);letter-spacing:.1em;margin-bottom:2px}}
.fv-action-val{{font-size:13px;font-weight:600}}
.fv-meta{{font-size:9px;color:var(--mut);line-height:1.6}}
.fv-meta div{{display:flex;justify-content:space-between;padding:2px 0}}
.fv-meta strong{{color:var(--txt);font-family:'DM Mono',monospace;font-weight:500}}
.fv-dip{{background:var(--surf2);border:.5px solid var(--bdr);border-radius:4px;padding:8px 10px;margin-top:8px;font-size:10px}}
.fv-dip-hd{{font-size:8px;letter-spacing:.1em;color:var(--mut);margin-bottom:4px}}
.fv-dip-val{{font-family:'Syne',sans-serif;font-size:16px;font-weight:700;margin-bottom:2px}}
.fv-dip-msg{{font-size:10px;color:var(--mut);margin-bottom:5px}}
.fv-dip-scale{{display:flex;justify-content:space-between;font-size:8px;color:var(--mut)}}
.fv-disc{{font-size:9px;color:var(--mut);margin-top:12px;line-height:1.6;opacity:.8}}
.dep-green{{color:#15803d}}
.dep-amber{{color:#b45309}}
.dep-red{{color:#b91c1c}}
.dep-neutral{{color:var(--mut)}}

/* ── YIELD CURVE ── */
.yc-section{{margin-bottom:32px}}
.yc-tabs{{display:flex;border-bottom:1px solid var(--bdr);margin-bottom:12px}}
.yc-tab{{font-size:10px;padding:7px 16px;border:none;background:transparent;color:var(--mut);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;letter-spacing:.05em}}
.yc-tab.on{{color:var(--txt);border-bottom-color:var(--zone)}}
.yc-wrap{{position:relative;width:100%;height:220px}}
.yc-legend{{display:flex;gap:16px;flex-wrap:wrap;margin-top:8px;font-size:9px;color:var(--mut)}}
.yc-li{{display:flex;align-items:center;gap:5px}}
.yc-ln{{width:18px;height:2px;flex-shrink:0}}
.yc-ld{{width:18px;height:2px;background-image:repeating-linear-gradient(90deg,currentColor 0,currentColor 4px,transparent 4px,transparent 8px)}}

/* ── FOOTER ── */
hr{{border:none;border-top:.5px solid var(--bdr);margin:24px 0 12px}}
.footer{{font-size:9px;color:var(--mut);line-height:2;text-align:center}}

@media(max-width:700px){{
  .cards{{grid-template-columns:1fr}}
  .tab,.yc-tab{{padding:6px 10px;font-size:9px}}
  /* On mobile, hide Current $, Target $, Live Price, Shares — keep Ticker, Target %, Gap $, Allocation $, Zone Action */
  .alloc-table th:nth-child(3),.alloc-table td:nth-child(3),
  .alloc-table th:nth-child(4),.alloc-table td:nth-child(4),
  .alloc-table th:nth-child(6),.alloc-table td:nth-child(6),
  .alloc-table th:nth-child(8),.alloc-table td:nth-child(8){{display:none}}
}}
</style>
</head>
<body>
<div class="page">

  <!-- HEADER -->
  <div class="hdr">
    <div class="hdr-left">
      <h1>Investment Dashboard <em>v{SCRIPT_VERSION}</em></h1>
      <div class="hdr-sub">SPYL Anchor · Mag6 Alpha · Strategic Earmarks · Active vs Legacy</div>
    </div>
    <div style="text-align:right">
      <div style="font-family:'Syne',sans-serif;font-size:11px;font-weight:700;color:var(--zone)">{zone_label}</div>
      <div style="font-size:9px;color:var(--mut);margin-top:2px">{zone_desc}</div>
    </div>
  </div>
  <div class="src">
    <span class="src-dot"></span>
    <span>Refreshed: {fetched_at} · Next: {next_refresh} · Twelve Data + FRED</span>
  </div>

  <!-- ZONE BANNER -->
  <div class="zone-banner">
    <div>
      <div style="font-size:9px;color:{zone_color};letter-spacing:.12em;text-transform:uppercase;margin-bottom:3px">10yr − 3mo Treasury Spread</div>
      <div class="zone-spread">{spread_fmt}</div>
    </div>
    <div class="zone-pill">{zone_label}</div>
    <div>
      <div style="font-size:9px;color:var(--mut)">OU mean reversion target</div>
      <div style="font-size:16px;font-weight:600;color:var(--mut)">+{OU_MU:.1f}% long-run</div>
    </div>
    <div class="zone-alloc-row">{zone_chip_html}
    </div>
  </div>


  <!-- ─────────────────────────────────────────────────────────────── -->
  <!-- 1. MONTHLY ALLOCATION TABLE (replaces Monday Action Table)       -->
  <!-- ─────────────────────────────────────────────────────────────── -->
  <div class="alloc-section">
    <div class="section-hd">
      <span>1 · MONTHLY ALLOCATION TABLE</span>
      <span style="font-size:9px;color:var(--zone)">Zone {current_zone} · Deployable: ${deployable_total:,.0f} (Total ${total_portfolio:,.0f} − BTC ${btc_value:,.0f} legacy)</span>
    </div>
    <div class="alloc-input-row">
      <span class="alloc-input-lbl">Deployment input (USD):</span>
      <input class="alloc-input" type="number" id="deployInput" value="{int(default_deploy)}" min="0" step="100" oninput="renderAllocTable()"/>
      <span class="alloc-hint">Default = $12,820 monthly + ${int(plain_cash_ibkr):,} plain IBKR cash → matrix-weight distribution</span>
    </div>
    <div class="alloc-cap">
      <strong>Strict zone matrix</strong> at whole-portfolio level (Active + Legacy combined, BTC excluded as legacy hold).
      Allocation distributes by matrix weight, renormalized to under-target ("open") sleeves. Full deployment input is always placed — some sleeves may temporarily exceed target by a small margin (resolves on next allocation cycle).
      <strong>RED gap</strong> = action needed (under target). <strong>GREEN gap</strong> = at-target or over (Citi-locked positions, structural).
    </div>
    <table class="alloc-table">
      <thead>
        <tr>
          <th>Ticker / Sleeve</th>
          <th class="alloc-num">Target %</th>
          <th class="alloc-num">Current $</th>
          <th class="alloc-num">Target $</th>
          <th class="alloc-num">Gap $</th>
          <th class="alloc-num">Live Price</th>
          <th class="alloc-num">Allocation $</th>
          <th class="alloc-num">Shares</th>
          <th>Zone Action</th>
        </tr>
      </thead>
      <tbody id="allocBody">{alloc_rows_html}
      </tbody>
    </table>
  </div>

  <!-- ─────────────────────────────────────────────────────────────── -->
  <!-- 2. HOLDINGS SNAPSHOT — Active / Legacy / Total                   -->
  <!-- ─────────────────────────────────────────────────────────────── -->
  <div class="hold-section">
    <div class="section-hd">
      <span>2 · HOLDINGS SNAPSHOT</span>
      <span style="font-size:9px">Active · Legacy · Total · YTD & life-to-date P&amp;L</span>
    </div>

    <!-- Summary trio -->
    <div class="hold-trio">
      <div class="hold-summary-card active">
        <div class="hold-card-lbl">Active Holdings (IBKR)</div>
        <div class="hold-card-val">${active_agg['value']:,.0f}</div>
        <div class="hold-card-row"><span>YTD</span><strong class="{('pos' if active_agg['ytd_pct']>=0 else 'neg')}">{('+' if active_agg['ytd_pct']>=0 else '')}{active_agg['ytd_pct']:.2f}%</strong></div>
        <div class="hold-card-row"><span>Life-to-date G/L</span><strong class="{('pos' if active_agg['pnl_ltd']>=0 else 'neg')}">{('+' if active_agg['pnl_ltd']>=0 else '')}${active_agg['pnl_ltd']:,.0f} ({active_agg['pnl_ltd_pct']:+.1f}%)</strong></div>
        <div class="hold-card-row"><span>Positions</span><strong>{active_agg['n_positions']}</strong></div>
      </div>
      <div class="hold-summary-card legacy">
        <div class="hold-card-lbl">Legacy Holdings (Citi + BTC)</div>
        <div class="hold-card-val">${legacy_agg['value']:,.0f}</div>
        <div class="hold-card-row"><span>YTD</span><strong class="{('pos' if legacy_agg['ytd_pct']>=0 else 'neg')}">{('+' if legacy_agg['ytd_pct']>=0 else '')}{legacy_agg['ytd_pct']:.2f}%</strong></div>
        <div class="hold-card-row"><span>Life-to-date G/L</span><strong class="{('pos' if legacy_agg['pnl_ltd']>=0 else 'neg')}">{('+' if legacy_agg['pnl_ltd']>=0 else '')}${legacy_agg['pnl_ltd']:,.0f} ({legacy_agg['pnl_ltd_pct']:+.1f}%)</strong></div>
        <div class="hold-card-row"><span>Positions</span><strong>{legacy_agg['n_positions']}</strong></div>
      </div>
      <div class="hold-summary-card total">
        <div class="hold-card-lbl">Total Portfolio</div>
        <div class="hold-card-val">${total_agg['value']:,.0f}</div>
        <div class="hold-card-row"><span>YTD</span><strong class="{('pos' if total_agg['ytd_pct']>=0 else 'neg')}">{('+' if total_agg['ytd_pct']>=0 else '')}{total_agg['ytd_pct']:.2f}%</strong></div>
        <div class="hold-card-row"><span>Life-to-date G/L</span><strong class="{('pos' if total_agg['pnl_ltd']>=0 else 'neg')}">{('+' if total_agg['pnl_ltd']>=0 else '')}${total_agg['pnl_ltd']:,.0f} ({total_agg['pnl_ltd_pct']:+.1f}%)</strong></div>
        <div class="hold-card-row"><span>Active mix</span><strong>{(active_agg['value']/total_agg['value']*100):.0f}% / {(legacy_agg['value']/total_agg['value']*100):.0f}%</strong></div>
      </div>
    </div>

    <!-- Active detail table -->
    <div class="hold-subhd">Active Holdings — IBKR (drives Zone Matrix)</div>
    <table class="hold-table">
      <thead>
        <tr>
          <th>Account</th>
          <th>Ticker</th>
          <th class="hold-num">Shares</th>
          <th class="hold-num">Price</th>
          <th class="hold-num">Value</th>
          <th class="hold-num">YTD %</th>
          <th class="hold-num">LTD P&amp;L</th>
          <th class="hold-num">LTD %</th>
        </tr>
      </thead>
      <tbody>{active_rows_html}
      </tbody>
    </table>

    <!-- Legacy detail table -->
    <div class="hold-subhd">Legacy Holdings — Citi (frozen) + BTC (never add)</div>
    <table class="hold-table">
      <thead>
        <tr>
          <th>Account</th>
          <th>Ticker</th>
          <th class="hold-num">Shares</th>
          <th class="hold-num">Price</th>
          <th class="hold-num">Value</th>
          <th class="hold-num">YTD %</th>
          <th class="hold-num">LTD P&amp;L</th>
          <th class="hold-num">LTD %</th>
        </tr>
      </thead>
      <tbody>{legacy_rows_html}
      </tbody>
    </table>
  </div>

  <!-- ─────────────────────────────────────────────────────────────── -->
  <!-- 3. PORTFOLIO PERFORMANCE — SPYL vs Mag6 vs Total Portfolio       -->
  <!-- ─────────────────────────────────────────────────────────────── -->
  <div class="chart-section">
    <div class="section-hd"><span>3 · PORTFOLIO PERFORMANCE</span><span style="font-size:9px">SPYL anchor vs Mag6 alpha vs Total Portfolio (index = 100 at base)</span></div>
    <div class="ctrls">
      <span class="cl">Scale</span>
      <button class="tog on" id="bl" onclick="setScale('linear')">Linear</button>
      <button class="tog"    id="bg" onclick="setScale('log')">Log</button>
    </div>
    <div class="tabs">
      <button class="tab on" onclick="setTab('7D')">7D / 7D</button>
      <button class="tab"    onclick="setTab('30D')">30D / 30D</button>
      <button class="tab"    onclick="setTab('6M')">6M / 6M</button>
      <button class="tab"    onclick="setTab('YTD')">YTD</button>
      <button class="tab"    onclick="setTab('1Y')">1Y / 1Y</button>
      <button class="tab"    onclick="setTab('5Y')">5Y / 5Y</button>
    </div>
    <div class="cards" id="cards"></div>
    <div class="legend">
      <span class="li"><span class="ln" style="background:var(--spyl)"></span>SPYL · S&amp;P Anchor</span>
      <span class="li"><span class="ln" style="background:var(--mag6)"></span>Mag6 · Alpha (conviction-weighted)</span>
      <span class="li"><span class="ln" style="background:var(--port)"></span>My Portfolio · Active + Legacy</span>
      <span class="li"><span class="ld" style="color:#888"></span>Projection</span>
    </div>
    <div class="note" id="note"></div>
    <div class="chart-wrap"><canvas id="chart" role="img" aria-label="Portfolio performance chart"></canvas></div>
    <div class="outperf" id="outperf"></div>
  </div>

  <!-- ─────────────────────────────────────────────────────────────── -->
  <!-- 4. FAIR VALUE ASSESSMENT CARDS                                    -->
  <!-- ─────────────────────────────────────────────────────────────── -->
  <div class="fv-section">
    <div class="section-hd">
      <span>4 · FAIR VALUE ASSESSMENT</span>
      <span style="font-size:9px">Twelve Data live · Analyst consensus · Zone {current_zone} actions</span>
    </div>
    <div class="fv-grid">{fv_cards_html}
    </div>
    <div class="fv-disc">Twelve Data live · Analyst consensus from stockanalysis.com / tipranks.com · SPYL target = Wall St 2026 S&amp;P consensus implied · BTC target = Stock-to-Flow model range · PEG = Fwd P/E ÷ Revenue growth · Zone actions per strategy.md · Not investment advice</div>
  </div>

  <!-- ─────────────────────────────────────────────────────────────── -->
  <!-- 5. MACRO OVERLAY — YIELD CURVE                                    -->
  <!-- ─────────────────────────────────────────────────────────────── -->
  <div class="yc-section">
    <div class="section-hd">
      <span>5 · MACRO OVERLAY — YIELD CURVE</span>
      <span style="font-size:9px">Zone boundaries: 0% · 0.5% · 1.21% · 2.0%</span>
    </div>
    <div class="yc-tabs">
      <button class="yc-tab on" onclick="setYCTab('5Y')">5Y / 5Y</button>
      <button class="yc-tab"    onclick="setYCTab('1Y')">1Y / 1Y</button>
      <button class="yc-tab"    onclick="setYCTab('6M')">6M / 6M</button>
      <button class="yc-tab"    onclick="setYCTab('30D')">30D / 30D</button>
    </div>
    <div class="yc-wrap"><canvas id="ycChart" role="img" aria-label="Yield curve spread chart"></canvas></div>
    <div class="yc-legend">
      <div class="yc-li"><div class="yc-ln" style="background:var(--zone)"></div>10yr−3mo spread</div>
      <div class="yc-li"><div class="yc-ld" style="color:var(--zone)"></div>OU projection → {OU_MU:.1f}% mean</div>
      <div class="yc-li"><div style="width:14px;height:7px;background:rgba(220,38,38,.15);border-radius:1px"></div>Zone 1 (inverted)</div>
      <div class="yc-li"><div style="width:14px;height:7px;background:rgba(234,88,12,.12);border-radius:1px"></div>Zone 2</div>
      <div class="yc-li"><div style="width:14px;height:7px;background:rgba(21,128,61,.10);border-radius:1px"></div>Zone 4+</div>
    </div>
  </div>

  <hr/>
  <div class="footer">
    Investment Dashboard · Twelve Data + FRED · Mag6: {mag6_footer}<br>
    Yield curve: OU mean reversion μ={OU_MU}% · Per strategy.md v3.0.0 · Not financial advice<br>
    <span style="opacity:.6">v{SCRIPT_VERSION} · {SCRIPT_DATE} · Generated {fetched_at}</span>
  </div>
</div>

<script>
const DATA = {payload};
const COLORS = {{SPYL:'#16a34a',MAG6:'#1d4ed8',PORTFOLIO:'#7c3aed'}};
const FWD    = {{SPYL:9,MAG6:12,PORTFOLIO:10.5}};
const LONG_H = new Set(['5Y','1Y','YTD']);
const LABELS = {{SPYL:'SPYL · ANCHOR',MAG6:'MAG6 · ALPHA',PORTFOLIO:'MY PORTFOLIO'}};
const NAMES  = {{SPYL:'SPYL Anchor',MAG6:'Mag6 Alpha',PORTFOLIO:'My Portfolio'}};
const ZONE_COLOR = '{zone_color}';
const ZONE_BOUNDARIES = {json.dumps(ZONE_BOUNDARIES)};
const ACTIVE_CAPITAL = {active_capital};

let curTab='7D', curYCTab='5Y', useLog=false;
let chartInst=null, ycInst=null;

// ── YIELD CURVE CHART ───────────────────────────────────────────────────────
function setYCTab(h){{
  curYCTab=h;
  document.querySelectorAll('.yc-tab').forEach(b=>b.classList.toggle('on',b.textContent.trim()===h+' / '+h||b.textContent.trim()===h));
  renderYC();
}}

function renderYC(){{
  const yd = DATA.yc.horizons[curYCTab];
  if(!yd)return;
  if(ycInst){{ycInst.destroy();ycInst=null;}}

  const todayX = new Date();
  const todayPl = {{id:'ycTL',afterDraw(c){{
    const xs=c.scales.x;if(!xs)return;
    const xp=xs.getPixelForValue(todayX);
    if(!xp||xp<xs.left||xp>xs.right)return;
    c.ctx.save();c.ctx.strokeStyle='rgba(100,100,100,.35)';c.ctx.lineWidth=1;c.ctx.setLineDash([4,4]);
    c.ctx.beginPath();c.ctx.moveTo(xp,c.chartArea.top);c.ctx.lineTo(xp,c.chartArea.bottom);c.ctx.stroke();
    c.ctx.fillStyle='rgba(100,100,100,.6)';c.ctx.font='8px monospace';c.ctx.fillText('today',xp+4,c.chartArea.top+10);
    c.ctx.restore();
  }}}};

  const zoneBandPl = {{id:'zb',beforeDraw(c){{
    const xs=c.scales.x, ys=c.scales.y;if(!xs||!ys)return;
    const ctx=c.ctx, ca=c.chartArea;
    ctx.save();
    const bands = [
      {{lo:-5,  hi:0,    bg:'rgba(220,38,38,.10)'}},
      {{lo:0,   hi:0.5,  bg:'rgba(234,88,12,.07)'}},
      {{lo:0.5, hi:1.21, bg:'rgba(217,119,6,.04)'}},
      {{lo:1.21,hi:2.0,  bg:'rgba(22,163,74,.07)'}},
      {{lo:2.0, hi:5,    bg:'rgba(21,128,61,.09)'}},
    ];
    bands.forEach(b=>{{
      const y1=Math.min(ys.getPixelForValue(b.hi),ca.bottom);
      const y2=Math.max(ys.getPixelForValue(b.lo),ca.top);
      if(y2>ca.bottom||y1<ca.top)return;
      ctx.fillStyle=b.bg;
      ctx.fillRect(ca.left,Math.min(y1,y2),ca.right-ca.left,Math.abs(y2-y1));
    }});
    const y0=ys.getPixelForValue(0);
    if(y0>=ca.top&&y0<=ca.bottom){{
      ctx.strokeStyle='rgba(220,38,38,.5)';ctx.lineWidth=1;ctx.setLineDash([3,3]);
      ctx.beginPath();ctx.moveTo(ca.left,y0);ctx.lineTo(ca.right,y0);ctx.stroke();
    }}
    ctx.restore();
  }}}};

  const datasets=[];
  datasets.push({{
    label:'Spread',
    data: yd.hist.map(([dt,v])=>{{return{{x:new Date(dt+'T12:00:00'),y:v}};}}),
    borderColor:ZONE_COLOR,backgroundColor:'transparent',borderWidth:2,pointRadius:0,tension:.15,order:2
  }});
  if(yd.proj&&yd.proj.length){{
    const lastH=yd.hist[yd.hist.length-1];
    const stitch=[{{x:new Date(lastH[0]+'T12:00:00'),y:lastH[1]}}];
    datasets.push({{
      label:'OU Projection',
      data:[...stitch,...yd.proj.map(([dt,v])=>{{return{{x:new Date(dt+'T12:00:00'),y:v}};}})],
      borderColor:ZONE_COLOR,backgroundColor:'transparent',borderWidth:1.5,pointRadius:0,tension:.2,borderDash:[6,4],order:1
    }});
    if(yd.upper&&yd.lower){{
      const stU=[{{x:new Date(lastH[0]+'T12:00:00'),y:lastH[1]}},...yd.upper.map(([dt,v])=>{{return{{x:new Date(dt+'T12:00:00'),y:v}};}})];
      const stL=[{{x:new Date(lastH[0]+'T12:00:00'),y:lastH[1]}},...yd.lower.map(([dt,v])=>{{return{{x:new Date(dt+'T12:00:00'),y:v}};}})];
      datasets.push({{label:'_u',data:stU,borderColor:'transparent',backgroundColor:'rgba(100,100,100,.08)',fill:'+1',borderWidth:0,pointRadius:0,tension:.2,order:3}});
      datasets.push({{label:'_l',data:stL,borderColor:'transparent',backgroundColor:'rgba(100,100,100,.08)',fill:false,borderWidth:0,pointRadius:0,tension:.2,order:3}});
    }}
  }}

  const allDates=[...yd.hist.map(([dt])=>dt), ...(yd.proj||[]).map(([dt])=>dt)];
  if(allDates.length>1){{
    datasets.push({{
      label:'Long-run mean +1.5%',
      data:[{{x:new Date(allDates[0]+'T12:00:00'),y:1.5}},{{x:new Date(allDates[allDates.length-1]+'T12:00:00'),y:1.5}}],
      borderColor:'rgba(21,128,61,.45)',backgroundColor:'transparent',borderWidth:1,pointRadius:0,borderDash:[2,6],tension:0,order:4
    }});
  }}

  ycInst=new Chart(document.getElementById('ycChart').getContext('2d'),{{
    type:'line',data:{{datasets}},
    options:{{
      responsive:true,maintainAspectRatio:false,animation:{{duration:200}},
      interaction:{{mode:'index',intersect:false}},
      plugins:{{
        legend:{{display:false}},
        tooltip:{{
          backgroundColor:'rgba(255,255,255,.97)',borderColor:'#d1d5db',borderWidth:.5,
          titleColor:'#111827',bodyColor:'#374151',
          titleFont:{{size:9,family:'monospace'}},bodyFont:{{size:9,family:'monospace'}},
          callbacks:{{
            title(i){{const d=i[0]?.raw?.x;return d?d.toLocaleDateString('en',{{month:'short',day:'numeric',year:'numeric'}}):''}},
            label(i){{if((i.dataset.label||'').startsWith('_'))return null;return` ${{i.dataset.label}}: ${{i.raw.y?.toFixed(3)}}%`}}
          }}
        }}
      }},
      scales:{{
        x:{{type:'time',time:{{tooltipFormat:'MMM d yyyy'}},ticks:{{color:'#9ca3af',font:{{size:8,family:'monospace'}},maxTicksLimit:8}},grid:{{color:'#f3f4f6'}}}},
        y:{{ticks:{{color:'#9ca3af',font:{{size:8,family:'monospace'}},callback:v=>v.toFixed(2)+'%',maxTicksLimit:8}},grid:{{color:'#f3f4f6'}},title:{{display:true,text:'Spread %',color:'#9ca3af',font:{{size:8,family:'monospace'}}}}}}
      }}
    }},
    plugins:[zoneBandPl,todayPl]
  }});
}}

// ── MONTHLY ALLOCATION TABLE ─────────────────────────────────────────────────
// Re-renders the table when user changes the deployment input.
// Handles SGOV parent + 3 sub-rows (Cash Dry Powder, SpaceX, Anthropic).
// Allocation math uses sub-rows and equity rows; parent aggregates for display.
const SGOV_SUB_TREE = {{"Cash Dry Powder":"├─", "SpaceX":"├─", "Anthropic":"└─"}};

function renderAllocTable(){{
  const deploy = parseFloat(document.getElementById('deployInput').value)||0;
  const rows = DATA.alloc_rows;
  const tbody = document.getElementById('allocBody');

  // Open sleeves for renormalization math: positive gap, EXCLUDING sgov_parent.
  // (Sub-rows carry the real matrix weights; parent is display-only aggregation.)
  const openRows = rows.filter(r => r.gap_dollar > 100 && r.row_type !== 'sgov_parent');
  const openMatrixTotal = openRows.reduce((s, r) => s + r.target_pct, 0);

  // Per-row allocation $ by pure matrix weight (no gap cap — always deploy full input)
  const allocAmts = {{}};
  openRows.forEach(r => {{
    const renormShare = openMatrixTotal > 0 ? (r.target_pct / openMatrixTotal) : 0;
    allocAmts[r.ticker] = deploy * renormShare;
  }});

  // Aggregate sub-row allocations into the SGOV parent (display only)
  const sgovParentAlloc = (allocAmts['Cash Dry Powder']||0) + (allocAmts['SpaceX']||0) + (allocAmts['Anthropic']||0);
  allocAmts['SGOV'] = sgovParentAlloc;

  // Total: sum unique sleeves only (don't double-count parent)
  const totalAllocated = Object.entries(allocAmts)
    .filter(([t]) => t !== 'SGOV')
    .reduce((a, [, v]) => a + v, 0);
  const unallocated = Math.max(0, deploy - totalAllocated);

  let html = '';
  rows.forEach(r => {{
    const gap = r.gap_dollar;
    const rowType = r.row_type || 'equity';
    const isParent = rowType === 'sgov_parent';
    const isSub = rowType === 'sgov_sub';

    let gapCls = 'alloc-ok';
    let sharesStr = '—';
    let allocStr = '—';
    let allocAmt = 0;

    if(gap > 100){{
      gapCls = 'alloc-red';
      allocAmt = allocAmts[r.ticker] || 0;
      allocStr = allocAmt > 0 ? '$' + Math.round(allocAmt).toLocaleString() : '—';
      // Shares column
      if(r.ticker === 'SpaceX' || r.ticker === 'Anthropic' || r.ticker === 'SGOV' || r.ticker === 'Cash Dry Powder'){{
        sharesStr = '—';
      }} else if(r.live_price && r.live_price > 0 && allocAmt > 0){{
        const shares = Math.floor(allocAmt / r.live_price);
        sharesStr = shares > 0 ? shares.toString() : '<1';
      }}
    }} else if(gap < -100){{
      gapCls = 'alloc-green';
      sharesStr = 'OVER (locked)';
    }}

    const gapSign = gap > 0 ? '+' : '';
    const priceStr = r.live_price ? '$' + r.live_price.toFixed(2) : '—';

    // Row class and ticker display
    let rowCls, tickerHtml;
    if(isParent){{
      rowCls = 'alloc-sgov-parent';
      tickerHtml = `<strong>${{r.ticker}}</strong><div class="alloc-sleeve">${{r.sleeve}}</div>`;
    }} else if(isSub){{
      rowCls = 'alloc-sgov-sub';
      const tree = SGOV_SUB_TREE[r.ticker] || '├─';
      tickerHtml = `<span class="alloc-tree">${{tree}}</span> ${{r.ticker}}<div class="alloc-sleeve alloc-sub-sleeve">${{r.sleeve}}</div>`;
    }} else {{
      rowCls = '';
      tickerHtml = `<strong>${{r.ticker}}</strong><div class="alloc-sleeve">${{r.sleeve}}</div>`;
    }}

    html += `<tr class="${{rowCls}}">
        <td>${{tickerHtml}}</td>
        <td class="alloc-num">${{(r.target_pct*100).toFixed(2)}}%</td>
        <td class="alloc-num">$${{Math.round(r.current_dollar).toLocaleString()}}</td>
        <td class="alloc-num">$${{Math.round(r.target_dollar).toLocaleString()}}</td>
        <td class="alloc-num ${{gapCls}}">${{gapSign}}$${{Math.round(gap).toLocaleString()}}</td>
        <td class="alloc-num">${{priceStr}}</td>
        <td class="alloc-num"><strong>${{allocStr}}</strong></td>
        <td class="alloc-num">${{sharesStr}}</td>
        <td><span class="alloc-act">${{r.action || '—'}}</span><div class="alloc-note">${{r.notes || ''}}</div></td>
      </tr>`;
  }});

  // Totals row — clean, no parenthetical breakdown
  const unallocMsg = unallocated > 10 ? `Unallocated $${{Math.round(unallocated).toLocaleString()}}` : 'Fully deployed';
  html += `<tr class="alloc-totals">
      <td colspan="6"><strong>TOTAL DEPLOYED</strong></td>
      <td class="alloc-num"><strong>$${{Math.round(totalAllocated).toLocaleString()}}</strong></td>
      <td class="alloc-num">—</td>
      <td><span class="alloc-note">${{unallocMsg}}</span></td>
    </tr>`;
  tbody.innerHTML = html;
}}

// ── PORTFOLIO PERFORMANCE CHART ───────────────────────────────────────────────
function setTab(h){{
  curTab=h;
  document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('on',b.textContent.trim()===h||b.textContent.trim()===h+' / '+h));
  render();
}}
function setScale(s){{
  useLog=s==='log';
  document.getElementById('bl').classList.toggle('on',!useLog);
  document.getElementById('bg').classList.toggle('on',useLog);
  render();
}}

function render(){{
  const hd=DATA.horizons[curTab];
  if(!hd)return;
  const keys=['SPYL','MAG6','PORTFOLIO'];

  // Performance cards
  document.getElementById('cards').innerHTML=keys.map(k=>{{
    const d=hd[k], col=COLORS[k];
    if(!d) return `<div class="card" style="border-top-color:${{col}}"><div class="card-lbl">${{LABELS[k]}}</div><div class="card-val" style="color:var(--mut)">—</div></div>`;
    const vc=d.ret>=0?'pos':'neg', sign=d.ret>=0?'+':'';
    const cagr=d.cagr!=null?d.cagr+'%':'—';
    return `<div class="card" style="border-top-color:${{col}}">
      <div class="card-lbl">${{LABELS[k]}}</div>
      <div class="card-val ${{vc}}">${{sign}}${{d.ret.toFixed(1)}}%</div>
      <div class="card-sub">CAGR ${{cagr}} · Fwd ${{FWD[k]}}%</div>
      <div class="card-base">Base $${{d.base_price}} · ${{d.base_date}}</div>
    </div>`;
  }}).join('');

  // Outperformance vs SPYL
  const spyl=hd['SPYL'];
  if(spyl) document.getElementById('outperf').innerHTML=['MAG6','PORTFOLIO'].map(k=>{{
    const d=hd[k];if(!d)return'';
    const a=d.ret-spyl.ret,col=a>=0?'var(--grn)':'var(--red)',sign=a>=0?'+':'';
    return `<span class="op">${{NAMES[k]}}: <span style="color:${{col}}">${{sign}}${{a.toFixed(1)}}pts vs SPYL</span></span>`;
  }}).join('');

  const isLong=LONG_H.has(curTab);
  const method=isLong?'CAGR geometric compounding':'Geometric Brownian Motion (vol-adjusted)';
  document.getElementById('note').textContent=`Projection: ${{method}} · Dashed = forward · My Portfolio = active + legacy weighted`;

  if(chartInst){{chartInst.destroy();chartInst=null;}}
  const datasets=[];
  const todayX=new Date();

  keys.forEach(k=>{{
    const d=hd[k];if(!d)return;
    const col=COLORS[k],nm=NAMES[k];
    datasets.push({{label:nm,data:d.hist.map(([dt,v])=>{{return{{x:new Date(dt+'T12:00:00'),y:v}};}}),borderColor:col,backgroundColor:'transparent',borderWidth:2.5,pointRadius:0,tension:.12,borderDash:[]}});
    if(d.proj&&d.proj.length){{
      const lh=d.hist[d.hist.length-1];
      datasets.push({{label:nm+' →',data:[{{x:new Date(lh[0]+'T12:00:00'),y:lh[1]}},...d.proj.map(([dt,v])=>{{return{{x:new Date(dt+'T12:00:00'),y:v}};}})],borderColor:col,backgroundColor:'transparent',borderWidth:1.8,pointRadius:0,tension:.12,borderDash:[6,4]}});
    }}
  }});

  const todayPl={{id:'tl',afterDraw(c){{
    const xs=c.scales.x;if(!xs)return;
    const xp=xs.getPixelForValue(todayX);if(!xp||xp<xs.left||xp>xs.right)return;
    c.ctx.save();c.ctx.strokeStyle='rgba(75,85,99,.35)';c.ctx.lineWidth=1;c.ctx.setLineDash([4,4]);
    c.ctx.beginPath();c.ctx.moveTo(xp,c.chartArea.top);c.ctx.lineTo(xp,c.chartArea.bottom);c.ctx.stroke();
    c.ctx.fillStyle='rgba(75,85,99,.6)';c.ctx.font='8px monospace';c.ctx.fillText('today',xp+4,c.chartArea.top+10);
    c.ctx.restore();
  }}}};

  chartInst=new Chart(document.getElementById('chart').getContext('2d'),{{
    type:'line',data:{{datasets}},
    options:{{
      responsive:true,maintainAspectRatio:false,animation:{{duration:250}},
      interaction:{{mode:'index',intersect:false}},
      plugins:{{
        legend:{{display:false}},
        tooltip:{{
          backgroundColor:'rgba(255,255,255,.98)',borderColor:'#d1d5db',borderWidth:.5,
          titleColor:'#111827',bodyColor:'#374151',
          titleFont:{{size:9,family:'monospace'}},bodyFont:{{size:9,family:'monospace'}},
          callbacks:{{
            title(i){{const d=i[0]?.raw?.x;return d?d.toLocaleDateString('en',{{month:'short',day:'numeric',year:'numeric'}}):''}},
            label(i){{if((i.dataset.label||'').startsWith('_'))return null;return` ${{i.dataset.label}}: ${{i.raw.y?.toFixed(1)}}`}}
          }}
        }}
      }},
      scales:{{
        x:{{type:'time',time:{{tooltipFormat:'MMM d yyyy'}},ticks:{{color:'#9ca3af',font:{{size:8,family:'monospace'}},maxTicksLimit:9}},grid:{{color:'#f3f4f6'}}}},
        y:{{type:useLog?'logarithmic':'linear',ticks:{{color:'#9ca3af',font:{{size:8,family:'monospace'}},callback:v=>parseFloat(v.toFixed(0)),maxTicksLimit:9}},grid:{{color:'#f3f4f6'}},title:{{display:true,text:'Index · base = 100',color:'#9ca3af',font:{{size:8,family:'monospace'}}}}}}
      }}
    }},
    plugins:[todayPl]
  }});
}}

// ── INIT ──────────────────────────────────────────────────────────────────────
renderYC();
render();
renderAllocTable();
</script>
</body>
</html>"""

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
with open(out_path, "w") as f:
    f.write(html)

print(f"\n✓ Saved: {out_path}")
if not os.environ.get("CI"):
    print("  Opening in browser...")
    webbrowser.open(f"file://{out_path}")
