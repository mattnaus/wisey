"""Crawl Thinkwise documentation site using its sitemap.xml."""

import asyncio
import re
import xml.etree.ElementTree as ET

import httpx
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

from wisey.clean import clean_markdown

SITEMAP_URL = "https://docs.thinkwisesoftware.com/sitemap.xml"

# Only crawl current (unversioned) docs and blog posts
INCLUDE_PATTERNS = [
    r"^https://docs\.thinkwisesoftware\.com/docs/(?!20\d{2}_)",  # current docs, not versioned
    r"^https://docs\.thinkwisesoftware\.com/blog/",  # release notes
]

# Skip navigation/index pages
EXCLUDE_PATTERNS = [
    r"/category/",
    r"/tags/",
    r"/search$",
    r"^https://docs\.thinkwisesoftware\.com/$",
]


async def fetch_sitemap_urls() -> list[str]:
    """Parse sitemap.xml and return filtered list of URLs to crawl."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(SITEMAP_URL)
        resp.raise_for_status()

    root = ET.fromstring(resp.text)
    ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    all_urls = [loc.text for loc in root.findall(".//ns:loc", ns) if loc.text]

    urls = []
    for url in all_urls:
        if any(re.search(p, url) for p in EXCLUDE_PATTERNS):
            continue
        if any(re.search(p, url) for p in INCLUDE_PATTERNS):
            urls.append(url)
    return urls


async def crawl_docs(urls: list[str] | None = None) -> list[dict]:
    """Crawl doc pages and return list of {url, title, markdown} dicts."""
    if urls is None:
        urls = await fetch_sitemap_urls()

    print(f"[docs] Crawling {len(urls)} pages...")

    results = []
    config = CrawlerRunConfig(
        word_count_threshold=10,
        excluded_tags=["nav", "footer", "header"],
    )

    async with AsyncWebCrawler() as crawler:
        for i, url in enumerate(urls):
            try:
                result = await crawler.arun(url=url, config=config)
                if not result.success:
                    print(f"[docs] Failed: {url}")
                    continue

                # crawl4ai 0.8+: result.markdown is a MarkdownGenerationResult
                md_result = result.markdown
                if hasattr(md_result, "raw_markdown"):
                    md = md_result.raw_markdown or ""
                else:
                    md = str(md_result) if md_result else ""

                md = clean_markdown(md)

                title = result.metadata.get("title", "") if result.metadata else ""
                title = re.sub(r"\s*\|.*$", "", title).strip()

                results.append({
                    "url": url,
                    "title": title,
                    "markdown": md,
                    "source_type": "release_notes" if "/blog/" in url else "docs",
                })

                if (i + 1) % 25 == 0:
                    print(f"[docs] Progress: {i + 1}/{len(urls)}")

            except Exception as e:
                print(f"[docs] Failed to crawl {url}: {e}")

    print(f"[docs] Crawled {len(results)} pages successfully")
    return results


if __name__ == "__main__":
    import json

    async def main():
        urls = await fetch_sitemap_urls()
        print(f"Found {len(urls)} URLs to crawl:")
        for u in urls[:10]:
            print(f"  {u}")
        if len(urls) > 10:
            print(f"  ... and {len(urls) - 10} more")

    asyncio.run(main())
