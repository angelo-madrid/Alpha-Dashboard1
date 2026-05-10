"""
generate_dashboard.py  —  Alpha-Dashboard1
==========================================
Generates index.html with:
  • Yield curve chart (top) — 10yr-3mo spread, zone bands, OU mean-reversion projection
  • Monday Action Table — editable cash input, zone-aware trade allocations
  • Zone × Deployment Panel
  • Fair value cards — all 9 instruments with PEG, deployment strategy, weight, allocation
  • SPYL dip trigger gauge
  • Stock price chart — 7D/30D/6M/YTD/1Y/5Y with analyst-target + CAGR projections

    pip install yfinance pandas numpy
    python generate_dashboard.py
"""

import json, webbrowser, os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf

# ── VERSION ───────────────────────────────────────────────────────────────────
SCRIPT_VERSION = "2.0.0"
SCRIPT_DATE    = "2026-05-10"

# ── HOLDINGS CONFIG ───────────────────────────────────────────────────────────
# Edit this when you execute trades. Format:
#   ACCOUNT: { TICKER: {"shares": N, "avg_cost": price}, "CASH": amount }
# Crypto held in CRYPTO account uses native unit (BTC count, not USD).
HOLDINGS = {
    "IBKR": {
        "META": {"shares": 18,   "avg_cost": 612.04},
        "MSFT": {"shares": 25,   "avg_cost": 419.18},
        "NVDA": {"shares": 50,   "avg_cost": 202.57},
        "SPYL": {"shares": 2065, "avg_cost": 17.72},   # SPYL.L
        "VOO":  {"shares": 28,   "avg_cost": 605.89},
        "CASH": 31144.43,
    },
    "CITI_401K": {
        "AMZN": {"shares": 100, "avg_cost": 163.51},
        "GOOG": {"shares": 141, "avg_cost": 122.71},   # GOOG not GOOGL in 401k
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
        "BTC": {"shares": 0.14730, "avg_cost": 0},   # native units
        "ETH": {"shares": 0.229,   "avg_cost": 0},
    },
}

# ── TARGET ALLOCATIONS (for Deployment Gaps tracker) ─────────────────────────
# Target weights as fraction of total US-investable portfolio
# Bucket 1 = AI Alpha (60% of risk capital), Bucket 2 = SPYL (20%), Bucket 3 = Asymmetric (5%)
TARGET_WEIGHTS = {
    "NVDA": 0.150,   # 25% of B1 (60%) = 15% of portfolio
    "MSFT": 0.120,   # 20% of B1
    "META": 0.120,   # 20% of B1
    "GOOGL":0.090,   # 15% of B1
    "AMZN": 0.090,   # 15% of B1
    "AAPL": 0.060,   # 10% of B1
    "SPYL": 0.200,   # Fixed 20%
    "VOO":  0.100,   # Beta anchor
    "TSLA": 0.025,   # 5% of B3 (5%) = 0.25% of portfolio (rounded up)
    "BTC":  0.012,   # Hold only
}

# ── ZONE CONFIG ───────────────────────────────────────────────────────────────
ZONE_META = {
    1: {"label":"ZONE 1 — INVERTED",  "color":"#dc2626","bg":"#fef2f2","desc":"Recession signal active"},
    2: {"label":"ZONE 2 — CAUTION",   "color":"#ea580c","bg":"#fff7ed","desc":"Post-inversion danger window"},
    3: {"label":"ZONE 3 — NEUTRAL",   "color":"#d97706","bg":"#fffbeb","desc":"Base operating zone"},
    4: {"label":"ZONE 4 — HEALTHY",   "color":"#16a34a","bg":"#f0fdf4","desc":"Expansion confirmed"},
    5: {"label":"ZONE 5 — BULL",      "color":"#15803d","bg":"#dcfce7","desc":"Strong expansion"},
}
ZONE_BOUNDARIES = [0.0, 0.5, 1.21, 2.0]   # spread thresholds in %
ZONE_DEPLOY = {
    1: {"B1":"25%","SPYL":"20%","B3":"0%", "Dry":"50%","PHP":"5%"},
    2: {"B1":"40%","SPYL":"20%","B3":"3%", "Dry":"32%","PHP":"5%"},
    3: {"B1":"60%","SPYL":"20%","B3":"5%", "Dry":"10%","PHP":"5%"},
    4: {"B1":"65%","SPYL":"20%","B3":"5%", "Dry":"5%", "PHP":"5%"},
    5: {"B1":"70%","SPYL":"20%","B3":"5%", "Dry":"0%", "PHP":"5%"},
}

def get_zone(spread):
    if spread is None: return 3
    if spread < 0:    return 1
    if spread < 0.5:  return 2
    if spread < 1.21: return 3
    if spread < 2.0:  return 4
    return 5

# ── STATIC OVERLAY CONFIG ────────────────────────────────────────────────────
# hist_pe = 5-year average forward P/E (used for valuation overlay)
# weight  = target allocation string
# b1_w    = fraction of Bucket 1 monthly deployment (0 if not in B1)
# bucket  = 1/2/3/hold
# zone_action = per-zone deployment instruction
FV_OVERLAY = {
    "NVDA": {
        "hist_pe": 50, "weight": "25% of Bucket 1", "b1_w": 0.25, "bucket": 1,
        "zone_action": {1:"Do Not Add",2:"Hold",3:"Buy Aggressively",4:"Buy Aggressively",5:"Max Deploy"},
    },
    "MSFT": {
        "hist_pe": 33, "weight": "20% of Bucket 1", "b1_w": 0.20, "bucket": 1,
        "zone_action": {1:"Do Not Add",2:"Hold",3:"Buy Aggressively",4:"Buy Aggressively",5:"Max Deploy"},
    },
    "GOOGL": {
        "hist_pe": 25, "weight": "15% of Bucket 1", "b1_w": 0.15, "bucket": 1,
        "zone_action": {1:"Do Not Add",2:"Hold",3:"Hold — At Consensus",4:"Buy Systematically",5:"Buy Systematically"},
    },
    "AAPL": {
        "hist_pe": 32, "weight": "10% of Bucket 1", "b1_w": 0.10, "bucket": 1,
        "zone_action": {1:"Do Not Add",2:"Hold",3:"Accumulate Slowly",4:"Buy Systematically",5:"Buy Aggressively"},
    },
    "META": {
        "hist_pe": 25, "weight": "20% of Bucket 1", "b1_w": 0.20, "bucket": 1,
        "zone_action": {1:"Do Not Add",2:"Hold",3:"Buy Aggressively",4:"Buy Aggressively",5:"Max Deploy"},
    },
    "AMZN": {
        "hist_pe": 22, "weight": "15% of Bucket 1", "b1_w": 0.15, "bucket": 1,
        "zone_action": {1:"Do Not Add",2:"Hold",3:"Buy Systematically",4:"Buy Systematically",5:"Buy Aggressively"},
    },
    "TSLA": {
        "hist_pe": 100, "weight": "5% of Bucket 3", "b1_w": 0.0, "bucket": 3,
        "zone_action": {1:"Do Not Add",2:"Do Not Add",3:"Do Not Add — Overvalued",4:"Small Position Only",5:"Small Position Only"},
    },
    "SPYL": {
        "hist_pe": None, "weight": "Fixed 20% of portfolio", "b1_w": 0.0, "bucket": 2,
        "spyl_target": 18.0,      # Wall St 2026 S&P consensus implied
        "spyl_target_hi": 18.50,
        "s52w_high": 17.50,
        "zone_action": {1:"DCA Buy Fixed",2:"DCA Buy Fixed",3:"DCA Buy Fixed",4:"DCA Buy Fixed",5:"DCA Buy Fixed"},
    },
    "BTC": {
        "hist_pe": None, "weight": "Hold — 1.2% portfolio", "b1_w": 0.0, "bucket": 0,
        "s2f_low": 100000, "s2f_high": 150000,
        "zone_action": {1:"Strategic Hold",2:"Strategic Hold",3:"Strategic Hold",4:"Strategic Hold",5:"Strategic Hold"},
    },
}

# ── ANALYST TARGETS (for stock price chart convergence projection) ────────────
ANALYST_TARGETS = {
    "TSLA": 280.0,   # consensus below current — will slope down
    "SPY":  None,    # no single target
    "MAG7": None,    # basket
    "BTC":  None,
}

# ── STOCK CHART CONFIG ────────────────────────────────────────────────────────
MAG7_W   = {"MSFT":0.25,"NVDA":0.25,"GOOGL":0.20,"META":0.15,"AMZN":0.10,"AAPL":0.05}
FWD_CAGR = {"SPY":0.08,"MAG7":0.11,"TSLA":0.15,"BTC":0.20}
VOLS     = {"SPY":0.16,"MAG7":0.22,"TSLA":0.65,"BTC":0.80}
# Tickers fetched for chart history. Holdings tickers (VOO, GOOG, ETH) added so we get prices for valuation.
ALL_TICKERS = list(MAG7_W.keys()) + ["SPY","TSLA","BTC-USD","VOO","GOOG","ETH-USD"]

