import asyncio
import re
from urllib.parse import urljoin

import feedparser
import httpx
from bs4 import BeautifulSoup
from readability import Document


async def extract_text_from_url(url: str) -> tuple[str, str]:
    """
    Extract text content from a URL.
    Returns (extracted_text, title).
    Uses readability-lxml first, falls back to RSS if text is too short.
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        resp = await client.get(url, headers={"User-Agent": "Wordprint/1.0"})
        resp.raise_for_status()
        html = resp.text

    doc = Document(html)
    title = doc.title()
    content_html = doc.summary()
    soup = BeautifulSoup(content_html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)

    # If text is too short, try RSS/Atom feed
    if len(text.split()) < 200:
        feed_text = await _try_feed_fallback(url, html)
        if feed_text and len(feed_text.split()) > len(text.split()):
            text = feed_text

    return text, title


async def _try_feed_fallback(url: str, html: str) -> str | None:
    """Try to find and parse an RSS/Atom feed from the page."""
    soup = BeautifulSoup(html, "html.parser")

    feed_link = soup.find("link", attrs={"type": re.compile(r"(rss|atom)")})
    if not feed_link or not feed_link.get("href"):
        return None

    feed_url = urljoin(url, feed_link["href"])
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        resp = await client.get(feed_url, headers={"User-Agent": "Wordprint/1.0"})
        resp.raise_for_status()

    feed = feedparser.parse(resp.text)
    texts = []
    for entry in feed.entries[:5]:
        content = ""
        if hasattr(entry, "content") and entry.content:
            content = entry.content[0].get("value", "")
        elif hasattr(entry, "summary"):
            content = entry.summary
        if content:
            entry_soup = BeautifulSoup(content, "html.parser")
            texts.append(entry_soup.get_text(separator=" ", strip=True))

    return "\n\n".join(texts) if texts else None


async def discover_blog_urls(blog_url: str) -> list[str]:
    """
    Discover article URLs from a blog.
    Prefers RSS/Atom feed, falls back to link scraping.
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        resp = await client.get(blog_url, headers={"User-Agent": "Wordprint/1.0"})
        resp.raise_for_status()
        html = resp.text

    # Try RSS/Atom first
    soup = BeautifulSoup(html, "html.parser")
    feed_link = soup.find("link", attrs={"type": re.compile(r"(rss|atom)")})

    if feed_link and feed_link.get("href"):
        feed_url = urljoin(blog_url, feed_link["href"])
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            resp = await client.get(feed_url, headers={"User-Agent": "Wordprint/1.0"})
            resp.raise_for_status()

        feed = feedparser.parse(resp.text)
        urls = []
        for entry in feed.entries:
            if hasattr(entry, "link") and entry.link:
                urls.append(entry.link)
        if urls:
            return urls

    # Fallback: scrape links from the page
    links = soup.find_all("a", href=True)
    article_urls = []
    seen = set()
    for link in links:
        href = urljoin(blog_url, link["href"])
        if href in seen or href == blog_url:
            continue
        seen.add(href)
        # Heuristic: article links usually contain date patterns or /post/ /article/ etc.
        if (re.search(r"/\d{4}/\d{2}/", href)
                or re.search(r"/(post|article|blog|beitrag)/", href, re.I)
                or (href.startswith(blog_url) and href.count("/") > 3)):
            article_urls.append(href)

    return article_urls
