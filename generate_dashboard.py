"""
generate_dashboard.py — Investment Dashboard
=============================================
VERSION : 1.6.0
DATE    : 2026-05-10 09:07 PHT
Fix     : pin yfinance==0.2.37 compatible; remove multi_level_index param

Sections: Zone Banner · Yield Curve · Action Table · Portfolio Growth ·
          Holdings Snapshot · Deployment Gaps · Market Chart · Fair Value Cards

    pip install yfinance pandas numpy
    python generate_dashboard.py
"""
SCRIPT_VERSION = "1.6.0"
SCRIPT_DATE    = "2026-05-10 09:07 PHT"
import json, webbrowser, os
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
import pandas as pd
import yfinance as yf

# ══ HOLDINGS CONFIG ══════════════════════════════════════════════════════════
HOLDINGS = {
    "IBKR": {
        "META":  {"shares": 18,   "avg_cost": 612.04},
        "MSFT":  {"shares": 25,   "avg_cost": 419.18},
        "NVDA":  {"shares": 50,   "avg_cost": 202.57},
        "SPYL":  {"shares": 2065, "avg_cost": 17.72},
        "VOO":   {"shares": 28,   "avg_cost": 605.89},
        "CASH":  {"value": 31144.43},
    },
    "CITI_401K": {
        "AMZN":  {"shares": 100,  "avg_cost": 163.51},
        "GOOG":  {"shares": 141,  "avg_cost": 122.71},
        "META":  {"shares": 25,   "avg_cost": 329.06},
        "CASH":  {"value": 59.06},
    },
    "CITI_ROTH": {
        "AAPL":  {"shares": 134,  "avg_cost": 127.05},
        "META":  {"shares": 25,   "avg_cost": 339.97},
        "CASH":  {"value": 179.42},
    },
    "CITI_BROK": {
        "META":  {"shares": 12,   "avg_cost": 154.14},
        "VOO":   {"shares": 7,    "avg_cost": 388.45},
        "CASH":  {"value": 737.30},
    },
    "CRYPTO": {
        "BTC":   {"value": 14730.00},
        "ETH":   {"value": 229.00},
    },
}
ACCT_LABELS  = {"IBKR":"IBKR","CITI_401K":"Citi 401k","CITI_ROTH":"Citi Roth","CITI_BROK":"Citi Brok","CRYPTO":"Crypto"}
ACCT_COLORS  = {"IBKR":"#1d4ed8","CITI_401K":"#16a34a","CITI_ROTH":"#9333ea","CITI_BROK":"#ea580c","CRYPTO":"#eab308"}
ACCT_STATUS  = {"IBKR":"ACTIVE","CITI_401K":"FROZEN","CITI_ROTH":"FROZEN","CITI_BROK":"FROZEN","CRYPTO":"HOLD"}
FIXED_KEYS   = {"CASH","BTC","ETH"}
SKIP_IBKR    = {"GOOGL","AAPL","GOOG"}

# ══ ZONE CONFIG ══════════════════════════════════════════════════════════════
ZONE_META = {
    1:{"label":"ZONE 1 — INVERTED","color":"#dc2626","bg":"#fef2f2","desc":"Recession signal active"},
    2:{"label":"ZONE 2 — CAUTION","color":"#ea580c","bg":"#fff7ed","desc":"Post-inversion danger window"},
    3:{"label":"ZONE 3 — NEUTRAL","color":"#d97706","bg":"#fffbeb","desc":"Base operating zone"},
    4:{"label":"ZONE 4 — HEALTHY","color":"#16a34a","bg":"#f0fdf4","desc":"Expansion confirmed"},
    5:{"label":"ZONE 5 — BULL","color":"#15803d","bg":"#dcfce7","desc":"Strong expansion"},
}
ZONE_BOUNDARIES = [0.0, 0.5, 1.21, 2.0]
ZONE_DEPLOY = {
    1:{"B1":"25%","SPYL":"20%","B3":"0%","Dry":"50%","PHP":"5%"},
    2:{"B1":"40%","SPYL":"20%","B3":"3%","Dry":"32%","PHP":"5%"},
    3:{"B1":"60%","SPYL":"20%","B3":"5%","Dry":"10%","PHP":"5%"},
    4:{"B1":"65%","SPYL":"20%","B3":"5%","Dry":"5%","PHP":"5%"},
    5:{"B1":"70%","SPYL":"20%","B3":"5%","Dry":"0%","PHP":"5%"},
}
def get_zone(s):
    if s is None: return 3
    if s < 0: return 1
    if s < 0.5: return 2
    if s < 1.21: return 3
    if s < 2.0: return 4
    return 5

# ══ FV OVERLAY ════════════════════════════════════════════════════════════════
FV_OVERLAY = {
    "NVDA": {"hist_pe":50,"weight":"25% of Bucket 1","b1_w":0.25,"bucket":1,
             "zone_action":{1:"Do Not Add",2:"Hold",3:"Buy Aggressively",4:"Buy Aggressively",5:"Max Deploy"}},
    "MSFT": {"hist_pe":33,"weight":"20% of Bucket 1","b1_w":0.20,"bucket":1,
             "zone_action":{1:"Do Not Add",2:"Hold",3:"Buy Aggressively",4:"Buy Aggressively",5:"Max Deploy"}},
    "GOOGL":{"hist_pe":25,"weight":"15% of Bucket 1","b1_w":0.15,"bucket":1,
             "zone_action":{1:"Do Not Add",2:"Hold",3:"Hold — At Consensus",4:"Buy Systematically",5:"Buy Systematically"}},
    "AAPL": {"hist_pe":32,"weight":"10% of Bucket 1","b1_w":0.10,"bucket":1,
             "zone_action":{1:"Do Not Add",2:"Hold",3:"Accumulate Slowly",4:"Buy Systematically",5:"Buy Aggressively"}},
    "META": {"hist_pe":25,"weight":"20% of Bucket 1","b1_w":0.20,"bucket":1,
             "zone_action":{1:"Do Not Add",2:"Hold",3:"Buy Aggressively",4:"Buy Aggressively",5:"Max Deploy"}},
    "AMZN": {"hist_pe":22,"weight":"15% of Bucket 1","b1_w":0.15,"bucket":1,
             "zone_action":{1:"Do Not Add",2:"Hold",3:"Buy Systematically",4:"Buy Systematically",5:"Buy Aggressively"}},
    "TSLA": {"hist_pe":100,"weight":"5% of Bucket 3","b1_w":0.0,"bucket":3,
             "zone_action":{1:"Do Not Add",2:"Do Not Add",3:"Do Not Add — Overvalued",4:"Small Position Only",5:"Small Position Only"}},
    "SPYL": {"hist_pe":None,"weight":"Fixed 20% of portfolio","b1_w":0.0,"bucket":2,
             "spyl_target":18.0,"spyl_target_hi":18.50,"s52w_high":17.50,
             "zone_action":{1:"DCA Buy Fixed",2:"DCA Buy Fixed",3:"DCA Buy Fixed",4:"DCA Buy Fixed",5:"DCA Buy Fixed"}},
    "BTC":  {"hist_pe":None,"weight":"Hold — 1.2% portfolio","b1_w":0.0,"bucket":0,
             "s2f_low":100000,"s2f_high":150000,
             "zone_action":{1:"Strategic Hold",2:"Strategic Hold",3:"Strategic Hold",4:"Strategic Hold",5:"Strategic Hold"}},
}
ANALYST_TARGETS = {"TSLA":280.0,"SPY":None,"MAG7":None,"BTC":None}
MAG7_W   = {"MSFT":0.25,"NVDA":0.25,"GOOGL":0.20,"META":0.15,"AMZN":0.10,"AAPL":0.05}
FWD_CAGR = {"SPY":0.08,"MAG7":0.11,"TSLA":0.15,"BTC":0.20}
VOLS     = {"SPY":0.16,"MAG7":0.22,"TSLA":0.65,"BTC":0.80}
HOLDINGS_EQ = ["META","MSFT","NVDA","SPYL","VOO","AMZN","GOOG","AAPL"]
CHART_TKS   = list(MAG7_W.keys()) + ["SPY","TSLA","BTC-USD"]
ALL_TKS     = list(set(HOLDINGS_EQ + CHART_TKS))

# ══ FETCH PRICES ══════════════════════════════════════════════════════════════
# Use individual Ticker.history() calls — more reliable than batch download
# in yfinance 1.x across different environments / GitHub Actions runners
print("Fetching prices...")
end = datetime.today(); start = end - timedelta(days=365*11)
prices = {}
# Try batch download first (fast); fall back to individual calls if batch returns empty
_batch_ok = False
try:
    _raw_dl = yf.download(
        ALL_TKS,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        auto_adjust=True, progress=False,
    )["Close"]
    if isinstance(_raw_dl, pd.DataFrame) and len(_raw_dl) > 20:
        for col in _raw_dl.columns:
            s = _raw_dl[col].dropna()
            if len(s) > 20:
                key = "BTC" if col == "BTC-USD" else str(col)
                prices[key] = s
                print(f"  {key}: {len(s)} rows  ${s.iloc[0]:.2f} → ${s.iloc[-1]:.2f}")
        if prices:
            _batch_ok = True
            print(f"  Batch download: {len(prices)} tickers loaded")
except Exception as _e:
    print(f"  Batch download failed: {_e}")

if not _batch_ok:
    print("  Batch returned empty — falling back to individual Ticker.history() calls")
    for _tk in ALL_TKS:
        try:
            _s = yf.Ticker(_tk).history(
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                auto_adjust=True,
            )["Close"].dropna()
            if len(_s) > 20:
                key = "BTC" if _tk == "BTC-USD" else str(_tk)
                prices[key] = _s
                print(f"  {key}: {len(_s)} rows  ${_s.iloc[0]:.2f} → ${_s.iloc[-1]:.2f}")
        except Exception as _e:
            print(f"  {_tk}: failed — {_e}")

components = []
for t, w in MAG7_W.items():
    s = prices.get(t)
    if s is not None: components.append((s/s.iloc[0]*100)*w)
if components:
    basket = pd.concat(components, axis=1).sum(axis=1)
    prices["MAG7"] = basket/basket.iloc[0]*100

# ══ MARK-TO-MARKET ════════════════════════════════════════════════════════════
def get_lp(tk):
    s = prices.get(tk)
    return float(s.iloc[-1]) if s is not None and len(s) > 0 else None

