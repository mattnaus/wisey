"""Clean up crawled markdown by removing navigation cruft and boilerplate."""

import re


def clean_markdown(text: str) -> str:
    """Remove common boilerplate patterns from crawled markdown."""
    # Remove "Skip to main content" links
    text = re.sub(r"\[Skip to main content\]\([^)]+\)\s*", "", text)

    # Remove version banner lines (Docusaurus)
    text = re.sub(r"^Version:\s*[\d.]+\s*$", "", text, flags=re.MULTILINE)

    # Remove "On this page" section headers
    text = re.sub(r"^On this page\s*$", "", text, flags=re.MULTILINE)

    # Remove Docusaurus edit/fragment links like [​](url#fragment)
    text = re.sub(r"\[​\]\([^)]+\)", "", text)

    # Remove image links that are just logos
    text = re.sub(
        r"!\[.*?(?:Logo|logo|icon).*?\]\([^)]+\)", "", text, flags=re.IGNORECASE
    )

    # Remove breadcrumb-style navigation lines (common in community)
    text = re.sub(r"^\[.*?\]\(.*?\)\s*[>/»]\s*\[.*?\]\(.*?\).*$", "", text, flags=re.MULTILINE)

    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