# ── FETCH EQUITY PRICES ───────────────────────────────────────────────────────
print("Fetching equity prices...")
end   = datetime.today()
start = end - timedelta(days=365*11)

raw = yf.download(
    ALL_TICKERS,
    start=start.strftime("%Y-%m-%d"),
    end=end.strftime("%Y-%m-%d"),
    auto_adjust=True, progress=False,
)["Close"]

prices = {}
for col in raw.columns:
    s = raw[col].dropna()
    if len(s) > 20:
        if col == "BTC-USD":
            key = "BTC"
        elif col == "ETH-USD":
            key = "ETH"
        else:
            key = str(col)
        prices[key] = s
        print(f"  {key}: {len(s)} rows  ${s.iloc[0]:.2f} → ${s.iloc[-1]:.2f}")

# MAG7 basket
components = []
for t, w in MAG7_W.items():
    s = prices.get(t)
    if s is not None:
        components.append((s / s.iloc[0] * 100) * w)
basket = pd.concat(components, axis=1).sum(axis=1)
prices["MAG7"] = basket / basket.iloc[0] * 100

# ── FETCH TREASURY YIELDS ─────────────────────────────────────────────────────
print("\nFetching Treasury yields (^TNX, ^IRX)...")
try:
    yld_raw = yf.download(
        ["^TNX","^IRX"],
        start=(end - timedelta(days=365*6)).strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        auto_adjust=True, progress=False,
    )["Close"]
    tnx = yld_raw["^TNX"].dropna()
    irx = yld_raw["^IRX"].dropna()
    spread_series = (tnx - irx).dropna()
    current_spread = float(spread_series.iloc[-1])
    print(f"  10yr: {float(tnx.iloc[-1]):.3f}%  3mo: {float(irx.iloc[-1]):.3f}%  spread: {current_spread:+.3f}%")
except Exception as e:
    print(f"  Treasury fetch failed: {e}  — using fallback spread 0.64")
    spread_series = pd.Series(dtype=float)
    current_spread = 0.64

current_zone = get_zone(current_spread)
print(f"  → {ZONE_META[current_zone]['label']}")

# ── OU MEAN-REVERSION PROJECTION ──────────────────────────────────────────────
OU_MU    = 1.5    # long-run mean spread %
OU_THETA = 0.35   # mean reversion speed (calibrated)
OU_SIGMA = 0.80   # spread volatility

def proj_ou(last_spread, last_date, end_date):
    """Ornstein-Uhlenbeck mean reversion: E[X(t)] = mu + (X0-mu)*exp(-theta*t)"""
    dates = pd.bdate_range(start=last_date + timedelta(days=1), end=end_date)
    if dates.empty: return [], [], []
    t = np.arange(1, len(dates)+1) / 252
    center = OU_MU + (last_spread - OU_MU) * np.exp(-OU_THETA * t)
    var    = (OU_SIGMA**2 / (2*OU_THETA)) * (1 - np.exp(-2*OU_THETA*t))
    band   = 1.645 * np.sqrt(np.maximum(var, 0))
    fmt = lambda arr: [(str(d.date()), round(float(v), 4)) for d, v in zip(dates, arr)]
    return fmt(center), fmt(center + band), fmt(center - band)

# ── BUILD YIELD CURVE HORIZON DATA ───────────────────────────────────────────
today = pd.Timestamp.today().normalize()

YC_HORIZONS = {
    "5Y":  {"back": pd.DateOffset(years=5),   "fwd": pd.DateOffset(years=5)},
    "1Y":  {"back": pd.DateOffset(years=1),   "fwd": pd.DateOffset(years=1)},
    "6M":  {"back": pd.DateOffset(months=6),  "fwd": pd.DateOffset(months=6)},
    "30D": {"back": pd.DateOffset(days=30),   "fwd": pd.DateOffset(days=30)},
}

yc_data = {}
for hkey, hcfg in YC_HORIZONS.items():
    if spread_series.empty:
        # fallback synthetic data
        dates_fb = pd.bdate_range(end=today, periods=60)
        hist_pts = [(str(d.date()), round(current_spread + np.random.normal(0,0.1), 3)) for d in dates_fb]
        proj_c, proj_u, proj_l = proj_ou(current_spread, today.to_pydatetime(), today + hcfg["fwd"])
        yc_data[hkey] = {"hist": hist_pts, "proj": proj_c, "upper": proj_u, "lower": proj_l}
        continue

    hist_start = today - hcfg["back"]
    proj_end   = today + hcfg["fwd"]
    sliced = spread_series.loc[(spread_series.index >= hist_start) & (spread_series.index <= today)]
    if len(sliced) < 2:
        sliced = spread_series.tail(5)

    hist_pts = [(str(d.date()), round(float(v), 4)) for d, v in sliced.items()]
    last_date = sliced.index[-1].to_pydatetime()
    proj_c, proj_u, proj_l = proj_ou(current_spread, last_date, proj_end)
    yc_data[hkey] = {"hist": hist_pts, "proj": proj_c, "upper": proj_u, "lower": proj_l}

# ── STOCK PRICE CHART HORIZON DATA ───────────────────────────────────────────
def biz_range(s, e):
    return pd.bdate_range(start=s + timedelta(days=1), end=e)

def proj_cagr(lv, ld, ed, rate):
    dates = biz_range(ld, ed)
    if dates.empty: return []
    days = np.arange(1, len(dates)+1)
    return [(str(d.date()), round(float(lv * (1+rate)**(i/252)), 2))
            for d, i in zip(dates, days)]

def proj_gbm(lv, ld, ed, rate, vol, seed):
    dates = biz_range(ld, ed)
    if dates.empty: return []
    rng = np.random.default_rng(seed=seed)
    dt  = 1/252
    shocks = rng.normal((rate - 0.5*vol**2)*dt, vol*np.sqrt(dt), len(dates))
    vals   = lv * np.exp(np.cumsum(shocks))
    return [(str(d.date()), round(float(v), 2)) for d, v in zip(dates, vals)]

def proj_analyst(lv, lv_price, target_price, ld, ed):
    """Linear convergence from current normalized value toward analyst target."""
    dates = biz_range(ld, ed)
    if dates.empty or not target_price or not lv_price: return []
    n = len(dates)
    target_norm = lv * (target_price / lv_price)
    vals = np.linspace(lv, target_norm, n)
    return [(str(d.date()), round(float(v), 2)) for d, v in zip(dates, vals)]

def vol_bands(proj_pts, vol):
    upper, lower = [], []
    for i, (d, v) in enumerate(proj_pts):
        t = (i+1)/252
        f = np.exp(1.645 * vol * np.sqrt(t))
        upper.append((d, round(v*f, 2)))
        lower.append((d, round(v/f, 2)))
    return upper, lower