holdings_mtm = {}; account_totals = {}; ticker_totals = defaultdict(float); grand_total = 0.0
for acct, positions in HOLDINGS.items():
    acct_total = 0.0; holdings_mtm[acct] = {}
    for tk, d in positions.items():
        if tk in FIXED_KEYS:
            val = d.get("value", 0)
            holdings_mtm[acct][tk] = {"value":val,"type":"cash"}
        else:
            lp = get_lp(tk) or d.get("avg_cost", 0)
            val = d["shares"] * lp; cost = d["shares"] * d["avg_cost"]
            gl = val - cost; gl_pct = (gl/cost*100) if cost > 0 else 0
            holdings_mtm[acct][tk] = {"shares":d["shares"],"avg_cost":d["avg_cost"],
                "last_price":lp,"value":val,"cost":cost,"gl":gl,"gl_pct":gl_pct,"type":"equity"}
            ticker_totals[tk] += val
        acct_total += val
    account_totals[acct] = acct_total; grand_total += acct_total
print(f"\nPortfolio total: ${grand_total:,.0f}")
for a,v in account_totals.items(): print(f"  {a}: ${v:,.0f}")

# ══ PORTFOLIO GROWTH RECONSTRUCTION ══════════════════════════════════════════
today = pd.Timestamp.today().normalize()
PTFL_H = {
    "7D": {"back":pd.DateOffset(days=7),"fwd":pd.DateOffset(days=7)},
    "30D":{"back":pd.DateOffset(days=30),"fwd":pd.DateOffset(days=30)},
    "6M": {"back":pd.DateOffset(months=6),"fwd":pd.DateOffset(months=6)},
    "YTD":{"back":None,"fwd":pd.DateOffset(months=6)},
    "1Y": {"back":pd.DateOffset(years=1),"fwd":pd.DateOffset(years=1)},
    "5Y": {"back":pd.DateOffset(years=5),"fwd":pd.DateOffset(years=5)},
}
portfolio_history = {}
for hkey, hcfg in PTFL_H.items():
    hist_start = (pd.Timestamp(today.year,1,1) if hkey=="YTD" else today-hcfg["back"])
    ref = prices.get("SPY")
    if ref is None: portfolio_history[hkey]=None; continue
    dr = ref.loc[(ref.index>=hist_start)&(ref.index<=today)].index
    if len(dr)<2: portfolio_history[hkey]=None; continue
    acct_series = {}; total_s = pd.Series(0.0, index=dr)
    for acct, positions in HOLDINGS.items():
        acs = pd.Series(0.0, index=dr)
        for tk, d in positions.items():
            if tk in FIXED_KEYS:
                acs += d.get("value",0)
            else:
                ps = prices.get(tk)
                if ps is None: continue
                acs += ps.reindex(dr, method="ffill") * d.get("shares",0)
        acct_series[acct] = acs; total_s += acs
    sv = float(total_s.iloc[0]); ev = float(total_s.iloc[-1])
    pgl = ev-sv; ppct = (pgl/sv*100) if sv>0 else 0
    td  = [(str(d.date()), round(float(v),0)) for d,v in total_s.items()]
    ti  = [(str(d.date()), round(float(v)/sv*100,2)) for d,v in total_s.items()]
    fwd = pd.bdate_range(start=today+timedelta(days=1), end=today+hcfg["fwd"])
    fwd_d = [(str(d.date()), round(ev*(1.105)**((i+1)/252),0)) for i,d in enumerate(fwd)]
    fwd_i = [(str(d.date()), round(ti[-1][1]*(1.105)**((i+1)/252),2)) for i,d in enumerate(fwd)]
    spy_s = prices["SPY"].reindex(dr, method="ffill")
    spy_i = [(str(d.date()), round(float(v)/float(spy_s.iloc[0])*100,2)) for d,v in spy_s.items()]
    bad = {a:[(str(d.date()),round(float(v),0)) for d,v in s.items()] for a,s in acct_series.items()}
    portfolio_history[hkey] = {"total_dollar":td,"total_indexed":ti,"fwd_dollar":fwd_d,
        "fwd_indexed":fwd_i,"spy_indexed":spy_i,"by_account":bad,
        "start_val":round(sv,0),"end_val":round(ev,0),"period_gl":round(pgl,0),"period_pct":round(ppct,2)}
    print(f"  Portfolio {hkey}: ${sv:,.0f} → ${ev:,.0f} ({ppct:+.1f}%)")

# ══ TREASURY YIELDS ═══════════════════════════════════════════════════════════
print("\nFetching yields...")
try:
    _yld_dl = yf.download(
        ["^TNX", "^IRX"],
        start=(end-timedelta(days=365*6)).strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        auto_adjust=True, progress=False,
    )["Close"]
    tnx = _yld_dl["^TNX"].dropna()
    irx = _yld_dl["^IRX"].dropna()
    spread_series=(tnx-irx).dropna(); current_spread=float(spread_series.iloc[-1])
    print(f"  Spread: {current_spread:+.3f}%")
except Exception as e:
    print(f"  Fallback: {e}"); spread_series=pd.Series(dtype=float); current_spread=0.64
current_zone = get_zone(current_spread)

# ══ OU PROJECTION ═════════════════════════════════════════════════════════════
OU_MU=1.5; OU_THETA=0.35; OU_SIGMA=0.80
def proj_ou(ls, ld, ed):
    dates=pd.bdate_range(start=ld+timedelta(days=1),end=ed)
    if dates.empty: return [],[],[]
    t=np.arange(1,len(dates)+1)/252
    c=OU_MU+(ls-OU_MU)*np.exp(-OU_THETA*t)
    var=(OU_SIGMA**2/(2*OU_THETA))*(1-np.exp(-2*OU_THETA*t))
    b=1.645*np.sqrt(np.maximum(var,0))
    fmt=lambda a:[(str(d.date()),round(float(v),4)) for d,v in zip(dates,a)]
    return fmt(c),fmt(c+b),fmt(c-b)

YC_H={"5Y":{"back":pd.DateOffset(years=5),"fwd":pd.DateOffset(years=5)},
      "1Y":{"back":pd.DateOffset(years=1),"fwd":pd.DateOffset(years=1)},
      "6M":{"back":pd.DateOffset(months=6),"fwd":pd.DateOffset(months=6)},
      "30D":{"back":pd.DateOffset(days=30),"fwd":pd.DateOffset(days=30)}}
yc_data={}
for hkey,hcfg in YC_H.items():
    if spread_series.empty:
        dates_fb=pd.bdate_range(end=today,periods=60)
        hp=[(str(d.date()),round(current_spread,3)) for d in dates_fb]
        pc,pu,pl=proj_ou(current_spread,today.to_pydatetime(),today+hcfg["fwd"])
        yc_data[hkey]={"hist":hp,"proj":pc,"upper":pu,"lower":pl}; continue
    hs=today-hcfg["back"]
    sl=spread_series.loc[(spread_series.index>=hs)&(spread_series.index<=today)]
    if len(sl)<2: sl=spread_series.tail(5)
    hp=[(str(d.date()),round(float(v),4)) for d,v in sl.items()]
    pc,pu,pl=proj_ou(current_spread,sl.index[-1].to_pydatetime(),today+hcfg["fwd"])
    yc_data[hkey]={"hist":hp,"proj":pc,"upper":pu,"lower":pl}

# ══ MARKET CHART DATA ═════════════════════════════════════════════════════════
def biz(s,e): return pd.bdate_range(start=s+timedelta(days=1),end=e)
def proj_cagr(lv,ld,ed,r):
    d=biz(ld,ed)
    return [] if d.empty else [(str(x.date()),round(float(lv*(1+r)**((i+1)/252)),2)) for i,x in enumerate(d)]
def proj_gbm(lv,ld,ed,r,v,seed):
    d=biz(ld,ed)
    if d.empty: return []
    rng=np.random.default_rng(seed=seed); dt=1/252
    sh=rng.normal((r-0.5*v**2)*dt,v*np.sqrt(dt),len(d))
    vs=lv*np.exp(np.cumsum(sh))
    return [(str(x.date()),round(float(y),2)) for x,y in zip(d,vs)]
def proj_analyst(lv,lp,tp,ld,ed):
    d=biz(ld,ed)
    if d.empty or not tp or not lp: return []
    vals=np.linspace(lv,lv*(tp/lp),len(d))
    return [(str(x.date()),round(float(y),2)) for x,y in zip(d,vals)]
def vbands(pp,v):
    u,l=[],[]
    for i,(d,val) in enumerate(pp):
        t=(i+1)/252; f=np.exp(1.645*v*np.sqrt(t))
        u.append((d,round(val*f,2))); l.append((d,round(val/f,2)))
    return u,l

hcfgs={"7D":{"back":pd.DateOffset(days=7),"fwd":pd.DateOffset(days=7),"kind":"gbm"},
       "30D":{"back":pd.DateOffset(days=30),"fwd":pd.DateOffset(days=30),"kind":"gbm"},
       "6M":{"back":pd.DateOffset(months=6),"fwd":pd.DateOffset(months=6),"kind":"gbm"},
       "YTD":{"back":None,"fwd":pd.DateOffset(months=6),"kind":"analyst"},
       "1Y":{"back":pd.DateOffset(years=1),"fwd":pd.DateOffset(years=1),"kind":"analyst"},
       "5Y":{"back":pd.DateOffset(years=5),"fwd":pd.DateOffset(years=5),"kind":"cagr"}}
all_data={}
for hkey,hcfg in hcfgs.items():
    hs=(pd.Timestamp(today.year,1,1) if hkey=="YTD" else today-hcfg["back"])
    pe=today+hcfg["fwd"]; kind=hcfg["kind"]; hd={}
    for key in ["SPY","MAG7","TSLA","BTC"]:
        rs=prices.get(key)
        if rs is None: continue
        sl=rs.loc[(rs.index>=hs)&(rs.index<=today)].dropna()
        if len(sl)<2: continue
        nm=sl/sl.iloc[0]*100
        hp=[(str(d.date()),round(float(v),2)) for d,v in nm.items()]
        lv=float(nm.iloc[-1]); lp=float(sl.iloc[-1]); ld=nm.index[-1].to_pydatetime()
        r=FWD_CAGR[key]; v=VOLS[key]; seed=abs(hash(f"{key}:{hkey}"))%(2**31)
        tgt=ANALYST_TARGETS.get(key)
        if kind=="cagr": pp=proj_cagr(lv,ld,pe,r)
        elif kind=="analyst" and tgt: pp=proj_analyst(lv,lp,tgt,ld,pe)
        else: pp=proj_gbm(lv,ld,pe,r,v,seed)
        e={"hist":hp,"proj":pp,"ret":round(lv-100,2),"base_price":round(float(sl.iloc[0]),2),
           "base_date":str(sl.index[0].date()),"last_price":round(lp,2)}
        yrs=(nm.index[-1]-nm.index[0]).days/365.25
        e["cagr"]=round((float(nm.iloc[-1]/nm.iloc[0])**(1/yrs)-1)*100,1) if yrs>0.1 else None
        if key in ("TSLA","BTC") and pp:
            u,l=vbands(pp,v); e["band_upper"]=u; e["band_lower"]=l
        hd[key]=e
    all_data[hkey]=hd

