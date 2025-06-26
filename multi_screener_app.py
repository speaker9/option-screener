import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import yfinance as yf
import json
import os
import yagmail

st.set_page_config(page_title="Option Screener + Chain Analysis", layout="wide")
st.title("📊 Full Option Screener: Greeks + BTST + SL/Target + News + Backtest")
# === Telegram Settings ===
TELEGRAM_TOKEN = "7595893051:AAGM3SAaU8Gl8w1jGNyEqKTMwDXZwmp0FqQ"
CHAT_ID = "5640139765"

# === Email Settings ===
EMAIL_USER = "jmjguntur@gmail.com"
EMAIL_PASSWORD = "zhpa fbqq ylid zxzw"
EMAIL_TO = "jmjguntur@gmail.com"

# === News Sentiment from NewsAPI.org ===
NEWS_API_KEY = "zhpa fbqq ylid zxzw"

# === Sector Mapping (example dummy sectors) ===
sector_map = {
    25000: "BANKING", 25500: "IT", 26000: "PHARMA", 24500: "FMCG", 24000: "AUTO"
}

# === Time check ===
now = datetime.now()
market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
is_market_time = market_open <= now <= market_close

# === Load previous signals ===
history_file = "signal_history.csv"
history_df = pd.read_csv(history_file) if os.path.exists(history_file) else pd.DataFrame()

def fetch_nse_option_chain(symbol="NIFTY"):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br"
        }
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        session = requests.Session()
        session.headers.update(headers)
        session.get("https://www.nseindia.com", timeout=5)
        response = session.get(url, timeout=10)
        data = response.json()
        return data.get("records", {}).get("data", [])
    except Exception as e:
        st.error(f"❌ Failed to fetch option chain: {e}")
        return []

def fetch_news_sentiment(stock_name):
    try:
        url = f"https://newsapi.org/v2/everything?q={stock_name}&language=en&sortBy=publishedAt&pageSize=5&apiKey={NEWS_API_KEY}"
        response = requests.get(url)
        data = response.json()

        if "articles" not in data:
            return "No News"

        headlines = " ".join([article["title"] for article in data["articles"]])
        positive_words = ["gain", "growth", "rise", "surge", "bullish"]
        negative_words = ["fall", "drop", "loss", "plunge", "bearish"]

        pos_count = sum(word in headlines.lower() for word in positive_words)
        neg_count = sum(word in headlines.lower() for word in negative_words)

        if pos_count > neg_count:
            return "Bullish"
        elif neg_count > pos_count:
            return "Bearish"
        else:
            return "Neutral"
    except:
        return "Error"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("📩 Telegram alert sent successfully!")
        else:
            print("❌ Failed to send Telegram alert:", response.text)
    except Exception as e:
        print("❌ Telegram error:", e)

def send_email(subject, content):
    try:
        yag = yagmail.SMTP(user=EMAIL_USER, password=EMAIL_PASSWORD)
        yag.send(to=EMAIL_TO, subject=subject, contents=content)
        print("📧 Email alert sent successfully!")
    except Exception as e:
        print("❌ Email alert failed:", e)

st.sidebar.markdown("### 🟢 Use Real-time Option Chain")
use_realtime = st.sidebar.checkbox("Fetch live NSE Option Chain")

if use_realtime:
    option_data = fetch_nse_option_chain()
    st.info(f"🔄 Live data fetched: {len(option_data)} strikes loaded")
    st.write(option_data[:3])
    st.stop()

