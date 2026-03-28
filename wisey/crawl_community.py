"""Crawl Thinkwise community forum (Gainsight inSided platform).

Strategy: paginate through each category listing to collect topic URLs,
then fetch each topic page for content. Uses plain HTTP (httpx) since
the content is server-side rendered — no headless browser needed.
"""

import asyncio
import html as html_mod
import re

import httpx
from markdownify import markdownify as md

from wisey.clean import clean_markdown

BASE_URL = "https://community.thinkwisesoftware.com"

# Categories with substantial topic content
CATEGORIES = [
    "/questions-conversations-78",  # ~3,200 topics
    "/thinkwise-platform-77",       # ~1,800 topics
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Delay between requests (seconds) — be polite
REQUEST_DELAY = 1.5


def _extract_topic_urls_from_html(html: str) -> set[str]:
    """Extract topic URLs from embedded JSON in inSided HTML."""
    unescaped = html_mod.unescape(html)
    raw_matches = re.findall(
        r'community\.thinkwisesoftware\.com[/\\]+[a-z0-9-]+-\d+[/\\]+[a-z0-9-]+-\d+',
        unescaped,
    )
    urls = set()
    for m in raw_matches:
        clean = re.sub(r'[/\\]+', '/', m)
        urls.add(f"https://{clean}")
    return urls


def _extract_post_content(html: str) -> str:
    """Extract post content from a community topic page and convert to markdown."""
    # Posts live in <div class="post__content"> blocks
    posts = re.findall(
        r'<div[^>]*class="[^"]*post__content[^"]*"[^>]*>(.*?)</div>',
        html,
        re.DOTALL | re.IGNORECASE,
    )
    if not posts:
        # Fallback: try the main content area
        main = re.search(r'<main[^>]*>(.*?)</main>', html, re.DOTALL)
        if main:
            return clean_markdown(md(main.group(1), strip=["img", "script", "style"]))
        return ""

    parts = [md(post, strip=["img", "script", "style"]).strip() for post in posts]
    return clean_markdown("\n\n---\n\n".join(p for p in parts if p))


def _extract_title(html: str) -> str:
    """Extract topic title from HTML."""
    match = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL | re.IGNORECASE)
    if match:
        title = html_mod.unescape(match.group(1)).strip()
        # Remove site suffix
        title = re.sub(r"\s*[-|].*community.*$", "", title, flags=re.IGNORECASE).strip()
        return title
    return ""


async def discover_topic_urls() -> list[str]:
    """Paginate through all category pages and extract topic URLs."""
    topic_urls: set[str] = set()

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=30) as client:
        for category in CATEGORIES:
            page = 1
            empty_streak = 0
            cat_name = category.strip("/").rsplit("-", 1)[0]
            print(f"[community] Scanning category: {cat_name}")

            while True:
                if page == 1:
                    url = f"{BASE_URL}{category}"
                else:
                    url = f"{BASE_URL}{category}/index{page}.html"

                try:
                    resp = await client.get(url)
                    if resp.status_code == 403:
                        print(f"[community] Rate limited at page {page}, backing off 30s...")
                        await asyncio.sleep(30)
                        resp = await client.get(url)  # retry once

                    if resp.status_code != 200:
                        print(f"[community] Got {resp.status_code} on {url}, stopping category")
                        break

                    found = _extract_topic_urls_from_html(resp.text)
                    new_urls = found - topic_urls

                    if not new_urls:
                        empty_streak += 1
                        if empty_streak >= 2:
                            break
                    else:
                        empty_streak = 0
                        topic_urls.update(new_urls)

                    page += 1
                    await asyncio.sleep(REQUEST_DELAY)

                except Exception as e:
                    print(f"[community] Error on {url}: {e}")
                    break

            print(f"[community] Found {len(topic_urls)} total topics so far")

    print(f"[community] Total unique topic URLs: {len(topic_urls)}")
    return sorted(topic_urls)


async def crawl_community(urls: list[str] | None = None) -> list[dict]:
    """Crawl community topic pages and return {url, title, markdown} dicts."""
    if urls is None:
        urls = await discover_topic_urls()

    print(f"[community] Crawling {len(urls)} topics...")

    results = []
    failures = 0

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=30) as client:
        for i, url in enumerate(urls):
            try:
                resp = await client.get(url)

                if resp.status_code == 403:
                    failures += 1
                    if failures >= 3:
                        print(f"[community] 3 consecutive 403s at topic {i+1}, backing off 60s...")
                        await asyncio.sleep(60)
                        failures = 0
                    else:
                        await asyncio.sleep(5)
                    continue

                if resp.status_code != 200:
                    continue

                failures = 0  # reset on success

                title = _extract_title(resp.text)
                content = _extract_post_content(resp.text)

                if content:
                    results.append({
                        "url": url,
                        "title": title,
                        "markdown": content,
                        "source_type": "community",
                    })

                if (i + 1) % 100 == 0:
                    print(f"[community] Progress: {i + 1}/{len(urls)} ({len(results)} with content)")

                await asyncio.sleep(REQUEST_DELAY)

            except Exception as e:
                print(f"[community] Error on {url}: {e}")

    print(f"[community] Crawled {len(results)} topics successfully out of {len(urls)}")
    return results


if __name__ == "__main__":
    asyncio.run(discover_topic_urls())
