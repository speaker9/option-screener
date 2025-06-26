import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# === Telegram Settings ===
TELEGRAM_TOKEN = "7595893051:AAGM3SAaU8Gl8w1jGNyEqKTMwDXZwmp0FqQ"
CHAT_ID = "5640139765"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("❌ Telegram error:", e)

# === Fetch NSE Option Chain (Stock)
def fetch_option_chain(symbol):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9"
        }
        url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
        session = requests.Session()
        session.headers.update(headers)
        session.get("https://www.nseindia.com", timeout=5)
        response = session.get(url, timeout=10)
        json_data = response.json()
        raw_data = json_data["records"]["data"]

        records = []
        for entry in raw_data:
            strike = entry.get("strikePrice")
            ce = entry.get("CE")
            pe = entry.get("PE")
            if ce and pe:
                records.append({
                    "Stock": symbol,
                    "Strike": strike,
                    "CE_LTP": ce.get("lastPrice", 0),
                    "CE_IV": ce.get("impliedVolatility", 0),
                    "CE_OI": ce.get("openInterest", 0),
                    "PE_LTP": pe.get("lastPrice", 0),
                    "PE_IV": pe.get("impliedVolatility", 0),
                    "PE_OI": pe.get("openInterest", 0)
                })
        return pd.DataFrame(records)
    except Exception as e:
        return pd.DataFrame()
# === Strategy Logic
# === RELAXED STRATEGY LOGIC ===
def apply_strategy(df):
    df = df[
        (df["CE_IV"] > 10) & (df["PE_IV"] > 10) &        # 🔽 Lowered IV filter
        (df["CE_OI"] > 10000) & (df["PE_OI"] > 10000)    # 🔽 Lowered OI filter
    ]
    
    df["CE_Target"] = df["CE_LTP"] * 1.4                # 🔁 Slightly tighter Target
    df["CE_SL"] = df["CE_LTP"] * 0.8
    df["PE_Target"] = df["PE_LTP"] * 1.4
    df["PE_SL"] = df["PE_LTP"] * 0.8

    df["Signal"] = df.apply(lambda row:
        "Buy CE" if row["CE_LTP"] < row["CE_Target"] and row["CE_IV"] > row["PE_IV"]
        else "Buy PE" if row["PE_LTP"] < row["PE_Target"] and row["PE_IV"] > row["CE_IV"]
        else "", axis=1)

    return df[df["Signal"] != ""]

# === Nifty 50 Stocks
nifty_50 = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "LT", "SBIN", "ITC", "KOTAKBANK",
    "AXISBANK", "HCLTECH", "WIPRO", "ADANIENT", "ADANIPORTS", "BAJFINANCE", "BAJAJFINSV",
    "BHARTIARTL", "HINDUNILVR", "MARUTI", "M&M", "SUNPHARMA", "TITAN", "ULTRACEMCO",
    "ONGC", "JSWSTEEL", "POWERGRID", "TATAMOTORS", "TATASTEEL", "NTPC", "DIVISLAB",
    "COALINDIA", "TECHM", "CIPLA", "BRITANNIA", "GRASIM", "NESTLEIND", "DRREDDY",
    "HDFCLIFE", "HEROMOTOCO", "INDUSINDBK", "BPCL", "EICHERMOT", "BAJAJ-AUTO",
    "SBILIFE", "APOLLOHOSP", "UPL", "SHRIRAMFIN", "ASIANPAINT"
]
# === Streamlit UI
st.set_page_config(page_title="Multi Stock Screener", layout="wide")
st.title("📈 Nifty 50 CE/PE Screener + Telegram Alerts")

all_signals = []

with st.spinner("📡 Fetching & analyzing option chain data..."):
    for stock in nifty_50:
        df = fetch_option_chain(stock)
        if not df.empty:
            filtered = apply_strategy(df)
            if not filtered.empty:
                for _, row in filtered.iterrows():
                    msg = f"""📢 *Option Signal Alert*
🧾 Stock: {row['Stock']}
🎯 Strike: {row['Strike']}
📈 Signal: {row['Signal']}
💰 LTP: {row['CE_LTP'] if row['Signal']=='Buy CE' else row['PE_LTP']}
🎯 Target: {row['CE_Target'] if row['Signal']=='Buy CE' else row['PE_Target']}
🛑 SL: {row['CE_SL'] if row['Signal']=='Buy CE' else row['PE_SL']}
🕒 Time: {datetime.now().strftime('%H:%M:%S')}"""
                    send_telegram(msg)
                all_signals.append(filtered)

# === Final Table
if all_signals:
    result_df = pd.concat(all_signals)
    st.success("✅ Screener Complete!")
    st.dataframe(result_df[["Stock", "Strike", "Signal", "CE_LTP", "CE_IV", "PE_LTP", "PE_IV"]])
    result_df.to_excel("multi_stock_option_signals.xlsx", index=False)
    with open("multi_stock_option_signals.xlsx", "rb") as f:
        st.download_button("📥 Download Screener Output", data=f, file_name="multi_stock_option_signals.xlsx")
else:
    st.warning("❌ No signals found for any stock.")