uploaded_file = st.file_uploader("📁 Upload Nifty Option Chain Excel", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    df.replace("-", 0, inplace=True)
    for col in ["CE_LTP", "PE_LTP", "Strike", "CE_OI", "PE_OI", "CE_IV", "PE_IV"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.dropna(subset=["CE_LTP", "PE_LTP", "Strike"], inplace=True)

    df = df[
        (df["CE_IV"] > 15) & (df["PE_IV"] > 15) &
        (df["CE_OI"] > 50000) & (df["PE_OI"] > 50000)
    ]

    df["BTST_Flag"] = np.where((df["CE_OI"] > df["PE_OI"] * 1.1), "✅ BTST Buy", "❌")

    def simulate_sl_target(df, sl_pct=0.3, target_pct=0.6):
        df["CE_SL"] = df["CE_LTP"] * (1 - sl_pct)
        df["CE_Target"] = df["CE_LTP"] * (1 + target_pct)
        df["CE_Outcome"] = df.apply(lambda row: (
            "Hit Target" if row["CE_LTP"] < row["CE_Target"] else (
            "Hit SL" if row["CE_LTP"] > row["CE_SL"] else "Open")
        ), axis=1)

        df["PE_SL"] = df["PE_LTP"] * (1 - sl_pct)
        df["PE_Target"] = df["PE_LTP"] * (1 + target_pct)

        df["PE_Outcome"] = df.apply(lambda row: (
            "Hit Target" if row["PE_LTP"] < row["PE_Target"] else (
            "Hit SL" if row["PE_LTP"] > row["PE_SL"] else "Open")
        ), axis=1)

        return df

    sl_pct = st.sidebar.slider("Stop Loss %", 0.05, 0.5, 0.3)
    target_pct = st.sidebar.slider("Target %", 0.1, 1.0, 0.6)
    df = simulate_sl_target(df, sl_pct, target_pct)

    df["News_Sentiment"] = df["Strike"].apply(lambda x: fetch_news_sentiment(str(x)))
    df["Sector"] = df["Strike"].map(sector_map).fillna("OTHERS")

    df["Final_Signal"] = np.where(
        (df["CE_Outcome"] == "Hit Target") & (df["News_Sentiment"] == "Bullish"), "Buy CE",
        np.where((df["PE_Outcome"] == "Hit Target") & (df["News_Sentiment"] == "Bearish"), "Buy PE", "")
    )
    final_df = df[df["Final_Signal"] != ""]

    # Store with timestamp
    final_df["Date"] = datetime.now().strftime("%Y-%m-%d")
    history_df = pd.concat([history_df, final_df]).drop_duplicates()
    history_df.to_csv(history_file, index=False)

    # Show only last 5 days signals
    history_df["Date"] = pd.to_datetime(history_df["Date"])
    last_5_days_df = history_df[history_df["Date"] >= datetime.now() - timedelta(days=5)]

    st.subheader("🎯 Final CE/PE Picks (Last 5 Days)")
    st.dataframe(last_5_days_df[[
        "Date", "Strike", "Final_Signal", "News_Sentiment", "Sector", "CE_LTP", "CE_Target", "CE_SL", "CE_Outcome",
        "PE_LTP", "PE_Target", "PE_SL", "PE_Outcome", "BTST_Flag"
    ]])

    st.subheader("📈 Backtesting Stats")
    ce_win = final_df["CE_Outcome"].value_counts().get("Hit Target", 0)
    pe_win = final_df["PE_Outcome"].value_counts().get("Hit Target", 0)
    total = len(final_df)
    win_rate = (ce_win + pe_win) / total * 100 if total > 0 else 0
    st.metric("✅ Win Rate (%)", f"{win_rate:.2f}%")

    # Live alert if market hours
    if is_market_time and not final_df.empty:
        for _, row in final_df.iterrows():
            signal_text = f"""
🚨 *Live Option Signal Alert* 🚨
🕒 {datetime.now().strftime('%H:%M:%S')}
🎯 Strike: {row['Strike']}
📢 Signal: {row['Final_Signal']}
📈 LTP: {row['CE_LTP'] if row['Final_Signal']=='Buy CE' else row['PE_LTP']}
🎯 Target: {row['CE_Target'] if row['Final_Signal']=='Buy CE' else row['PE_Target']}
🛑 Stop Loss: {row['CE_SL'] if row['Final_Signal']=='Buy CE' else row['PE_SL']}
📊 Sentiment: {row['News_Sentiment']}
🏷️ Sector: {row['Sector']}
"""
            send_telegram_message(signal_text)
            subject = f"Live Option Signal: {row['Final_Signal']} at {row['Strike']}"
            send_email(subject, signal_text)

    final_df.to_excel("Final_CE_PE_Picks.xlsx", index=False)
    with open("Final_CE_PE_Picks.xlsx", "rb") as f:
        st.download_button(label="📥 Download Final Picks Excel", data=f, file_name="Final_CE_PE_Picks.xlsx")
else:
    st.warning("📂 Please upload an Excel file to begin.")
