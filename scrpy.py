#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
import feedparser
from newspaper import Article
import newspaper  # ✅ Needed for settings!
from datetime import datetime
import pytz
import yfinance as yf
from transformers import BertTokenizer, BertForSequenceClassification, pipeline
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from colorama import Fore, Style, init as colorama_init
import tempfile

# ---------------------------
# CONFIG
# ---------------------------
FINNHUB_API_KEY = "d1ilckhr01qhbuvqnvk0d1ilckhr01qhbuvqnvkg"
NIFTY_THRESHOLD = 20000
STOCKS_FILE = "stocks.txt"
REPORTS_DIR = "reports"

# ---------------------------
# INIT
# ---------------------------
colorama_init(autoreset=True)

model_name = "yiyanghkust/finbert-tone"
tokenizer = BertTokenizer.from_pretrained(model_name)
model = BertForSequenceClassification.from_pretrained(model_name)
finbert = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)

vader = SentimentIntensityAnalyzer()

# Fix newspaper temp dir issue
CUSTOM_CACHE_DIR = os.path.join(tempfile.gettempdir(), "news_cache")
os.makedirs(CUSTOM_CACHE_DIR, exist_ok=True)
newspaper.settings.ARTICLE_DIRECTORY = CUSTOM_CACHE_DIR

# ---------------------------
# HELPERS
# ---------------------------
def search_symbol_finnhub(company_name):
    url = f"https://finnhub.io/api/v1/search?q={company_name}&token={FINNHUB_API_KEY}"
    response = requests.get(url)
    data = response.json()
    if data.get("count", 0) > 0:
        top_result = data["result"][0]
        symbol = top_result["symbol"]
        description = top_result["description"]
        return symbol, description
    return None, None

def fetch_combined_sentiments(query, max_articles=5):
    feed_url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}"
    feed = feedparser.parse(feed_url)

    combined_results = []

    for entry in feed.entries[:max_articles]:
        article_url = entry.link
        article = Article(article_url)
        try:
            article.download()
            article.parse()

            text = f"{article.title}. {article.text[:300]}"
            if not article.text.strip():
                text = f"{article.title}. {entry.get('description', '')}"

            finbert_result = finbert(text)[0]["label"].lower()

            vs = vader.polarity_scores(text)
            if vs["compound"] >= 0.05:
                vader_result = "positive"
            elif vs["compound"] <= -0.05:
                vader_result = "negative"
            else:
                vader_result = "neutral"

            combined_results.append((finbert_result, vader_result))

        except Exception as e:
            print(f"Error fetching article: {e}")

    return combined_results

def merge_weighted_results(pairs, colored=True):
    merged_counts = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}

    for finbert, vader in pairs:
        votes = {"positive": 0, "negative": 0, "neutral": 0}
        votes[finbert] += 0.7
        votes[vader] += 0.3
        winner = max(votes, key=lambda k: votes[k])

        if winner == finbert and winner == vader:
            merged_counts[winner] += 1
        elif votes[winner] >= 0.7:
            merged_counts[winner] += 1
        else:
            merged_counts["mixed"] += 1

    main_sentiment = max(merged_counts, key=lambda k: merged_counts[k])

    def color_label(label):
        if not colored:
            return label.upper()
        if "positive" in label:
            return f"{Fore.GREEN}{label.upper()}{Style.RESET_ALL}"
        elif "negative" in label:
            return f"{Fore.RED}{label.upper()}{Style.RESET_ALL}"
        elif "mixed" in label:
            return f"{Fore.YELLOW}{label.upper()}{Style.RESET_ALL}"
        else:
            return f"{Fore.BLUE}{label.upper()}{Style.RESET_ALL}"

    report = [
        f"🧮 Weighted Combined Majority: {color_label(main_sentiment)}",
        f"Counts: {merged_counts}"
    ]
    return "\n".join(report)

def get_price_movement(stock, colored=True):
    info = stock.info
    current_price = info.get("regularMarketPrice")
    previous_close = info.get("previousClose")

    if current_price is None or previous_close is None:
        return "⚠️ Price info unavailable."

    change = current_price - previous_close
    change_percent = (change / previous_close) * 100 if previous_close else 0

    emoji = "🔼" if change > 0 else "🔽" if change < 0 else "➡️"

    if change > 0:
        color = Fore.GREEN if colored else ""
    elif change < 0:
        color = Fore.RED if colored else ""
    else:
        color = Fore.BLUE if colored else ""

    reset = Style.RESET_ALL if colored else ""

    result = (
        f"{color}💰 PRICE MOVEMENT:\n"
        f"Current: {current_price}\n"
        f"Previous Close: {previous_close}\n"
        f"Change: {change:+.2f} ({change_percent:+.2f}%) {emoji}{reset}"
    )
    return result

