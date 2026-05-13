# ═════════════════════════════════════════════════════════════════════════════
# ALPHA DASHBOARD — generate_dashboard.py
# ═════════════════════════════════════════════════════════════════════════════
#   VERSION   : 3.4.1
#   DATE      : 2026-05-13
#   PAIRS WITH: refresh.yml v3.0.8+, holdings.json v1.0+, Google Sheets (4 tabs)
#   STRATEGY  : Bogle/Buffett anchored, Mag6-dominant, Active vs Legacy split
#   CHANGELOG :
#     3.4.1 — CRITICAL HOTFIX (May 13):
#             • Restored function setYCTab() declaration that was eaten by
#                an earlier str_replace edit, leaving an orphan function body.
#             • This was throwing a SyntaxError on page load, breaking ALL
#                JavaScript including switchMainTab() — so no tabs worked.
#             • Bug shipped in v3.4.0; affected anyone trying to navigate
#                from the default Investment Dashboard tab to any other tab.
#             • Also: file write now forces utf-8 encoding to fix mangled
#                ₱ peso signs and em-dashes in deployed HTML (showed as
#                "â±" and "â" garbage on the live site).
#     3.4.0 — Major Cashouts tab + scenario toggle (Phase 4, May 12):
#             • New "Major Cashouts" tab between Cashflow and Projection.
#             • Scenario toggle (us_private / us_public / ph_with_masters)
#                drives per-scenario summary, table, and impact chart.
#                Selection persists in localStorage across sessions.
#             • Sheet schema extended: Major_Cashouts now has `Scenario`
#                column. Rows tagged 'base' apply to all scenarios; education
#                rows tagged with a specific scenario.
#             • _build_projection() refactored to compute net worth
#                trajectory PER scenario (projections_by_scenario dict).
#                Plus a '__base_only__' reference (no education at all).
#             • Tab content: (1) scenario summary cards with category +
#                decade totals, (2) full cashout table for active scenario,
#                (3) impact chart overlaying all 3 scenarios + reference line.
#             • "Edit in Sheet" deep-link buttons → opens Major_Cashouts tab.
#             • Empty state with template guidance when Sheet is unpopulated.
#             • Projection horizon auto-extends if cashouts go past default
#                15-yr window (e.g. ph_with_masters has masters in 2052).
#             • Projection tab's NW chart now honors active scenario from
#                Major Cashouts toggle — switch scenario there, projection
#                chart updates next time it's viewed.
#     3.3.0 — Cashflow + Projection tabs (Phase 2/3, May 12):
#             • Cashflow tab: 3 stacked sections — Annual Summary (3 cards:
#                cash surplus, total wealth growth incl. unrealized gains,
#                active income surplus), Monthly distribution chart (income/
#                expenses by frequency, net line overlay), Category drilldown
#                (expandable rows for income/expense categories with line items).
#             • Projection tab: 4 sections — Assumption chips header
#                (salary growth, expense inflation, investment return,
#                horizon, starting NW), Cashout timeline (bubble chart),
#                Year-by-year table (NW trajectory with cashout impact),
#                15-yr net worth chart (with cashouts vs reference line).
#             • Phase 3 skeleton mode: shows empty-state banner when
#                Major_Cashouts sheet has no rows; projection still computed
#                using Settings tab assumptions and Cashflow data.
#             • Currency toggle extended: cashflow/projection use PHP-native
#                values (data-php attribute); switchCurrency now handles both
#                data-usd (Balance Sheet) and data-php (Cashflow/Projection)
#                sources cleanly.
#             • restoreTab now supports all four tabs (was hardcoded to
#                only 'holdings' before).
#             • Charts on hidden tabs deferred until first activation to
#                avoid layout/sizing issues.
#     3.2.2 — FX rate sourced from Google Sheet (May 12):
#             • Settings tab `usdphp_rate` key (GOOGLEFINANCE formula) is now
#                the primary source for USD/PHP conversions.
#             • Twelve Data remains as fallback; hardcoded ₱61 as last resort.
#             • Dashboard footer shows actual FX source (Google Finance vs
#                Twelve Data vs fallback) for transparency.
#             • Hardcoded fallback bumped from ₱58 → ₱61 (closer to May 2026 spot).
#     3.2.1 — Balance Sheet expansion + PHP currency bug fix (May 12):
#             • Added esel_investments category to _parse_balance_sheet_rows
#                and _build_balance_sheet — renders as "Esel — Investments" section.
#             • CRITICAL FIX: real_estate, vehicles, business_equity, and
#                other_investments now properly convert PHP→USD using live
#                USDPHP_RATE. Previously these sections treated raw PHP values
#                as USD, massively overstating net worth (e.g. ₱30M condo read
#                as $30M USD instead of ~$517K).
#             • Standard parser schema now stores `currency` field on every
#                row (not just cash/liabilities) so downstream conversions work.
#             • Fixed PHP liability limit parser: now strips ₱ symbol and converts
#                PHP limits to USD using live USDPHP_RATE before storing.
#             • Liabilities balance also normalized to USD when currency=PHP.
#     3.2.0 — Google Sheets data source for cashflow data (May 12):
#             • cashflow.json deprecated as primary source — Google Sheets
#                is now the source of truth for balance sheet, cashflow,
#                major cashouts, and settings data.
#             • Sheet at https://docs.google.com/spreadsheets/d/1Kal6N5jcJz3wUfBhxvkIS1YMm5ToEz4CI6tsZPZSZG4
#             • Script fetches 4 published CSV tabs at refresh time:
#                Balance_Sheet, Cashflow, Major_Cashouts, Settings.
#             • Edit values directly in the Sheet — dashboard auto-syncs
#                on next workflow run. No GitHub commits needed for data updates.
#             • Fallback: if Sheets fetch fails, script falls back to
#                cashflow.json (still in repo as safety net).
#             • Phase 2 (Cashflow) and Phase 3 (Major Cashouts) data is
#                loaded but not yet rendered. Will be wired up in future iterations.
#     3.1.0 — Total Holdings tab — Phase 1: Balance Sheet (May 12):
#             • Added second top-level tab "Total Holdings" alongside the
#                Investment Dashboard. Switches via tab buttons; preference
#                persists in localStorage.
#             • New file: cashflow.json holds non-investment assets and
#                liabilities (real estate, vehicles, business equity, other
#                investments, cash accounts, liabilities). Loaded at runtime.
#             • Balance Sheet view: Total Assets − Liabilities = Net Worth
#                headline, plus categorized asset table and liabilities table.
#             • Investment accounts auto-sync from holdings.json × live prices
#                (no duplication with cashflow.json).
#             • PHP/USD currency toggle: all values re-render in chosen ccy
#                on click. Toggle state persists in localStorage.
#             • USD/PHP FX rate fetched live from Twelve Data forex endpoint
#                (USD/PHP pair). Fallback to ₱58/$ if API fails.
#             • Phase 2 (Cashflow: income vs expenses) and Phase 3 (15-year
#                projection with major cashouts) planned for future iteration.
#     3.0.9 — SPYL price calibration (May 12):
#             • Updated SPYL_RATIO from 0.0241 → 0.02477.
#             • Calibrated against actual IBKR SPYL.L quote ($18.31).
#             • Removes the ~2.75% gap between dashboard and IBKR portfolio value.
#             • Note: ratio drifts ~1.3-1.5%/year as SPYL accumulates dividends
#                vs distributing SPY. Annual recalibration recommended.
#     3.0.8 — SGOV live price fetch (May 12):
#             • Added SGOV to ALL_TICKERS list so it fetches live price from
#                Twelve Data instead of falling back to avg_cost placeholder.
#             • Resolves "⚠ no price for SGOV (IBKR)" warning in logs.
#     3.0.7 — Holdings externalized to holdings.json (May 11):
#             • HOLDINGS dict moved to holdings.json — edit there after trades.
#             • Script loads positions at runtime via _load_holdings().
#             • Embedded fallback HOLDINGS preserved in script for safety
#                (used if holdings.json missing or malformed).
#             • Account classification + labels now live in JSON file too.
#             • Schema version field for future-proofing.
#             • Trade-update workflow: edit holdings.json in GitHub web UI,
#                commit, wait for next refresh. No script changes needed.
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
SCRIPT_VERSION = "3.4.1"
SCRIPT_DATE    = "2026-05-13"

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
TWELVEDATA_API_KEY = "0fbd7cea5285446e85d0880d27fd9085"   # ← paste your Twelve Data key between the quotes
FRED_API_KEY       = "b8a3d518f4e1032f09e949b4ed7c2214"   # ← paste your FRED key between the quotes

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
    if t == "USD/PHP": return "USD/PHP"   # forex pair, passed through directly
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
# Holdings now live in holdings.json (separate file for easier editing).
# Update that file via GitHub web UI after each trade — no need to touch this script.
#
# CLASSIFICATION (per strategy doc):
#   ACTIVE  = IBKR  → drives zone matrix, receives monthly contributions
#   LEGACY  = Citi* (frozen) + CRYPTO (BTC, never add)
#
# Note: VOO in IBKR is conceptually merged with SPYL (same exposure).
#
# Format per account in holdings.json:
#   {
#     "classification": "ACTIVE" | "LEGACY",
#     "label": "Display Name",
#     "TICKER": {"shares": N, "avg_cost": price},
#     "CASH": amount
#   }
#
# Fallback: if holdings.json is missing or malformed, the embedded HOLDINGS
# dict below kicks in so the script still runs (with potentially stale data).

# Embedded fallback (also serves as the default if no holdings.json exists)
_HOLDINGS_FALLBACK = {
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
        "BTC": {"shares": 0.18486736, "avg_cost": 91760},
    },
}
_ACTIVE_FALLBACK = ["IBKR"]
_LEGACY_FALLBACK = ["CITI_401K", "CITI_ROTH", "CITI_BROK", "CRYPTO"]
_LABELS_FALLBACK = {
    "IBKR":      "IBKR",
    "CITI_401K": "Citi 401k",
    "CITI_ROTH": "Citi Roth",
    "CITI_BROK": "Citi Brokerage",
    "CRYPTO":    "Crypto (BTC)",
}

def _load_holdings():
    """Load holdings from holdings.json next to the script.
    Returns (HOLDINGS, ACTIVE_ACCOUNTS, LEGACY_ACCOUNTS, ACCOUNT_LABELS, meta_dict).
    Falls back to embedded defaults if the file is missing or malformed."""
    holdings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "holdings.json")
    if not os.path.exists(holdings_path):
        print(f"⚠ holdings.json not found at {holdings_path} — using embedded fallback")
        return _HOLDINGS_FALLBACK, _ACTIVE_FALLBACK, _LEGACY_FALLBACK, _LABELS_FALLBACK, {}
    try:
        with open(holdings_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"⚠ holdings.json malformed ({e}) — using embedded fallback")
        return _HOLDINGS_FALLBACK, _ACTIVE_FALLBACK, _LEGACY_FALLBACK, _LABELS_FALLBACK, {}

    accounts_raw = data.get("accounts", {})
    if not accounts_raw:
        print("⚠ holdings.json has no 'accounts' key — using embedded fallback")
        return _HOLDINGS_FALLBACK, _ACTIVE_FALLBACK, _LEGACY_FALLBACK, _LABELS_FALLBACK, {}

    holdings = {}
    active = []
    legacy = []
    labels = {}
    for acct_name, acct_data in accounts_raw.items():
        # Strip out the schema fields (classification, label, comments starting with _)
        positions = {}
        for k, v in acct_data.items():
            if k.startswith("_"):           # comment field, skip
                continue
            if k in ("classification", "label"):
                continue
            positions[k] = v
        holdings[acct_name] = positions

        cls = acct_data.get("classification", "LEGACY").upper()
        if cls == "ACTIVE":
            active.append(acct_name)
        else:
            legacy.append(acct_name)
        labels[acct_name] = acct_data.get("label", acct_name)

    meta = data.get("_meta", {})
    print(f"✓ Loaded holdings.json (last updated: {meta.get('last_updated', 'unknown')})")
    if meta.get("last_trade_notes"):
        print(f"  Last trade: {meta['last_trade_notes']}")
    return holdings, active, legacy, labels, meta

HOLDINGS, ACTIVE_ACCOUNTS, LEGACY_ACCOUNTS, ACCOUNT_LABELS, HOLDINGS_META = _load_holdings()

# ─────────────────────────────────────────────────────────────────────────────
# CASHFLOW DATA — GOOGLE SHEETS INTEGRATION (Total Holdings tab)
# ─────────────────────────────────────────────────────────────────────────────
# Data source: published Google Sheets CSV (4 tabs).
# Edit values directly in the Sheet at:
#   https://docs.google.com/spreadsheets/d/1Kal6N5jcJz3wUfBhxvkIS1YMm5ToEz4CI6tsZPZSZG4
# The dashboard fetches all 4 tabs on each refresh.
#
# Fallback: if Sheets fetch fails, fall back to cashflow.json in the repo.
# This means the Sheet can break without taking down the dashboard.

SHEET_CSV_URLS = {
    "Balance_Sheet":  "https://docs.google.com/spreadsheets/d/e/2PACX-1vSW4QL7uriDrm8ZjdHkrUi-yzsOZ2XrBvY46JyRsS7ynnt4G6p_SiQ50Ssyz0Y8KPT8DTalVtRvONra/pub?gid=1887223052&single=true&output=csv",
    "Cashflow":       "https://docs.google.com/spreadsheets/d/e/2PACX-1vSW4QL7uriDrm8ZjdHkrUi-yzsOZ2XrBvY46JyRsS7ynnt4G6p_SiQ50Ssyz0Y8KPT8DTalVtRvONra/pub?gid=168657384&single=true&output=csv",
    "Major_Cashouts": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSW4QL7uriDrm8ZjdHkrUi-yzsOZ2XrBvY46JyRsS7ynnt4G6p_SiQ50Ssyz0Y8KPT8DTalVtRvONra/pub?gid=2138882399&single=true&output=csv",
    "Settings":       "https://docs.google.com/spreadsheets/d/e/2PACX-1vSW4QL7uriDrm8ZjdHkrUi-yzsOZ2XrBvY46JyRsS7ynnt4G6p_SiQ50Ssyz0Y8KPT8DTalVtRvONra/pub?gid=669129657&single=true&output=csv",
}

def _fetch_sheet_csv(name, url, timeout=20):
    """Fetch one tab's CSV from the published Google Sheets URL.
    Returns list of dict rows (with column headers as keys), or None on failure."""
    import csv
    from io import StringIO
    try:
        r = HTTP_SESSION.get(url, timeout=timeout,
                             headers={"User-Agent": "Mozilla/5.0 (Dashboard)"})
        if r.status_code != 200:
            print(f"  ✗ {name}: HTTP {r.status_code}")
            return None
        # Google may serve UTF-8 BOM; strip it
        text = r.text.lstrip("\ufeff")
        reader = csv.DictReader(StringIO(text))
        rows = [row for row in reader if any(v.strip() for v in row.values() if v)]
        return rows
    except Exception as e:
        print(f"  ✗ {name}: fetch failed ({type(e).__name__}: {e})")
        return None