# ══ FAIR VALUE CARDS ══════════════════════════════════════════════════════════
print("\nFetching fair value data...")
FV_CFG=[("NVDA","NVDA","NVIDIA Corporation","stock"),("MSFT","MSFT","Microsoft Corporation","stock"),
        ("META","META","Meta Platforms Inc.","stock"),("GOOGL","GOOGL","Alphabet Inc.","stock"),
        ("AMZN","AMZN","Amazon.com Inc.","stock"),("AAPL","AAPL","Apple Inc.","stock"),
        ("TSLA","TSLA","Tesla Inc.","stock"),("SPYL.L","SPYL","SPDR S&P 500 UCITS ETF","etf"),
        ("BTC-USD","BTC","Bitcoin","crypto")]
def _fv(yt):
    try: return yf.Ticker(yt).info or {}
    except: return {}
def _fmt(v,dec=2):
    if v is None: return "—"
    if abs(v)>=1e12: return f"${v/1e12:.2f}T"
    if abs(v)>=1e9: return f"${v/1e9:.1f}B"
    if abs(v)>=1e6: return f"${v/1e6:.1f}M"
    return f"${v:,.{dec}f}" if dec>0 else f"${int(round(v)):,}"
def _badge(rec,up,disp):
    if disp=="SPYL": return "fv-dca","DCA BUY"
    if disp=="BTC": return "fv-strat","STRATEGIC HOLD"
    r=(rec or "").lower()
    if "strong" in r and "buy" in r: return "fv-buy","Strong Buy"
    if "buy" in r: return "fv-buy","Buy"
    if "hold" in r or "neutral" in r: return "fv-hold","Hold"
    if "sell" in r: return "fv-cau","Sell"
    if up is None: return "fv-hold","—"
    if up>=25: return "fv-buy","Strong Buy"
    if up>=10: return "fv-buy","Buy"
    if up>=-5: return "fv-hold","Hold"
    return "fv-cau","Sell"
def _dc(a):
    a=a.lower()
    if "aggressively" in a or "max" in a or "dca" in a: return "dep-green"
    if "systematic" in a or "slowly" in a or "small" in a: return "dep-amber"
    if "do not" in a or "overvalued" in a: return "dep-red"
    if "hold" in a: return "dep-amber"
    return "dep-neutral"

def _build_card(yt,disp,co,cls):
    info=_fv(yt); ov=FV_OVERLAY.get(disp,{}); price=info.get("regularMarketPrice") or info.get("currentPrice"); dec=0 if cls=="crypto" else 2
    if disp=="SPYL":
        target=ov.get("spyl_target",18.0);low_t=info.get("fiftyTwoWeekLow",14.80);high_t=ov.get("spyl_target_hi",18.50)
    elif disp=="BTC":
        target=ov.get("s2f_low",100000);low_t=info.get("fiftyTwoWeekLow",70000);high_t=ov.get("s2f_high",150000)
    else:
        target=info.get("targetMeanPrice");low_t=info.get("targetLowPrice") or info.get("fiftyTwoWeekLow");high_t=info.get("targetHighPrice") or info.get("fiftyTwoWeekHigh")
    up=((target/price-1)*100) if (price and target) else None
    fp=50.0
    if price and low_t and high_t and high_t>low_t: fp=max(0,min(100,(price-low_t)/(high_t-low_t)*100))
    bc="#2563eb" if (up or 0)>=10 else "#16a34a" if (up or 0)>=0 else "#dc2626"
    bcls,btxt=_badge(info.get("recommendationKey"),up,disp)
    if cls=="crypto": m=[("Market Cap",_fmt(info.get("marketCap"),0)),("52w High",_fmt(info.get("fiftyTwoWeekHigh"),0)),("52w Low",_fmt(info.get("fiftyTwoWeekLow"),0))]
    elif cls=="etf":
        dy=info.get("yield") or info.get("dividendYield")
        m=[("Div Yield",f"{dy*100:.2f}%" if dy else "—"),("52w High",_fmt(info.get("fiftyTwoWeekHigh"),2)),("52w Low",_fmt(info.get("fiftyTwoWeekLow"),2))]
    else:
        rg=info.get("revenueGrowth")
        m=[("Fwd P/E",f"{info['forwardPE']:.1f}x" if info.get("forwardPE") else "—"),("Rev Growth",f"{rg*100:+.1f}%" if rg is not None else "—"),("Analysts",str(info.get("numberOfAnalystOpinions") or "—"))]
    fpe=info.get("forwardPE"); rg=info.get("revenueGrowth"); hpe=ov.get("hist_pe")
    peg=round(fpe/(rg*100),2) if (fpe and rg and rg>0) else None
    peg_txt=f"{peg:.2f}x" if peg is not None else "—"
    pvh=""
    if fpe and hpe:
        diff=((fpe/hpe)-1)*100; pvh=f"{'↓' if diff<0 else '↑'}{abs(diff):.0f}% vs 5yr avg"
    da=ov.get("zone_action",{}).get(current_zone,"—"); dcc=_dc(da); fw=ov.get("weight","—")
    b1w=ov.get("b1_w",0.0); bkt=ov.get("bucket",0)
    if bkt==1:
        bf={"1":0.25,"2":0.40,"3":0.60,"4":0.65,"5":0.70}.get(str(current_zone),0.60)
        at=f"~${b1w*bf*50000:,.0f}/mo (Zone {current_zone})"
    elif bkt==2: at=f"~${0.20*50000:,.0f}/mo fixed"
    elif bkt==3: at="5% total portfolio"
    else: at="No new capital"
    dip_html=""
    if disp=="SPYL" and price:
        s52h=info.get("fiftyTwoWeekHigh") or ov.get("s52w_high",17.50)
        ddp=(price/s52h-1)*100 if s52h else 0; bf2=min(100,abs(ddp)/30*100)
        t1=10/30*100; t2=20/30*100
        tc="#dc2626" if abs(ddp)>=10 else "#d97706" if abs(ddp)>=7 else "#16a34a"
        tl="⚠ TRANCHE 1 TRIGGERED" if abs(ddp)>=10 else ("⚡ APPROACHING T1" if abs(ddp)>=7 else "✓ Within normal range")
        dip_html=f"""<div class="fv-dip"><div class="fv-dip-title">DIP TRIGGER MONITOR</div>
      <div class="fv-dip-vals"><span>Drawdown: <strong style="color:{tc}">{ddp:.1f}%</strong></span><span style="color:{tc};font-size:10px">{tl}</span></div>
      <div class="fv-dip-bar"><div class="fv-dip-fill" style="width:{bf2:.1f}%;background:{tc}"></div>
      <div class="fv-dip-mark" style="left:{t1:.1f}%"></div><div class="fv-dip-mark" style="left:{t2:.1f}%"></div></div>
      <div class="fv-dip-labels"><span>0%</span><span>-10% T1</span><span>-20% T2</span><span>-30% T3</span></div></div>"""
    btcn=""
    if disp=="BTC":
        s52h=info.get("fiftyTwoWeekHigh") or 125000
        cdd=(price/s52h-1)*100 if (price and s52h) else 0
        btcn=f"""<div class="fv-btcnote">
      <div class="fv-btcrow"><span>S2F Target</span><span>${ov.get('s2f_low',100000):,.0f}–${ov.get('s2f_high',150000):,.0f}</span></div>
      <div class="fv-btcrow"><span>Cycle drawdown</span><span style="color:#dc2626">{cdd:.1f}% from peak</span></div>
      <div class="fv-btcrow"><span>Strategy</span><span style="color:#d97706">Hold — never add</span></div></div>"""
    ut=f"{up:+.1f}%" if up is not None else "—"; uc="fv-pos" if (up or 0)>=0 else "fv-neg"
    tl2="S2F TARGET" if disp=="BTC" else ("WALL ST TARGET" if disp=="SPYL" else "TARGET")
    print(f"  {disp}: {_fmt(price,dec)} → {_fmt(target,dec)} ({ut})")
    return f"""<div class="fv-card" data-ticker="{disp}" data-price="{price or 0}" data-bucket="{bkt}" data-b1w="{b1w}">
      <div class="fv-head"><div><div class="fv-tk">{disp}</div><div class="fv-co">{co}</div></div><span class="fv-bdg {bcls}">{btxt}</span></div>
      <div class="fv-prow">
        <div class="fv-pblk"><div class="fv-plbl">PRICE</div><div class="fv-pval">{_fmt(price,dec) if price else '—'}</div></div>
        <div class="fv-pblk"><div class="fv-plbl">{tl2}</div><div class="fv-pval {uc}">{_fmt(target,dec) if target else '—'}</div></div>
        <div class="fv-pblk"><div class="fv-plbl">UPSIDE</div><div class="fv-pval {uc}">{ut}</div></div>
      </div>
      <div class="fv-bar"><div class="fv-blbl"><span>Low {_fmt(low_t,dec) if low_t else '—'}</span><span>Current</span><span>High {_fmt(high_t,dec) if high_t else '—'}</span></div>
        <div class="fv-bg"><div class="fv-fl" style="width:{fp:.0f}%;background:{bc}"></div></div></div>
      <div class="fv-mtx">
        <div class="fv-mbox"><div class="fv-mlbl">{m[0][0]}</div><div class="fv-mval">{m[0][1]}</div></div>
        <div class="fv-mbox"><div class="fv-mlbl">{m[1][0]}</div><div class="fv-mval">{m[1][1]}</div></div>
        <div class="fv-mbox"><div class="fv-mlbl">{m[2][0]}</div><div class="fv-mval">{m[2][1]}</div></div>
      </div>
      <div class="fv-overlay">
        <div class="fv-orow"><span class="fv-olbl">Zone {current_zone} Action</span><span class="fv-oval {dcc}">{da}</span></div>
        <div class="fv-orow"><span class="fv-olbl">PEG Ratio</span><span class="fv-oval">{peg_txt}{"  "+pvh if pvh else ""}</span></div>
        <div class="fv-orow"><span class="fv-olbl">Target Weight</span><span class="fv-oval">{fw}</span></div>
        <div class="fv-orow"><span class="fv-olbl">Monthly Alloc</span><span class="fv-oval">{at}</span></div>
      </div>{dip_html}{btcn}</div>"""

