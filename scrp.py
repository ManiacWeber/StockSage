import requests
import feedparser
from newspaper import Article
from datetime import datetime
import pytz
import yfinance as yf
from transformers import BertTokenizer, BertForSequenceClassification, pipeline
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import os

# ---------------------------
# CONFIG
# ---------------------------
FINNHUB_API_KEY = "d1ilckhr01qhbuvqnvk0d1ilckhr01qhbuvqnvkg"  # <<<< PUT YOUR API KEY HERE
NIFTY_THRESHOLD = 20000
STOCKS_FILE = "stocks.txt"  # Each line: one company name

# ---------------------------
# LOAD MODELS
# ---------------------------
model_name = "yiyanghkust/finbert-tone"
tokenizer = BertTokenizer.from_pretrained(model_name)
model = BertForSequenceClassification.from_pretrained(model_name)
finbert = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)

vader = SentimentIntensityAnalyzer()

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

def fetch_news_sentiments(query, max_articles=5):
    feed_url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}"
    feed = feedparser.parse(feed_url)

    finbert_sentiments = []
    vader_sentiments = []

    for entry in feed.entries[:max_articles]:
        article_url = entry.link
        article = Article(article_url)
        try:
            article.download()
            article.parse()

            text = f"{article.title}. {article.text[:300]}"
            if not article.text.strip():
                text = f"{article.title}. {entry.get('description', '')}"

            finbert_result = finbert(text)[0]
            finbert_sentiments.append(finbert_result['label'])

            vs = vader.polarity_scores(text)
            vader_label = "positive" if vs['compound'] > 0.05 else "negative" if vs['compound'] < -0.05 else "neutral"
            vader_sentiments.append(vader_label)

        except Exception as e:
            print(f"Error fetching article: {e}")

    return finbert_sentiments, vader_sentiments

def analyze_sentiments(finbert_list, vader_list):
    def count(labels):
        counts = {"positive": 0, "negative": 0, "neutral": 0}
        for s in labels:
            label = s.lower()
            if label in counts:
                counts[label] += 1
        return counts

    finbert_counts = count(finbert_list)
    vader_counts = count(vader_list)

    def majority(counts):
        if counts["positive"] > counts["negative"] and counts["positive"] > counts["neutral"]:
            return "positive"
        elif counts["negative"] > counts["positive"] and counts["negative"] > counts["neutral"]:
            return "negative"
        else:
            return "neutral/mixed"

    finbert_majority = majority(finbert_counts)
    vader_majority = majority(vader_counts)

    report = []
    report.append(f"📊 FinBERT: {finbert_majority.upper()} ({finbert_counts})")
    report.append(f"📰 VADER: {vader_majority.upper()} ({vader_counts})")
    return "\n".join(report)

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
    summary += "NIFTY 50 is an index representing the top 50 companies listed on the National Stock Exchange (NSE) of India, chosen based on market capitalisation and liquidity.\n"

    if current_price is None:
        summary += "\n⚠️ Could not fetch NIFTY data.\n"
        return summary

    if current_price > NIFTY_THRESHOLD:
        summary += f"\n🚨 NIFTY Alert: Above {NIFTY_THRESHOLD}! Current: {current_price}\n"
    else:
        summary += f"\n✅ NIFTY: Below {NIFTY_THRESHOLD}. Current: {current_price}\n"

    return summary

# ---------------------------
# MAIN EXECUTION
# ---------------------------
if __name__ == "__main__":
    tz = pytz.timezone("Asia/Kolkata")
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")

    print("📌 Choose:")
    print("1. Run for **one** company name")
    print("2. Run for **multiple** from `stocks.txt`")

    choice = input("Enter 1 or 2: ").strip()

    if choice == "1":
        companies = [input("Enter company name: ").strip()]
    else:
        with open(STOCKS_FILE, "r") as f:
            companies = [line.strip() for line in f if line.strip()]

    print(f"\n🔍 Running for: {companies}\n")

    # Get NIFTY once
    nifty_data = get_nifty_info()
    nifty_summary = check_nifty_alert(nifty_data['currentPrice'])

    os.makedirs("reports", exist_ok=True)

    for company in companies:
        symbol, description = search_symbol_finnhub(company)

        if not symbol:
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

        finbert_sents, vader_sents = fetch_news_sentiments(company, max_articles=7)
        sentiment_report = analyze_sentiments(finbert_sents, vader_sents)

        report = []
        report.append(f"📄 REPORT for: {company} ({symbol}) - {description}")
        report.append(f"🕒 Last Updated: {now}\n")
        report.append(sentiment_report)
        report.append(nifty_summary)

        report_text = "\n".join(report)
        print("\n" + report_text + "\n")

        filename = f"reports/{company}_{symbol}_{now[:10]}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report_text)

    print("\n✅ All reports saved to `reports/` folder.\n")