def _parse_balance_sheet_rows(rows):
    """Convert Balance_Sheet sheet rows → cashflow.json balance_sheet structure.
    Sheet columns: Category, Subcategory, Label, Value, Currency, Notes"""
    bs = {
        "real_estate": [], "vehicles": [], "business_equity": [],
        "other_investments": [], "esel_investments": [],
        "cash_accounts": [], "liabilities": [],
    }
    for row in rows:
        cat = (row.get("Category") or "").strip().lower()
        if not cat or cat not in bs:
            continue
        label = (row.get("Label") or "").strip()
        if not label:
            continue
        try:
            value = float((row.get("Value") or "0").replace(",", ""))
        except ValueError:
            value = 0.0
        ccy = (row.get("Currency") or "USD").strip().upper()
        note = (row.get("Notes") or "").strip()

        if cat == "cash_accounts":
            # Cash uses {value, currency} schema
            bs[cat].append({
                "label": label,
                "currency": ccy,
                "value": value,
                "_note": note,
            })
        elif cat == "liabilities":
            # Liabilities: balance + limit, both normalized to USD.
            # Limit extracted from Notes field — handles $ (USD) and ₱ (PHP).
            limit = 0.0
            if "limit:" in note.lower():
                try:
                    limit_str = note.lower().split("limit:")[-1].strip()
                    limit_is_php = ("₱" in limit_str or ccy == "PHP")
                    limit_str = limit_str.replace("$","").replace("₱","").replace(",","").strip()
                    import re as _re
                    m = _re.search(r"[\d.]+", limit_str)
                    if m:
                        limit_native = float(m.group())
                        limit = limit_native / USDPHP_RATE if limit_is_php else limit_native
                except Exception:
                    limit = 0.0
            bal_usd = value / USDPHP_RATE if ccy == "PHP" else value
            bs[cat].append({
                "label": label,
                "balance_usd": bal_usd,
                "limit_usd": limit,
                "currency": ccy,
                "_note": note,
            })
        else:
            # Standard schema: {label, value_usd, currency, _note}
            # `currency` enables PHP→USD conversion downstream (esel_investments uses this).
            bs[cat].append({
                "label": label,
                "value_usd": value,
                "currency": ccy,
                "_note": note,
            })
    return bs

def _parse_cashflow_rows(rows):
    """Convert Cashflow sheet rows → cashflow structure for Phase 2.
    Sheet columns: Type, Category, Label, Amount_PHP, Frequency, Annual_Total_PHP, Notes
    Phase 2 not yet rendered — data loaded for future use."""
    items = []
    for row in rows:
        type_ = (row.get("Type") or "").strip().lower()
        if type_ not in ("income", "expense"):
            continue
        try:
            amount = float((row.get("Amount_PHP") or "0").replace(",", ""))
            freq = float((row.get("Frequency") or "1").replace(",", ""))
            annual = float((row.get("Annual_Total_PHP") or "0").replace(",", ""))
        except ValueError:
            amount = freq = annual = 0.0
        items.append({
            "type": type_,
            "category": (row.get("Category") or "").strip(),
            "label": (row.get("Label") or "").strip(),
            "amount_php": amount,
            "frequency": freq,
            "annual_php": annual if annual > 0 else amount * freq,
            "note": (row.get("Notes") or "").strip(),
        })
    return items

def _parse_major_cashouts_rows(rows):
    """Convert Major_Cashouts sheet rows → list for Phase 3/4.
    Sheet columns: Year, Item, Amount_USD, Category, Scenario, Notes
    Scenario column added in v3.4.0:
      - 'base' = always applies (vehicles, real estate, healthcare)
      - 'us_private' / 'us_public' / 'ph_with_masters' = education scenarios
      - blank or unknown = treated as 'base' for backward compat"""
    items = []
    for row in rows:
        try:
            year = int(row.get("Year") or 0)
        except ValueError:
            continue
        if not year:
            continue
        try:
            amount = float((row.get("Amount_USD") or "0").replace(",", ""))
        except ValueError:
            amount = 0.0
        scenario = (row.get("Scenario") or "base").strip().lower()
        if not scenario:
            scenario = "base"
        items.append({
            "year": year,
            "item": (row.get("Item") or "").strip(),
            "amount_usd": amount,
            "category": (row.get("Category") or "").strip(),
            "scenario": scenario,
            "note": (row.get("Notes") or "").strip(),
        })
    return sorted(items, key=lambda r: (r["year"], -r["amount_usd"]))

def _parse_settings_rows(rows):
    """Convert Settings sheet rows → flat dict.
    Sheet columns: Key, Value, Description"""
    out = {}
    for row in rows:
        k = (row.get("Key") or "").strip()
        if not k or k.startswith("#"):
            continue
        v = (row.get("Value") or "").strip()
        # Try to parse numeric values
        try:
            v_num = float(v.replace(",", ""))
            out[k] = v_num
        except ValueError:
            out[k] = v
    return out

def _load_cashflow_from_json_fallback():
    """Fallback: load Balance Sheet from cashflow.json if Sheets fetch fails."""
    cashflow_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cashflow.json")
    if not os.path.exists(cashflow_path):
        print(f"⚠ cashflow.json fallback not found — Total Holdings tab will be empty")
        return {"balance_sheet": {}, "cashflow": [], "major_cashouts": [], "settings": {}}, {}
    try:
        with open(cashflow_path) as f:
            data = json.load(f)
        meta = data.get("_meta", {})
        print(f"  ↪ Using cashflow.json fallback (last updated: {meta.get('last_updated', 'unknown')})")
        return {
            "balance_sheet": data.get("balance_sheet", {}),
            "cashflow": [],
            "major_cashouts": [],
            "settings": {},
        }, meta
    except json.JSONDecodeError as e:
        print(f"⚠ cashflow.json malformed ({e})")
        return {"balance_sheet": {}, "cashflow": [], "major_cashouts": [], "settings": {}}, {}

def _load_cashflow():
    """Load cashflow data from Google Sheets (preferred) with cashflow.json fallback.
    Returns (data_dict, meta_dict) where data_dict has keys:
      balance_sheet   — dict of category → list of items (Phase 1, currently rendered)
      cashflow        — list of income/expense items (Phase 2, future)
      major_cashouts  — list of future expenses by year (Phase 3, future)
      settings        — dict of config key/value pairs"""
    print("\nFetching cashflow data from Google Sheets...")
    sheet_data = {}
    fetch_success = True

    for tab_name, url in SHEET_CSV_URLS.items():
        rows = _fetch_sheet_csv(tab_name, url)
        if rows is None:
            fetch_success = False
            break
        sheet_data[tab_name] = rows
        print(f"  ✓ {tab_name}: {len(rows)} rows")

    if not fetch_success or not sheet_data:
        print("  ⚠ Sheets fetch incomplete — falling back to cashflow.json")
        return _load_cashflow_from_json_fallback()

    # Parse each tab into its native structure
    result = {
        "balance_sheet":  _parse_balance_sheet_rows(sheet_data.get("Balance_Sheet", [])),
        "cashflow":       _parse_cashflow_rows(sheet_data.get("Cashflow", [])),
        "major_cashouts": _parse_major_cashouts_rows(sheet_data.get("Major_Cashouts", [])),
        "settings":       _parse_settings_rows(sheet_data.get("Settings", [])),
    }
    # Diagnostic on Phase 2/3 data (loaded but not yet rendered)
    cf_items = result["cashflow"]
    mc_items = result["major_cashouts"]
    if cf_items:
        income_total = sum(r["annual_php"] for r in cf_items if r["type"] == "income")
        expense_total = sum(r["annual_php"] for r in cf_items if r["type"] == "expense")
        print(f"  ℹ Cashflow data ready (Phase 2 not yet rendered): "
              f"₱{income_total:,.0f} income / ₱{expense_total:,.0f} expense annual")
    if mc_items:
        print(f"  ℹ Major cashouts data ready (Phase 3 not yet rendered): "
              f"{len(mc_items)} items spanning {mc_items[0]['year']}-{mc_items[-1]['year']}")

    meta = {
        "source": "google_sheets",
        "last_updated": fetched_at if 'fetched_at' in globals() else "",
    }
    return result, meta

# NB: _load_cashflow() is called AFTER price/forex fetch so this is just the bind.
# Actual call happens after fetched_at is set.

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
ALL_TICKERS = ["NVDA","MSFT","META","GOOGL","AMZN","AAPL","SPY","VOO","GOOG","BTC-USD","SGOV"]
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

# ── SPYL Proxy: SPYL = SPY × 0.02477 ─────────────────────────────────────────
# SPYL.L (London-listed SPDR S&P 500 UCITS ETF) is Twelve Data Grow-tier only,
# so we synthesize from SPY US. Calibrated 2026-05-12 against IBKR SPYL.L quote:
#   SPY $739.30 × 0.02477 → SPYL $18.31 (matches IBKR exactly)
#
# IMPORTANT: SPYL is *accumulating* (reinvests dividends), SPY is *distributing*.
# This means SPYL grows ~1.3-1.5%/year faster than SPY long-term. Review and
# recalibrate this ratio annually (or when IBKR vs dashboard SPYL price drifts >2%).
#   To recalibrate: new_ratio = (current SPYL.L price) / (current SPY price)
SPYL_RATIO = 0.02477  # calibrated 2026-05-12
if "SPY" in prices and "SPYL" not in prices:
    prices["SPYL"] = prices["SPY"] * SPYL_RATIO
    print(f"  SPYL: synthesized from SPY × {SPYL_RATIO} → ${prices['SPYL'].iloc[-1]:.2f}")

# ── USD/PHP FX RATE — for Total Holdings dashboard dual-currency toggle ──────
# Priority order:
#   1. Google Sheets Settings tab `usdphp_rate` key (preferred — uses GOOGLEFINANCE)
#   2. Twelve Data forex endpoint (fallback)
#   3. Hardcoded ₱61 fallback (last resort)
# Sheet override is applied AFTER _load_cashflow() runs, before _build_balance_sheet().
FX_FALLBACK = 61.00  # rough May 2026 spot rate; only used if both Sheet and TD fail
USDPHP_RATE = td_quote("USD/PHP")
if USDPHP_RATE and USDPHP_RATE > 30 and USDPHP_RATE < 100:
    print(f"  ✓ USD/PHP: Twelve Data live → ₱{USDPHP_RATE:.4f}/$ (may be overridden by Sheet)")
else:
    USDPHP_RATE = FX_FALLBACK
    print(f"  ⚠ USD/PHP: Twelve Data failed, using fallback ₱{USDPHP_RATE}/$ (may be overridden by Sheet)")
FX_SOURCE = "twelve_data"  # tracks where the rate came from for the dashboard footer

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

# ── LOAD CASHFLOW DATA (Google Sheets, with cashflow.json fallback) ──────────
# Called AFTER fetched_at is set (used in meta). Defined earlier near _load_holdings.
CASHFLOW_DATA, CASHFLOW_META = _load_cashflow()

# ── OVERRIDE USDPHP_RATE FROM SHEET SETTINGS (preferred source) ──────────────
# The Settings tab has a `usdphp_rate` key driven by GOOGLEFINANCE("CURRENCY:USDPHP").
# This is the user's preferred source — overrides the Twelve Data fetch above
# if the Sheet has a valid rate (sanity-checked to 30 < rate < 100).
_sheet_settings = CASHFLOW_DATA.get("settings", {})
_sheet_fx = _sheet_settings.get("usdphp_rate")
if _sheet_fx is not None:
    try:
        _sheet_fx_val = float(_sheet_fx)
        if 30 < _sheet_fx_val < 100:
            USDPHP_RATE = _sheet_fx_val
            FX_SOURCE = "google_sheets"
            print(f"  ✓ USD/PHP: Sheet override → ₱{USDPHP_RATE:.4f}/$ (Google Finance)")
        else:
            print(f"  ⚠ USD/PHP: Sheet value {_sheet_fx_val} out of range — keeping previous ₱{USDPHP_RATE:.4f}/$")
    except (ValueError, TypeError):
        print(f"  ⚠ USD/PHP: Sheet value '{_sheet_fx}' not numeric — keeping previous ₱{USDPHP_RATE:.4f}/$")

# ─────────────────────────────────────────────────────────────────────────────
# BALANCE SHEET COMPUTATION (Total Holdings tab — Phase 1)
# ─────────────────────────────────────────────────────────────────────────────
# Build a structured balance sheet combining:
#   - Investment accounts (from holdings.json × live prices, computed earlier)
#   - Real estate, vehicles, business equity, other investments, cash, liabilities
#     (from cashflow.json)
#
# All values stored in USD natively. PHP cash accounts are converted using
# the live USD/PHP rate (USDPHP_RATE fetched above). The dashboard's JS
# layer handles the PHP/USD toggle by converting display values on the fly.