fv_html = "".join(_build_card(*c) for c in FV_CFG)

# ══ GAP-WEIGHTED ACTION TABLE ═════════════════════════════════════════════════
ibkr_pos = holdings_mtm.get("IBKR",{})
ibkr_cash_v = ibkr_pos.get("CASH",{}).get("value",0)
ibkr_eq_v = sum(v.get("value",0) for tk,v in ibkr_pos.items() if tk not in FIXED_KEYS and tk!="CASH")
ibkr_total_v = ibkr_eq_v + ibkr_cash_v + ibkr_pos.get("VOO",{}).get("value",0)
B1_FULL={"NVDA":0.25,"MSFT":0.20,"META":0.20,"AMZN":0.15,"GOOGL":0.15,"AAPL":0.10}
B1_ACT={k:v for k,v in B1_FULL.items() if k not in SKIP_IBKR}
tw=sum(B1_ACT.values()); B1_ADJ={k:v/tw for k,v in B1_ACT.items()}
B1_ZF={1:0.25,2:0.40,3:0.60,4:0.65,5:0.70}; b1f=B1_ZF.get(current_zone,0.60)
def ibkr_tgt(tk):
    if tk in B1_ADJ: return ibkr_total_v*b1f*B1_ADJ[tk]
    if tk=="SPYL": return ibkr_total_v*0.20
    if tk=="TSLA": return ibkr_total_v*0.05
    return 0
def ibkr_cur(tk): return ibkr_pos.get(tk,{}).get("value",0)

ar=[]
for yt,disp,co,cls in FV_CFG:
    ov=FV_OVERLAY.get(disp,{}); bkt=ov.get("bucket",0); b1w=ov.get("b1_w",0.0)
    act=ov.get("zone_action",{}).get(current_zone,"Hold"); dcc=_dc(act)
    if "aggressively" in act.lower() or "max" in act.lower(): urg="HIGH"
    elif "systematic" in act.lower() or "slowly" in act.lower() or "dca" in act.lower(): urg="MEDIUM"
    elif "do not" in act.lower() or "strategic hold" in act.lower(): urg="SKIP"
    else: urg="LOW"
    cv=ibkr_cur(disp); tv=ibkr_tgt(disp); gv=max(0,tv-cv)
    cs=disp in SKIP_IBKR or disp=="GOOG"
    if cs: urg="SKIP"; act="Citi handles — skip at IBKR"; dcc="dep-neutral"; gv=0
    ar.append({"ticker":disp,"bucket":bkt,"b1_w":B1_ADJ.get(disp,0),"action":act,"dep_cls":dcc,
               "urgency":urg,"cur_ibkr":round(cv,0),"tgt_ibkr":round(tv,0),"gap_ibkr":round(gv,0),"citi_skip":cs})
ar_json=json.dumps(ar,separators=(",",":"))

# ══ HOLDINGS HTML ════════════════════════════════════════════════════════════
def build_holdings():
    rows=[]
    for acct,positions in holdings_mtm.items():
        col=ACCT_COLORS.get(acct,"#64748b"); lbl=ACCT_LABELS.get(acct,acct)
        st=ACCT_STATUS.get(acct,""); at=account_totals.get(acct,0)
        sb=f'<span class="acct-status acct-{st.lower()}">{st}</span>'
        rows.append(f'<tr class="acct-hdr"><td colspan="7"><span style="color:{col};font-weight:700">{lbl}</span>{sb}<span class="acct-total">${at:,.0f}</span></td></tr>')
        for tk,d in positions.items():
            if tk in FIXED_KEYS:
                rows.append(f'<tr class="pos-row cash-row"><td>{tk}</td><td colspan="3" style="color:var(--mut)">Cash/Stable</td><td>${d.get("value",0):,.2f}</td><td>—</td><td>—</td></tr>')
            else:
                gl=d.get("gl",0); glp=d.get("gl_pct",0); gc="#16a34a" if gl>=0 else "#dc2626"; gs="+" if gl>=0 else ""
                rows.append(f'<tr class="pos-row"><td style="font-weight:600">{tk}</td><td>{d["shares"]:,.0f}</td><td>${d["avg_cost"]:,.2f}</td><td>${d["last_price"]:,.2f}</td><td>${d["value"]:,.0f}</td><td style="color:{gc}">{gs}${gl:,.0f}</td><td style="color:{gc}">{gs}{glp:.1f}%</td></tr>')
    return "\n".join(rows)
holdings_html=build_holdings()

# ══ PROGRESS BARS HTML ════════════════════════════════════════════════════════
def build_progress():
    bars=[]
    for yt,disp,co,cls in FV_CFG:
        if disp in ("BTC","GOOG","AAPL","GOOGL","ETH"): continue
        cv=ibkr_cur(disp); tv=ibkr_tgt(disp)
        if tv<=0: continue
        pct=min(100,cv/tv*100)
        if cv>tv*1.05: bc="#eab308"; st="OVER"; sc="#b45309"
        elif pct>=90: bc="#16a34a"; st="ON TARGET"; sc="#15803d"
        elif pct>=50: bc="#1d4ed8"; st=f"{pct:.0f}% of target"; sc="#1d4ed8"
        else: bc="#dc2626"; st=f"{pct:.0f}% — BUY"; sc="#b91c1c"
        gap=max(0,tv-cv)
        bars.append(f"""<div class="prog-row">
      <div class="prog-lbl"><span style="font-weight:700;font-size:12px">{disp}</span><span style="color:{sc};font-size:10px">{st}</span></div>
      <div class="prog-track"><div class="prog-fill" style="width:{pct:.1f}%;background:{bc}"></div></div>
      <div class="prog-vals"><span>${cv:,.0f}</span><span style="color:var(--mut)">/ ${tv:,.0f}</span><span style="color:{bc}">{'+'if gap==0 else '-'}${abs(gap):,.0f}</span></div></div>""")
    return "\n".join(bars)
progress_html=build_progress()

# ══ TIMESTAMP ═════════════════════════════════════════════════════════════════
nm=datetime.utcnow()+timedelta(hours=8)
nxt=(nm+timedelta(days=1)).replace(hour=14,minute=0,second=0,microsecond=0)
fetched_at=nm.strftime("%b %d, %Y %H:%M PHT"); next_refresh=nxt.strftime("%b %d, %Y 14:00 PHT")

# ══ TOTALS FOR DISPLAY ════════════════════════════════════════════════════════
total_gl=sum(d.get("gl",0) for ap in holdings_mtm.values() for tk,d in ap.items() if d.get("type")=="equity")
gtf=f"${grand_total:,.0f}"; tgls="+" if total_gl>=0 else ""; tglf=f"{tgls}${abs(total_gl):,.0f}"

# ══ PAYLOAD ═══════════════════════════════════════════════════════════════════
payload=json.dumps({"horizons":all_data,"portfolio":portfolio_history,
    "yc":{"horizons":yc_data,"current_spread":round(current_spread,4),"current_zone":current_zone,
          "ou_mu":OU_MU,"zone_boundaries":ZONE_BOUNDARIES},
    "zone_deploy":ZONE_DEPLOY,"zone_meta":{str(k):v for k,v in ZONE_META.items()},
    "action_rows":ar,"account_totals":account_totals,"account_colors":ACCT_COLORS,
    "account_labels":ACCT_LABELS,"grand_total":round(grand_total,0),"total_gl":round(total_gl,0),
    "fetched_at":fetched_at},separators=(",",":"))

print(f"\nGenerating index.html...")
zc=ZONE_META[current_zone]["color"]; zb=ZONE_META[current_zone]["bg"]
zl=ZONE_META[current_zone]["label"]; zd=ZONE_META[current_zone]["desc"]
zdep=ZONE_DEPLOY[current_zone]; sf=f"{current_spread:+.2f}%"
ibkr_tv=account_totals.get("IBKR",0)
citi_tv=sum(account_totals.get(a,0) for a in ["CITI_401K","CITI_ROTH","CITI_BROK"])

