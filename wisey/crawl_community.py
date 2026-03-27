"""Crawl Thinkwise community forum (Gainsight inSided platform).

Strategy: paginate through each category listing to collect topic URLs,
then crawl each topic page for content.
"""

import asyncio
import re

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

from wisey.clean import clean_markdown

BASE_URL = "https://community.thinkwisesoftware.com"

# All top-level categories — we paginate through each to discover topic URLs
CATEGORIES = [
    "/questions-conversations-78",
    "/ideas-68",
    "/knowledge-base-69",
    "/announcements-70",
    "/events-71",
    "/academy-77",
    "/getting-started-on-the-thinkwise-community-72",
    "/thinkwise-insights-74",
    "/thinkwise-platform-77",
    "/thinkstore-87",
    "/news-blogs-21",
]


async def discover_topic_urls() -> list[str]:
    """Paginate through all category pages and extract topic URLs."""
    topic_urls: set[str] = set()
    # Pattern to match topic links: /{category-slug}-{id}/{topic-slug}-{id}
    topic_pattern = re.compile(
        r'href="(/[a-z0-9-]+-\d+/[a-z0-9-]+-\d+)"', re.IGNORECASE
    )

    config = CrawlerRunConfig(
        word_count_threshold=0,
    )

    async with AsyncWebCrawler() as crawler:
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
                    found = topic_pattern.findall(html)
                    new_urls = {f"{BASE_URL}{path}" for path in found} - topic_urls

                    if not new_urls:
                        empty_streak += 1
                        if empty_streak >= 2:
                            break
                    else:
                        empty_streak = 0
                        topic_urls.update(new_urls)

                    page += 1
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
    config = CrawlerRunConfig(
        word_count_threshold=10,
        excluded_tags=["nav", "footer", "header", "aside"],
    )

    async with AsyncWebCrawler() as crawler:
        for i, url in enumerate(urls):
            try:
                result = await crawler.arun(url=url, config=config)
                if not result.success:
                    print(f"[community] Failed: {url}")
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

            except Exception as e:
                print(f"[community] Failed to crawl {url}: {e}")

    print(f"[community] Crawled {len(results)} topics successfully")
    return results


if __name__ == "__main__":
    asyncio.run(discover_topic_urls())
