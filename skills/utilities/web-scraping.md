---
id: web-scraping
name: Web Scraping
category: utilities
level1: "For scraping websites, extracting structured data from HTML, and handling dynamic pages"
platforms: [claude-code, cursor, codex, gemini-cli, antigravity, opencode, aider, windsurf]
priority: 2
keywords: [scraping, scrape, crawler, crawl, BeautifulSoup, Scrapy, Playwright, robots.txt, selector, pagination, rate limit, web data]
level1_tokens: 45
level2_tokens: 480
level3_tokens: 2000
author: community-contributor
version: 1.0.0
---

<!-- LEVEL 1 START -->
## Web Scraping
Activate for: scraping web pages, extracting data from HTML, crawling pagination, JavaScript-rendered pages, robots.txt and rate limits.
<!-- LEVEL 1 END -->

<!-- LEVEL 2 START -->
## Core Instructions

1. **Check permissions first**: Read the site's robots.txt and terms of service. Skip disallowed paths. Never bypass logins, CAPTCHAs, or paywalls.
2. **Find the real data source**: Check static HTML, then the browser DevTools Network tab for a JSON API. An API is more stable than HTML.
3. **Use the lightest tool**: `requests` + BeautifulSoup for static pages. Use Playwright only when content is rendered by JavaScript.
4. **Rate-limit every request**: Wait 1-2 seconds between requests, send an identifying User-Agent, and back off on 429/503.
5. **Select stable elements**: Prefer ids, data attributes, and semantic tags over positional XPath or generated class names.
6. **Bound pagination**: Stop when there is no next link, a page is empty, or a maximum page count is reached.
7. **Store with provenance**: Normalise fields, record source URL and timestamp, and log failures instead of skipping them silently.

### Quick Checklist
- [ ] robots.txt and terms checked
- [ ] Data source identified (HTML, JSON API, or browser)
- [ ] Delay and User-Agent set
- [ ] Pagination has a stop condition
- [ ] Failures logged, output includes source URL
<!-- LEVEL 2 END -->

<!-- LEVEL 3 START -->
## Full Reference

### 1. Check robots.txt before fetching
```python
from urllib import robotparser
from urllib.parse import urlparse

def allowed(url: str, agent: str = "MyScraper/1.0") -> bool:
    parts = urlparse(url)
    rp = robotparser.RobotFileParser()
    rp.set_url(f"{parts.scheme}://{parts.netloc}/robots.txt")
    rp.read()
    return rp.can_fetch(agent, url)
```

### 2. Polite fetch with delay and retry
```python
import time
import requests

HEADERS = {"User-Agent": "MyScraper/1.0 (contact: you@example.com)"}

def fetch(url: str, delay: float = 1.5, retries: int = 3) -> str:
    for attempt in range(retries):
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code in (429, 503):
            time.sleep(delay * (2 ** attempt))  # exponential backoff
            continue
        resp.raise_for_status()
        time.sleep(delay)
        return resp.text
    raise RuntimeError(f"Gave up on {url} after {retries} attempts")
```

### 3. Parse with BeautifulSoup
```python
from bs4 import BeautifulSoup

def parse_items(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for card in soup.select("article.product"):
        title = card.select_one("h2")
        if title is None:
            continue  # skip malformed cards, do not crash
        price = card.select_one("[data-price]")
        items.append({
            "title": title.get_text(strip=True),
            "price": price.get("data-price") if price else None,
        })
    return items
```

### 4. Pagination with a stop condition
```python
from urllib.parse import urljoin

def crawl(start_url: str, max_pages: int = 50) -> list[dict]:
    results, url = [], start_url
    for _ in range(max_pages):
        html = fetch(url)
        results.extend(parse_items(html))
        next_link = BeautifulSoup(html, "html.parser").select_one("a[rel=next]")
        if next_link is None or not next_link.get("href"):
            break
        url = urljoin(url, next_link["href"])
    return results
```

### 5. JavaScript-rendered pages with Playwright
```python
from playwright.sync_api import sync_playwright

def fetch_rendered(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=HEADERS["User-Agent"])
        page.goto(url, wait_until="networkidle", timeout=30000)
        html = page.content()
        browser.close()
    return html
```

### 6. Scrapy spider (larger crawls)
```python
import scrapy

class ProductSpider(scrapy.Spider):
    name = "products"
    start_urls = ["https://example.com/products"]
    custom_settings = {"DOWNLOAD_DELAY": 1.5, "ROBOTSTXT_OBEY": True}

    def parse(self, response):
        for card in response.css("article.product"):
            yield {"title": card.css("h2::text").get(), "url": response.url}
        next_page = response.css("a[rel=next]::attr(href)").get()
        if next_page:
            yield response.follow(next_page, self.parse)
```

### Anti-patterns
- No delay between requests: this looks like an attack and gets IPs blocked.
- `except Exception: pass`: hides broken selectors. Log the URL and the error.
- Parallel requests to one host without a limit.
- Brittle XPath such as `/html/body/div[3]/div[2]/span`: breaks on any layout change.
- Collecting personal data (names, contact details) without a lawful purpose.

### Troubleshooting
- Empty results: the content is probably rendered by JavaScript. Check the page source, then switch to Playwright or an API.
- 403 on every request: the site blocks the default client. Do not spoof a browser to get past a block without permission. Check the terms.
- Results change between runs: store the raw HTML or JSON with a timestamp so the parse step can be re-run.
<!-- LEVEL 3 END -->