def _build_balance_sheet():
    """Construct the balance sheet data structure for the Total Holdings tab."""
    bs = CASHFLOW_DATA.get("balance_sheet", {})
    sections = []

    # ── Section 1: Real Estate (PHP/USD aware) ──
    re_items = []
    re_total = 0.0
    for item in bs.get("real_estate", []):
        ccy = item.get("currency", "USD").upper()
        raw_val = float(item.get("value_usd", 0))
        usd_val = raw_val / USDPHP_RATE if ccy == "PHP" else raw_val
        re_items.append({
            "label": item["label"], "value_usd": usd_val,
            "currency": ccy, "native_value": raw_val,
            "note": item.get("_note", ""),
        })
        re_total += usd_val
    sections.append({"id": "real_estate", "label": "Real Estate",
                     "items": re_items, "total_usd": re_total})

    # ── Section 2: Investment Accounts — ACTIVE (auto-sync from holdings.json) ──
    active_items = []
    active_total = 0.0
    for acct in ACTIVE_ACCOUNTS:
        positions = HOLDINGS.get(acct, {})
        acct_value = 0.0
        for ticker, pos in positions.items():
            if ticker == "CASH":
                acct_value += float(pos)
            elif isinstance(pos, dict):
                shares = float(pos.get("shares", 0))
                # Use live price if available, else fall back to avg cost
                live = _holding_price(ticker)
                price = live if live and live > 0 else float(pos.get("avg_cost", 0))
                acct_value += shares * price
        if acct_value > 0:
            active_items.append({"label": ACCOUNT_LABELS.get(acct, acct),
                                 "value_usd": acct_value,
                                 "note": "Active strategy universe"})
            active_total += acct_value
    sections.append({"id": "investments_active",
                     "label": "Investment Accounts — Active",
                     "items": active_items, "total_usd": active_total})

    # ── Section 3: Investment Accounts — LEGACY (auto-sync) ──
    legacy_items = []
    legacy_total = 0.0
    for acct in LEGACY_ACCOUNTS:
        positions = HOLDINGS.get(acct, {})
        acct_value = 0.0
        for ticker, pos in positions.items():
            if ticker == "CASH":
                acct_value += float(pos)
            elif isinstance(pos, dict):
                shares = float(pos.get("shares", 0))
                live = _holding_price(ticker)
                price = live if live and live > 0 else float(pos.get("avg_cost", 0))
                acct_value += shares * price
        if acct_value > 0:
            legacy_items.append({"label": ACCOUNT_LABELS.get(acct, acct),
                                 "value_usd": acct_value,
                                 "note": "Frozen / hold indefinitely"})
            legacy_total += acct_value
    sections.append({"id": "investments_legacy",
                     "label": "Investment Accounts — Legacy",
                     "items": legacy_items, "total_usd": legacy_total})

    # ── Section 4: Other Investments (PHP/USD aware) ──
    other_items = []
    other_total = 0.0
    for item in bs.get("other_investments", []):
        ccy = item.get("currency", "USD").upper()
        raw_val = float(item.get("value_usd", 0))
        usd_val = raw_val / USDPHP_RATE if ccy == "PHP" else raw_val
        other_items.append({
            "label": item["label"], "value_usd": usd_val,
            "currency": ccy, "native_value": raw_val,
            "note": item.get("_note", ""),
        })
        other_total += usd_val
    sections.append({"id": "investments_other",
                     "label": "Other Investments",
                     "items": other_items, "total_usd": other_total})

    # ── Section 5: Esel Investments (static values from Sheet — not in matrix) ──
    esel_items = []
    esel_total = 0.0
    for item in bs.get("esel_investments", []):
        ccy = item.get("currency", "USD").upper()
        raw_val = float(item.get("value_usd", 0))
        if ccy == "PHP":
            usd_val = raw_val / USDPHP_RATE
        else:
            usd_val = raw_val
        esel_items.append({
            "label": item["label"],
            "value_usd": usd_val,
            "currency": ccy,
            "native_value": raw_val,
            "note": item.get("_note", ""),
        })
        esel_total += usd_val
    sections.append({"id": "esel_investments",
                     "label": "Esel — Investments",
                     "items": esel_items, "total_usd": esel_total})

    # ── Section 6: Vehicles (PHP/USD aware) ──
    veh_items = []
    veh_total = 0.0
    for item in bs.get("vehicles", []):
        ccy = item.get("currency", "USD").upper()
        raw_val = float(item.get("value_usd", 0))
        usd_val = raw_val / USDPHP_RATE if ccy == "PHP" else raw_val
        veh_items.append({
            "label": item["label"], "value_usd": usd_val,
            "currency": ccy, "native_value": raw_val,
            "note": item.get("_note", ""),
        })
        veh_total += usd_val
    sections.append({"id": "vehicles", "label": "Vehicles",
                     "items": veh_items, "total_usd": veh_total})

    # ── Section 7: Business Equity (PHP/USD aware) ──
    biz_items = []
    biz_total = 0.0
    for item in bs.get("business_equity", []):
        ccy = item.get("currency", "USD").upper()
        raw_val = float(item.get("value_usd", 0))
        usd_val = raw_val / USDPHP_RATE if ccy == "PHP" else raw_val
        biz_items.append({
            "label": item["label"], "value_usd": usd_val,
            "currency": ccy, "native_value": raw_val,
            "note": item.get("_note", ""),
        })
        biz_total += usd_val
    sections.append({"id": "business_equity", "label": "Business Equity",
                     "items": biz_items, "total_usd": biz_total})

    # ── Section 7: Cash Accounts (mixed USD + PHP, normalized to USD) ──
    cash_items = []
    cash_total = 0.0
    for item in bs.get("cash_accounts", []):
        ccy = item.get("currency", "USD").upper()
        raw_val = float(item.get("value", 0))
        if ccy == "PHP":
            usd_val = raw_val / USDPHP_RATE
        else:
            usd_val = raw_val
        cash_items.append({"label": item["label"],
                           "value_usd": usd_val,
                           "currency": ccy,
                           "native_value": raw_val,
                           "note": ""})
        cash_total += usd_val
    sections.append({"id": "cash_accounts", "label": "Cash Accounts",
                     "items": cash_items, "total_usd": cash_total})

    # ── Liabilities (separate from assets) ──
    liab_items = []
    liab_total = 0.0
    for item in bs.get("liabilities", []):
        bal = float(item.get("balance_usd", 0))
        limit = float(item.get("limit_usd", 0))
        liab_items.append({"label": item["label"], "value_usd": bal,
                           "limit_usd": limit, "note": item.get("_note", "")})
        liab_total += bal

    total_assets = sum(s["total_usd"] for s in sections)
    net_worth = total_assets - liab_total

    return {
        "asset_sections": sections,
        "liabilities": {"items": liab_items, "total_usd": liab_total},
        "totals": {
            "assets_usd": total_assets,
            "liabilities_usd": liab_total,
            "net_worth_usd": net_worth,
        },
        "fx": {
            "usdphp_rate": USDPHP_RATE,
        },
    }

balance_sheet = _build_balance_sheet()

