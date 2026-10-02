from ddgs import DDGS


def web_search(query: str, max_results: int = 5):
    results = DDGS().text(
        query,
        max_results=max_results + 3,
    )

    clean_results = []

    for result in results:
        url = result.get("href", "")

        if "bing.com/aclick" in url:
            continue

        clean_results.append(
            {
                "title": result.get("title", ""),
                "url": url,
                "snippet": result.get("body", ""),
            }
        )

        if len(clean_results) >= max_results:
            break

    return clean_results