# renderPtfl is extracted as a raw string to avoid f-string brace escaping issues
_render_ptfl_js = r"""
function setPT(h){curPT=h;document.querySelectorAll('.ptfl-tab').forEach(b=>b.classList.toggle('on',b.textContent.trim()===h||b.textContent.trim()===h+' / '+h));renderPtfl();}
function setPM(m){pm=m;document.getElementById('pdollar').classList.toggle('on',m==='dollar');document.getElementById('pindex').classList.toggle('on',m==='indexed');renderPtfl();}
function setPL(v){pl=v;document.getElementById('pall').classList.toggle('on',v==='all');document.getElementById('ptotal').classList.toggle('on',v==='total');renderPtfl();}
function renderPtfl(){
  const pd=DATA.portfolio[curPT];if(!pd)return;
  if(ptI){ptI.destroy();ptI=null;}
  const isDollar=pm==='dollar';const tk=isDollar?'total_dollar':'total_indexed';const fk=isDollar?'fwd_dollar':'fwd_indexed';
  const sign=pd.period_pct>=0?'+':'';
  const gStr=isDollar?'$'+Math.abs(pd.period_gl).toLocaleString('en-US')+' ('+sign+pd.period_pct.toFixed(1)+'%)'
    :sign+pd.period_pct.toFixed(1)+'%';
  const gn=document.getElementById('ptflGainNote');gn.textContent=curPT+' gain: '+gStr;
  gn.style.color=pd.period_pct>=0?'var(--grn)':'var(--red)';
  const note5=curPT==='5Y'?' · assumes current positions held':curPT==='YTD'?' · from Jan 1, 2026':'';
  document.getElementById('ptflNote').textContent='Mark-to-market reconstruction · Dashed = projection'+note5;
  const ds=[];
  const td2=pd[tk].map(([dt,v])=>{return{x:new Date(dt+'T12:00:00'),y:v}});
  ds.push({label:'Total Portfolio',data:td2,borderColor:'#1a1814',backgroundColor:'transparent',borderWidth:2.5,pointRadius:0,tension:.12});
  if(pd[fk]&&pd[fk].length){const lh=pd[tk][pd[tk].length-1];
    ds.push({label:'Projection',data:[{x:new Date(lh[0]+'T12:00:00'),y:lh[1]},...pd[fk].map(([dt,v])=>{return{x:new Date(dt+'T12:00:00'),y:v}})],borderColor:'#1a1814',backgroundColor:'transparent',borderWidth:1.5,pointRadius:0,tension:.12,borderDash:[6,4]});}
  if(pl==='all'&&pd.by_account){Object.entries(pd.by_account).forEach(([a,pts])=>{
    const col=AC[a]||'#94a3b8',lbl=AL[a]||a;let data;
    if(isDollar) data=pts.map(([dt,v])=>{return{x:new Date(dt+'T12:00:00'),y:v}});
    else{const base=pts[0][1];data=pts.map(([dt,v])=>{return{x:new Date(dt+'T12:00:00'),y:base>0?Math.round(v/base*10000)/100:0}});}
    ds.push({label:lbl,data,borderColor:col,backgroundColor:'transparent',borderWidth:1.5,pointRadius:0,tension:.12,borderDash:[3,3]});
  });}
  if(!isDollar&&pd.spy_indexed) ds.push({label:'SPY Benchmark',data:pd.spy_indexed.map(([dt,v])=>{return{x:new Date(dt+'T12:00:00'),y:v}}),borderColor:'rgba(22,163,74,.5)',backgroundColor:'transparent',borderWidth:1.5,pointRadius:0,tension:.12,borderDash:[2,4]});
  const legs=[{l:'Total Portfolio',c:'#1a1814',d:false}];
  if(pl==='all') Object.entries(AC).forEach(([a,c])=>legs.push({l:AL[a],c,d:true}));
  if(!isDollar) legs.push({l:'SPY',c:'rgba(22,163,74,.5)',d:true});
  document.getElementById('ptflLegend').innerHTML=legs.map(x=>{const st=x.d?'background-image:repeating-linear-gradient(90deg,'+x.c+' 0,'+x.c+' 4px,transparent 4px,transparent 8px)':'background:'+x.c;return'<div class="ptfl-li"><div class="ptfl-ln" style="'+st+'"></div>'+x.l+'</div>';}).join('');
  const yT=isDollar?'Portfolio Value (USD)':'Index base=100';
  const yCb=isDollar?v=>'$'+Math.round(v/1000)+'K':v=>v.toFixed(0);
  const ptOpts={responsive:true,maintainAspectRatio:false,animation:{duration:250},
    interaction:{mode:'index',intersect:false},
    plugins:{legend:{display:false},tooltip:{backgroundColor:'rgba(255,255,255,.98)',
      borderColor:'#d1d5db',borderWidth:.5,
      titleFont:{size:9,family:'monospace'},bodyFont:{size:9,family:'monospace'},
      callbacks:{
        title(i){const d=i[0]&&i[0].raw&&i[0].raw.x;return d?d.toLocaleDateString('en',{month:'short',day:'numeric',year:'numeric'}):'' },
        label(i){if((i.dataset.label||'').startsWith('_'))return null;
          const v=i.raw.y,lbl=i.dataset.label;
          return isDollar?' '+lbl+': $'+Math.round(v).toLocaleString('en-US')
                        :' '+lbl+': '+(v!=null?v.toFixed(1):'');}
      }}},
    scales:{
      x:{type:'time',time:{tooltipFormat:'MMM d yyyy'},
         ticks:{color:'#9ca3af',font:{size:8,family:'monospace'},maxTicksLimit:9},grid:{color:'#f3f4f6'}},
      y:{ticks:{color:'#9ca3af',font:{size:8,family:'monospace'},callback:yCb,maxTicksLimit:9},
         grid:{color:'#f3f4f6'},title:{display:true,text:yT,color:'#9ca3af',font:{size:8,family:'monospace'}}}
    }};
  ptI=new Chart(document.getElementById('ptflChart').getContext('2d'),
    {type:'line',data:{datasets:ds},options:ptOpts,plugins:[todayPl('pt')]});
}
"""