print(f"\n── Balance Sheet Snapshot ──")
print(f"  Total Assets     : ${balance_sheet['totals']['assets_usd']:>14,.0f}")
print(f"  Total Liabilities: ${balance_sheet['totals']['liabilities_usd']:>14,.0f}")
print(f"  NET WORTH        : ${balance_sheet['totals']['net_worth_usd']:>14,.0f}")
print(f"  FX rate (PHP/USD): ₱{USDPHP_RATE:.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# CASHFLOW COMPUTATION (Total Holdings tab — Phase 2)
# ─────────────────────────────────────────────────────────────────────────────
# Builds three views from the Cashflow sheet data:
#   1. Annual summary: 3 surplus calculations (cash, with unrealized gains, active only)
#   2. Monthly distribution: 12-month breakdown by frequency
#   3. Category drilldown: line items grouped by category, sortable
#
# Settings tab values used:
#   - investment_return: applied to liquid investments (excludes SPM Fund to avoid
#     double-counting since SPM's 7% interest is already counted in income)
#
# Income/expense items have a `frequency` field that indicates how many times
# per year that amount occurs (1 = annual lump sum, 12 = monthly, 4 = quarterly).
# To distribute across 12 months we infer which months each frequency hits.

def _build_cashflow_summary():
    """Construct cashflow summary, monthly distribution, and category drilldown."""
    cf_items = CASHFLOW_DATA.get("cashflow", [])
    settings = CASHFLOW_DATA.get("settings", {})

    if not cf_items:
        # Phase 2 empty state — Sheet has no data yet
        return {
            "has_data": False,
            "summary": {"income_php": 0, "expense_php": 0, "surplus_cash_php": 0,
                        "investment_gains_php": 0, "surplus_with_gains_php": 0,
                        "active_income_php": 0, "surplus_active_php": 0,
                        "spm_interest_php": 0},
            "monthly": [],
            "income_categories": [],
            "expense_categories": [],
            "fx": {"usdphp_rate": USDPHP_RATE},
        }

    # ── 1. Annual Summary ──
    income_total = sum(it["annual_php"] for it in cf_items if it["type"] == "income")
    expense_total = sum(it["annual_php"] for it in cf_items if it["type"] == "expense")
    surplus_cash = income_total - expense_total

    # SPM interest (already in income — needed to avoid double-counting when adding
    # unrealized gains from liquid investments)
    spm_interest = sum(it["annual_php"] for it in cf_items
                       if it["type"] == "income" and "spm" in it["label"].lower()
                       and ("interest" in it["label"].lower() or "interest" in it["category"].lower()))

    # Liquid investment portfolio for unrealized-gains estimate.
    # We use total liquid investments from the balance sheet (active + legacy +
    # esel + other_investments), then exclude SPM since its interest is already
    # counted in income. Vehicles, real estate, business equity excluded as illiquid.
    bs_data = balance_sheet
    liquid_usd = 0.0
    spm_value_usd = 0.0
    for section in bs_data.get("asset_sections", []):
        sid = section.get("id", "")
        if sid in ("investments_active", "investments_legacy", "esel_investments"):
            liquid_usd += section.get("total_usd", 0)
        elif sid == "investments_other":
            # SPM Fund lives here — subtract it specifically
            for item in section.get("items", []):
                lbl = item.get("label", "").lower()
                if "spm" in lbl:
                    spm_value_usd += item.get("value_usd", 0)
                else:
                    liquid_usd += item.get("value_usd", 0)
    liquid_php = liquid_usd * USDPHP_RATE

    inv_return_pct = float(settings.get("investment_return", 9)) / 100.0  # 9% default
    investment_gains_php = liquid_php * inv_return_pct
    surplus_with_gains = surplus_cash + investment_gains_php

    # Active income surplus: income excluding SPM interest (work-driven income only)
    active_income = income_total - spm_interest
    surplus_active = active_income - expense_total

    summary = {
        "income_php": income_total,
        "expense_php": expense_total,
        "surplus_cash_php": surplus_cash,
        "investment_gains_php": investment_gains_php,
        "surplus_with_gains_php": surplus_with_gains,
        "active_income_php": active_income,
        "surplus_active_php": surplus_active,
        "spm_interest_php": spm_interest,
        "liquid_invest_php": liquid_php,
        "inv_return_pct": inv_return_pct * 100,
    }

    # ── 2. Monthly Distribution ──
    # Distribute each item across 12 months by frequency.
    # Heuristic:
    #   freq == 12 (monthly) → spread evenly across all 12 months
    #   freq == 4 (quarterly) → hit months 3, 6, 9, 12 (Mar/Jun/Sep/Dec)
    #   freq == 2 (semi-annual) → hit months 6, 12 (Jun/Dec)
    #   freq == 1 (annual lump) → hit month 1 (Jan) for salaries; otherwise month 12 (Dec)
    #     Salaries/major income hit January (annual paycheck distribution)
    #     Other annual items (insurance, taxes, etc) default to January as well
    #     for predictability — user can refine via Sheet later.
    #   freq == 3, 6, etc → spread evenly across that many months starting Jan
    months_income = [0.0] * 12
    months_expense = [0.0] * 12
    for it in cf_items:
        freq = int(it.get("frequency", 1))
        annual = it["annual_php"]
        bucket = months_income if it["type"] == "income" else months_expense
        if freq <= 0:
            continue
        per_event = annual / freq
        if freq == 12:
            for m in range(12): bucket[m] += per_event
        elif freq == 4:
            for m in [2, 5, 8, 11]: bucket[m] += per_event   # Mar/Jun/Sep/Dec
        elif freq == 2:
            for m in [5, 11]: bucket[m] += per_event          # Jun/Dec
        elif freq == 1:
            bucket[0] += per_event   # All annual → January
        else:
            # Distribute evenly across first N months
            for m in range(min(freq, 12)): bucket[m] += per_event

    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly = []
    for i, lbl in enumerate(month_labels):
        monthly.append({
            "month": lbl,
            "income_php": months_income[i],
            "expense_php": months_expense[i],
            "net_php": months_income[i] - months_expense[i],
        })

    # ── 3. Category Drilldown ──
    # Group items by (type, category), preserve line items as children.
    def _group(type_):
        groups = {}
        order = []
        for it in cf_items:
            if it["type"] != type_:
                continue
            cat = it["category"] or "Uncategorized"
            if cat not in groups:
                groups[cat] = {"category": cat, "total_php": 0.0, "items": []}
                order.append(cat)
            groups[cat]["total_php"] += it["annual_php"]
            groups[cat]["items"].append({
                "label": it["label"],
                "annual_php": it["annual_php"],
                "amount_php": it["amount_php"],
                "frequency": it["frequency"],
                "note": it.get("note", ""),
            })
        out = [groups[c] for c in order]
        out.sort(key=lambda g: g["total_php"], reverse=True)
        return out

    income_categories = _group("income")
    expense_categories = _group("expense")

    return {
        "has_data": True,
        "summary": summary,
        "monthly": monthly,
        "income_categories": income_categories,
        "expense_categories": expense_categories,
        "fx": {"usdphp_rate": USDPHP_RATE},
    }

cashflow_summary = _build_cashflow_summary()

if cashflow_summary["has_data"]:
    s = cashflow_summary["summary"]
    print(f"\n── Cashflow Summary ──")
    print(f"  Annual Income    : ₱{s['income_php']:>14,.0f}")
    print(f"  Annual Expenses  : ₱{s['expense_php']:>14,.0f}")
    print(f"  Cash Surplus     : ₱{s['surplus_cash_php']:>14,.0f}")
    print(f"  Unrealized Gains : ₱{s['investment_gains_php']:>14,.0f} ({s['inv_return_pct']:.1f}% on ₱{s['liquid_invest_php']:,.0f} liquid)")
    print(f"  Total w/ Gains   : ₱{s['surplus_with_gains_php']:>14,.0f}")
    print(f"  Active Income    : ₱{s['active_income_php']:>14,.0f} (excludes SPM ₱{s['spm_interest_php']:,.0f})")
    print(f"  Active Surplus   : ₱{s['surplus_active_php']:>14,.0f}")
else:
    print(f"\n── Cashflow Summary ── (Phase 2 — no Sheet data yet)")

# ─────────────────────────────────────────────────────────────────────────────
# MAJOR CASHOUTS + 15-YEAR PROJECTION (Total Holdings tab — Phase 3)
# ─────────────────────────────────────────────────────────────────────────────
# Builds the 15-year net worth projection layered with major life events.
# Uses Settings tab assumptions:
#   - salary_growth_rate: annual % increase in income
#   - expense_inflation: annual % increase in expenses (uniform across categories)
#   - investment_return: annual return on portfolio
#   - projection_years: how many years to project (default 15)

def _build_projection():
    """Construct major cashouts table + per-scenario 15-year net worth projection.

    Scenarios (v3.4.0):
      Cashouts are tagged with a `scenario` field in the Sheet:
        - 'base'             → always applied (vehicles, real estate, healthcare)
        - 'us_private'       → all 4 kids US private undergrad (base case)
        - 'us_public'        → all 4 kids US public undergrad
        - 'ph_with_masters'  → all 4 kids Manila undergrad + masters abroad later

      For each toggle-able scenario we compute a separate projection series.
      `base` items are always included regardless of toggle.
    """
    cashouts = CASHFLOW_DATA.get("major_cashouts", [])
    settings = CASHFLOW_DATA.get("settings", {})
    cf_summary = cashflow_summary["summary"]

    proj_years = int(settings.get("projection_years", 15))
    salary_growth = float(settings.get("salary_growth_rate", 5)) / 100.0
    expense_infl = float(settings.get("expense_inflation", 4)) / 100.0
    inv_return = float(settings.get("investment_return", 9)) / 100.0

    starting_nw_usd = balance_sheet["totals"]["net_worth_usd"]
    starting_nw_php = starting_nw_usd * USDPHP_RATE
    starting_income = cf_summary.get("income_php", 0)
    starting_expense = cf_summary.get("expense_php", 0)

    current_year = datetime.today().year

    # Auto-extend horizon if cashouts go past the default window.
    # E.g. ph_with_masters has Anul's masters in 2052; we'd want to model through then.
    if cashouts:
        max_cashout_year = max(co["year"] for co in cashouts)
        years_to_max = max_cashout_year - current_year
        if years_to_max > proj_years:
            proj_years = years_to_max + 2   # extra buffer past last cashout
            print(f"  ℹ Projection horizon auto-extended to {proj_years}yr to cover cashouts through {max_cashout_year}")

    # Discover unique scenario tags + classify each
    BASE_TAG = "base"
    scenario_tags = sorted(set(co["scenario"] for co in cashouts))
    toggle_scenarios = [s for s in scenario_tags if s != BASE_TAG]
    if not toggle_scenarios:
        # Empty Sheet or only base items — show one "base" scenario anyway
        toggle_scenarios = [BASE_TAG]

    # Friendly labels for each scenario (used by dashboard toggle)
    SCENARIO_LABELS = {
        "base":             "Base only",
        "us_private":       "US Private (base case)",
        "us_public":        "US Public",
        "ph_with_masters":  "Manila + Masters",
    }

    def _project_for_scenarios(active_scenarios):
        """Run the year-by-year compounding model for a given set of active scenarios.
        Base items always count; toggle scenarios only count if in active_scenarios."""
        # Aggregate cashouts by year, filtered by scenario membership
        cashouts_by_year = {}
        for co in cashouts:
            sc = co["scenario"]
            if sc != BASE_TAG and sc not in active_scenarios:
                continue
            yr = co["year"]
            amt_php = co.get("amount_usd", 0) * USDPHP_RATE
            cashouts_by_year[yr] = cashouts_by_year.get(yr, 0) + amt_php

        projection = []
        nw_php = starting_nw_php
        running_total = 0.0
        for i in range(proj_years + 1):
            yr = current_year + i
            income_yr = starting_income * ((1 + salary_growth) ** i)
            expense_yr = starting_expense * ((1 + expense_infl) ** i)
            surplus_yr = income_yr - expense_yr
            gains_yr = nw_php * inv_return
            cashout_yr = cashouts_by_year.get(yr, 0)
            running_total += cashout_yr
            nw_php = nw_php + surplus_yr + gains_yr - cashout_yr
            projection.append({
                "year": yr, "year_index": i,
                "income_php": income_yr, "expense_php": expense_yr,
                "surplus_php": surplus_yr, "gains_php": gains_yr,
                "cashout_php": cashout_yr,
                "net_worth_php": nw_php,
                "running_cashout_php": running_total,
            })
        return projection

    # Build projection series for each scenario (base only, plus each toggle scenario)
    projections_by_scenario = {}
    for sc in toggle_scenarios:
        projections_by_scenario[sc] = _project_for_scenarios({sc})
    # Also include a "base only" series (no education) for comparison
    projections_by_scenario["__base_only__"] = _project_for_scenarios(set())

    # Default scenario for initial render: us_private if available, else first toggle
    default_scenario = "us_private" if "us_private" in toggle_scenarios else toggle_scenarios[0]

    # Cashouts grouped by scenario (for tab rendering)
    cashouts_by_scenario = {}
    for co in cashouts:
        cashouts_by_scenario.setdefault(co["scenario"], []).append(co)

    # Category totals (used by Major Cashouts tab summary cards)
    def _category_totals(active_scenarios):
        totals = {}
        for co in cashouts:
            sc = co["scenario"]
            if sc != BASE_TAG and sc not in active_scenarios:
                continue
            cat = co.get("category") or "Uncategorized"
            totals[cat] = totals.get(cat, 0) + co.get("amount_usd", 0)
        return totals

    category_totals_by_scenario = {
        sc: _category_totals({sc}) for sc in toggle_scenarios
    }

    # For backward compat (Projection tab existing code), also expose the
    # "default" projection at the top level
    default_projection = projections_by_scenario.get(default_scenario, [])

    return {
        "has_cashout_data": len(cashouts) > 0,
        "cashouts": cashouts,
        "cashouts_by_scenario": cashouts_by_scenario,
        "scenarios": toggle_scenarios,
        "scenario_labels": {sc: SCENARIO_LABELS.get(sc, sc.replace("_", " ").title())
                            for sc in toggle_scenarios + ["__base_only__"]},
        "default_scenario": default_scenario,
        "projections_by_scenario": projections_by_scenario,
        "category_totals_by_scenario": category_totals_by_scenario,
        "projection": default_projection,   # backward compat
        "assumptions": {
            "salary_growth_pct": salary_growth * 100,
            "expense_inflation_pct": expense_infl * 100,
            "investment_return_pct": inv_return * 100,
            "projection_years": proj_years,
            "starting_nw_php": starting_nw_php,
            "starting_nw_usd": starting_nw_usd,
        },
        "fx": {"usdphp_rate": USDPHP_RATE},
    }

projection_data = _build_projection()
print(f"\n── Projection (Phase 3/4) ──")
print(f"  Years projected   : {projection_data['assumptions']['projection_years']}")
print(f"  Starting NW       : ₱{projection_data['assumptions']['starting_nw_php']:,.0f}")
print(f"  Major cashouts    : {len(projection_data['cashouts'])} items"
      + (" (Sheet empty — populate Major_Cashouts tab)" if not projection_data["has_cashout_data"] else ""))
if projection_data["scenarios"]:
    print(f"  Scenarios         : {', '.join(projection_data['scenarios'])} (default: {projection_data['default_scenario']})")
    for sc in projection_data["scenarios"]:
        sc_proj = projection_data["projections_by_scenario"][sc]
        if sc_proj:
            final = sc_proj[-1]
            sc_total = sum(co["amount_usd"] for co in projection_data["cashouts_by_scenario"].get(sc, []))
            print(f"    {sc:20s} → Year {final['year']} NW: ₱{final['net_worth_php']:,.0f} "
                  f"(scenario total cashouts: ${sc_total:,.0f})")
if projection_data["projection"]:
    final = projection_data["projection"][-1]
    print(f"  Default scenario  : Year {final['year']} NW: ₱{final['net_worth_php']:,.0f}")

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
    "balance_sheet": balance_sheet,
    "cashflow_summary": cashflow_summary,
    "projection": projection_data,
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

# ── Balance Sheet HTML rows (Total Holdings tab) ──
# Build section headers + line item rows.
# Each value cell gets a data-usd attribute so JS can re-render in PHP on toggle.
_total_assets = balance_sheet["totals"]["assets_usd"]
bs_assets_html = ""
for section in balance_sheet["asset_sections"]:
    sec_pct = (section["total_usd"] / _total_assets * 100) if _total_assets > 0 else 0
    # Section header row
    bs_assets_html += f"""
        <tr class="bs-section-row">
          <td><strong>{section['label']}</strong></td>
          <td class="bs-num"><strong data-usd="{section['total_usd']:.2f}">${section['total_usd']:,.0f}</strong></td>
          <td class="bs-num"><strong>{sec_pct:.1f}%</strong></td>
          <td></td>
        </tr>"""
    # Line items
    for it in section["items"]:
        note = it.get("note", "")
        native_info = ""
        if it.get("currency") == "PHP":
            native_info = f" <span class='bs-native'>(₱{it['native_value']:,.0f} native)</span>"
        bs_assets_html += f"""
        <tr class="bs-item-row">
          <td><span class="bs-tree">├─</span> {it['label']}{native_info}</td>
          <td class="bs-num" data-usd="{it['value_usd']:.2f}">${it['value_usd']:,.0f}</td>
          <td class="bs-num bs-mut">—</td>
          <td class="bs-note">{note}</td>
        </tr>"""

# Liabilities rows
bs_liab_html = ""
liab_items = balance_sheet["liabilities"]["items"]
if not liab_items:
    bs_liab_html = """
        <tr class="bs-item-row">
          <td colspan="4" style="text-align:center;color:var(--mut);font-style:italic">No liabilities tracked</td>
        </tr>"""
else:
    for it in liab_items:
        bs_liab_html += f"""
        <tr class="bs-item-row">
          <td>{it['label']}</td>
          <td class="bs-num" data-usd="{it['value_usd']:.2f}">${it['value_usd']:,.0f}</td>
          <td class="bs-num bs-mut" data-usd="{it['limit_usd']:.2f}">${it['limit_usd']:,.0f}</td>
          <td class="bs-note">{it.get('note', '')}</td>
        </tr>"""


# ── Cashflow tab HTML (Phase 2) ──
# Three stacked sections: annual summary, monthly chart, category drilldown.
# Values stored in PHP with data-php attributes for JS currency toggle.
def _build_cashflow_tab_html():
    cs = cashflow_summary
    rate = USDPHP_RATE
    if not cs["has_data"]:
        return f"""
    <!-- Currency toggle (matches Balance Sheet pattern) -->
    <div class="bs-header-row">
      <div class="bs-fx-info">
        <span class="bs-fx-label">FX Rate:</span>
        <span class="bs-fx-rate">₱{rate:.4f} / $1</span>
      </div>
      <div class="bs-currency-toggle">
        <button class="bs-ccy-btn active" data-ccy="USD" onclick="switchCurrency('USD')">USD ($)</button>
        <button class="bs-ccy-btn" data-ccy="PHP" onclick="switchCurrency('PHP')">PHP (₱)</button>
      </div>
    </div>
    <div class="bs-section">
      <div class="cf-empty">
        <div class="cf-empty-icon">⏳</div>
        <div class="cf-empty-title">Cashflow tab — waiting for Sheet data</div>
        <div class="cf-empty-msg">Populate the <code>Cashflow</code> tab of your Google Sheet with income and expense rows. Columns: Type, Category, Label, Amount_PHP, Frequency, Annual_Total_PHP, Notes.</div>
      </div>
    </div>"""

    s = cs["summary"]

    def php_cell(php_val, bold=False):
        """Render a cell with both PHP and USD values, toggleable."""
        usd_val = php_val / rate if rate else 0
        wrapper = "strong" if bold else "span"
        return f'<{wrapper} data-php="{php_val:.2f}" data-usd="{usd_val:.2f}">₱{php_val:,.0f}</{wrapper}>'

    # ── 1. Annual Summary cards ──
    header_html = f"""
    <!-- Currency toggle (matches Balance Sheet pattern) -->
    <div class="bs-header-row">
      <div class="bs-fx-info">
        <span class="bs-fx-label">FX Rate:</span>
        <span class="bs-fx-rate">₱{rate:.4f} / $1</span>
      </div>
      <div class="bs-currency-toggle">
        <button class="bs-ccy-btn active" data-ccy="USD" onclick="switchCurrency('USD')">USD ($)</button>
        <button class="bs-ccy-btn" data-ccy="PHP" onclick="switchCurrency('PHP')">PHP (₱)</button>
      </div>
    </div>"""
    summary_html = f"""
    <div class="bs-section">
      <div class="section-hd">
        <span>1 · ANNUAL SUMMARY</span>
        <span style="font-size:9px;color:var(--mut)">Three views of yearly surplus</span>
      </div>
      <div class="cf-summary-grid">
        <div class="cf-summary-card">
          <div class="cf-card-title">Cash Surplus</div>
          <div class="cf-card-sub">Income − Expenses (Sheet totals)</div>
          <div class="cf-card-row"><span>Income</span>{php_cell(s['income_php'])}</div>
          <div class="cf-card-row"><span>Expenses</span>{php_cell(s['expense_php'])}</div>
          <div class="cf-card-divider"></div>
          <div class="cf-card-headline">{php_cell(s['surplus_cash_php'], bold=True)}</div>
        </div>

        <div class="cf-summary-card cf-card-mid">
          <div class="cf-card-title">Total Wealth Growth</div>
          <div class="cf-card-sub">Cash surplus + unrealized investment gains ({s['inv_return_pct']:.1f}% on liquid)</div>
          <div class="cf-card-row"><span>Cash Surplus</span>{php_cell(s['surplus_cash_php'])}</div>
          <div class="cf-card-row"><span>Inv. Gains (est.)</span>{php_cell(s['investment_gains_php'])}</div>
          <div class="cf-card-divider"></div>
          <div class="cf-card-headline">{php_cell(s['surplus_with_gains_php'], bold=True)}</div>
        </div>

        <div class="cf-summary-card">
          <div class="cf-card-title">Active Income Surplus</div>
          <div class="cf-card-sub">Work-driven (excludes SPM ₱{s['spm_interest_php']:,.0f} interest)</div>
          <div class="cf-card-row"><span>Active Income</span>{php_cell(s['active_income_php'])}</div>
          <div class="cf-card-row"><span>Expenses</span>{php_cell(s['expense_php'])}</div>
          <div class="cf-card-divider"></div>
          <div class="cf-card-headline">{php_cell(s['surplus_active_php'], bold=True)}</div>
        </div>
      </div>
    </div>"""

    # ── 2. Monthly Breakdown Chart ──
    monthly_html = """
    <div class="bs-section">
      <div class="section-hd">
        <span>2 · MONTHLY BREAKDOWN</span>
        <span style="font-size:9px;color:var(--mut)">Income/expenses distributed by frequency · Annual lumps → January</span>
      </div>
      <div class="cf-chart-wrap"><canvas id="cfMonthlyChart" role="img" aria-label="Monthly income vs expenses chart"></canvas></div>
      <div class="cf-legend">
        <div class="cf-li"><div class="cf-ln" style="background:#15803d"></div>Income</div>
        <div class="cf-li"><div class="cf-ln" style="background:#b91c1c"></div>Expenses</div>
        <div class="cf-li"><div class="cf-ln" style="background:#1d4ed8;height:3px"></div>Net Cashflow</div>
      </div>
    </div>"""

    # ── 3. Income Categories drilldown ──
    income_rows = ""
    for cat in cs["income_categories"]:
        cat_id = "inc-" + cat["category"].replace(" ", "-").lower()
        income_rows += f"""
        <tr class="cf-cat-row" onclick="toggleCategory('{cat_id}')">
          <td><span class="cf-toggle" id="{cat_id}-toggle">▸</span> <strong>{cat['category']}</strong></td>
          <td class="cf-num">{php_cell(cat['total_php'], bold=True)}</td>
          <td class="cf-num bs-mut">{len(cat['items'])} item{'s' if len(cat['items']) != 1 else ''}</td>
        </tr>"""
        for it in cat["items"]:
            freq = int(it["frequency"])
            freq_lbl = {12: "monthly", 4: "quarterly", 2: "semi-annual", 1: "annual"}.get(freq, f"{freq}×/yr")
            income_rows += f"""
        <tr class="cf-item-row cf-hidden" data-parent="{cat_id}">
          <td><span class="bs-tree">├─</span> {it['label']} <span class="cf-freq">({freq_lbl})</span></td>
          <td class="cf-num">{php_cell(it['annual_php'])}</td>
          <td class="cf-num bs-mut">{it.get('note', '')}</td>
        </tr>"""

    expense_rows = ""
    for cat in cs["expense_categories"]:
        cat_id = "exp-" + cat["category"].replace(" ", "-").lower()
        pct = (cat["total_php"] / s["expense_php"] * 100) if s["expense_php"] else 0
        expense_rows += f"""
        <tr class="cf-cat-row" onclick="toggleCategory('{cat_id}')">
          <td><span class="cf-toggle" id="{cat_id}-toggle">▸</span> <strong>{cat['category']}</strong></td>
          <td class="cf-num">{php_cell(cat['total_php'], bold=True)}</td>
          <td class="cf-num bs-mut">{pct:.1f}% · {len(cat['items'])} item{'s' if len(cat['items']) != 1 else ''}</td>
        </tr>"""
        for it in cat["items"]:
            freq = int(it["frequency"])
            freq_lbl = {12: "monthly", 4: "quarterly", 2: "semi-annual", 1: "annual"}.get(freq, f"{freq}×/yr")
            expense_rows += f"""
        <tr class="cf-item-row cf-hidden" data-parent="{cat_id}">
          <td><span class="bs-tree">├─</span> {it['label']} <span class="cf-freq">({freq_lbl})</span></td>
          <td class="cf-num">{php_cell(it['annual_php'])}</td>
          <td class="cf-num bs-mut">{it.get('note', '')}</td>
        </tr>"""

    drilldown_html = f"""
    <div class="bs-section">
      <div class="section-hd">
        <span>3 · CATEGORY DRILLDOWN</span>
        <span style="font-size:9px;color:var(--mut)">Click any category row to expand line items</span>
      </div>

      <div class="cf-subhd cf-subhd-inc">INCOME · ₱{s['income_php']:,.0f} annual</div>
      <table class="cf-table">
        <thead>
          <tr><th>Category / Line Item</th><th class="cf-num">Annual</th><th class="cf-num">Detail</th></tr>
        </thead>
        <tbody>{income_rows}
        </tbody>
      </table>

      <div class="cf-subhd cf-subhd-exp" style="margin-top:20px">EXPENSES · ₱{s['expense_php']:,.0f} annual</div>
      <table class="cf-table">
        <thead>
          <tr><th>Category / Line Item</th><th class="cf-num">Annual</th><th class="cf-num">% / Detail</th></tr>
        </thead>
        <tbody>{expense_rows}
        </tbody>
      </table>
    </div>"""

    return header_html + summary_html + monthly_html + drilldown_html

cashflow_tab_html = _build_cashflow_tab_html()

# ── Projection tab HTML (Phase 3) ──
# Three stacked sections: timeline chart, year-by-year table, 15-yr NW projection.
# Skeleton mode when Major_Cashouts sheet is empty.
def _build_projection_tab_html():
    pd_ = projection_data
    a = pd_["assumptions"]
    has_co = pd_["has_cashout_data"]
    rate = USDPHP_RATE

    header_html = f"""
    <!-- Currency toggle (matches Balance Sheet pattern) -->
    <div class="bs-header-row">
      <div class="bs-fx-info">
        <span class="bs-fx-label">FX Rate:</span>
        <span class="bs-fx-rate">₱{rate:.4f} / $1</span>
      </div>
      <div class="bs-currency-toggle">
        <button class="bs-ccy-btn active" data-ccy="USD" onclick="switchCurrency('USD')">USD ($)</button>
        <button class="bs-ccy-btn" data-ccy="PHP" onclick="switchCurrency('PHP')">PHP (₱)</button>
      </div>
    </div>"""

    # Empty-state banner if Sheet not populated
    cashout_banner = ""
    if not has_co:
        cashout_banner = """
      <div class="cf-empty cf-empty-inline">
        <strong>No major cashouts populated yet.</strong> Add rows to the <code>Major_Cashouts</code> tab (columns: Year, Item, Amount_USD, Category, Notes) to see them appear in the timeline and pull from net worth in the projection.
      </div>"""

    # ── Assumption chips header ──
    assumptions_html = f"""
    <div class="bs-section">
      <div class="section-hd">
        <span>PROJECTION ASSUMPTIONS</span>
        <span style="font-size:9px;color:var(--mut)">From Settings tab · Editable in Sheet</span>
      </div>
      <div class="proj-chips">
        <div class="proj-chip"><span>{a['salary_growth_pct']:.1f}%</span><small>Salary Growth</small></div>
        <div class="proj-chip"><span>{a['expense_inflation_pct']:.1f}%</span><small>Expense Inflation</small></div>
        <div class="proj-chip"><span>{a['investment_return_pct']:.1f}%</span><small>Investment Return</small></div>
        <div class="proj-chip"><span>{a['projection_years']}y</span><small>Horizon</small></div>
        <div class="proj-chip proj-chip-nw"><span>${a['starting_nw_usd']/1000:,.0f}K</span><small>Starting Net Worth</small></div>
      </div>
    </div>"""

    # ── 1. Timeline chart ──
    timeline_html = f"""
    <div class="bs-section">
      <div class="section-hd">
        <span>1 · CASHOUT TIMELINE</span>
        <span style="font-size:9px;color:var(--mut)">Bubble size = amount · Hover for details</span>
      </div>
      {cashout_banner}
      <div class="cf-chart-wrap"><canvas id="projTimelineChart" role="img" aria-label="Major cashouts timeline"></canvas></div>
    </div>"""

    # ── 2. Year-by-year table ──
    table_rows = ""
    cashouts_by_year = {}
    for co in pd_["cashouts"]:
        cashouts_by_year.setdefault(co["year"], []).append(co)

    for row in pd_["projection"]:
        yr = row["year"]
        yr_cashouts = cashouts_by_year.get(yr, [])
        nw_php = row["net_worth_php"]
        nw_usd = nw_php / USDPHP_RATE if USDPHP_RATE else 0
        co_php = row["cashout_php"]
        co_usd = co_php / USDPHP_RATE if USDPHP_RATE else 0
        running_co_usd = row["running_cashout_php"] / USDPHP_RATE if USDPHP_RATE else 0

        # Cashout items column
        if yr_cashouts:
            items_str = ", ".join([f"{co['item']} (${co['amount_usd']/1000:,.0f}K)" for co in yr_cashouts])
        else:
            items_str = "—"

        cashout_cls = "cf-num proj-cashout" if co_php > 0 else "cf-num bs-mut"
        table_rows += f"""
        <tr class="proj-row">
          <td><strong>{yr}</strong></td>
          <td class="cf-num"><span data-php="{nw_php:.2f}" data-usd="{nw_usd:.2f}">₱{nw_php/1e6:,.1f}M</span></td>
          <td class="{cashout_cls}"><span data-php="{co_php:.2f}" data-usd="{co_usd:.2f}">{'₱' + f'{co_php/1e6:,.1f}M' if co_php > 0 else '—'}</span></td>
          <td class="cf-num bs-mut"><span data-php="{row['running_cashout_php']:.2f}" data-usd="{running_co_usd:.2f}">₱{row['running_cashout_php']/1e6:,.1f}M</span></td>
          <td class="cf-num bs-mut">{items_str}</td>
        </tr>"""

    yearly_html = f"""
    <div class="bs-section">
      <div class="section-hd">
        <span>2 · YEAR-BY-YEAR</span>
        <span style="font-size:9px;color:var(--mut)">Net worth trajectory with cashout impact</span>
      </div>
      <table class="cf-table">
        <thead>
          <tr>
            <th>Year</th>
            <th class="cf-num">Net Worth (EOY)</th>
            <th class="cf-num">Cashout</th>
            <th class="cf-num">Running Total</th>
            <th class="cf-num">Items</th>
          </tr>
        </thead>
        <tbody>{table_rows}
        </tbody>
      </table>
    </div>"""

    # ── 3. 15-year projection chart ──
    nw_chart_html = """
    <div class="bs-section">
      <div class="section-hd">
        <span>3 · 15-YEAR NET WORTH PROJECTION</span>
        <span style="font-size:9px;color:var(--mut)">Compound growth − major cashouts</span>
      </div>
      <div class="cf-chart-wrap" style="height:340px"><canvas id="projNWChart" role="img" aria-label="15-year net worth projection"></canvas></div>
      <div class="cf-legend">
        <div class="cf-li"><div class="cf-ln" style="background:#7c3aed"></div>Net Worth (with cashouts)</div>
        <div class="cf-li"><div class="cf-ln" style="background:#7c3aed;opacity:.35;border-top:1.5px dashed #7c3aed"></div>Without cashouts (reference)</div>
      </div>
    </div>"""

    return header_html + assumptions_html + timeline_html + yearly_html + nw_chart_html

projection_tab_html = _build_projection_tab_html()

# ── Major Cashouts tab HTML (Phase 4) ──
# Three sections + scenario toggle:
#   1. Scenario toggle (US Private / US Public / Manila + Masters)
#   2. Summary cards (total cashouts, by category, by decade)
#   3. Filterable table (all rows for active scenario + base)
#   4. "Edit in Sheet" button (deep link)
def _build_cashouts_tab_html():
    pd_ = projection_data
    has_co = pd_["has_cashout_data"]
    rate = USDPHP_RATE

    # Currency toggle header (consistent with other tabs)
    header_html = f"""
    <div class="bs-header-row">
      <div class="bs-fx-info">
        <span class="bs-fx-label">FX Rate:</span>
        <span class="bs-fx-rate">₱{rate:.4f} / $1</span>
      </div>
      <div class="bs-currency-toggle">
        <button class="bs-ccy-btn active" data-ccy="USD" onclick="switchCurrency('USD')">USD ($)</button>
        <button class="bs-ccy-btn" data-ccy="PHP" onclick="switchCurrency('PHP')">PHP (₱)</button>
      </div>
    </div>"""

    if not has_co:
        # Empty state — Sheet not populated yet
        sheet_url = "https://docs.google.com/spreadsheets/d/1Kal6N5jcJz3wUfBhxvkIS1YMm5ToEz4CI6tsZPZSZG4"
        return header_html + f"""
    <div class="bs-section">
      <div class="cf-empty">
        <div class="cf-empty-icon">📋</div>
        <div class="cf-empty-title">Major Cashouts tab — waiting for Sheet data</div>
        <div class="cf-empty-msg">Populate the <code>Major_Cashouts</code> tab of your Google Sheet with future large expenses.<br/>
        Columns: <code>Year</code> · <code>Item</code> · <code>Amount_USD</code> · <code>Category</code> · <code>Scenario</code> · <code>Notes</code></div>
        <a href="{sheet_url}" target="_blank" class="cf-btn cf-btn-primary" style="margin-top:14px">Open Sheet to Edit</a>
      </div>
    </div>"""

    # Scenario tabs + "Edit in Sheet" button
    scenario_labels = pd_["scenario_labels"]
    default_sc = pd_["default_scenario"]
    sheet_url = "https://docs.google.com/spreadsheets/d/1Kal6N5jcJz3wUfBhxvkIS1YMm5ToEz4CI6tsZPZSZG4/edit#gid=2138882399"
    scenario_btns = "".join([
        f'<button class="co-sc-btn{" active" if sc == default_sc else ""}" data-scenario="{sc}" onclick="switchScenario(\'{sc}\')">{scenario_labels[sc]}</button>'
        for sc in pd_["scenarios"]
    ])

    toolbar_html = f"""
    <div class="co-toolbar">
      <div class="co-sc-toggle">
        <span class="co-sc-label">SCENARIO:</span>{scenario_btns}
      </div>
      <a href="{sheet_url}" target="_blank" class="cf-btn">+ Edit in Sheet</a>
    </div>"""

    # Build per-scenario summary cards
    # We render ALL scenarios but only show one at a time via JS class toggling
    summary_cards = ""
    for sc in pd_["scenarios"]:
        cat_totals = pd_["category_totals_by_scenario"][sc]
        sc_cashouts = pd_["cashouts_by_scenario"].get(sc, [])
        base_cashouts = pd_["cashouts_by_scenario"].get("base", [])
        total_usd = sum(co["amount_usd"] for co in sc_cashouts) + sum(co["amount_usd"] for co in base_cashouts)
        total_php = total_usd * rate

        # Category cards
        cat_cards = ""
        for cat, amt_usd in sorted(cat_totals.items(), key=lambda x: -x[1]):
            amt_php = amt_usd * rate
            pct = (amt_usd / total_usd * 100) if total_usd > 0 else 0
            cat_cards += f"""
        <div class="co-cat-card">
          <div class="co-cat-name">{cat}</div>
          <div class="co-cat-amt" data-php="{amt_php:.2f}" data-usd="{amt_usd:.2f}">${amt_usd:,.0f}</div>
          <div class="co-cat-pct">{pct:.0f}% of total</div>
        </div>"""

        # By-decade summary
        decade_totals = {}
        for co in sc_cashouts + base_cashouts:
            decade = (co["year"] // 10) * 10
            decade_totals[decade] = decade_totals.get(decade, 0) + co["amount_usd"]
        decade_cards = ""
        for dec, amt_usd in sorted(decade_totals.items()):
            amt_php = amt_usd * rate
            decade_cards += f"""
        <div class="co-dec-card">
          <div class="co-dec-name">{dec}s</div>
          <div class="co-dec-amt" data-php="{amt_php:.2f}" data-usd="{amt_usd:.2f}">${amt_usd:,.0f}</div>
        </div>"""

        summary_cards += f"""
      <div class="co-summary-block co-sc-content" data-scenario="{sc}" style="{'display:block' if sc == default_sc else 'display:none'}">
        <div class="co-headline-row">
          <div class="co-headline-card">
            <div class="co-headline-label">TOTAL CASHOUTS · {scenario_labels[sc]}</div>
            <div class="co-headline-value" data-php="{total_php:.2f}" data-usd="{total_usd:.2f}">${total_usd:,.0f}</div>
            <div class="co-headline-sub">{len(sc_cashouts) + len(base_cashouts)} items across {pd_["assumptions"]["projection_years"]+1} years</div>
          </div>
        </div>

        <div class="co-subhd">BY CATEGORY</div>
        <div class="co-cat-grid">{cat_cards}
        </div>

        <div class="co-subhd" style="margin-top:18px">BY DECADE</div>
        <div class="co-dec-grid">{decade_cards}
        </div>
      </div>"""

    summary_html = f"""
    <div class="bs-section">
      <div class="section-hd">
        <span>1 · SCENARIO SUMMARY</span>
        <span style="font-size:9px;color:var(--mut)">Base items always counted · Education varies by scenario</span>
      </div>{summary_cards}
    </div>"""

    # Build per-scenario tables
    table_blocks = ""
    for sc in pd_["scenarios"]:
        sc_cashouts = pd_["cashouts_by_scenario"].get(sc, [])
        base_cashouts = pd_["cashouts_by_scenario"].get("base", [])
        combined = sorted(sc_cashouts + base_cashouts, key=lambda r: (r["year"], -r["amount_usd"]))

        rows_html = ""
        for co in combined:
            amt_usd = co["amount_usd"]
            amt_php = amt_usd * rate
            sc_label = "base" if co["scenario"] == "base" else co["scenario"]
            sc_class = "co-tag-base" if co["scenario"] == "base" else "co-tag-scenario"
            note = co.get("note", "") or "—"
            rows_html += f"""
          <tr>
            <td><strong>{co['year']}</strong></td>
            <td>{co['item']}</td>
            <td class="cf-num"><span data-php="{amt_php:.2f}" data-usd="{amt_usd:.2f}">${amt_usd:,.0f}</span></td>
            <td><span class="co-cat-tag">{co['category']}</span></td>
            <td><span class="co-tag {sc_class}">{sc_label}</span></td>
            <td class="co-note">{note}</td>
          </tr>"""

        table_blocks += f"""
      <div class="co-sc-content" data-scenario="{sc}" style="{'display:block' if sc == default_sc else 'display:none'}">
        <table class="cf-table">
          <thead>
            <tr>
              <th>Year</th>
              <th>Item</th>
              <th class="cf-num">Amount</th>
              <th>Category</th>
              <th>Scenario</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>{rows_html}
          </tbody>
        </table>
      </div>"""

    table_html = f"""
    <div class="bs-section">
      <div class="section-hd">
        <span>2 · CASHOUT DETAIL</span>
        <span style="font-size:9px;color:var(--mut)">All items in active scenario · Sorted by year</span>
      </div>{table_blocks}
    </div>"""

    # Build per-scenario impact chart
    impact_html = """
    <div class="bs-section">
      <div class="section-hd">
        <span>3 · NET WORTH IMPACT</span>
        <span style="font-size:9px;color:var(--mut)">All three scenarios overlaid · Toggle above shifts emphasis</span>
      </div>
      <div class="cf-chart-wrap" style="height:340px"><canvas id="coImpactChart" role="img" aria-label="Net worth impact by scenario"></canvas></div>
      <div class="cf-legend" id="coImpactLegend"></div>
    </div>"""

    return header_html + toolbar_html + summary_html + table_html + impact_html

cashouts_tab_html = _build_cashouts_tab_html()

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

/* ═══════════════════════════════════════════════════════════════════════════
   TAB NAVIGATION — Investment Dashboard | Total Holdings
   ═══════════════════════════════════════════════════════════════════════════ */
.main-tabs{{display:flex;gap:0;border-bottom:1.5px solid var(--bdr2);margin:18px 0 20px;padding:0}}
.main-tab{{background:transparent;border:none;padding:11px 22px;font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:600;color:var(--mut);cursor:pointer;letter-spacing:.04em;text-transform:uppercase;border-bottom:2.5px solid transparent;margin-bottom:-1.5px;transition:all .15s ease}}
.main-tab:hover{{color:var(--txt)}}
.main-tab.active{{color:var(--txt);border-bottom-color:var(--zone)}}
.tab-content{{display:none}}
.tab-content.active{{display:block}}

/* ═══════════════════════════════════════════════════════════════════════════
   TOTAL HOLDINGS TAB — Phase 1: Balance Sheet
   ═══════════════════════════════════════════════════════════════════════════ */

/* Header row: FX info + currency toggle */
.bs-header-row{{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;padding:14px 18px;background:var(--surf2);border:.5px solid var(--bdr);border-radius:6px}}
.bs-fx-info{{display:flex;align-items:center;gap:10px;font-size:11px}}
.bs-fx-label{{color:var(--mut);letter-spacing:.04em;text-transform:uppercase;font-size:9px}}
.bs-fx-rate{{font-weight:700;color:var(--txt);font-size:13px}}
.bs-fx-source{{font-size:9px;color:var(--mut);font-style:italic}}
.bs-currency-toggle{{display:flex;gap:0;background:var(--bg);border:.5px solid var(--bdr);border-radius:4px;padding:2px}}
.bs-ccy-btn{{background:transparent;border:none;padding:6px 14px;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:600;color:var(--mut);cursor:pointer;border-radius:3px;transition:all .15s}}
.bs-ccy-btn:hover{{color:var(--txt)}}
.bs-ccy-btn.active{{background:var(--txt);color:var(--bg)}}

/* Net worth headline cards */
.bs-headline{{display:flex;align-items:center;gap:14px;margin-bottom:28px}}
.bs-headline-card{{flex:1;padding:18px 20px;background:var(--surf);border:.5px solid var(--bdr);border-radius:6px}}
.bs-headline-card.bs-networth{{background:linear-gradient(180deg, var(--surf) 0%, var(--surf2) 100%);border-color:var(--zone);border-width:1px}}
.bs-headline-label{{font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:var(--mut);margin-bottom:8px}}
.bs-headline-value{{font-family:'Syne',sans-serif;font-size:26px;font-weight:700;color:var(--txt);letter-spacing:-.01em}}
.bs-networth .bs-headline-value{{color:var(--zone)}}
.bs-headline-op{{font-size:24px;font-weight:300;color:var(--mut);font-family:'Syne',sans-serif}}

/* Balance sheet section */
.bs-section{{margin-bottom:28px}}

/* Balance sheet table */
.bs-table{{width:100%;border-collapse:collapse;font-size:11px}}
.bs-table th{{text-align:left;padding:9px 10px;font-weight:600;color:var(--mut);font-size:9px;letter-spacing:.08em;text-transform:uppercase;border-bottom:1px solid var(--bdr2);background:var(--surf2)}}
.bs-table th.bs-num{{text-align:right}}
.bs-table td{{padding:8px 10px;border-bottom:.5px solid var(--bdr)}}
.bs-table td.bs-num{{text-align:right;font-variant-numeric:tabular-nums;font-feature-settings:"tnum" 1}}
.bs-mut{{color:var(--mut)}}
.bs-note{{font-size:10px;color:var(--mut);font-style:italic}}
.bs-note-col{{max-width:280px}}

/* Section header rows (Real Estate, Investments — Active, etc.) */
.bs-section-row{{background:var(--surf2);border-top:1px solid var(--bdr2)}}
.bs-section-row td{{padding:11px 10px;font-size:11.5px;color:var(--txt)}}

/* Line item rows (indented) */
.bs-item-row td:first-child{{padding-left:24px;font-size:10.5px;color:var(--txt)}}
.bs-tree{{color:var(--mut);font-family:monospace;margin-right:4px;font-size:9px}}
.bs-native{{font-size:9px;color:var(--mut);font-style:italic;margin-left:6px}}

/* Grand total footer row */
.bs-grand-total{{background:var(--surf2);border-top:1.5px solid var(--bdr2);font-weight:700}}
.bs-grand-total td{{padding:12px 10px;font-size:12px}}

/* Footnote */
.bs-footnote{{margin-top:20px;padding:12px 14px;background:var(--surf2);border:.5px solid var(--bdr);border-radius:4px;font-size:10px;color:var(--mut);line-height:1.6}}
.bs-footnote code{{background:var(--bg);padding:1px 5px;border-radius:2px;font-family:'JetBrains Mono',monospace;font-size:9.5px;color:var(--txt)}}

/* ═══════════════════════════════════════════════════════════════════════════
   CASHFLOW + PROJECTION TABS — Phase 2/3
   ═══════════════════════════════════════════════════════════════════════════ */

/* Empty state */
.cf-empty{{padding:32px 24px;background:var(--surf2);border:.5px solid var(--bdr);border-radius:6px;text-align:center;color:var(--mut)}}
.cf-empty-inline{{padding:14px 16px;text-align:left;margin-bottom:16px;font-size:11px;color:var(--mut)}}
.cf-empty-inline strong{{color:var(--txt)}}
.cf-empty-icon{{font-size:32px;margin-bottom:10px}}
.cf-empty-title{{font-family:'Syne',sans-serif;font-size:15px;font-weight:700;color:var(--txt);margin-bottom:6px}}
.cf-empty-msg{{font-size:11px;line-height:1.6;max-width:560px;margin:0 auto}}
.cf-empty code{{background:var(--bg);padding:1px 5px;border-radius:2px;font-size:10px;color:var(--txt)}}

/* Annual Summary cards (3-col grid) */
.cf-summary-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}}
.cf-summary-card{{background:var(--surf);border:.5px solid var(--bdr);border-radius:6px;padding:16px 18px}}
.cf-card-mid{{border-top:2px solid var(--zone)}}
.cf-card-title{{font-family:'Syne',sans-serif;font-size:13px;font-weight:700;color:var(--txt);margin-bottom:2px}}
.cf-card-sub{{font-size:9px;color:var(--mut);margin-bottom:14px;line-height:1.4}}
.cf-card-row{{display:flex;justify-content:space-between;font-size:11px;padding:5px 0;color:var(--mut)}}
.cf-card-row strong, .cf-card-row span[data-php]{{color:var(--txt);font-family:'DM Mono',monospace;font-weight:500}}
.cf-card-divider{{height:1px;background:var(--bdr);margin:10px 0 6px}}
.cf-card-headline{{font-family:'Syne',sans-serif;font-size:22px;font-weight:700;color:var(--txt);text-align:right;letter-spacing:-.01em}}
.cf-card-mid .cf-card-headline{{color:var(--zone)}}

