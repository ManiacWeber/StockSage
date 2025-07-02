import feedparser
from newspaper import Article
from datetime import datetime
import pytz
import yfinance as yf

def fetch_google_news_links(query, max_articles=5):
    feed_url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}"
    feed = feedparser.parse(feed_url)
    articles = []

    for entry in feed.entries[:max_articles]:
        article_url = entry.link
        article = Article(article_url)
        try:
            article.download()
            article.parse()
            articles.append({
                "title": article.title,
                "summary": article.text[:400] + '...',
                "source": entry.get("source", {}).get("title", "Unknown"),
                "published": entry.published,
                "link": article_url
            })
        except Exception as e:
            print(f"Error parsing article: {article_url}\n{e}")
    return articles

def get_nifty_info():
    nifty = yf.Ticker("^NSEI")
    info = nifty.info
    return {
        "currentPrice": info.get("regularMarketPrice"),
        "previousClose": info.get("previousClose"),
        "change": info.get("regularMarketChange"),
        "changePercent": info.get("regularMarketChangePercent")
    }

def check_nifty_alert(current_price, threshold=20000):
    if current_price is None:
        print("Could not fetch NIFTY data.")
        return
    print("\n📌 What is the NIFTY Index?")
    print("NIFTY 50 is an index representing the top 50 companies listed on the National Stock Exchange (NSE) of India, chosen based on market capitalisation and liquidity.\n")
    if current_price > threshold:
        print(f"🚨 ALERT: NIFTY is above {threshold}! Current: {current_price}")
    else:
        print(f"✅ NIFTY is below threshold. Current: {current_price}")

if __name__ == "__main__":
    # Set your timezone
    tz = pytz.timezone("Asia/Kolkata")
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")

    stock_name = input("Enter stock or company name: ")
    print(f"\nFetching news for: {stock_name}...")
    news_articles = fetch_google_news_links(stock_name, max_articles=7)

    print("\n📰 Top Headlines:\n")
    for idx, article in enumerate(news_articles, start=1):
        print(f"{idx}. {article['title']}")
        print(f"   Published: {article['published']}")
        print(f"   Source: {article['source']}")
        print(f"   Summary: {article['summary'][:250]}...")
        print(f"   Link: {article['link']}\n")

    print("\n📈 Checking NIFTY Index...\n")
    nifty_data = get_nifty_info()
    check_nifty_alert(nifty_data['currentPrice'], threshold=20000)

    print(f"\n🕒 Last Updated: {now}")