HTML=f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Investment Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@700;800&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet"/>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{--bg:#f8f7f4;--surf:#fff;--bdr:#e2e0db;--bdr2:#ccc9c2;--txt:#1a1814;--mut:#7c7970;--dim:#f0efe9;--grn:#15803d;--red:#b91c1c;--spy:#16a34a;--mag:#1d4ed8;--tsl:#dc2626;--btc:#eab308;--zone:{zc}}}
html,body{{background:var(--bg);color:var(--txt);font-family:'DM Mono',monospace;font-size:13px;min-height:100vh}}
.page{{max-width:1280px;margin:0 auto;padding:32px 24px 64px}}
.hdr{{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:8px;flex-wrap:wrap;gap:12px;border-bottom:1.5px solid var(--txt);padding-bottom:14px}}
.hdr h1{{font-family:'Syne',sans-serif;font-size:28px;font-weight:800;letter-spacing:-1px}}
.hdr-sub{{font-size:9px;color:var(--mut);letter-spacing:.15em;text-transform:uppercase;margin-top:4px}}
.src{{font-size:9px;color:var(--mut);margin-bottom:24px;display:flex;align-items:center;gap:6px}}
.src-dot{{width:6px;height:6px;border-radius:50%;background:#22c55e;animation:pulse 2s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.4}}}}
.shd{{font-size:9px;letter-spacing:.18em;text-transform:uppercase;color:var(--mut);margin-bottom:14px;padding-bottom:6px;border-bottom:.5px solid var(--bdr);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px}}
.zone-banner{{background:{zb};border:1px solid {zc}33;border-radius:8px;padding:14px 18px;margin-bottom:20px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}}
.zone-pill{{background:{zc};color:#fff;font-family:'Syne',sans-serif;font-size:13px;font-weight:700;padding:5px 14px;border-radius:20px;white-space:nowrap}}
.zone-spread{{font-size:22px;font-family:'Syne',sans-serif;font-weight:700;color:{zc}}}
.zone-alloc-row{{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;width:100%}}
.zone-alloc-chip{{background:var(--surf);border:.5px solid var(--bdr);border-radius:4px;padding:4px 10px;font-size:10px;text-align:center}}
.zone-alloc-chip span{{display:block;font-size:16px;font-weight:600;line-height:1.2}}
.zone-alloc-chip small{{color:var(--mut)}}
.yc-tabs,.ptfl-tabs,.tabs{{display:flex;border-bottom:1px solid var(--bdr);margin-bottom:12px}}
.yc-tab,.ptfl-tab,.tab{{font-size:10px;padding:7px 16px;border:none;background:transparent;color:var(--mut);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;font-family:'DM Mono',monospace;letter-spacing:.04em}}
.yc-tab.on{{color:var(--txt);border-bottom-color:var(--zone)}}
.ptfl-tab.on,.tab.on{{color:var(--txt);border-bottom-color:var(--txt)}}
.yc-wrap,.ptfl-wrap{{position:relative;width:100%;height:260px}}
.chart-wrap{{position:relative;width:100%;height:400px}}
.yc-legend,.ptfl-legend,.legend{{display:flex;gap:14px;flex-wrap:wrap;margin-top:8px;font-size:9px;color:var(--mut)}}
.yc-li,.ptfl-li,.li{{display:flex;align-items:center;gap:5px}}
.yc-ln,.ptfl-ln,.ln{{width:18px;height:2px;flex-shrink:0}}
.section{{margin-bottom:32px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin-bottom:14px}}
.kpi{{background:var(--surf);border:.5px solid var(--bdr);border-radius:6px;padding:10px 14px}}
.kpi-lbl{{font-size:9px;color:var(--mut);letter-spacing:.08em;text-transform:uppercase;margin-bottom:3px}}
.kpi-val{{font-size:18px;font-weight:600;font-family:'Syne',sans-serif}}
.ctrls{{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:10px}}
.cl{{font-size:9px;color:var(--mut);letter-spacing:.06em}}
.tog{{font-size:10px;padding:4px 11px;border-radius:4px;border:.5px solid var(--bdr2);background:transparent;color:var(--mut);cursor:pointer;font-family:'DM Mono',monospace}}
.tog.on{{background:var(--txt);color:#fff;border-color:var(--txt)}}
.vsep{{width:1px;height:18px;background:var(--bdr);margin:0 4px}}
.cards{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin-bottom:12px}}
.card{{background:var(--surf);border-radius:6px;border:.5px solid var(--bdr);border-top:2px solid transparent;padding:11px 13px}}
.card-lbl{{font-size:9px;color:var(--mut);letter-spacing:.1em;margin-bottom:4px}}
.card-val{{font-size:20px;font-weight:500;margin-bottom:2px}}
.card-sub,.card-base{{font-size:9px;color:var(--mut)}}
.card-base{{opacity:.5;margin-top:2px}}
.pos{{color:var(--grn)}} .neg{{color:var(--red)}}
.note{{font-size:9px;color:var(--mut);opacity:.6;margin-bottom:6px;line-height:1.5}}
.outperf{{display:flex;gap:14px;flex-wrap:wrap;margin-top:8px;font-size:10px;color:var(--mut)}}
.cash-input-row{{display:flex;align-items:center;gap:12px;margin-bottom:14px;flex-wrap:wrap}}
.cash-label{{font-size:10px;color:var(--mut);white-space:nowrap}}
.cash-input{{font-family:'DM Mono',monospace;font-size:18px;font-weight:500;color:var(--txt);border:1.5px solid var(--zone);border-radius:6px;padding:7px 14px;width:180px;background:var(--surf);outline:none}}
.cash-input:focus{{border-color:var(--txt);box-shadow:0 0 0 3px rgba(0,0,0,.06)}}
.cash-hint{{font-size:9px;color:var(--mut)}}
.at{{width:100%;border-collapse:collapse;font-size:11px}}
.at th{{font-size:9px;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);padding:6px 8px;text-align:left;border-bottom:1px solid var(--bdr);white-space:nowrap}}
.at td{{padding:8px 8px;border-bottom:.5px solid var(--bdr);vertical-align:middle}}
.at tr:hover td{{background:var(--dim)}}
.at-tk{{font-family:'Syne',sans-serif;font-weight:700;font-size:13px}}
.at-bkt{{font-size:9px;color:var(--mut);margin-top:1px}}
.urgency-HIGH{{color:#fff;background:#dc2626;padding:2px 7px;border-radius:3px;font-size:9px;font-weight:600}}
.urgency-MEDIUM{{color:#92400e;background:#fef3c7;padding:2px 7px;border-radius:3px;font-size:9px}}
.urgency-LOW{{color:#1e40af;background:#dbeafe;padding:2px 7px;border-radius:3px;font-size:9px}}
.urgency-SKIP{{color:var(--mut);background:var(--dim);padding:2px 7px;border-radius:3px;font-size:9px}}
.residual{{background:var(--dim);border-top:1px solid var(--bdr);font-size:11px;padding:8px 10px;display:flex;justify-content:space-between;border-radius:0 0 6px 6px}}
.dep-green{{color:#15803d;font-weight:600}} .dep-amber{{color:#b45309;font-weight:500}} .dep-red{{color:#b91c1c;font-weight:500}} .dep-neutral{{color:var(--mut)}}
.ht{{width:100%;border-collapse:collapse;font-size:11px}}
.ht th{{font-size:9px;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);padding:6px 10px;text-align:right;border-bottom:1px solid var(--bdr)}}
.ht th:first-child{{text-align:left}}
.ht td{{padding:7px 10px;border-bottom:.5px solid rgba(0,0,0,.04);text-align:right}}
.ht td:first-child{{text-align:left}}
.acct-hdr td{{background:var(--dim);font-size:10px;padding:6px 10px;border-bottom:1px solid var(--bdr)}}
.acct-total{{float:right;font-weight:600}}
.acct-status{{font-size:8px;padding:1px 6px;border-radius:3px;margin-left:6px;font-weight:600}}
.acct-active{{background:#dbeafe;color:#1e40af}} .acct-frozen{{background:#f3e8ff;color:#6b21a8}} .acct-hold{{background:#fef3c7;color:#92400e}}
.pos-row:hover td{{background:var(--dim)}} .cash-row td{{color:var(--mut);font-style:italic}}
.prog-row{{display:grid;grid-template-columns:110px 1fr 180px;gap:10px;align-items:center;margin-bottom:10px}}
.prog-lbl{{display:flex;flex-direction:column;gap:2px}}
.prog-track{{height:8px;background:var(--dim);border-radius:4px;overflow:hidden}}
.prog-fill{{height:100%;border-radius:4px;transition:width .4s}}
.prog-vals{{display:flex;gap:8px;justify-content:flex-end;font-size:10px}}
.ptfl-note{{font-size:9px;color:var(--mut);opacity:.7;margin-bottom:6px}}
.fv-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}}
.fv-card{{background:var(--surf);border:.5px solid var(--bdr);border-radius:8px;padding:14px 16px}}
.fv-head{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px}}
.fv-tk{{font-family:'Syne',sans-serif;font-size:18px;font-weight:800}}
.fv-co{{font-size:10px;color:var(--mut);margin-top:1px}}
.fv-bdg{{font-size:9px;padding:3px 8px;border-radius:3px;font-weight:600;letter-spacing:.04em;white-space:nowrap}}
.fv-buy{{background:#dcfce7;color:#166534}} .fv-hold{{background:#fef3c7;color:#92400e}} .fv-cau{{background:#fee2e2;color:#991b1b}}
.fv-dca{{background:#dbeafe;color:#1e40af}} .fv-strat{{background:#f3e8ff;color:#6b21a8}}
.fv-prow{{display:flex;gap:12px;margin-bottom:10px}}
.fv-pblk{{flex:1}}
.fv-plbl{{font-size:8px;color:var(--mut);letter-spacing:.1em;text-transform:uppercase;margin-bottom:2px}}
.fv-pval{{font-size:16px;font-weight:600;font-family:'Syne',sans-serif}}
.fv-pos{{color:var(--grn)}} .fv-neg{{color:var(--red)}}
.fv-bar{{margin:6px 0}}
.fv-blbl{{display:flex;justify-content:space-between;font-size:8px;color:var(--mut);margin-bottom:3px}}
.fv-bg{{height:4px;background:var(--dim);border-radius:2px;overflow:hidden}}
.fv-fl{{height:100%;border-radius:2px}}
.fv-mtx{{display:flex;gap:6px;margin-top:8px}}
.fv-mbox{{flex:1;background:var(--dim);border-radius:4px;padding:5px 8px;text-align:center}}
.fv-mlbl{{font-size:8px;color:var(--mut);margin-bottom:1px}} .fv-mval{{font-size:11px;font-weight:600}}
.fv-overlay{{margin-top:10px;padding-top:8px;border-top:.5px solid var(--bdr)}}
.fv-orow{{display:flex;justify-content:space-between;align-items:center;padding:3px 0;font-size:10px}}
.fv-olbl{{color:var(--mut);flex-shrink:0;margin-right:8px}} .fv-oval{{text-align:right}}
.fv-disc{{font-size:8px;color:var(--mut);margin-top:14px;padding-top:8px;border-top:.5px solid var(--bdr);line-height:1.6}}
.fv-dip{{margin-top:10px;padding:8px 10px;background:var(--dim);border-radius:5px}}
.fv-dip-title{{font-size:8px;letter-spacing:.12em;text-transform:uppercase;color:var(--mut);margin-bottom:5px}}
.fv-dip-vals{{display:flex;justify-content:space-between;font-size:10px;margin-bottom:5px}}
.fv-dip-bar{{height:5px;background:#e5e7eb;border-radius:3px;position:relative;overflow:visible;margin-bottom:2px}}
.fv-dip-fill{{height:100%;border-radius:3px}} .fv-dip-mark{{position:absolute;top:-3px;width:1.5px;height:11px;background:#94a3b8}}
.fv-dip-labels{{display:flex;justify-content:space-between;font-size:8px;color:var(--mut)}}
.fv-btcnote{{margin-top:10px;padding:8px 10px;background:var(--dim);border-radius:5px}}
.fv-btcrow{{display:flex;justify-content:space-between;font-size:10px;padding:2px 0}}
hr{{border:none;border-top:.5px solid var(--bdr);margin:24px 0 12px}}
.footer{{font-size:9px;color:var(--mut);line-height:2;text-align:center}}
@media(max-width:700px){{.cards{{grid-template-columns:repeat(2,1fr)}}.prog-row{{grid-template-columns:80px 1fr}}.prog-vals{{display:none}}.at th:nth-child(n+7),.at td:nth-child(n+7){{display:none}}.ht th:nth-child(n+5),.ht td:nth-child(n+5){{display:none}}}}
</style></head><body>
<div class="page">

<div class="hdr">
  <div><h1>Investment Dashboard</h1><div class="hdr-sub">AI Alpha Engine · Passive Anchor · Asymmetric Bets</div></div>
  <div style="text-align:right">
    <div style="font-family:'Syne',sans-serif;font-size:22px;font-weight:800">{gtf}</div>
    <div style="font-size:11px;color:var(--grn);font-weight:600">{tglf} unrealized gain</div>
    <div style="font-size:9px;color:var(--mut);margin-top:2px">{zl} · {zd}</div>
  </div>
</div>
<div class="src"><span class="src-dot"></span><span>Refreshed: {fetched_at} · Next: {next_refresh} · Yahoo Finance via yfinance</span></div>

<div class="zone-banner">
  <div><div style="font-size:9px;color:{zc};letter-spacing:.12em;text-transform:uppercase;margin-bottom:3px">10yr − 3mo Treasury Spread</div><div class="zone-spread">{sf}</div></div>
  <div class="zone-pill">{zl}</div>
  <div><div style="font-size:9px;color:var(--mut)">OU mean reversion target</div><div style="font-size:16px;font-weight:600;color:var(--mut)">+{OU_MU:.1f}% long-run</div></div>
  <div class="zone-alloc-row">
    <div class="zone-alloc-chip"><span>{zdep['B1']}</span><small>Bucket 1</small></div>
    <div class="zone-alloc-chip"><span>{zdep['SPYL']}</span><small>SPYL</small></div>
    <div class="zone-alloc-chip"><span>{zdep['B3']}</span><small>Bucket 3</small></div>
    <div class="zone-alloc-chip"><span>{zdep['Dry']}</span><small>Dry Powder</small></div>
    <div class="zone-alloc-chip"><span>{zdep['PHP']}</span><small>PHP Cash</small></div>
  </div>
</div>

<div class="section"><div class="shd"><span>MACRO OVERLAY — YIELD CURVE</span><span>Boundaries: 0% · 0.5% · 1.21% · 2.0%</span></div>
  <div class="yc-tabs">
    <button class="yc-tab on" onclick="setYCTab('5Y')">5Y / 5Y</button>
    <button class="yc-tab" onclick="setYCTab('1Y')">1Y / 1Y</button>
    <button class="yc-tab" onclick="setYCTab('6M')">6M / 6M</button>
    <button class="yc-tab" onclick="setYCTab('30D')">30D / 30D</button>
  </div>
  <div class="yc-wrap"><canvas id="ycChart"></canvas></div>
  <div class="yc-legend">
    <div class="yc-li"><div class="yc-ln" style="background:var(--zone)"></div>Spread</div>
    <div class="yc-li"><div style="width:18px;height:2px;background-image:repeating-linear-gradient(90deg,var(--zone) 0,var(--zone) 4px,transparent 4px,transparent 8px)"></div>OU projection → +1.5%</div>
  </div>
</div>

<div class="section"><div class="shd"><span>MONDAY ACTION TABLE</span><span style="color:var(--zone)">Zone {current_zone} · Gap-weighted</span></div>
  <div class="cash-input-row">
    <span class="cash-label">Weekly deployment (USD):</span>
    <input class="cash-input" type="number" id="cashInput" value="50000" min="0" step="1000" oninput="renderTable()"/>
    <span class="cash-hint">Edit to match IBKR settled cash → table recalculates instantly</span>
  </div>
  <table class="at" id="actionTable">
    <thead><tr>
      <th>Ticker</th><th>Zone Action</th><th>Urgency</th><th>Price</th>
      <th>IBKR Now</th><th>Target</th><th>Gap</th><th>This Week</th><th>Shares</th><th>Limit</th>
    </tr></thead>
    <tbody id="actionBody"></tbody>
  </table>
  <div class="residual" id="residualRow"><span>Residual → dry powder / PHP buffer</span><span id="residualAmt">—</span></div>
</div>

<div class="section"><div class="shd"><span>TOTAL PORTFOLIO GROWTH</span><span id="ptflGainNote" style="font-weight:600"></span></div>
  <div class="kpis">
    <div class="kpi"><div class="kpi-lbl">Total Portfolio</div><div class="kpi-val">{gtf}</div></div>
    <div class="kpi"><div class="kpi-lbl">Unrealized Gain</div><div class="kpi-val" style="color:var(--grn)">{tglf}</div></div>
    <div class="kpi"><div class="kpi-lbl">IBKR (Active)</div><div class="kpi-val" style="color:#1d4ed8">${ibkr_tv:,.0f}</div></div>
    <div class="kpi"><div class="kpi-lbl">Citi (Frozen)</div><div class="kpi-val" style="color:#9333ea">${citi_tv:,.0f}</div></div>
  </div>
  <div class="ctrls">
    <span class="cl">View</span>
    <button class="tog on" id="pdollar" onclick="setPM('dollar')">$ Dollar</button>
    <button class="tog" id="pindex" onclick="setPM('indexed')">Indexed</button>
    <div class="vsep"></div>
    <span class="cl">Lines</span>
    <button class="tog on" id="pall" onclick="setPL('all')">All accounts</button>
    <button class="tog" id="ptotal" onclick="setPL('total')">Total only</button>
  </div>
  <div class="ptfl-tabs">
    <button class="ptfl-tab on" onclick="setPT('7D')">7D / 7D</button>
    <button class="ptfl-tab" onclick="setPT('30D')">30D / 30D</button>
    <button class="ptfl-tab" onclick="setPT('6M')">6M / 6M</button>
    <button class="ptfl-tab" onclick="setPT('YTD')">YTD</button>
    <button class="ptfl-tab" onclick="setPT('1Y')">1Y / 1Y</button>
    <button class="ptfl-tab" onclick="setPT('5Y')">5Y / 5Y</button>
  </div>
  <div class="ptfl-note" id="ptflNote"></div>
  <div class="ptfl-wrap"><canvas id="ptflChart"></canvas></div>
  <div class="ptfl-legend" id="ptflLegend"></div>
</div>

<div class="section"><div class="shd"><span>HOLDINGS SNAPSHOT</span><span>Mark-to-market · Citi frozen · IBKR active</span></div>
  <table class="ht"><thead><tr>
    <th>Security</th><th style="text-align:right">Shares</th><th style="text-align:right">Avg Cost</th>
    <th style="text-align:right">Last Price</th><th style="text-align:right">Market Value</th>
    <th style="text-align:right">Unreal G/L</th><th style="text-align:right">G/L %</th>
  </tr></thead><tbody>{holdings_html}</tbody></table>
</div>

<div class="section"><div class="shd"><span>IBKR DEPLOYMENT GAP TRACKER</span><span>Current vs target · Gap drives action table</span></div>
  {progress_html}
</div>

<div class="section"><div class="shd"><span>MARKET PERFORMANCE</span></div>
  <div class="ctrls">
    <span class="cl">Scale</span>
    <button class="tog on" id="bl" onclick="setScale('linear')">Linear</button>
    <button class="tog" id="bg" onclick="setScale('log')">Log</button>
    <div class="vsep"></div>
    <span class="cl">Vol bands</span>
    <button class="tog on" id="bbon" onclick="setBands(true)">Show</button>
    <button class="tog" id="bboff" onclick="setBands(false)">Hide</button>
  </div>
  <div class="tabs">
    <button class="tab on" onclick="setTab('7D')">7D / 7D</button>
    <button class="tab" onclick="setTab('30D')">30D / 30D</button>
    <button class="tab" onclick="setTab('6M')">6M / 6M</button>
    <button class="tab" onclick="setTab('YTD')">YTD</button>
    <button class="tab" onclick="setTab('1Y')">1Y / 1Y</button>
    <button class="tab" onclick="setTab('5Y')">5Y / 5Y</button>
  </div>
  <div class="cards" id="cards"></div>
  <div class="legend">
    <span class="li"><span class="ln" style="background:var(--spy)"></span>SPY</span>
    <span class="li"><span class="ln" style="background:var(--mag)"></span>Mag7</span>
    <span class="li"><span class="ln" style="background:var(--tsl)"></span>Tesla</span>
    <span class="li"><span class="ln" style="background:var(--btc)"></span>Bitcoin</span>
  </div>
  <div class="note" id="note"></div>
  <div class="chart-wrap"><canvas id="chart"></canvas></div>
  <div class="outperf" id="outperf"></div>
</div>

<div class="section"><div class="shd"><span>FAIR VALUE ASSESSMENT</span><span>Zone {current_zone} actions · Live yfinance</span></div>
  <div class="fv-grid">{fv_html}</div>
  <div class="fv-disc">Live yfinance · Analyst consensus · SPYL: Wall St 2026 S&P implied · BTC: S2F model · PEG = Fwd P/E ÷ Rev growth · Not investment advice</div>
</div>

<hr/>
<div class="footer">
  Investment Dashboard · yfinance · MAG7: MSFT 25%/NVDA 25%/GOOGL 20%/META 15%/AMZN 10%/AAPL 5%<br>
  Portfolio: mark-to-market reconstruction · Yield curve: OU μ={OU_MU}% · Not financial advice<br>
  <span style="font-family:'DM Mono',monospace;font-size:11px;color:var(--zone);font-weight:600;letter-spacing:.05em">
    v{{SCRIPT_VERSION}} &nbsp;·&nbsp; {{SCRIPT_DATE}}
  </span>
</div>
</div>

<script>
const DATA={payload};
const AC={json.dumps(ACCT_COLORS)};const AL={json.dumps(ACCT_LABELS)};
const COLORS={{SPY:'#16a34a',MAG7:'#1d4ed8',TSLA:'#dc2626',BTC:'#eab308'}};
const FWD={{SPY:8,MAG7:11,TSLA:15,BTC:20}};
const LONG_H=new Set(['5Y']);
const LABELS={{SPY:'SPY · BETA',MAG7:'MAG7 · ALPHA',TSLA:'TESLA · BET',BTC:'BITCOIN · BET'}};
const NAMES={{SPY:'SPY (Beta)',MAG7:'Mag7 Alpha',TSLA:'Tesla',BTC:'Bitcoin'}};
const ZC='{zc}';
let curTab='7D',curYCTab='5Y',curPT='7D',useLog=false,showBands=true,pm='dollar',pl='all';
let cI=null,ycI=null,ptI=null;
const todayX=new Date();

function todayPl(id){{return{{id,afterDraw(c){{const xs=c.scales.x;if(!xs)return;const xp=xs.getPixelForValue(todayX);if(!xp||xp<xs.left||xp>xs.right)return;c.ctx.save();c.ctx.strokeStyle='rgba(75,85,99,.35)';c.ctx.lineWidth=1;c.ctx.setLineDash([4,4]);c.ctx.beginPath();c.ctx.moveTo(xp,c.chartArea.top);c.ctx.lineTo(xp,c.chartArea.bottom);c.ctx.stroke();c.ctx.restore();}}}}}}

// YIELD CURVE
function setYCTab(h){{curYCTab=h;document.querySelectorAll('.yc-tab').forEach(b=>b.classList.toggle('on',b.textContent.trim().startsWith(h)));renderYC();}}
function renderYC(){{
  const yd=DATA.yc.horizons[curYCTab];if(!yd)return;
  if(ycI){{ycI.destroy();ycI=null;}}
  const zbPl={{id:'zb',beforeDraw(c){{const xs=c.scales.x,ys=c.scales.y;if(!xs||!ys)return;const ctx=c.ctx,ca=c.chartArea;ctx.save();
    [{{lo:-5,hi:0,bg:'rgba(220,38,38,.10)'}},{{lo:0,hi:.5,bg:'rgba(234,88,12,.07)'}},{{lo:.5,hi:1.21,bg:'rgba(217,119,6,.04)'}},{{lo:1.21,hi:2,bg:'rgba(22,163,74,.07)'}},{{lo:2,hi:5,bg:'rgba(21,128,61,.09)'}}].forEach(b=>{{const y1=Math.min(ys.getPixelForValue(b.hi),ca.bottom),y2=Math.max(ys.getPixelForValue(b.lo),ca.top);if(y2>ca.bottom||y1<ca.top)return;ctx.fillStyle=b.bg;ctx.fillRect(ca.left,Math.min(y1,y2),ca.right-ca.left,Math.abs(y2-y1));}});
    const y0=ys.getPixelForValue(0);if(y0>=ca.top&&y0<=ca.bottom){{ctx.strokeStyle='rgba(220,38,38,.5)';ctx.lineWidth=1;ctx.setLineDash([3,3]);ctx.beginPath();ctx.moveTo(ca.left,y0);ctx.lineTo(ca.right,y0);ctx.stroke();}}ctx.restore();}}}};
  const ds=[];
  ds.push({{label:'Spread',data:yd.hist.map(([dt,v])=>{{return{{x:new Date(dt+'T12:00:00'),y:v}}}}),borderColor:ZC,backgroundColor:'transparent',borderWidth:2,pointRadius:0,tension:.15,order:2}});
  if(yd.proj&&yd.proj.length){{const lh=yd.hist[yd.hist.length-1];
    ds.push({{label:'OU Proj',data:[{{x:new Date(lh[0]+'T12:00:00'),y:lh[1]}},...yd.proj.map(([dt,v])=>{{return{{x:new Date(dt+'T12:00:00'),y:v}}}})],borderColor:ZC,backgroundColor:'transparent',borderWidth:1.5,pointRadius:0,tension:.2,borderDash:[6,4],order:1}});
    if(yd.upper&&yd.lower){{const su=[{{x:new Date(lh[0]+'T12:00:00'),y:lh[1]}},...yd.upper.map(([dt,v])=>{{return{{x:new Date(dt+'T12:00:00'),y:v}}}})] ,sl=[{{x:new Date(lh[0]+'T12:00:00'),y:lh[1]}},...yd.lower.map(([dt,v])=>{{return{{x:new Date(dt+'T12:00:00'),y:v}}}})] ;
      ds.push({{label:'_u',data:su,borderColor:'transparent',backgroundColor:'rgba(100,100,100,.08)',fill:'+1',borderWidth:0,pointRadius:0,order:3}});
      ds.push({{label:'_l',data:sl,borderColor:'transparent',backgroundColor:'rgba(100,100,100,.08)',fill:false,borderWidth:0,pointRadius:0,order:3}});}}}}
  const ad=[...yd.hist.map(([dt])=>dt),...(yd.proj||[]).map(([dt])=>dt)];
  if(ad.length>1) ds.push({{label:'+1.5%',data:[{{x:new Date(ad[0]+'T12:00:00'),y:1.5}},{{x:new Date(ad[ad.length-1]+'T12:00:00'),y:1.5}}],borderColor:'rgba(21,128,61,.45)',backgroundColor:'transparent',borderWidth:1,pointRadius:0,borderDash:[2,6],order:4}});
  ycI=new Chart(document.getElementById('ycChart').getContext('2d'),{{type:'line',data:{{datasets:ds}},options:{{responsive:true,maintainAspectRatio:false,animation:{{duration:200}},interaction:{{mode:'index',intersect:false}},plugins:{{legend:{{display:false}},tooltip:{{backgroundColor:'rgba(255,255,255,.97)',borderColor:'#d1d5db',borderWidth:.5,titleFont:{{size:9,family:'monospace'}},bodyFont:{{size:9,family:'monospace'}},callbacks:{{title(i){{const d=i[0]?.raw?.x;return d?d.toLocaleDateString('en',{{month:'short',day:'numeric',year:'numeric'}}):''}},label(i){{if((i.dataset.label||'').startsWith('_'))return null;return` ${{i.dataset.label}}: ${{i.raw.y?.toFixed(3)}}%`}}}}}}}},scales:{{x:{{type:'time',time:{{tooltipFormat:'MMM d yyyy'}},ticks:{{color:'#9ca3af',font:{{size:8,family:'monospace'}},maxTicksLimit:8}},grid:{{color:'#f3f4f6'}}}},y:{{ticks:{{color:'#9ca3af',font:{{size:8,family:'monospace'}},callback:v=>v.toFixed(2)+'%',maxTicksLimit:8}},grid:{{color:'#f3f4f6'}},title:{{display:true,text:'Spread %',color:'#9ca3af',font:{{size:8,family:'monospace'}}}}}}}}}},plugins:[zbPl,todayPl('yt')]}});
}}

// ACTION TABLE
const AR={ar_json};
const B1ZF={{"1":0.25,"2":0.40,"3":0.60,"4":0.65,"5":0.70}};
const CZ="{current_zone}";const B1F=B1ZF[CZ]||0.60;const SF=0.20;
function getLivePrices(){{const p={{}};document.querySelectorAll('.fv-card').forEach(c=>{{const tk=c.dataset.ticker,pr=parseFloat(c.dataset.price);if(tk&&pr)p[tk]=pr;}});return p;}}
function renderTable(){{
  const cash=parseFloat(document.getElementById('cashInput').value)||0;
  const prices=getLivePrices();const tbody=document.getElementById('actionBody');let deployed=0,html='';
  const b1rows=AR.filter(r=>r.bucket===1&&r.urgency!=='SKIP'&&r.gap_ibkr>0);
  const tg=b1rows.reduce((s,r)=>s+r.gap_ibkr,0);const b1c=cash*B1F;const sc=cash*SF;
  AR.forEach(r=>{{
    const price=prices[r.ticker]||0;let alloc=0;
    if(r.bucket===1&&r.urgency!=='SKIP') alloc=b1c*(tg>0?r.gap_ibkr/tg:r.b1_w);
    else if(r.bucket===2&&r.urgency!=='SKIP') alloc=sc;
    else if(r.bucket===3&&r.urgency!=='SKIP') alloc=cash*0.05;
    const skip=r.urgency==='SKIP'||r.bucket===0;if(!skip)deployed+=alloc;
    const shares=(price>0&&alloc>0&&!skip)?Math.floor(alloc/price):0;
    const limit=(price>0)?(price*1.003).toFixed(price<1000?2:0):'—';
    const fD=v=>'$'+Math.round(v).toLocaleString('en-US');
    const aF=alloc>0&&!skip?fD(alloc):'—';const shF=shares>0?shares:(skip?'—':'<1');const lF=shares>0&&!skip?'$'+limit:'—';
    const rs=skip?'opacity:.40':'';
    const gC=r.gap_ibkr>0?'var(--red)':r.gap_ibkr<0?'#b45309':'var(--mut)';
    const gF=r.gap_ibkr>0?fD(r.gap_ibkr):(r.gap_ibkr<0?'OVER':'✓');
    const bL=r.bucket===1?'B1':r.bucket===2?'B2':r.bucket===3?'B3':'—';
    html+=`<tr style="${{rs}}"><td><div class="at-tk">${{r.ticker}}</div><div class="at-bkt">${{bL}}</div></td>
      <td><span class="dep-${{r.dep_cls.split('-')[1]}}" style="font-size:10px">${{r.action}}</span></td>
      <td><span class="urgency-${{r.urgency}}">${{r.urgency}}</span></td>
      <td style="font-family:'Syne',sans-serif;font-weight:700">${{price>0?'$'+price.toLocaleString('en',{{minimumFractionDigits:price<1000?2:0}}):'—'}}</td>
      <td>${{r.cur_ibkr>0?fD(r.cur_ibkr):'—'}}</td>
      <td>${{r.tgt_ibkr>0?fD(r.tgt_ibkr):'—'}}</td>
      <td style="color:${{gC}};font-weight:600">${{gF}}</td>
      <td style="color:${{skip?'var(--mut)':'var(--txt)}}">${{aF}}</td>
      <td>${{shF}}</td><td style="color:var(--mut)">${{lF}}</td></tr>`;
  }});
  tbody.innerHTML=html;
  document.getElementById('residualAmt').textContent='$'+Math.round(cash-deployed).toLocaleString('en-US')+' → dry powder';
}}

// PORTFOLIO CHART
{_render_ptfl_js}
// MARKET CHART
function setTab(h){{curTab=h;document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('on',b.textContent.trim()===h||b.textContent.trim()===h+' / '+h));render();}}
function setScale(s){{useLog=s==='log';document.getElementById('bl').classList.toggle('on',!useLog);document.getElementById('bg').classList.toggle('on',useLog);render();}}
function setBands(v){{showBands=v;document.getElementById('bbon').classList.toggle('on',v);document.getElementById('bboff').classList.toggle('on',!v);render();}}
function render(){{
  const hd=DATA.horizons[curTab];if(!hd)return;
  const keys=['SPY','MAG7','TSLA','BTC'];
  document.getElementById('cards').innerHTML=keys.map(k=>{{const d=hd[k],col=COLORS[k];
    if(!d)return`<div class="card" style="border-top-color:${{col}}"><div class="card-lbl">${{LABELS[k]}}</div><div class="card-val" style="color:var(--mut)">—</div></div>`;
    const vc=d.ret>=0?'pos':'neg',sign=d.ret>=0?'+':'';
    return`<div class="card" style="border-top-color:${{col}}"><div class="card-lbl">${{LABELS[k]}}</div><div class="card-val ${{vc}}">${{sign}}${{d.ret.toFixed(1)}}%</div><div class="card-sub">CAGR ${{d.cagr!=null?d.cagr+'%':'—'}} · Fwd ${{FWD[k]}}%</div><div class="card-base">Base $${{d.base_price}} · ${{d.base_date}}</div></div>`;
  }}).join('');
  const spy=hd['SPY'];
  if(spy) document.getElementById('outperf').innerHTML=['MAG7','TSLA','BTC'].map(k=>{{const d=hd[k];if(!d)return'';const a=d.ret-spy.ret,col=a>=0?'var(--grn)':'var(--red)',sign=a>=0?'+':'';return`<span class="op">${{{{MAG7:'Mag7',TSLA:'Tesla',BTC:'Bitcoin'}}[k]}}: <span style="color:${{col}}">${{sign}}${{a.toFixed(1)}}pts vs SPY</span></span>`;}}).join('');
  const isL=LONG_H.has(curTab);
  document.getElementById('note').textContent=`Projection: ${{isL?'CAGR':curTab==='1Y'||curTab==='YTD'?'Analyst target':'GBM'}} · Dashed = forward · 90% bands on TSLA & BTC`;
  if(cI){{cI.destroy();cI=null;}}const ds=[];
  keys.forEach(k=>{{const d=hd[k];if(!d)return;const col=COLORS[k],nm=NAMES[k];
    ds.push({{label:nm,data:d.hist.map(([dt,v])=>{{return{{x:new Date(dt+'T12:00:00'),y:v}}}}),borderColor:col,backgroundColor:'transparent',borderWidth:2.5,pointRadius:0,tension:.12}});
    if(d.proj&&d.proj.length){{const lh=d.hist[d.hist.length-1];ds.push({{label:nm+' →',data:[{{x:new Date(lh[0]+'T12:00:00'),y:lh[1]}},...d.proj.map(([dt,v])=>{{return{{x:new Date(dt+'T12:00:00'),y:v}}}})],borderColor:col,backgroundColor:'transparent',borderWidth:1.8,pointRadius:0,tension:.12,borderDash:[6,4]}});}}
    if(showBands&&d.band_upper&&d.band_lower){{const hex=col.replace('#',''),r=parseInt(hex.slice(0,2),16),g=parseInt(hex.slice(2,4),16),b=parseInt(hex.slice(4,6),16);const fc=`rgba(${{r}},${{g}},${{b}},0.10)`;const lh=d.hist[d.hist.length-1];
      const su=[{{x:new Date(lh[0]+'T12:00:00'),y:lh[1]}},...d.band_upper.map(([dt,v])=>{{return{{x:new Date(dt+'T12:00:00'),y:v}}}})] ,sl=[{{x:new Date(lh[0]+'T12:00:00'),y:lh[1]}},...d.band_lower.map(([dt,v])=>{{return{{x:new Date(dt+'T12:00:00'),y:v}}}})] ;
      ds.push({{label:`_${{k}}_u`,data:su,borderColor:'transparent',backgroundColor:fc,fill:'+1',borderWidth:0,pointRadius:0,tension:.12}});
      ds.push({{label:`_${{k}}_l`,data:sl,borderColor:'transparent',backgroundColor:fc,fill:false,borderWidth:0,pointRadius:0,tension:.12}});}}
  }});
  cI=new Chart(document.getElementById('chart').getContext('2d'),{{type:'line',data:{{datasets:ds}},options:{{responsive:true,maintainAspectRatio:false,animation:{{duration:250}},interaction:{{mode:'index',intersect:false}},plugins:{{legend:{{display:false}},tooltip:{{backgroundColor:'rgba(255,255,255,.98)',borderColor:'#d1d5db',borderWidth:.5,titleFont:{{size:9,family:'monospace'}},bodyFont:{{size:9,family:'monospace'}},callbacks:{{title(i){{const d=i[0]?.raw?.x;return d?d.toLocaleDateString('en',{{month:'short',day:'numeric',year:'numeric'}}):''}},label(i){{if((i.dataset.label||'').startsWith('_'))return null;return` ${{i.dataset.label}}: ${{i.raw.y?.toFixed(1)}}`}}}}}}}},scales:{{x:{{type:'time',time:{{tooltipFormat:'MMM d yyyy'}},ticks:{{color:'#9ca3af',font:{{size:8,family:'monospace'}},maxTicksLimit:9}},grid:{{color:'#f3f4f6'}}}},y:{{type:useLog?'logarithmic':'linear',ticks:{{color:'#9ca3af',font:{{size:8,family:'monospace'}},callback:v=>parseFloat(v.toFixed(0)),maxTicksLimit:9}},grid:{{color:'#f3f4f6'}},title:{{display:true,text:'Index · base=100',color:'#9ca3af',font:{{size:8,family:'monospace'}}}}}}}}}},plugins:[todayPl('mc')]}});
}}

renderYC();renderPtfl();renderTable();render();
</script></body></html>"""

out_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),"index.html")
with open(out_path,"w") as f: f.write(HTML)
print(f"\n✓ Saved: {out_path}")
if not os.environ.get("CI"):
    print("  Opening in browser...")
    webbrowser.open(f"file://{out_path}")