# New horizons: 7D/30D/6M/YTD/1Y/5Y
horizons_cfg = {
    "7D":  {"back": pd.DateOffset(days=7),   "fwd": pd.DateOffset(days=7),   "kind":"gbm"},
    "30D": {"back": pd.DateOffset(days=30),  "fwd": pd.DateOffset(days=30),  "kind":"gbm"},
    "6M":  {"back": pd.DateOffset(months=6), "fwd": pd.DateOffset(months=6), "kind":"gbm"},
    "YTD": {"back": None,                    "fwd": pd.DateOffset(months=6), "kind":"analyst"},
    "1Y":  {"back": pd.DateOffset(years=1),  "fwd": pd.DateOffset(years=1),  "kind":"analyst"},
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

    for key in ["SPY","MAG7","TSLA","BTC"]:
        raw_s = prices.get(key)
        if raw_s is None: continue

        sliced = raw_s.loc[(raw_s.index >= hist_start) & (raw_s.index <= today)].dropna()
        if len(sliced) < 2: continue

        normed   = sliced / sliced.iloc[0] * 100
        hist_pts = [(str(d.date()), round(float(v), 2)) for d, v in normed.items()]

        lv    = float(normed.iloc[-1])
        lp    = float(sliced.iloc[-1])   # last raw price
        ld    = normed.index[-1].to_pydatetime()
        rate  = FWD_CAGR[key]
        vol   = VOLS[key]
        seed  = abs(hash(f"{key}:{hkey}")) % (2**31)
        tgt   = ANALYST_TARGETS.get(key)

        if kind == "cagr":
            proj_pts = proj_cagr(lv, ld, proj_end, rate)
        elif kind == "analyst" and tgt:
            proj_pts = proj_analyst(lv, lp, tgt, ld, proj_end)
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

        if key in ("TSLA","BTC") and proj_pts:
            u, l = vol_bands(proj_pts, vol)
            entry["band_upper"] = u
            entry["band_lower"] = l

        h_data[key] = entry

    all_data[hkey] = h_data

# ── FAIR VALUE CARDS ──────────────────────────────────────────────────────────
print("\nFetching fair value data...")

FV_CONFIG = [
    ("NVDA",    "NVDA",  "NVIDIA Corporation",      "stock"),
    ("MSFT",    "MSFT",  "Microsoft Corporation",   "stock"),
    ("META",    "META",  "Meta Platforms Inc.",     "stock"),
    ("GOOGL",   "GOOGL", "Alphabet Inc.",           "stock"),
    ("AMZN",    "AMZN",  "Amazon.com Inc.",         "stock"),
    ("AAPL",    "AAPL",  "Apple Inc.",              "stock"),
    ("TSLA",    "TSLA",  "Tesla Inc.",              "stock"),
    ("SPYL.L",  "SPYL",  "SPDR S&P 500 UCITS ETF",  "etf"),
    ("BTC-USD", "BTC",   "Bitcoin",                 "crypto"),
]

def _fetch_fv(yt):
    try:
        info = yf.Ticker(yt).info or {}
    except Exception as e:
        print(f"  {yt} failed: {e}")
        info = {}
    return info

def _fmt(v, dec=2):
    if v is None: return "—"
    if abs(v) >= 1e12: return f"${v/1e12:.2f}T"
    if abs(v) >= 1e9:  return f"${v/1e9:.1f}B"
    if abs(v) >= 1e6:  return f"${v/1e6:.1f}M"
    return f"${v:,.{dec}f}" if dec > 0 else f"${int(round(v)):,}"

def _badge(rec, upside, disp):
    """Return (css_class, label) — with special handling for SPYL/BTC."""
    if disp == "SPYL":
        return "fv-dca", "DCA BUY"
    if disp == "BTC":
        return "fv-strat", "STRATEGIC HOLD"
    r = (rec or "").lower()
    if "strong" in r and "buy" in r: return "fv-buy", "Strong Buy"
    if "buy" in r:                   return "fv-buy", "Buy"
    if "hold" in r or "neutral" in r: return "fv-hold", "Hold"
    if "sell" in r:                  return "fv-cau", "Sell"
    if upside is None: return "fv-hold", "—"
    if upside >= 25:   return "fv-buy", "Strong Buy"
    if upside >= 10:   return "fv-buy", "Buy"
    if upside >= -5:   return "fv-hold", "Hold"
    return "fv-cau", "Sell"

def _deploy_color(action):
    a = action.lower()
    if "aggressively" in a or "max" in a or "dca" in a: return "dep-green"
    if "systematic" in a or "slowly" in a or "small" in a: return "dep-amber"
    if "do not" in a or "overvalued" in a: return "dep-red"
    if "hold" in a: return "dep-amber"
    return "dep-neutral"

live_prices = {}   # disp -> live price; populated by _build_card

def _build_card(yt, disp, co, cls):
    info   = _fetch_fv(yt)
    ov     = FV_OVERLAY.get(disp, {})
    price  = info.get("regularMarketPrice") or info.get("currentPrice")
    dec    = 0 if cls == "crypto" else 2

    # Save live price for holdings valuation (fall back to chart price if .info fails)
    if price:
        live_prices[disp] = float(price)
    elif disp in prices:
        live_prices[disp] = float(prices[disp].iloc[-1])

    # ── Target & upside ──────────────────────────────────────────────────
    if disp == "SPYL":
        target  = ov.get("spyl_target", 18.0)
        low_t   = info.get("fiftyTwoWeekLow",  14.80)
        high_t  = ov.get("spyl_target_hi", 18.50)
    elif disp == "BTC":
        target  = ov.get("s2f_low", 100000)
        low_t   = info.get("fiftyTwoWeekLow",  70000)
        high_t  = ov.get("s2f_high", 150000)
    else:
        target  = info.get("targetMeanPrice")
        low_t   = info.get("targetLowPrice")  or info.get("fiftyTwoWeekLow")
        high_t  = info.get("targetHighPrice") or info.get("fiftyTwoWeekHigh")

    upside   = ((target/price - 1)*100) if (price and target) else None
    fill_pct = 50.0
    if price and low_t and high_t and high_t > low_t:
        fill_pct = max(0, min(100, (price - low_t) / (high_t - low_t) * 100))

    bar_color = "#2563eb" if (upside or 0) >= 10 else "#16a34a" if (upside or 0) >= 0 else "#dc2626"
    bcls, btxt = _badge(info.get("recommendationKey"), upside, disp)

    # ── Core metrics row ─────────────────────────────────────────────────
    if cls == "crypto":
        m = [("Market Cap", _fmt(info.get("marketCap"), 0)),
             ("52w High",   _fmt(info.get("fiftyTwoWeekHigh"), 0)),
             ("52w Low",    _fmt(info.get("fiftyTwoWeekLow"),  0))]
    elif cls == "etf":
        dy = info.get("yield") or info.get("dividendYield")
        m = [("Div Yield",  f"{dy*100:.2f}%" if dy else "—"),
             ("52w High",   _fmt(info.get("fiftyTwoWeekHigh"), 2)),
             ("52w Low",    _fmt(info.get("fiftyTwoWeekLow"),  2))]
    else:
        rg = info.get("revenueGrowth")
        m = [("Fwd P/E",    f"{info['forwardPE']:.1f}x" if info.get("forwardPE") else "—"),
             ("Rev Growth", f"{rg*100:+.1f}%" if rg is not None else "—"),
             ("Analysts",   str(info.get("numberOfAnalystOpinions") or "—"))]

    # ── Valuation overlay ─────────────────────────────────────────────────
    fwd_pe   = info.get("forwardPE")
    rev_g    = info.get("revenueGrowth")
    hist_pe  = ov.get("hist_pe")
    peg      = round(fwd_pe / (rev_g * 100), 2) if (fwd_pe and rev_g and rev_g > 0) else None
    peg_txt  = f"{peg:.2f}x" if peg is not None else "—"

    pe_vs_hist_txt = ""
    if fwd_pe and hist_pe:
        diff = ((fwd_pe / hist_pe) - 1) * 100
        arrow = "↓" if diff < 0 else "↑"
        pe_vs_hist_txt = f"{arrow}{abs(diff):.0f}% vs 5yr avg"

    # ── Zone-aware deployment ─────────────────────────────────────────────
    deploy_action = ov.get("zone_action", {}).get(current_zone, "—")
    dep_cls       = _deploy_color(deploy_action)
    final_weight  = ov.get("weight", "—")

    # Monthly allocation display
    b1_w   = ov.get("b1_w", 0.0)
    bucket = ov.get("bucket", 0)
    if bucket == 1:
        # Zone 3 = 60% of monthly deployment → Bucket 1
        b1_deploy_frac = {"1":0.25,"2":0.40,"3":0.60,"4":0.65,"5":0.70}.get(str(current_zone), 0.60)
        monthly_alloc  = b1_w * b1_deploy_frac * 50000
        alloc_txt = f"~${monthly_alloc:,.0f}/mo (Zone {current_zone})"
    elif bucket == 2:
        monthly_alloc = 0.20 * 50000
        alloc_txt = f"~${monthly_alloc:,.0f}/mo fixed"
    elif bucket == 3:
        alloc_txt = "5% total portfolio"
    else:
        alloc_txt = "No new capital"

    # ── SPYL-specific dip trigger ─────────────────────────────────────────
    spyl_dip_html = ""
    if disp == "SPYL" and price:
        s52h = info.get("fiftyTwoWeekHigh") or ov.get("s52w_high", 17.50)
        drawdown_pct = (price / s52h - 1) * 100 if s52h else 0
        bar_fill = min(100, abs(drawdown_pct) / 30 * 100)
        t1_pct = 10; t2_pct = 20; t3_pct = 30
        t1_fill = t1_pct/30*100; t2_fill = t2_pct/30*100
        trigger_color = "#dc2626" if abs(drawdown_pct) >= 10 else "#d97706" if abs(drawdown_pct) >= 7 else "#16a34a"
        trigger_label = "⚠ TRANCHE 1 TRIGGERED" if abs(drawdown_pct) >= 10 else (
                        "⚡ APPROACHING T1" if abs(drawdown_pct) >= 7 else "✓ Within normal range")
        spyl_dip_html = f"""
      <div class="fv-dip">
        <div class="fv-dip-title">DIP TRIGGER MONITOR</div>
        <div class="fv-dip-vals">
          <span>Drawdown from peak: <strong style="color:{trigger_color}">{drawdown_pct:.1f}%</strong></span>
          <span style="color:{trigger_color};font-size:10px">{trigger_label}</span>
        </div>
        <div class="fv-dip-bar">
          <div class="fv-dip-fill" style="width:{bar_fill:.1f}%;background:{trigger_color}"></div>
          <div class="fv-dip-mark" style="left:{t1_fill:.1f}%" title="T1 trigger −10%"></div>
          <div class="fv-dip-mark" style="left:{t2_fill:.1f}%" title="T2 trigger −20%"></div>
        </div>
        <div class="fv-dip-labels">
          <span>0%</span><span>−10% T1</span><span>−20% T2</span><span>−30% T3</span>
        </div>
      </div>"""

    # ── BTC-specific cycle note ───────────────────────────────────────────
    btc_cycle_html = ""
    if disp == "BTC":
        s52h = info.get("fiftyTwoWeekHigh") or 125000
        cycle_dd = (price / s52h - 1) * 100 if (price and s52h) else 0
        s2f_lo = ov.get("s2f_low", 100000)
        s2f_hi = ov.get("s2f_high", 150000)
        btc_cycle_html = f"""
      <div class="fv-btcnote">
        <div class="fv-btcrow"><span>S2F Model Target</span><span>${s2f_lo:,.0f} – ${s2f_hi:,.0f}</span></div>
        <div class="fv-btcrow"><span>Cycle drawdown</span><span style="color:#dc2626">{cycle_dd:.1f}% from peak</span></div>
        <div class="fv-btcrow"><span>Strategy</span><span style="color:#d97706">Hold — never add</span></div>
      </div>"""

    upside_txt = f"{upside:+.1f}%" if upside is not None else "—"
    upside_cls = "fv-pos" if (upside or 0) >= 0 else "fv-neg"
    target_lbl = "S2F TARGET" if disp == "BTC" else ("WALL ST TARGET" if disp == "SPYL" else "TARGET")
    target_txt = _fmt(target, dec) if target else "—"
    price_txt  = _fmt(price,  dec) if price else "—"
    low_txt    = _fmt(low_t,  dec) if low_t else "—"
    high_txt   = _fmt(high_t, dec) if high_t else "—"

    print(f"  {disp}: {price_txt} → {target_txt} ({upside_txt}) | Zone{current_zone}: {deploy_action}")

    return f"""
    <div class="fv-card" data-ticker="{disp}" data-price="{price or 0}" data-bucket="{bucket}" data-b1w="{b1_w}">
      <div class="fv-head">
        <div><div class="fv-tk">{disp}</div><div class="fv-co">{co}</div></div>
        <span class="fv-bdg {bcls}">{btxt}</span>
      </div>
      <div class="fv-prow">
        <div class="fv-pblk"><div class="fv-plbl">PRICE</div><div class="fv-pval">{price_txt}</div></div>
        <div class="fv-pblk"><div class="fv-plbl">{target_lbl}</div><div class="fv-pval {upside_cls}">{target_txt}</div></div>
        <div class="fv-pblk"><div class="fv-plbl">UPSIDE</div><div class="fv-pval {upside_cls}">{upside_txt}</div></div>
      </div>
      <div class="fv-bar">
        <div class="fv-blbl"><span>Low {low_txt}</span><span>Current</span><span>High {high_txt}</span></div>
        <div class="fv-bg"><div class="fv-fl" style="width:{fill_pct:.0f}%;background:{bar_color}"></div></div>
      </div>
      <div class="fv-mtx">
        <div class="fv-mbox"><div class="fv-mlbl">{m[0][0]}</div><div class="fv-mval">{m[0][1]}</div></div>
        <div class="fv-mbox"><div class="fv-mlbl">{m[1][0]}</div><div class="fv-mval">{m[1][1]}</div></div>
        <div class="fv-mbox"><div class="fv-mlbl">{m[2][0]}</div><div class="fv-mval">{m[2][1]}</div></div>
      </div>
      <div class="fv-overlay">
        <div class="fv-orow">
          <span class="fv-olbl">Zone {current_zone} Action</span>
          <span class="fv-oval {dep_cls}">{deploy_action}</span>
        </div>
        <div class="fv-orow">
          <span class="fv-olbl">PEG Ratio</span>
          <span class="fv-oval">{peg_txt}{"  " + pe_vs_hist_txt if pe_vs_hist_txt else ""}</span>
        </div>
        <div class="fv-orow">
          <span class="fv-olbl">Target Weight</span>
          <span class="fv-oval">{final_weight}</span>
        </div>
        <div class="fv-orow">
          <span class="fv-olbl">Monthly Alloc</span>
          <span class="fv-oval">{alloc_txt}</span>
        </div>
      </div>{spyl_dip_html}{btc_cycle_html}
    </div>"""

fv_cards_html = "".join(_build_card(*c) for c in FV_CONFIG)

# ── PORTFOLIO HOLDINGS VALUATION ─────────────────────────────────────────────
# Use live_prices populated by _build_card. For tickers not in FV_CONFIG (VOO, GOOG, ETH),
# fall back to the chart-history last close.
def _holding_price(ticker):
    """Best-available live price for a holdings ticker."""
    if ticker in live_prices:
        return live_prices[ticker]
    # GOOG ≈ GOOGL price (different share class but tracks closely)
    if ticker == "GOOG" and "GOOG" in prices:
        return float(prices["GOOG"].iloc[-1])
    if ticker in prices:
        return float(prices[ticker].iloc[-1])
    # GOOG fallback to GOOGL if separate fetch failed
    if ticker == "GOOG" and "GOOGL" in live_prices:
        return live_prices["GOOGL"]
    return None

# Build per-account holdings + totals
holdings_rows  = []   # flat list for the snapshot table
account_totals = {}   # account -> {value, cost, cash}
total_value    = 0.0
total_cost     = 0.0
total_cash     = 0.0

for account, positions in HOLDINGS.items():
    acc_value = 0.0
    acc_cost  = 0.0
    acc_cash  = 0.0
    for ticker, holding in positions.items():
        if ticker == "CASH":
            acc_cash   += holding
            acc_value  += holding
            total_cash += holding
            holdings_rows.append({
                "account": account, "ticker": "CASH",
                "shares": None, "avg_cost": None, "price": None,
                "cost_basis": holding, "value": holding, "pnl": 0.0, "pnl_pct": 0.0,
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
        pnl        = value - cost_basis
        pnl_pct    = (pnl / cost_basis * 100) if cost_basis > 0 else 0.0
        acc_value += value
        acc_cost  += cost_basis
        holdings_rows.append({
            "account": account, "ticker": ticker,
            "shares": shares, "avg_cost": avg_cost, "price": price,
            "cost_basis": cost_basis, "value": value, "pnl": pnl, "pnl_pct": pnl_pct,
        })
    account_totals[account] = {"value": acc_value, "cost": acc_cost, "cash": acc_cash}
    total_value += acc_value
    total_cost  += acc_cost

total_pnl     = total_value - total_cost - total_cash   # cash isn't a "position" with P&L
total_pnl_pct = (total_pnl / (total_cost) * 100) if total_cost > 0 else 0.0

print(f"\n── Portfolio Snapshot ──")
print(f"  Total value: ${total_value:,.2f}")
print(f"  Total cost:  ${total_cost:,.2f}")
print(f"  Total cash:  ${total_cash:,.2f}")
print(f"  Unrealized:  ${total_pnl:+,.2f} ({total_pnl_pct:+.2f}%)")

# ── BUILD HOLDINGS SNAPSHOT TABLE HTML ───────────────────────────────────────
def _fmt_usd(v, dec=2):
    if v is None: return "—"
    return f"${v:,.{dec}f}" if dec > 0 else f"${int(round(v)):,}"

def _fmt_shares(s):
    if s is None: return "—"
    if s < 1: return f"{s:.4f}"
    return f"{int(s):,}" if s == int(s) else f"{s:,.2f}"

ACCOUNT_LABELS = {
    "IBKR":      "IBKR",
    "CITI_401K": "Citi 401k",
    "CITI_ROTH": "Citi Roth",
    "CITI_BROK": "Citi Brokerage",
    "CRYPTO":    "Crypto",
}

snapshot_rows_html = ""
for r in holdings_rows:
    pnl_cls  = "pos" if r["pnl"] >= 0 else "neg"
    sign     = "+" if r["pnl"] >= 0 else ""
    is_cash  = r["ticker"] == "CASH"
    acc_lbl  = ACCOUNT_LABELS.get(r["account"], r["account"])
    snapshot_rows_html += f"""
        <tr class="hold-row{' hold-cash' if is_cash else ''}">
          <td class="hold-acc">{acc_lbl}</td>
          <td class="hold-tk">{r['ticker']}</td>
          <td class="hold-num">{_fmt_shares(r['shares'])}</td>
          <td class="hold-num">{_fmt_usd(r['avg_cost'])}</td>
          <td class="hold-num">{_fmt_usd(r['price'])}</td>
          <td class="hold-num">{_fmt_usd(r['cost_basis'])}</td>
          <td class="hold-num"><strong>{_fmt_usd(r['value'])}</strong></td>
          <td class="hold-num {pnl_cls}">{sign}{_fmt_usd(r['pnl']) if not is_cash else '—'}</td>
          <td class="hold-num {pnl_cls}">{(sign + f"{r['pnl_pct']:.1f}%") if not is_cash else '—'}</td>
        </tr>"""

# Account subtotals row
account_subtotal_html = ""
for acc, t in account_totals.items():
    acc_lbl = ACCOUNT_LABELS.get(acc, acc)
    account_subtotal_html += f"""
      <div class="acc-pill">
        <div class="acc-name">{acc_lbl}</div>
        <div class="acc-val">{_fmt_usd(t['value'], 0)}</div>
      </div>"""

# ── DEPLOYMENT GAPS TRACKER ──────────────────────────────────────────────────
# For each ticker in TARGET_WEIGHTS, compute current weight vs target weight.
# Sum holdings of that ticker across all accounts.
def _holdings_for_ticker(t):
    total = 0.0
    for account, positions in HOLDINGS.items():
        for ticker, h in positions.items():
            if ticker == t and isinstance(h, dict):
                price = _holding_price(t) or 0
                total += h["shares"] * price
    return total

gaps_rows = []
for ticker, target_w in TARGET_WEIGHTS.items():
    cur_value   = _holdings_for_ticker(ticker)
    cur_weight  = (cur_value / total_value) if total_value > 0 else 0
    target_val  = target_w * total_value
    gap_dollar  = target_val - cur_value
    gap_pct     = (target_w - cur_weight) * 100  # in percentage points
    progress    = (cur_weight / target_w * 100) if target_w > 0 else 0
    gaps_rows.append({
        "ticker": ticker,
        "current_value": cur_value,
        "current_weight": cur_weight * 100,
        "target_weight": target_w * 100,
        "target_value":  target_val,
        "gap_dollar":    gap_dollar,
        "gap_pct":       gap_pct,
        "progress":      min(progress, 150),   # cap visual at 150% over-allocation
    })

gaps_rows_html = ""
for g in gaps_rows:
    gap_cls    = "pos" if g["gap_dollar"] <= 0 else "neg"
    gap_sign   = "" if g["gap_dollar"] <= 0 else "+"
    bar_color  = "#15803d" if g["progress"] >= 95 else "#b45309" if g["progress"] >= 60 else "#b91c1c"
    bar_pct    = min(g["progress"], 100)
    gaps_rows_html += f"""
        <tr>
          <td class="gap-tk">{g['ticker']}</td>
          <td class="hold-num">{_fmt_usd(g['current_value'], 0)}</td>
          <td class="hold-num">{g['current_weight']:.1f}%</td>
          <td class="hold-num">{g['target_weight']:.1f}%</td>
          <td class="hold-num">{_fmt_usd(g['target_value'], 0)}</td>
          <td class="hold-num {gap_cls}">{gap_sign}{_fmt_usd(g['gap_dollar'], 0)}</td>
          <td>
            <div class="gap-bar">
              <div class="gap-fill" style="width:{bar_pct:.1f}%;background:{bar_color}"></div>
            </div>
            <div class="gap-pct">{g['progress']:.0f}% of target</div>
          </td>
        </tr>"""

# ── ACTION TABLE ROWS (Python-generated, JS makes interactive) ────────────────
# Build per-ticker action data for the Monday table
action_rows_data = []
for yt, disp, co, cls in FV_CONFIG:
    ov = FV_OVERLAY.get(disp, {})
    bucket = ov.get("bucket", 0)
    b1_w   = ov.get("b1_w", 0.0)
    action = ov.get("zone_action", {}).get(current_zone, "Hold")
    dep_cls = _deploy_color(action)
    # Urgency
    if "aggressively" in action.lower() or "max" in action.lower(): urgency = "HIGH"
    elif "systematic" in action.lower() or "slowly" in action.lower() or "dca" in action.lower(): urgency = "MEDIUM"
    elif "do not" in action.lower() or "strategic hold" in action.lower(): urgency = "SKIP"
    else: urgency = "LOW"
    action_rows_data.append({
        "ticker": disp, "bucket": bucket, "b1_w": b1_w,
        "action": action, "dep_cls": dep_cls, "urgency": urgency,
    })

action_rows_json = json.dumps(action_rows_data, separators=(",",":"))

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
    "zone_deploy":  ZONE_DEPLOY,
    "zone_meta":    {str(k): v for k, v in ZONE_META.items()},
    "action_rows":  action_rows_data,
    "fetched_at":   fetched_at,
}, separators=(",",":"))

print(f"\nGenerating index.html...")

# ── HTML ──────────────────────────────────────────────────────────────────────
zone_color  = ZONE_META[current_zone]["color"]
zone_bg     = ZONE_META[current_zone]["bg"]
zone_label  = ZONE_META[current_zone]["label"]
zone_desc   = ZONE_META[current_zone]["desc"]
zone_deploy = ZONE_DEPLOY[current_zone]
spread_fmt  = f"{current_spread:+.2f}%"

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
  --spy:#16a34a;--mag:#1d4ed8;--tsl:#dc2626;--btc:#eab308;
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
.zone-banner{{background:{zone_bg};border:1px solid {zone_color}33;border-radius:8px;padding:14px 18px;margin-bottom:20px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}}
.zone-pill{{background:{zone_color};color:#fff;font-family:'Syne',sans-serif;font-size:13px;font-weight:700;padding:5px 14px;border-radius:20px;letter-spacing:.03em;white-space:nowrap}}
.zone-spread{{font-size:22px;font-family:'Syne',sans-serif;font-weight:700;color:{zone_color}}}
.zone-desc{{font-size:11px;color:var(--mut)}}
.zone-alloc-row{{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;width:100%}}
.zone-alloc-chip{{background:var(--surf);border:.5px solid var(--bdr);border-radius:4px;padding:4px 10px;font-size:10px;text-align:center}}
.zone-alloc-chip span{{display:block;font-size:16px;font-weight:600;color:var(--txt);line-height:1.2}}
.zone-alloc-chip small{{color:var(--mut)}}

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

/* ── ACTION TABLE ── */
.action-section{{margin-bottom:32px}}
.cash-input-row{{display:flex;align-items:center;gap:12px;margin-bottom:16px;flex-wrap:wrap}}
.cash-label{{font-size:10px;color:var(--mut);white-space:nowrap}}
.cash-input{{font-family:'DM Mono',monospace;font-size:18px;font-weight:500;color:var(--txt);border:1.5px solid var(--zone);border-radius:6px;padding:7px 14px;width:180px;background:var(--surf);outline:none}}
.cash-input:focus{{border-color:var(--txt);box-shadow:0 0 0 3px rgba(0,0,0,.06)}}
.cash-hint{{font-size:9px;color:var(--mut)}}
.action-table{{width:100%;border-collapse:collapse;font-size:11px}}
.action-table th{{font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:var(--mut);padding:6px 10px;text-align:left;border-bottom:1px solid var(--bdr);white-space:nowrap}}
.action-table td{{padding:9px 10px;border-bottom:.5px solid var(--bdr);vertical-align:middle}}
.action-table tr:last-child td{{border-bottom:none}}
.action-table tr:hover td{{background:var(--dim)}}
.at-ticker{{font-family:'Syne',sans-serif;font-weight:700;font-size:13px}}
.at-bucket{{font-size:9px;color:var(--mut);margin-top:1px}}
.urgency-HIGH{{color:#fff;background:#dc2626;padding:2px 7px;border-radius:3px;font-size:9px;font-weight:600}}
.urgency-MEDIUM{{color:#92400e;background:#fef3c7;padding:2px 7px;border-radius:3px;font-size:9px}}
.urgency-LOW{{color:#1e40af;background:#dbeafe;padding:2px 7px;border-radius:3px;font-size:9px}}
.urgency-SKIP{{color:var(--mut);background:var(--dim);padding:2px 7px;border-radius:3px;font-size:9px}}
.at-alloc{{font-size:13px;font-weight:600}}
.at-shares{{font-size:13px;font-weight:500;color:var(--txt)}}
.at-limit{{font-size:12px;color:var(--mut)}}
.at-action{{font-size:10px}}
.dep-green{{color:#15803d;font-weight:600}}
.dep-amber{{color:#b45309;font-weight:500}}
.dep-red{{color:#b91c1c;font-weight:500}}
.dep-neutral{{color:var(--mut)}}
.residual-row{{background:var(--dim);border-top:1px solid var(--bdr);font-size:11px;padding:8px 10px;display:flex;justify-content:space-between;border-radius:0 0 6px 6px}}

/* ── STOCK CHART ── */
.chart-section{{margin-bottom:32px}}
.ctrls{{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:12px}}
.cl{{font-size:9px;color:var(--mut);letter-spacing:.06em}}
.tog{{font-size:10px;padding:4px 11px;border-radius:4px;border:.5px solid var(--bdr2);background:transparent;color:var(--mut);cursor:pointer;font-family:'DM Mono',monospace}}
.tog.on{{background:var(--txt);color:#fff;border-color:var(--txt)}}
.vsep{{width:1px;height:18px;background:var(--bdr);margin:0 4px}}
.tabs{{display:flex;border-bottom:1px solid var(--bdr);margin-bottom:12px}}
.tab{{font-size:10px;padding:7px 16px;border:none;background:transparent;color:var(--mut);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;font-family:'DM Mono',monospace;letter-spacing:.04em}}
.tab.on{{color:var(--txt);border-bottom-color:var(--txt)}}
.cards{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin-bottom:12px}}
.card{{background:var(--surf);border-radius:6px;border:.5px solid var(--bdr);border-top:2px solid transparent;padding:11px 13px}}
.card-lbl{{font-size:9px;color:var(--mut);letter-spacing:.1em;margin-bottom:4px}}
.card-val{{font-size:20px;font-weight:500;margin-bottom:2px}}
.card-sub{{font-size:9px;color:var(--mut)}}
.card-base{{font-size:9px;color:var(--mut);opacity:.5;margin-top:2px}}
.pos{{color:var(--grn)}} .neg{{color:var(--red)}}
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
.fv-strat{{background:#f3e8ff;color:#6b21a8}}
.fv-prow{{display:flex;gap:12px;margin-bottom:10px}}
.fv-pblk{{flex:1}}
.fv-plbl{{font-size:8px;color:var(--mut);letter-spacing:.1em;text-transform:uppercase;margin-bottom:2px}}
.fv-pval{{font-size:16px;font-weight:600;color:var(--txt);font-family:'Syne',sans-serif}}
.fv-pos{{color:var(--grn)}} .fv-neg{{color:var(--red)}}
.fv-bar{{margin:6px 0}}
.fv-blbl{{display:flex;justify-content:space-between;font-size:8px;color:var(--mut);margin-bottom:3px}}
.fv-bg{{height:4px;background:var(--dim);border-radius:2px;overflow:hidden}}
.fv-fl{{height:100%;border-radius:2px}}
.fv-mtx{{display:flex;gap:6px;margin-top:8px}}
.fv-mbox{{flex:1;background:var(--dim);border-radius:4px;padding:5px 8px;text-align:center}}
.fv-mlbl{{font-size:8px;color:var(--mut);margin-bottom:1px}}
.fv-mval{{font-size:11px;font-weight:600;color:var(--txt)}}
.fv-overlay{{margin-top:10px;padding-top:8px;border-top:.5px solid var(--bdr)}}
.fv-orow{{display:flex;justify-content:space-between;align-items:center;padding:3px 0;font-size:10px}}
.fv-olbl{{color:var(--mut);flex-shrink:0;margin-right:8px}}
.fv-oval{{text-align:right}}
.fv-disc{{font-size:8px;color:var(--mut);margin-top:16px;padding-top:8px;border-top:.5px solid var(--bdr);line-height:1.6}}

/* SPYL dip trigger */
.fv-dip{{margin-top:10px;padding:8px 10px;background:var(--dim);border-radius:5px}}
.fv-dip-title{{font-size:8px;letter-spacing:.12em;text-transform:uppercase;color:var(--mut);margin-bottom:5px}}
.fv-dip-vals{{display:flex;justify-content:space-between;font-size:10px;margin-bottom:5px}}
.fv-dip-bar{{height:5px;background:#e5e7eb;border-radius:3px;position:relative;overflow:visible;margin-bottom:2px}}
.fv-dip-fill{{height:100%;border-radius:3px;transition:width .3s}}
.fv-dip-mark{{position:absolute;top:-3px;width:1.5px;height:11px;background:#94a3b8}}
.fv-dip-labels{{display:flex;justify-content:space-between;font-size:8px;color:var(--mut)}}

/* BTC note */
.fv-btcnote{{margin-top:10px;padding:8px 10px;background:var(--dim);border-radius:5px}}
.fv-btcrow{{display:flex;justify-content:space-between;font-size:10px;padding:2px 0}}

/* ── PORTFOLIO SNAPSHOT (HERO) ── */
.snap-section{{margin-bottom:32px}}
.snap-hero{{background:linear-gradient(135deg,var(--surf) 0%,var(--surf2) 100%);border:1px solid var(--bdr);border-radius:10px;padding:20px 24px;margin-bottom:14px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px}}
.snap-total-block{{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}}
.snap-total-lbl{{font-size:9px;letter-spacing:.18em;text-transform:uppercase;color:var(--mut)}}
.snap-total-val{{font-family:'Syne',sans-serif;font-size:36px;font-weight:800;color:var(--txt);letter-spacing:-.5px;line-height:1}}
.snap-pnl{{font-family:'Syne',sans-serif;font-size:13px;font-weight:700;padding:4px 10px;border-radius:6px}}
.snap-pnl.pos{{background:#dcfce7;color:#15803d}}
.snap-pnl.neg{{background:#fee2e2;color:#b91c1c}}
.snap-meta{{display:flex;gap:18px;font-size:10px;color:var(--mut);flex-wrap:wrap}}
.snap-meta strong{{color:var(--txt);font-family:'Syne',sans-serif;font-size:14px;display:block;margin-top:2px}}
.acc-pill-row{{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}}
.acc-pill{{background:var(--surf);border:.5px solid var(--bdr);border-radius:6px;padding:8px 14px}}
.acc-name{{font-size:9px;color:var(--mut);letter-spacing:.06em;text-transform:uppercase}}
.acc-val{{font-family:'Syne',sans-serif;font-size:14px;font-weight:700;color:var(--txt);margin-top:2px}}

/* ── HOLDINGS TABLE ── */
.hold-section{{margin-bottom:32px}}
.hold-table{{width:100%;border-collapse:collapse;font-size:11px;background:var(--surf);border:.5px solid var(--bdr);border-radius:6px;overflow:hidden}}
.hold-table th{{font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:var(--mut);padding:8px 10px;text-align:left;border-bottom:1px solid var(--bdr);background:var(--surf2);white-space:nowrap}}
.hold-table th.hold-num,.hold-table td.hold-num{{text-align:right}}
.hold-table td{{padding:8px 10px;border-bottom:.5px solid var(--bdr);vertical-align:middle}}
.hold-row:hover td{{background:var(--dim)}}
.hold-row.hold-cash{{background:#fffbeb}}
.hold-row.hold-cash td{{color:var(--mut);font-style:italic}}
.hold-acc{{font-size:10px;color:var(--mut)}}
.hold-tk{{font-family:'Syne',sans-serif;font-weight:700;font-size:12px}}

/* ── DEPLOYMENT GAPS ── */
.gap-section{{margin-bottom:32px}}
.gap-table{{width:100%;border-collapse:collapse;font-size:11px;background:var(--surf);border:.5px solid var(--bdr);border-radius:6px;overflow:hidden}}
.gap-table th{{font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:var(--mut);padding:8px 10px;text-align:left;border-bottom:1px solid var(--bdr);background:var(--surf2);white-space:nowrap}}
.gap-table th.hold-num,.gap-table td.hold-num{{text-align:right}}
.gap-table td{{padding:8px 10px;border-bottom:.5px solid var(--bdr);vertical-align:middle}}
.gap-tk{{font-family:'Syne',sans-serif;font-weight:700;font-size:12px}}
.gap-bar{{height:5px;background:#e5e7eb;border-radius:3px;overflow:hidden;width:140px}}
.gap-fill{{height:100%;border-radius:3px;transition:width .3s}}
.gap-pct{{font-size:9px;color:var(--mut);margin-top:3px;width:140px}}

/* ── FOOTER ── */
hr{{border:none;border-top:.5px solid var(--bdr);margin:24px 0 12px}}
.footer{{font-size:9px;color:var(--mut);line-height:2;text-align:center}}

@media(max-width:700px){{
  .cards{{grid-template-columns:repeat(2,1fr)}}
  .tab,.yc-tab{{padding:6px 10px;font-size:9px}}
  .action-table th:nth-child(n+5),.action-table td:nth-child(n+5){{display:none}}
}}
</style>
</head>
<body>
<div class="page">

  <!-- HEADER -->
  <div class="hdr">
    <div class="hdr-left">
      <h1>Investment Dashboard</h1>
      <div class="hdr-sub">AI Alpha Engine · Passive Anchor · Asymmetric Bets</div>
    </div>
    <div style="text-align:right">
      <div style="font-family:'Syne',sans-serif;font-size:11px;font-weight:700;color:var(--zone)">{zone_label}</div>
      <div style="font-size:9px;color:var(--mut);margin-top:2px">{zone_desc}</div>
    </div>
  </div>
  <div class="src">
    <span class="src-dot"></span>
    <span>Refreshed: {fetched_at} · Next: {next_refresh} · Yahoo Finance via yfinance</span>
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
    <div class="zone-alloc-row">
      <div class="zone-alloc-chip"><span>{zone_deploy['B1']}</span><small>Bucket 1</small></div>
      <div class="zone-alloc-chip"><span>{zone_deploy['SPYL']}</span><small>SPYL</small></div>
      <div class="zone-alloc-chip"><span>{zone_deploy['B3']}</span><small>Bucket 3</small></div>
      <div class="zone-alloc-chip"><span>{zone_deploy['Dry']}</span><small>Dry Powder</small></div>
      <div class="zone-alloc-chip"><span>{zone_deploy['PHP']}</span><small>PHP Cash</small></div>
    </div>
  </div>

  <!-- PORTFOLIO SNAPSHOT -->
  <div class="snap-section">
    <div class="section-hd">
      <span>PORTFOLIO SNAPSHOT</span>
      <span style="font-size:9px">Live valuation · {len(holdings_rows)} positions across {len(account_totals)} accounts</span>
    </div>
    <div class="snap-hero">
      <div class="snap-total-block">
        <div>
          <div class="snap-total-lbl">Total Portfolio Value</div>
          <div class="snap-total-val">${total_value:,.0f}</div>
        </div>
        <div class="snap-pnl {'pos' if total_pnl >= 0 else 'neg'}">
          {'+' if total_pnl >= 0 else ''}${total_pnl:,.0f} ({'+' if total_pnl >= 0 else ''}{total_pnl_pct:.1f}%)
        </div>
      </div>
      <div class="snap-meta">
        <div>Cost basis<strong>${total_cost:,.0f}</strong></div>
        <div>Cash on hand<strong>${total_cash:,.0f}</strong></div>
        <div>Invested<strong>${total_value - total_cash:,.0f}</strong></div>
      </div>
    </div>
    <div class="acc-pill-row">{account_subtotal_html}
    </div>
  </div>

  <!-- HOLDINGS DETAIL -->
  <div class="hold-section">
    <div class="section-hd">
      <span>HOLDINGS SNAPSHOT</span>
      <span style="font-size:9px">Per-position cost · current value · unrealized P&amp;L</span>
    </div>
    <table class="hold-table">
      <thead>
        <tr>
          <th>Account</th>
          <th>Ticker</th>
          <th class="hold-num">Shares</th>
          <th class="hold-num">Avg Cost</th>
          <th class="hold-num">Price</th>
          <th class="hold-num">Cost Basis</th>
          <th class="hold-num">Value</th>
          <th class="hold-num">P&amp;L</th>
          <th class="hold-num">P&amp;L %</th>
        </tr>
      </thead>
      <tbody>{snapshot_rows_html}
      </tbody>
    </table>
  </div>

  <!-- DEPLOYMENT GAPS -->
  <div class="gap-section">
    <div class="section-hd">
      <span>DEPLOYMENT GAPS</span>
      <span style="font-size:9px">Current allocation vs target weights · gap = $ to deploy</span>
    </div>
    <table class="gap-table">
      <thead>
        <tr>
          <th>Ticker</th>
          <th class="hold-num">Current Value</th>
          <th class="hold-num">Current Wt</th>
          <th class="hold-num">Target Wt</th>
          <th class="hold-num">Target $</th>
          <th class="hold-num">Gap to Target</th>
          <th>Progress</th>
        </tr>
      </thead>
      <tbody>{gaps_rows_html}
      </tbody>
    </table>
  </div>

  <!-- YIELD CURVE CHART -->
  <div class="yc-section">
    <div class="section-hd">
      <span>MACRO OVERLAY — YIELD CURVE</span>
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

  <!-- MONDAY ACTION TABLE -->
  <div class="action-section">
    <div class="section-hd">
      <span>MONDAY ACTION TABLE</span>
      <span style="font-size:9px;color:var(--zone)">Zone {current_zone} · US market opens 9:30PM Manila</span>
    </div>
    <div class="cash-input-row">
      <span class="cash-label">Weekly deployment (USD):</span>
      <input class="cash-input" type="number" id="cashInput" value="50000" min="0" step="1000" oninput="renderTable()"/>
      <span class="cash-hint">Edit to match IBKR settled cash → table updates instantly</span>
    </div>
    <table class="action-table" id="actionTable">
      <thead>
        <tr>
          <th>Ticker</th>
          <th>Bucket</th>
          <th>Zone Action</th>
          <th>Urgency</th>
          <th>Current Price</th>
          <th>Allocation</th>
          <th>Shares to Buy</th>
          <th>Limit Price</th>
        </tr>
      </thead>
      <tbody id="actionBody"></tbody>
    </table>
    <div class="residual-row" id="residualRow">
      <span>Residual cash (dry powder)</span>
      <span id="residualAmt">—</span>
    </div>
  </div>

  <!-- STOCK PERFORMANCE CHART -->
  <div class="chart-section">
    <div class="section-hd"><span>PORTFOLIO PERFORMANCE</span></div>
    <div class="ctrls">
      <span class="cl">Scale</span>
      <button class="tog on" id="bl" onclick="setScale('linear')">Linear</button>
      <button class="tog"    id="bg" onclick="setScale('log')">Log</button>
      <div class="vsep"></div>
      <span class="cl">Vol bands</span>
      <button class="tog on" id="bbon"  onclick="setBands(true)">Show</button>
      <button class="tog"    id="bboff" onclick="setBands(false)">Hide</button>
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
      <span class="li"><span class="ln" style="background:var(--spy)"></span>SPY · Beta</span>
      <span class="li"><span class="ln" style="background:var(--mag)"></span>Mag7 · Alpha</span>
      <span class="li"><span class="ln" style="background:var(--tsl)"></span>Tesla</span>
      <span class="li"><span class="ln" style="background:var(--btc)"></span>Bitcoin</span>
      <span class="li"><span class="ld" style="color:#888"></span>Projection</span>
      <span class="li" id="bandLeg"><span style="display:inline-block;width:14px;height:6px;background:rgba(150,150,150,.15);border-radius:1px"></span>90% band</span>
    </div>
    <div class="note" id="note"></div>
    <div class="chart-wrap"><canvas id="chart" role="img" aria-label="Multi-horizon performance chart"></canvas></div>
    <div class="outperf" id="outperf"></div>
  </div>

  <!-- FAIR VALUE CARDS -->
  <div class="fv-section">
    <div class="section-hd">
      <span>FAIR VALUE ASSESSMENT</span>
      <span style="font-size:9px">Live yfinance · Analyst consensus · Zone {current_zone} actions shown</span>
    </div>
    <div class="fv-grid">{fv_cards_html}
    </div>
    <div class="fv-disc">Live yfinance data · Analyst consensus from Yahoo Finance · SPYL target = Wall St 2026 S&P consensus implied · BTC target = Stock-to-Flow model range · PEG = Fwd P/E ÷ Revenue growth · Zone actions update with yield curve · Not investment advice</div>
  </div>

  <hr/>
  <div class="footer">
    Investment Dashboard · yfinance data · MAG7: MSFT 25% / NVDA 25% / GOOGL 20% / META 15% / AMZN 10% / AAPL 5%<br>
    Yield curve: OU mean reversion μ={OU_MU}% · Stock projections: CAGR (5Y) · Analyst target (≤1Y) · GBM (≤6M) · Not financial advice<br>
    <span style="opacity:.6">v{SCRIPT_VERSION} · {SCRIPT_DATE} · Generated {fetched_at}</span>
  </div>
</div>

<script>
const DATA = {payload};
const COLORS = {{SPY:'#16a34a',MAG7:'#1d4ed8',TSLA:'#dc2626',BTC:'#eab308'}};
const FWD    = {{SPY:8,MAG7:11,TSLA:15,BTC:20}};
const LONG_H = new Set(['5Y']);
const LABELS = {{SPY:'SPY · BETA',MAG7:'MAG7 · ALPHA',TSLA:'TESLA · BET',BTC:'BITCOIN · BET'}};
const NAMES  = {{SPY:'SPY (Beta)',MAG7:'Mag7 Alpha',TSLA:'Tesla',BTC:'Bitcoin'}};
const ZONE_COLOR = '{zone_color}';
const ZONE_BOUNDARIES = {json.dumps(ZONE_BOUNDARIES)};
const ZONE_COLORS = ['#dc2626','#ea580c','#d97706','#16a34a','#15803d'];
const ZONE_BG     = ['rgba(220,38,38,.08)','rgba(234,88,12,.06)','rgba(217,119,6,.04)','rgba(22,163,74,.06)','rgba(21,128,61,.08)'];

let curTab='7D', curYCTab='5Y', useLog=false, showBands=true;
let chartInst=null, ycInst=null;

// ── YIELD CURVE CHART ─────────────────────────────────────────────────────────
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

  // Zone band background plugin
  const zoneBandPl = {{id:'zb',beforeDraw(c){{
    const xs=c.scales.x, ys=c.scales.y;if(!xs||!ys)return;
    const ctx=c.ctx, ca=c.chartArea;
    ctx.save();
    // Zone bands (horizontal)
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
    // Zero line
    const y0=ys.getPixelForValue(0);
    if(y0>=ca.top&&y0<=ca.bottom){{
      ctx.strokeStyle='rgba(220,38,38,.5)';ctx.lineWidth=1;ctx.setLineDash([3,3]);
      ctx.beginPath();ctx.moveTo(ca.left,y0);ctx.lineTo(ca.right,y0);ctx.stroke();
    }}
    ctx.restore();
  }}}};

  const datasets=[];
  // Historical
  datasets.push({{
    label:'Spread',
    data: yd.hist.map(([dt,v])=>{{return{{x:new Date(dt+'T12:00:00'),y:v}};}}),
    borderColor:ZONE_COLOR,backgroundColor:'transparent',borderWidth:2,pointRadius:0,tension:.15,order:2
  }});
  // OU projection (center)
  if(yd.proj&&yd.proj.length){{
    const lastH=yd.hist[yd.hist.length-1];
    const stitch=[{{x:new Date(lastH[0]+'T12:00:00'),y:lastH[1]}}];
    datasets.push({{
      label:'OU Projection',
      data:[...stitch,...yd.proj.map(([dt,v])=>{{return{{x:new Date(dt+'T12:00:00'),y:v}};}})] ,
      borderColor:ZONE_COLOR,backgroundColor:'transparent',borderWidth:1.5,pointRadius:0,tension:.2,borderDash:[6,4],order:1
    }});
    // Confidence band
    if(yd.upper&&yd.lower){{
      const stU=[{{x:new Date(lastH[0]+'T12:00:00'),y:lastH[1]}},...yd.upper.map(([dt,v])=>{{return{{x:new Date(dt+'T12:00:00'),y:v}};}})] ;
      const stL=[{{x:new Date(lastH[0]+'T12:00:00'),y:lastH[1]}},...yd.lower.map(([dt,v])=>{{return{{x:new Date(dt+'T12:00:00'),y:v}};}})] ;
      datasets.push({{label:'_u',data:stU,borderColor:'transparent',backgroundColor:'rgba(100,100,100,.08)',fill:'+1',borderWidth:0,pointRadius:0,tension:.2,order:3}});
      datasets.push({{label:'_l',data:stL,borderColor:'transparent',backgroundColor:'rgba(100,100,100,.08)',fill:false,borderWidth:0,pointRadius:0,tension:.2,order:3}});
    }}
  }}

  // Long-run mean reference line (static)
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

// ── MONDAY ACTION TABLE ───────────────────────────────────────────────────────
const ACTION_ROWS = {action_rows_json};
const ZONE_B1_FRAC = {{"1":0.25,"2":0.40,"3":0.60,"4":0.65,"5":0.70}};
const CUR_ZONE = "{current_zone}";
const B1_FRAC  = ZONE_B1_FRAC[CUR_ZONE] || 0.60;
const SPYL_FRAC = 0.20;

// Fetch live prices from card data attributes
function getLivePrices(){{
  const prices={{}};
  document.querySelectorAll('.fv-card').forEach(card=>{{
    const tk=card.dataset.ticker;
    const pr=parseFloat(card.dataset.price);
    if(tk&&pr) prices[tk]=pr;
  }});
  return prices;
}}

function renderTable(){{
  const cash = parseFloat(document.getElementById('cashInput').value)||0;
  const prices = getLivePrices();
  const rows   = ACTION_ROWS;
  const tbody  = document.getElementById('actionBody');
  let   deployed = 0;
  let   html = '';

  rows.forEach(r=>{{
    const price = prices[r.ticker]||0;
    let alloc = 0;
    if(r.bucket===1)      alloc = r.b1_w * B1_FRAC * cash;
    else if(r.bucket===2) alloc = SPYL_FRAC * cash;
    else if(r.bucket===3) alloc = 0.05 * cash * (r.urgency!=='SKIP'?1:0);

    const skip = r.urgency==='SKIP' || r.bucket===0;
    if(!skip) deployed += alloc;

    const shares = (price>0&&alloc>0&&!skip) ? Math.floor(alloc/price) : 0;
    const limit  = (price>0) ? (price*1.003).toFixed(price<10?3:2) : '—';
    const fmtN = v => Math.round(v).toString().replace(/(\d)(?=(\d\d\d)+(?!\d))/g,'$1,');
    const allocFmt = alloc>0&&!skip ? '$'+fmtN(alloc) : '—';
    const sharesFmt = shares>0 ? shares : (skip?'—':'<1');
    const limitFmt  = shares>0&&!skip ? '$'+limit : '—';
    const rowStyle  = skip ? 'opacity:.45' : '';

    const bktLabel  = r.bucket===1?'Bucket 1 · AI Alpha':r.bucket===2?'Bucket 2 · SPYL':r.bucket===3?'Bucket 3 · Asymmetric':'Hold';

    html += `<tr style="${{rowStyle}}">
      <td><div class="at-ticker">${{r.ticker}}</div><div class="at-bucket">${{bktLabel}}</div></td>
      <td style="font-size:11px">${{bktLabel.split(' ')[0]+' '+bktLabel.split(' ')[1]}}</td>
      <td><span class="at-action ${{r.dep_cls}}">${{r.action}}</span></td>
      <td><span class="urgency-${{r.urgency}}">${{r.urgency}}</span></td>
      <td style="font-family:'Syne',sans-serif;font-weight:700">${{price>0?'$'+price.toLocaleString('en',{{minimumFractionDigits:price<100?2:0}}):'—'}}</td>
      <td class="at-alloc" style="color:${{skip?'var(--mut)':'var(--txt)'}}">${{allocFmt}}</td>
      <td class="at-shares">${{sharesFmt}}</td>
      <td class="at-limit">${{limitFmt}}</td>
    </tr>`;
  }});

  tbody.innerHTML = html;
  const residual = cash - deployed;
  const fmtResidual = v => Math.round(v).toString().replace(/(\d)(?=(\d\d\d)+(?!\d))/g,'$1,');
  document.getElementById('residualAmt').textContent =
    '$'+fmtResidual(residual) + ' → dry powder / PHP buffer';
}}

// ── STOCK PERFORMANCE CHART ───────────────────────────────────────────────────
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
function setBands(v){{
  showBands=v;
  document.getElementById('bbon').classList.toggle('on',v);
  document.getElementById('bboff').classList.toggle('on',!v);
  document.getElementById('bandLeg').style.opacity=v?1:0.3;
  render();
}}

function render(){{
  const hd=DATA.horizons[curTab];
  if(!hd)return;
  const keys=['SPY','MAG7','TSLA','BTC'];

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

  // Outperformance
  const spy=hd['SPY'];
  if(spy) document.getElementById('outperf').innerHTML=['MAG7','TSLA','BTC'].map(k=>{{
    const d=hd[k];if(!d)return'';
    const a=d.ret-spy.ret,col=a>=0?'var(--grn)':'var(--red)',sign=a>=0?'+':'';
    return `<span class="op">${{{{MAG7:'Mag7',TSLA:'Tesla',BTC:'Bitcoin'}}[k]}}: <span style="color:${{col}}">${{sign}}${{a.toFixed(1)}}pts vs SPY</span></span>`;
  }}).join('');

  // Method note
  const isLong=LONG_H.has(curTab);
  const method=isLong?'CAGR geometric compounding':curTab==='1Y'||curTab==='YTD'?'Analyst target convergence':'Geometric Brownian Motion';
  document.getElementById('note').textContent=`Projection: ${{method}} · Dashed = forward · 90% vol bands on Tesla & Bitcoin`;

  // Chart
  if(chartInst){{chartInst.destroy();chartInst=null;}}
  const datasets=[];
  const todayX=new Date();

  keys.forEach(k=>{{
    const d=hd[k];if(!d)return;
    const col=COLORS[k],nm=NAMES[k];
    datasets.push({{label:nm,data:d.hist.map(([dt,v])=>{{return{{x:new Date(dt+'T12:00:00'),y:v}};}}),borderColor:col,backgroundColor:'transparent',borderWidth:2.5,pointRadius:0,tension:.12,borderDash:[]}});
    if(d.proj&&d.proj.length){{
      const lh=d.hist[d.hist.length-1];
      datasets.push({{label:nm+' →',data:[{{x:new Date(lh[0]+'T12:00:00'),y:lh[1]}},...d.proj.map(([dt,v])=>{{return{{x:new Date(dt+'T12:00:00'),y:v}};}})] ,borderColor:col,backgroundColor:'transparent',borderWidth:1.8,pointRadius:0,tension:.12,borderDash:[6,4]}});
    }}
    if(showBands&&d.band_upper&&d.band_lower){{
      const hex=col.replace('#',''),r=parseInt(hex.slice(0,2),16),g=parseInt(hex.slice(2,4),16),b=parseInt(hex.slice(4,6),16);
      const fc=`rgba(${{r}},${{g}},${{b}},0.10)`;
      const lh=d.hist[d.hist.length-1];
      const stU=[{{x:new Date(lh[0]+'T12:00:00'),y:lh[1]}},...d.band_upper.map(([dt,v])=>{{return{{x:new Date(dt+'T12:00:00'),y:v}};}})] ;
      const stL=[{{x:new Date(lh[0]+'T12:00:00'),y:lh[1]}},...d.band_lower.map(([dt,v])=>{{return{{x:new Date(dt+'T12:00:00'),y:v}};}})] ;
      datasets.push({{label:`_${{k}}_u`,data:stU,borderColor:'transparent',backgroundColor:fc,fill:'+1',borderWidth:0,pointRadius:0,tension:.12}});
      datasets.push({{label:`_${{k}}_l`,data:stL,borderColor:'transparent',backgroundColor:fc,fill:false,borderWidth:0,pointRadius:0,tension:.12}});
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
renderTable();
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
