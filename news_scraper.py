import feedparser
from newspaper import Article
from datetime import datetime

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
                "source": entry.source.get("title", "Unknown"),
                "published": entry.published,
                "link": article_url
            })
        except Exception as e:
            print(f"Error parsing article: {article_url}\n{e}")
    return articles

if __name__ == "__main__":
    stock_name = input("Enter stock or company name: ")
    print(f"Fetching news for: {stock_name}")
    news_articles = fetch_google_news_links(stock_name, max_articles=7)

    print("\nTop Headlines:\n")
    for idx, article in enumerate(news_articles, start=1):
        print(f"{idx}. {article['title']}")
        print(f"   Published: {article['published']}")
        print(f"   Source: {article['source']}")
        print(f"   Summary: {article['summary'][:250]}...")
        print(f"   Link: {article['link']}\n")
