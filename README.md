# 📊 StockSage – AI-Powered Stock Risk Analyzer

StockSage is a smart stock risk analysis tool that scrapes financial news and uses AI-based sentiment analysis (FinBERT) to forecast short-term risk and stock trend.

## 🔹 Week 1 - News Scraper Module

This module allows users to:
- Input a stock/company name
- Fetch recent news headlines
- Extract article summaries, publish date, and sources

### 🚀 Run Locally
```bash
pip install newspaper3k feedparser lxml_html_clean
python news_scraper.py