def get_nifty_info():
    nifty = yf.Ticker("^NSEI")
    info = nifty.info
    return {
        "currentPrice": info.get("regularMarketPrice"),
        "previousClose": info.get("previousClose"),
        "change": info.get("regularMarketChange"),
        "changePercent": info.get("regularMarketChangePercent")
    }

def check_nifty_alert(current_price):
    summary = "\n📌 What is the NIFTY Index?\n"
    summary += (
        "NIFTY 50 is an index representing the top 50 companies listed on the "
        "National Stock Exchange (NSE) of India, chosen based on market capitalisation and liquidity.\n"
    )

    if current_price is None:
        summary += "\n⚠️ Could not fetch NIFTY data.\n"
        return summary

    if current_price > NIFTY_THRESHOLD:
        summary += f"\n🚨 NIFTY Alert: Above {NIFTY_THRESHOLD}! Current: {current_price}\n"
    else:
        summary += f"\n✅ NIFTY: Below {NIFTY_THRESHOLD}. Current: {current_price}\n"

    return summary

# ---------------------------
# MAIN
# ---------------------------
if __name__ == "__main__":
    tz = pytz.timezone("Asia/Kolkata")
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")

    print("📌 Choose:")
    print("1. Run for ONE company name")
    print("2. Run for MULTIPLE from `stocks.txt`")

    choice = input("Enter 1 or 2: ").strip()

    if choice == "1":
        companies = [input("Enter company name: ").strip()]
    else:
        with open(STOCKS_FILE, "r", encoding="utf-8") as f:
            companies = [line.strip() for line in f if line.strip()]

    print(f"\n🔍 Running for: {companies}\n")

    nifty_data = get_nifty_info()
    nifty_summary = check_nifty_alert(nifty_data['currentPrice'])

    os.makedirs(REPORTS_DIR, exist_ok=True)

    for company in companies:
        symbol, description = search_symbol_finnhub(company)

        if not symbol:
            # ✅ Try NSE fallback automatically
            nse_try = f"{company.upper()}.NS"
            test_ticker = yf.Ticker(nse_try)
            if test_ticker.info and test_ticker.info.get("regularMarketPrice"):
                symbol = nse_try
                description = f"(Auto NSE fallback for {company})"
            else:
                print(f"⚠️ Could not auto-find ticker for: {company}")
                manual_symbol = input("🔍 Enter exact NSE/BSE ticker symbol manually (or press Enter to skip): ").strip().upper()
                if manual_symbol:
                    symbol = manual_symbol
                    description = f"Manual ticker input for {company}"
                else:
                    print(f"❌ Skipping {company} — no valid ticker.")
                    continue

        stock = yf.Ticker(symbol)
        if not stock.info or not stock.info.get("regularMarketPrice"):
            print(f"❌ No price data for ticker: {symbol}")
            continue

        combined_pairs = fetch_combined_sentiments(company, max_articles=7)
        merged_report_colored = merge_weighted_results(combined_pairs, colored=True)
        merged_report_plain = merge_weighted_results(combined_pairs, colored=False)

        price_movement_colored = get_price_movement(stock, colored=True)
        price_movement_plain = get_price_movement(stock, colored=False)

        report_colored = []
        report_colored.append(f"📄 REPORT for: {company} ({symbol}) - {description}")
        report_colored.append(f"🕒 Last Updated: {now}\n")
        report_colored.append(merged_report_colored)
        report_colored.append(price_movement_colored)

        print("\n" + "\n".join(report_colored) + "\n")

        report_plain = []
        report_plain.append(f"📄 REPORT for: {company} ({symbol}) - {description}")
        report_plain.append(f"🕒 Last Updated: {now}\n")
        report_plain.append(merged_report_plain)
        report_plain.append(price_movement_plain)

        filename = f"{company}_{symbol}_{now[:10]}.txt"
        filepath = os.path.join(REPORTS_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(report_plain))

    # ✅ Print NIFTY info ONCE at the end
    print(nifty_summary)

    print(f"\n✅ All reports saved to `{REPORTS_DIR}/`.\n")