/* Monthly chart */
.cf-chart-wrap{{position:relative;width:100%;height:280px;background:var(--surf);border:.5px solid var(--bdr);border-radius:6px;padding:14px}}
.cf-legend{{display:flex;gap:16px;flex-wrap:wrap;margin-top:8px;font-size:9px;color:var(--mut)}}
.cf-li{{display:flex;align-items:center;gap:5px}}
.cf-ln{{width:14px;height:2px;flex-shrink:0}}

/* Drilldown table */
.cf-subhd{{font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--mut);margin:0 0 8px;padding:6px 10px;background:var(--surf2);border-radius:3px;font-weight:600}}
.cf-subhd-inc{{color:#15803d;background:#f0fdf4}}
.cf-subhd-exp{{color:#b91c1c;background:#fef2f2}}
.cf-table{{width:100%;border-collapse:collapse;font-size:11px;background:var(--surf);border:.5px solid var(--bdr);border-radius:6px;overflow:hidden;margin-bottom:8px}}
.cf-table th{{font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:var(--mut);padding:7px 10px;text-align:left;border-bottom:1px solid var(--bdr);background:var(--surf2);white-space:nowrap}}
.cf-table th.cf-num{{text-align:right}}
.cf-table td{{padding:8px 10px;border-bottom:.5px solid var(--bdr);vertical-align:middle}}
.cf-table tr:last-child td{{border-bottom:none}}
.cf-num{{text-align:right;font-variant-numeric:tabular-nums}}
.cf-cat-row{{cursor:pointer;background:var(--surf)}}
.cf-cat-row:hover{{background:var(--dim)}}
.cf-cat-row td{{padding:9px 10px}}
.cf-toggle{{color:var(--mut);font-family:monospace;display:inline-block;width:12px;font-size:10px;transition:transform .15s}}
.cf-toggle.open{{transform:rotate(90deg)}}
.cf-item-row{{background:#fafaf7}}
.cf-item-row td:first-child{{padding-left:30px;font-size:10.5px;color:var(--mut)}}
.cf-item-row td.cf-num{{color:var(--txt)}}
.cf-hidden{{display:none}}
.cf-freq{{font-size:9px;color:var(--mut);font-style:italic;margin-left:4px}}

/* Projection tab */
.proj-chips{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px}}
.proj-chip{{background:var(--surf);border:.5px solid var(--bdr);border-radius:5px;padding:10px 14px;text-align:center;min-width:100px}}
.proj-chip span{{display:block;font-family:'Syne',sans-serif;font-size:18px;font-weight:700;color:var(--txt);line-height:1.1}}
.proj-chip small{{font-size:9px;color:var(--mut);letter-spacing:.08em;text-transform:uppercase}}
.proj-chip-nw{{border-color:var(--zone);background:linear-gradient(180deg, var(--surf) 0%, var(--surf2) 100%)}}
.proj-chip-nw span{{color:var(--zone)}}
.proj-row td{{padding:7px 10px}}
.proj-cashout{{color:var(--red);font-weight:600}}

@media(max-width:780px){{
  .cf-summary-grid{{grid-template-columns:1fr;gap:8px}}
  .proj-chips{{justify-content:center}}
  .cf-table th:nth-child(3),.cf-table td:nth-child(3){{display:none}}
  .cf-table th:nth-child(5),.cf-table td:nth-child(5){{display:none}}
}}

/* ═══════════════════════════════════════════════════════════════════════════
   MAJOR CASHOUTS TAB — Phase 4
   ═══════════════════════════════════════════════════════════════════════════ */

/* Toolbar with scenario toggle + edit button */
.co-toolbar{{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:18px;padding:12px 16px;background:var(--surf);border:.5px solid var(--bdr);border-radius:6px}}
.co-sc-toggle{{display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
.co-sc-label{{font-size:9px;letter-spacing:.12em;color:var(--mut);margin-right:6px}}
.co-sc-btn{{background:transparent;border:1px solid var(--bdr);padding:6px 12px;font-family:'DM Mono',monospace;font-size:10.5px;font-weight:500;color:var(--mut);cursor:pointer;border-radius:4px;transition:all .15s}}
.co-sc-btn:hover{{color:var(--txt);border-color:var(--bdr2)}}
.co-sc-btn.active{{background:var(--txt);color:var(--bg);border-color:var(--txt)}}

.cf-btn{{display:inline-block;padding:7px 14px;background:var(--surf2);border:1px solid var(--bdr);border-radius:4px;font-family:'DM Mono',monospace;font-size:10.5px;color:var(--txt);text-decoration:none;cursor:pointer;transition:all .15s;white-space:nowrap}}
.cf-btn:hover{{background:var(--txt);color:var(--bg);border-color:var(--txt)}}
.cf-btn-primary{{background:var(--txt);color:var(--bg);border-color:var(--txt)}}
.cf-btn-primary:hover{{opacity:.85}}

/* Headline + summary */
.co-headline-row{{margin-bottom:18px}}
.co-headline-card{{padding:18px 22px;background:linear-gradient(180deg, var(--surf) 0%, var(--surf2) 100%);border:1px solid var(--zone);border-radius:6px}}
.co-headline-label{{font-size:9px;letter-spacing:.12em;color:var(--mut);margin-bottom:8px}}
.co-headline-value{{font-family:'Syne',sans-serif;font-size:30px;font-weight:700;color:var(--zone);letter-spacing:-.01em;margin-bottom:4px}}
.co-headline-sub{{font-size:10px;color:var(--mut)}}

.co-subhd{{font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:var(--mut);margin:14px 0 8px;font-weight:600}}

/* Category grid */
.co-cat-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px}}
.co-cat-card{{background:var(--surf);border:.5px solid var(--bdr);border-radius:5px;padding:10px 12px}}
.co-cat-name{{font-size:9px;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);margin-bottom:3px}}
.co-cat-amt{{font-family:'Syne',sans-serif;font-size:17px;font-weight:700;color:var(--txt);line-height:1.1;margin-bottom:2px}}
.co-cat-pct{{font-size:9px;color:var(--mut)}}

/* Decade grid */
.co-dec-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:6px}}
.co-dec-card{{background:var(--surf2);border:.5px solid var(--bdr);border-radius:4px;padding:8px 10px;text-align:center}}
.co-dec-name{{font-size:9px;letter-spacing:.08em;color:var(--mut);margin-bottom:2px}}
.co-dec-amt{{font-family:'DM Mono',monospace;font-size:13px;font-weight:600;color:var(--txt)}}

/* Tags */
.co-cat-tag{{font-size:9px;padding:2px 7px;background:var(--surf2);border-radius:10px;color:var(--mut);letter-spacing:.04em}}
.co-tag{{font-size:9px;padding:2px 7px;border-radius:10px;letter-spacing:.04em}}
.co-tag-base{{background:#fef3c7;color:#92400e}}
.co-tag-scenario{{background:#dbeafe;color:#1e40af}}
.co-note{{font-size:10px;color:var(--mut);max-width:280px}}

@media(max-width:780px){{
  .co-toolbar{{flex-direction:column;align-items:stretch}}
  .co-sc-toggle{{justify-content:center}}
  .co-cat-grid{{grid-template-columns:1fr 1fr}}
}}

@media(max-width:780px){{
  .bs-headline{{flex-direction:column;gap:6px}}
  .bs-headline-op{{display:none}}
  .bs-table th:nth-child(3),.bs-table td:nth-child(3){{display:none}}
  .bs-note-col{{display:none}}
  .bs-table th:nth-child(4),.bs-table td:nth-child(4){{display:none}}
}}

@media(max-width:700px){{
  .cards{{grid-template-columns:1fr}}
  .tab,.yc-tab{{padding:6px 10px;font-size:9px}}
  /* On mobile, hide Current $, Target $, Live Price, Shares — keep Ticker, Target %, Gap $, Allocation $, Zone Action */
  .alloc-table th:nth-child(3),.alloc-table td:nth-child(3),
  .alloc-table th:nth-child(4),.alloc-table td:nth-child(4),
  .alloc-table th:nth-child(6),.alloc-table td:nth-child(6),
  .alloc-table th:nth-child(8),.alloc-table td:nth-child(8){{display:none}}
  .main-tab{{padding:9px 14px;font-size:10.5px}}
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

  <!-- ─────────────────────────────────────────────────────────────── -->
  <!-- TAB NAVIGATION — Investment Dashboard | Total Holdings          -->
  <!-- ─────────────────────────────────────────────────────────────── -->
  <div class="main-tabs">
    <button class="main-tab active" data-tab="investment" onclick="switchMainTab('investment')">Investment Dashboard</button>
    <button class="main-tab" data-tab="holdings" onclick="switchMainTab('holdings')">Total Holdings</button>
    <button class="main-tab" data-tab="cashflow" onclick="switchMainTab('cashflow')">Cashflow</button>
    <button class="main-tab" data-tab="cashouts" onclick="switchMainTab('cashouts')">Major Cashouts</button>
    <button class="main-tab" data-tab="projection" onclick="switchMainTab('projection')">Projection</button>
  </div>

  <!-- ═══════════════════════════════════════════════════════════════ -->
  <!-- TAB 1: INVESTMENT DASHBOARD (existing content)                  -->
  <!-- ═══════════════════════════════════════════════════════════════ -->
  <div id="tab-investment" class="tab-content active">

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

  </div> <!-- end #tab-investment -->

  <!-- ═══════════════════════════════════════════════════════════════ -->
  <!-- TAB 2: TOTAL HOLDINGS (Phase 1: Balance Sheet)                  -->
  <!-- ═══════════════════════════════════════════════════════════════ -->
  <div id="tab-holdings" class="tab-content">

    <!-- Currency toggle + FX badge -->
    <div class="bs-header-row">
      <div class="bs-fx-info">
        <span class="bs-fx-label">FX Rate:</span>
        <span class="bs-fx-rate">₱{USDPHP_RATE:.4f} / $1</span>
        <span class="bs-fx-source">{'Google Finance (Sheet)' if FX_SOURCE == 'google_sheets' else 'Twelve Data live' if FX_SOURCE == 'twelve_data' else 'fallback'}</span>
      </div>
      <div class="bs-currency-toggle">
        <button class="bs-ccy-btn active" data-ccy="USD" onclick="switchCurrency('USD')">USD ($)</button>
        <button class="bs-ccy-btn" data-ccy="PHP" onclick="switchCurrency('PHP')">PHP (₱)</button>
      </div>
    </div>

    <!-- Net Worth Headline -->
    <div class="bs-headline">
      <div class="bs-headline-card bs-assets">
        <div class="bs-headline-label">TOTAL ASSETS</div>
        <div class="bs-headline-value" data-usd="{balance_sheet['totals']['assets_usd']:.2f}">${balance_sheet['totals']['assets_usd']:,.0f}</div>
      </div>
      <div class="bs-headline-op">−</div>
      <div class="bs-headline-card bs-liab">
        <div class="bs-headline-label">TOTAL LIABILITIES</div>
        <div class="bs-headline-value" data-usd="{balance_sheet['totals']['liabilities_usd']:.2f}">${balance_sheet['totals']['liabilities_usd']:,.0f}</div>
      </div>
      <div class="bs-headline-op">=</div>
      <div class="bs-headline-card bs-networth">
        <div class="bs-headline-label">NET WORTH</div>
        <div class="bs-headline-value" data-usd="{balance_sheet['totals']['net_worth_usd']:.2f}">${balance_sheet['totals']['net_worth_usd']:,.0f}</div>
      </div>
    </div>

    <!-- Asset Sections -->
    <div class="bs-section">
      <div class="section-hd">
        <span>ASSETS · BY CATEGORY</span>
        <span style="font-size:9px;color:var(--mut)">Auto-synced from holdings.json + cashflow.json</span>
      </div>
      <table class="bs-table">
        <thead>
          <tr>
            <th>Category / Line Item</th>
            <th class="bs-num">Value</th>
            <th class="bs-num">% of Assets</th>
            <th class="bs-note-col">Notes</th>
          </tr>
        </thead>
        <tbody id="bsAssetsBody">{bs_assets_html}
        </tbody>
        <tfoot>
          <tr class="bs-grand-total">
            <td><strong>TOTAL ASSETS</strong></td>
            <td class="bs-num"><strong data-usd="{balance_sheet['totals']['assets_usd']:.2f}">${balance_sheet['totals']['assets_usd']:,.0f}</strong></td>
            <td class="bs-num"><strong>100.0%</strong></td>
            <td></td>
          </tr>
        </tfoot>
      </table>
    </div>

    <!-- Liabilities Section -->
    <div class="bs-section">
      <div class="section-hd">
        <span>LIABILITIES</span>
        <span style="font-size:9px;color:var(--mut)">Credit card balances + other debts</span>
      </div>
      <table class="bs-table">
        <thead>
          <tr>
            <th>Line Item</th>
            <th class="bs-num">Balance Owed</th>
            <th class="bs-num">Credit Limit</th>
            <th class="bs-note-col">Notes</th>
          </tr>
        </thead>
        <tbody id="bsLiabBody">{bs_liab_html}
        </tbody>
        <tfoot>
          <tr class="bs-grand-total">
            <td><strong>TOTAL LIABILITIES</strong></td>
            <td class="bs-num"><strong data-usd="{balance_sheet['totals']['liabilities_usd']:.2f}">${balance_sheet['totals']['liabilities_usd']:,.0f}</strong></td>
            <td class="bs-num">—</td>
            <td></td>
          </tr>
        </tfoot>
      </table>
    </div>

    <div class="bs-footnote">
      Balance Sheet auto-syncs from Google Sheets <code>Balance_Sheet</code> tab + <code>holdings.json</code> × live prices.
      Cashflow and Projection tabs use <code>Cashflow</code>, <code>Major_Cashouts</code>, and <code>Settings</code> tabs.
      PHP values converted at FX rate from Settings tab (GOOGLEFINANCE) or Twelve Data fallback.
    </div>

  </div> <!-- end #tab-holdings -->

  <!-- ═══════════════════════════════════════════════════════════════ -->
  <!-- TAB 3: CASHFLOW (Phase 2)                                       -->
  <!-- ═══════════════════════════════════════════════════════════════ -->
  <div id="tab-cashflow" class="tab-content">{cashflow_tab_html}
  </div> <!-- end #tab-cashflow -->

  <!-- ═══════════════════════════════════════════════════════════════ -->
  <!-- TAB 4: MAJOR CASHOUTS (Phase 4)                                 -->
  <!-- ═══════════════════════════════════════════════════════════════ -->
  <div id="tab-cashouts" class="tab-content">{cashouts_tab_html}
  </div> <!-- end #tab-cashouts -->

  <!-- ═══════════════════════════════════════════════════════════════ -->
  <!-- TAB 5: PROJECTION (Phase 3)                                     -->
  <!-- ═══════════════════════════════════════════════════════════════ -->
  <div id="tab-projection" class="tab-content">{projection_tab_html}
  </div> <!-- end #tab-projection -->

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
const FX_USDPHP = {USDPHP_RATE};

let curTab='7D', curYCTab='5Y', useLog=false;
let chartInst=null, ycInst=null;
let curCurrency = 'USD';   // toggle state for Total Holdings tab

// ── MAIN TAB SWITCHING — Investment Dashboard | Total Holdings | Cashflow | Projection ──
function switchMainTab(tabId){{
  document.querySelectorAll('.main-tab').forEach(b => {{
    b.classList.toggle('active', b.dataset.tab === tabId);
  }});
  document.querySelectorAll('.tab-content').forEach(div => {{
    div.classList.toggle('active', div.id === 'tab-' + tabId);
  }});
  // Persist tab preference
  try {{ localStorage.setItem('dashboard_tab', tabId); }} catch(e) {{}}
  // Charts need a redraw when their container becomes visible
  if(tabId === 'investment' && chartInst){{
    setTimeout(() => {{ try{{ chartInst.update(); ycInst && ycInst.update(); }} catch(e){{}} }}, 50);
  }}
  if(tabId === 'cashflow'){{
    setTimeout(() => {{ renderCashflowChart(); }}, 50);
  }}
  if(tabId === 'cashouts'){{
    setTimeout(() => {{ renderCashoutsImpactChart(); }}, 50);
  }}
  if(tabId === 'projection'){{
    setTimeout(() => {{ renderProjectionCharts(); }}, 50);
  }}
}}

// Restore last selected tab from localStorage on page load
function restoreTab(){{
  try {{
    const saved = localStorage.getItem('dashboard_tab');
    if(saved && saved !== 'investment') switchMainTab(saved);
  }} catch(e) {{}}
}}

// ── CURRENCY TOGGLE — USD ↔ PHP for Total Holdings tab ──────────────────────
function fmtCurrency(amountUsd, ccy){{
  if(ccy === 'PHP'){{
    const php = amountUsd * FX_USDPHP;
    // Round to nearest peso for display
    return '₱' + Math.round(php).toLocaleString();
  }}
  return '$' + Math.round(amountUsd).toLocaleString();
}}

function fmtPhpUsd(phpVal, ccy){{
  // Used by Cashflow/Projection tabs where values are PHP-native
  if(ccy === 'PHP'){{
    // Smart-format: M for millions, K for thousands
    if(Math.abs(phpVal) >= 1e6) return '₱' + (phpVal/1e6).toFixed(1) + 'M';
    if(Math.abs(phpVal) >= 1e4) return '₱' + Math.round(phpVal).toLocaleString();
    return '₱' + Math.round(phpVal).toLocaleString();
  }}
  const usd = phpVal / FX_USDPHP;
  if(Math.abs(usd) >= 1e6) return '$' + (usd/1e6).toFixed(2) + 'M';
  if(Math.abs(usd) >= 1e3) return '$' + Math.round(usd).toLocaleString();
  return '$' + usd.toFixed(2);
}}

function switchCurrency(ccy){{
  curCurrency = ccy;
  // Update button states
  document.querySelectorAll('.bs-ccy-btn').forEach(b => {{
    b.classList.toggle('active', b.dataset.ccy === ccy);
  }});
  // Re-render USD-native elements (Balance Sheet tab)
  document.querySelectorAll('[data-usd]:not([data-php])').forEach(el => {{
    const usd = parseFloat(el.getAttribute('data-usd'));
    if(!isNaN(usd)) el.textContent = fmtCurrency(usd, ccy);
  }});
  // Re-render PHP-native elements (Cashflow/Projection tabs) — uses both data-php
  // (canonical) and data-usd (computed) attributes for accurate conversion
  document.querySelectorAll('[data-php]').forEach(el => {{
    const php = parseFloat(el.getAttribute('data-php'));
    if(!isNaN(php)) el.textContent = fmtPhpUsd(php, ccy);
  }});
  // Re-render charts to reflect new currency (cashflow + projection + cashouts)
  if(typeof renderCashflowChart === 'function') renderCashflowChart();
  if(typeof renderProjectionCharts === 'function') renderProjectionCharts();
  if(typeof renderCashoutsImpactChart === 'function') renderCashoutsImpactChart();
  // Persist preference
  try {{ localStorage.setItem('dashboard_ccy', ccy); }} catch(e) {{}}
}}

// Restore last currency preference
function restoreCurrency(){{
  try {{
    const saved = localStorage.getItem('dashboard_ccy');
    if(saved === 'PHP') switchCurrency('PHP');
  }} catch(e) {{}}
}}

// ── CATEGORY DRILLDOWN TOGGLE ───────────────────────────────────────────────
function toggleCategory(catId){{
  const toggle = document.getElementById(catId + '-toggle');
  const rows = document.querySelectorAll(`tr[data-parent="${{catId}}"]`);
  const isOpen = toggle && toggle.classList.contains('open');
  rows.forEach(r => r.classList.toggle('cf-hidden', isOpen));
  if(toggle) toggle.classList.toggle('open', !isOpen);
}}

// ── CASHFLOW: MONTHLY CHART ─────────────────────────────────────────────────
let cfMonthlyInst = null;
function renderCashflowChart(){{
  if(!DATA.cashflow_summary || !DATA.cashflow_summary.has_data) return;
  const monthly = DATA.cashflow_summary.monthly;
  const canvas = document.getElementById('cfMonthlyChart');
  if(!canvas) return;
  if(cfMonthlyInst){{ cfMonthlyInst.destroy(); cfMonthlyInst = null; }}

  const ccy = curCurrency;
  const conv = v => ccy === 'PHP' ? v : v / FX_USDPHP;
  const symbol = ccy === 'PHP' ? '₱' : '$';

  const labels = monthly.map(m => m.month);
  const incomeData = monthly.map(m => conv(m.income_php));
  const expenseData = monthly.map(m => conv(m.expense_php));
  const netData = monthly.map(m => conv(m.net_php));

  cfMonthlyInst = new Chart(canvas.getContext('2d'), {{
    type: 'bar',
    data: {{
      labels: labels,
      datasets: [
        {{label: 'Income',   data: incomeData,  backgroundColor: 'rgba(21,128,61,.75)',  borderColor: '#15803d', borderWidth: 0, order: 2}},
        {{label: 'Expenses', data: expenseData, backgroundColor: 'rgba(185,28,28,.75)',  borderColor: '#b91c1c', borderWidth: 0, order: 2}},
        {{label: 'Net',      data: netData,     type: 'line', borderColor: '#1d4ed8', borderWidth: 2.5, pointRadius: 3, pointBackgroundColor: '#1d4ed8', tension: .1, order: 1, backgroundColor: 'transparent'}}
      ]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false, animation: {{duration: 250}},
      interaction: {{mode: 'index', intersect: false}},
      plugins: {{
        legend: {{display: false}},
        tooltip: {{
          backgroundColor: 'rgba(255,255,255,.98)', borderColor: '#d1d5db', borderWidth: .5,
          titleColor: '#111827', bodyColor: '#374151',
          titleFont: {{size: 10, family: 'monospace'}}, bodyFont: {{size: 10, family: 'monospace'}},
          callbacks: {{
            label(i){{
              const v = i.raw;
              if(Math.abs(v) >= 1e6) return ` ${{i.dataset.label}}: ${{symbol}}${{(v/1e6).toFixed(2)}}M`;
              if(Math.abs(v) >= 1e3) return ` ${{i.dataset.label}}: ${{symbol}}${{Math.round(v).toLocaleString()}}`;
              return ` ${{i.dataset.label}}: ${{symbol}}${{Math.round(v).toLocaleString()}}`;
            }}
          }}
        }}
      }},
      scales: {{
        x: {{ticks: {{color: '#9ca3af', font: {{size: 9, family: 'monospace'}}}}, grid: {{color: '#f3f4f6'}}}},
        y: {{ticks: {{color: '#9ca3af', font: {{size: 9, family: 'monospace'}}, callback: v => {{
              if(Math.abs(v) >= 1e6) return symbol + (v/1e6).toFixed(1) + 'M';
              if(Math.abs(v) >= 1e3) return symbol + Math.round(v/1e3) + 'K';
              return symbol + v;
            }}}}, grid: {{color: '#f3f4f6'}}}}
      }}
    }}
  }});
}}

// ── PROJECTION: TIMELINE + 15-YR NET WORTH CHARTS ───────────────────────────
let projTimelineInst = null;
let projNWInst = null;
function renderProjectionCharts(){{
  if(!DATA.projection) return;
  // Honor active scenario from Major Cashouts tab toggle (or default)
  const activeScenario = curScenario || DATA.projection.default_scenario;
  const proj = (DATA.projection.projections_by_scenario && activeScenario
                && DATA.projection.projections_by_scenario[activeScenario])
               || DATA.projection.projection;
  // Filter cashouts to active scenario (+ base)
  const allCashouts = DATA.projection.cashouts || [];
  const cashouts = allCashouts.filter(co =>
    co.scenario === 'base' || co.scenario === activeScenario
  );
  const a = DATA.projection.assumptions;
  const ccy = curCurrency;
  const conv = v => ccy === 'PHP' ? v : v / FX_USDPHP;
  const symbol = ccy === 'PHP' ? '₱' : '$';
  const fmtBig = v => {{
    if(Math.abs(v) >= 1e6) return symbol + (v/1e6).toFixed(1) + 'M';
    if(Math.abs(v) >= 1e3) return symbol + Math.round(v/1e3) + 'K';
    return symbol + Math.round(v);
  }};

  // 1. Timeline chart — bubbles sized by amount
  const tcanvas = document.getElementById('projTimelineChart');
  if(tcanvas){{
    if(projTimelineInst){{ projTimelineInst.destroy(); projTimelineInst = null; }}
    const bubbleData = cashouts.map(co => ({{
      x: co.year,
      y: conv(co.amount_usd * FX_USDPHP),
      r: Math.max(5, Math.min(35, Math.sqrt(co.amount_usd) / 8)),
      item: co.item,
      category: co.category,
    }}));
    projTimelineInst = new Chart(tcanvas.getContext('2d'), {{
      type: 'bubble',
      data: {{datasets: [{{label: 'Cashouts', data: bubbleData, backgroundColor: 'rgba(124,58,237,.55)', borderColor: '#7c3aed', borderWidth: 1.5}}]}},
      options: {{
        responsive: true, maintainAspectRatio: false, animation: {{duration: 250}},
        plugins: {{
          legend: {{display: false}},
          tooltip: {{
            backgroundColor: 'rgba(255,255,255,.98)', borderColor: '#d1d5db', borderWidth: .5,
            titleColor: '#111827', bodyColor: '#374151',
            titleFont: {{size: 10, family: 'monospace'}}, bodyFont: {{size: 10, family: 'monospace'}},
            callbacks: {{
              title(i){{ return i[0].raw.item + ' (' + i[0].raw.year + ')'; }},
              label(i){{ return ' ' + fmtBig(i.raw.y) + ' · ' + i.raw.category; }},
            }}
          }}
        }},
        scales: {{
          x: {{type: 'linear', ticks: {{color: '#9ca3af', font: {{size: 9, family: 'monospace'}}, stepSize: 1, callback: v => v}}, grid: {{color: '#f3f4f6'}}, min: proj[0].year - 0.5, max: proj[proj.length-1].year + 0.5}},
          y: {{ticks: {{color: '#9ca3af', font: {{size: 9, family: 'monospace'}}, callback: fmtBig}}, grid: {{color: '#f3f4f6'}}}}
        }}
      }}
    }});
  }}

  // 2. 15-year net worth projection
  const ncanvas = document.getElementById('projNWChart');
  if(ncanvas){{
    if(projNWInst){{ projNWInst.destroy(); projNWInst = null; }}

    // Compute "no cashouts" reference line
    const startingNw = a.starting_nw_php;
    const incReturn = a.investment_return_pct / 100;
    const salaryGrowth = a.salary_growth_pct / 100;
    const expenseInfl = a.expense_inflation_pct / 100;
    const startIncome = DATA.cashflow_summary?.summary?.income_php || 0;
    const startExpense = DATA.cashflow_summary?.summary?.expense_php || 0;

    const noCashoutSeries = [];
    let nw_nc = startingNw;
    for(let i = 0; i < proj.length; i++){{
      const inc = startIncome * Math.pow(1 + salaryGrowth, i);
      const exp = startExpense * Math.pow(1 + expenseInfl, i);
      const gains = nw_nc * incReturn;
      nw_nc = nw_nc + (inc - exp) + gains;
      noCashoutSeries.push({{x: proj[i].year, y: conv(nw_nc)}});
    }}

    const nwSeries = proj.map(p => ({{x: p.year, y: conv(p.net_worth_php)}}));

    projNWInst = new Chart(ncanvas.getContext('2d'), {{
      type: 'line',
      data: {{
        datasets: [
          {{label: 'Net Worth (with cashouts)', data: nwSeries, borderColor: '#7c3aed', backgroundColor: 'rgba(124,58,237,.08)', borderWidth: 2.5, pointRadius: 3, tension: .15, fill: true}},
          {{label: 'Without cashouts', data: noCashoutSeries, borderColor: 'rgba(124,58,237,.45)', backgroundColor: 'transparent', borderWidth: 1.5, pointRadius: 0, borderDash: [5,4], tension: .15}}
        ]
      }},
      options: {{
        responsive: true, maintainAspectRatio: false, animation: {{duration: 250}},
        interaction: {{mode: 'index', intersect: false}},
        plugins: {{
          legend: {{display: false}},
          tooltip: {{
            backgroundColor: 'rgba(255,255,255,.98)', borderColor: '#d1d5db', borderWidth: .5,
            titleColor: '#111827', bodyColor: '#374151',
            titleFont: {{size: 10, family: 'monospace'}}, bodyFont: {{size: 10, family: 'monospace'}},
            callbacks: {{
              title(i){{ return 'Year ' + i[0].raw.x; }},
              label(i){{ return ' ' + i.dataset.label + ': ' + fmtBig(i.raw.y); }},
            }}
          }}
        }},
        scales: {{
          x: {{type: 'linear', ticks: {{color: '#9ca3af', font: {{size: 9, family: 'monospace'}}, stepSize: 1, callback: v => v}}, grid: {{color: '#f3f4f6'}}}},
          y: {{ticks: {{color: '#9ca3af', font: {{size: 9, family: 'monospace'}}, callback: fmtBig}}, grid: {{color: '#f3f4f6'}}, title: {{display: true, text: 'Net Worth (' + symbol + ')', color: '#9ca3af', font: {{size: 9, family: 'monospace'}}}}}}
        }}
      }}
    }});
  }}
}}

// ── MAJOR CASHOUTS: SCENARIO TOGGLE + IMPACT CHART ──────────────────────────
let curScenario = null;   // tracks which scenario is currently active
let coImpactInst = null;

const SCENARIO_COLORS = {{
  us_private:      '#b91c1c',   // red — most expensive
  us_public:       '#d97706',   // amber — middle
  ph_with_masters: '#15803d',   // green — cheapest
  __base_only__:   '#6b7280',   // gray — reference line, no education
}};

function switchScenario(sc){{
  curScenario = sc;
  // Update button states
  document.querySelectorAll('.co-sc-btn').forEach(b => {{
    b.classList.toggle('active', b.dataset.scenario === sc);
  }});
  // Show/hide scenario-specific content blocks
  document.querySelectorAll('.co-sc-content').forEach(el => {{
    el.style.display = (el.dataset.scenario === sc) ? 'block' : 'none';
  }});
  // Re-render currency on newly visible elements
  document.querySelectorAll('.co-sc-content [data-php]').forEach(el => {{
    const php = parseFloat(el.getAttribute('data-php'));
    if(!isNaN(php)) el.textContent = fmtPhpUsd(php, curCurrency);
  }});
  // Persist
  try {{ localStorage.setItem('dashboard_scenario', sc); }} catch(e) {{}}
  // Re-render impact chart with emphasis on this scenario
  renderCashoutsImpactChart();
  // Also re-render Projection tab charts if user later switches to that tab
  if(typeof renderProjectionCharts === 'function'){{
    // Only re-render if projection tab is currently visible (avoid wasted work)
    const projTab = document.getElementById('tab-projection');
    if(projTab && projTab.classList.contains('active')) renderProjectionCharts();
  }}
}}

function renderCashoutsImpactChart(){{
  if(!DATA.projection) return;
  const pj = DATA.projection;
  const scenarios = pj.scenarios || [];
  if(scenarios.length === 0) return;

  const canvas = document.getElementById('coImpactChart');
  if(!canvas) return;
  if(coImpactInst){{ coImpactInst.destroy(); coImpactInst = null; }}

  const ccy = curCurrency;
  const conv = v => ccy === 'PHP' ? v : v / FX_USDPHP;
  const symbol = ccy === 'PHP' ? '₱' : '$';
  const fmtBig = v => {{
    if(Math.abs(v) >= 1e6) return symbol + (v/1e6).toFixed(1) + 'M';
    if(Math.abs(v) >= 1e3) return symbol + Math.round(v/1e3) + 'K';
    return symbol + Math.round(v);
  }};

  const activeScenario = curScenario || pj.default_scenario;
  const datasets = [];
  const labels = pj.scenario_labels || {{}};

  // One line per toggle-able scenario, plus a "no education" reference
  scenarios.forEach(sc => {{
    const series = pj.projections_by_scenario[sc];
    if(!series) return;
    const isActive = sc === activeScenario;
    const color = SCENARIO_COLORS[sc] || '#6b7280';
    datasets.push({{
      label: labels[sc] || sc,
      data: series.map(p => ({{x: p.year, y: conv(p.net_worth_php)}})),
      borderColor: color,
      backgroundColor: isActive ? color + '22' : 'transparent',
      borderWidth: isActive ? 2.5 : 1.5,
      pointRadius: isActive ? 3 : 0,
      tension: .15,
      fill: isActive,
      order: isActive ? 1 : 2,
      borderDash: isActive ? [] : [],
    }});
  }});

  // Add "no education" reference line (gray dashed)
  const baseOnly = pj.projections_by_scenario['__base_only__'];
  if(baseOnly){{
    datasets.push({{
      label: 'Base only (no education)',
      data: baseOnly.map(p => ({{x: p.year, y: conv(p.net_worth_php)}})),
      borderColor: 'rgba(107,114,128,.6)',
      backgroundColor: 'transparent',
      borderWidth: 1.2,
      pointRadius: 0,
      borderDash: [4, 4],
      tension: .15,
      order: 3,
    }});
  }}

  coImpactInst = new Chart(canvas.getContext('2d'), {{
    type: 'line',
    data: {{datasets}},
    options: {{
      responsive: true, maintainAspectRatio: false, animation: {{duration: 250}},
      interaction: {{mode: 'index', intersect: false}},
      plugins: {{
        legend: {{display: false}},
        tooltip: {{
          backgroundColor: 'rgba(255,255,255,.98)', borderColor: '#d1d5db', borderWidth: .5,
          titleColor: '#111827', bodyColor: '#374151',
          titleFont: {{size: 10, family: 'monospace'}}, bodyFont: {{size: 9, family: 'monospace'}},
          callbacks: {{
            title(i){{ return 'Year ' + i[0].raw.x; }},
            label(i){{ return ' ' + i.dataset.label + ': ' + fmtBig(i.raw.y); }},
          }}
        }}
      }},
      scales: {{
        x: {{type: 'linear', ticks: {{color: '#9ca3af', font: {{size: 9, family: 'monospace'}}, stepSize: 2, callback: v => v}}, grid: {{color: '#f3f4f6'}}}},
        y: {{ticks: {{color: '#9ca3af', font: {{size: 9, family: 'monospace'}}, callback: fmtBig}}, grid: {{color: '#f3f4f6'}}, title: {{display: true, text: 'Net Worth (' + symbol + ')', color: '#9ca3af', font: {{size: 9, family: 'monospace'}}}}}}
      }}
    }}
  }});

  // Custom legend (mirrors scenario colors + active emphasis)
  const legendEl = document.getElementById('coImpactLegend');
  if(legendEl){{
    legendEl.innerHTML = scenarios.map(sc => {{
      const color = SCENARIO_COLORS[sc] || '#6b7280';
      const isActive = sc === activeScenario;
      const weight = isActive ? '600' : '400';
      return `<div class="cf-li"><div class="cf-ln" style="background:${{color}};height:${{isActive ? 3 : 2}}px"></div><span style="font-weight:${{weight}};color:${{isActive ? 'var(--txt)' : 'var(--mut)'}}">${{labels[sc] || sc}}${{isActive ? ' · active' : ''}}</span></div>`;
    }}).join('') + `<div class="cf-li"><div class="cf-ln" style="background:rgba(107,114,128,.6);border-top:1.5px dashed rgba(107,114,128,.6)"></div>Base only (no education)</div>`;
  }}
}}

function restoreScenario(){{
  // Read scenario from localStorage if previously set + still valid
  try {{
    const saved = localStorage.getItem('dashboard_scenario');
    if(saved && DATA.projection && DATA.projection.scenarios.includes(saved)){{
      switchScenario(saved);
      return;
    }}
  }} catch(e) {{}}
  // Default: us_private if exists, else first scenario
  if(DATA.projection && DATA.projection.default_scenario){{
    switchScenario(DATA.projection.default_scenario);
  }}
}}

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
restoreTab();
restoreCurrency();
restoreScenario();
</script>
</body>
</html>"""

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n✓ Saved: {out_path}")
if not os.environ.get("CI"):
    print("  Opening in browser...")
    webbrowser.open(f"file://{out_path}")
