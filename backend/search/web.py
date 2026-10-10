"""Public web search and safe page extraction for Medha."""
from __future__ import annotations
import ipaddress
import socket
from urllib.parse import urljoin, urlparse, parse_qs
import requests
from bs4 import BeautifulSoup

USER_AGENT = "MedhaPersonalAssistant/1.0"
TIMEOUT = (3.0, 7.0)
MAX_REDIRECTS = 4
MAX_PAGE_BYTES = 1_000_000

def _validate_public_url(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only valid public HTTP(S) URLs are supported.")
    host = parsed.hostname.rstrip(".")
    if host.lower() in {"localhost", "localhost.localdomain"} or host.lower().endswith(".local"):
        raise ValueError("Local network addresses are not allowed.")
    try:
        addresses = {ipaddress.ip_address(host)}
    except ValueError:
        try:
            addresses = {ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))}
        except (OSError, ValueError):
            raise ValueError("Hostname could not be resolved.") from None
    if not addresses or any(a.is_private or a.is_loopback or a.is_link_local or a.is_reserved or a.is_multicast or a.is_unspecified for a in addresses):
        raise ValueError("Local or non-public network addresses are not allowed.")
    return url

def _fetch_public(url: str) -> requests.Response:
    current = _validate_public_url(url)
    session = requests.Session()
    for _ in range(MAX_REDIRECTS + 1):
        response = session.get(current, headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain"}, timeout=TIMEOUT, allow_redirects=False, stream=True)
        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get("Location")
            response.close()
            if not location:
                raise ValueError("Invalid redirect.")
            current = _validate_public_url(urljoin(current, location))
            continue
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        if "text/html" not in content_type and "text/plain" not in content_type:
            response.close()
            raise ValueError("Only HTML and plain-text pages can be opened.")
        chunks, size = [], 0
        for chunk in response.iter_content(16384):
            size += len(chunk)
            if size > MAX_PAGE_BYTES:
                response.close()
                raise ValueError("Page exceeds the 1 MB reading limit.")
            chunks.append(chunk)
        response._content = b"".join(chunks)
        response.close()
        return response
    raise ValueError("Too many redirects.")

def search_web(query: str, limit: int = 5) -> list[dict[str, str]]:
    """Return search results with titles, snippets, and usable destination URLs."""
    query = " ".join(str(query or "").split())[:500]
    if not query:
        return []
    try:
        response = requests.get("https://html.duckduckgo.com/html/", params={"q": query}, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        for result in soup.select(".result"):
            anchor = result.select_one(".result__title a")
            if not anchor:
                continue
            href = str(anchor.get("href", "")).strip()
            if href.startswith("//"):
                href = "https:" + href
            parsed = urlparse(href)
            if "duckduckgo.com" in (parsed.hostname or "") and parsed.path.startswith("/l/"):
                href = parse_qs(parsed.query).get("uddg", [href])[0]
            if urlparse(href).scheme not in {"http", "https"}:
                continue
            snippet = result.select_one(".result__snippet")
            results.append({"title": anchor.get_text(" ", strip=True)[:300], "snippet": snippet.get_text(" ", strip=True)[:1200] if snippet else "", "url": href})
            if len(results) >= max(1, min(int(limit), 10)):
                break
        return results
    except (requests.RequestException, ValueError, TypeError):
        return []

def open_web_page(url: str) -> dict[str, str]:
    """Read a public web page with redirect, local-network, and size checks."""
    response = _fetch_public(url)
    content_type = response.headers.get("Content-Type", "").lower()
    if "text/plain" in content_type:
        title, body = response.url, response.text
    else:
        soup = BeautifulSoup(response.text, "html.parser")
        for node in soup(["script", "style", "noscript", "svg", "nav", "footer", "header", "form"]):
            node.decompose()
        title = soup.title.get_text(" ", strip=True) if soup.title else response.url
        body = soup.get_text(" ", strip=True)
    return {"title": title[:300], "url": response.url, "text": " ".join(body.split())[:12000]}
