"""Crawl Thinkwise community forum (Gainsight inSided platform).

Strategy: paginate through each category listing to collect topic URLs,
then crawl each topic page for content.
"""

import asyncio
import re

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

from wisey.clean import clean_markdown

BASE_URL = "https://community.thinkwisesoftware.com"

# Categories with substantial topic content — ordered largest first
CATEGORIES = [
    "/questions-conversations-78",  # ~3,200 topics
    "/thinkwise-platform-77",       # ~1,800 topics
]


def _extract_topic_urls_from_html(html: str) -> set[str]:
    """Extract topic URLs from embedded JSON in inSided HTML."""
    import html as html_mod
    unescaped = html_mod.unescape(html)
    # Match topic URLs with any combination of escaped/unescaped slashes
    raw_matches = re.findall(
        r'community\.thinkwisesoftware\.com[/\\]+[a-z0-9-]+-\d+[/\\]+[a-z0-9-]+-\d+',
        unescaped,
    )
    urls = set()
    for m in raw_matches:
        clean = re.sub(r'[/\\]+', '/', m)
        urls.add(f"https://{clean}")
    return urls


async def discover_topic_urls() -> list[str]:
    """Paginate through all category pages and extract topic URLs."""
    topic_urls: set[str] = set()

    browser_config = BrowserConfig(
        headless=True,
        browser_type="chromium",
        use_managed_browser=True,
    )
    config = CrawlerRunConfig(
        word_count_threshold=0,
        page_timeout=30000,
        wait_until="domcontentloaded",
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
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
                    result = await crawler.arun(url=url, config=config)
                    if not result.success:
                        break

                    html = result.html or ""
                    found = _extract_topic_urls_from_html(html)
                    new_urls = found - topic_urls

                    if not new_urls:
                        empty_streak += 1
                        if empty_streak >= 2:
                            break
                    else:
                        empty_streak = 0
                        topic_urls.update(new_urls)

                    page += 1
                    await asyncio.sleep(1)  # polite delay between pages
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
    browser_config = BrowserConfig(
        headless=True,
        browser_type="chromium",
        use_managed_browser=True,
    )
    config = CrawlerRunConfig(
        word_count_threshold=10,
        excluded_tags=["nav", "footer", "header", "aside"],
        page_timeout=30000,
        wait_until="domcontentloaded",
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        for i, url in enumerate(urls):
            try:
                result = await crawler.arun(url=url, config=config)
                if not result.success:
                    print(f"[community] Failed: {url}")
                    await asyncio.sleep(2)  # back off on failure
                    continue

                md_result = result.markdown
                if hasattr(md_result, "raw_markdown"):
                    md = md_result.raw_markdown or ""
                else:
                    md = str(md_result) if md_result else ""

                md = clean_markdown(md)

                title = result.metadata.get("title", "") if result.metadata else ""
                title = re.sub(r"\s*[-|].*community.*$", "", title, flags=re.IGNORECASE).strip()

                if md:
                    results.append({
                        "url": url,
                        "title": title,
                        "markdown": md,
                        "source_type": "community",
                    })

                if (i + 1) % 100 == 0:
                    print(f"[community] Progress: {i + 1}/{len(urls)}")

                await asyncio.sleep(0.5)  # polite delay

            except Exception as e:
                print(f"[community] Failed to crawl {url}: {e}")

    print(f"[community] Crawled {len(results)} topics successfully")
    return results


if __name__ == "__main__":
    asyncio.run(discover_topic_urls())
