from responce_init import ScrapeOpsFakeBrowserHeaderAgentMiddleware
import trafilatura
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from random import randint
import time
import os
from proxy_manager import get_random_proxy

# Default timeout for all HTTP requests (seconds)
REQUEST_TIMEOUT = 15


# ──────────────────────────────────────────────
# SHARED HELPERS
# ──────────────────────────────────────────────

def extract_og_image(soup):
    """Return the OpenGraph image URL from a BeautifulSoup-parsed page."""
    meta = soup.find("meta", property="og:image")
    if meta and meta.get("content"):
        return meta["content"]
    return None


def _trafilatura_extract(html: str):
    """Extract (text, title, image_url) from raw HTML using trafilatura.

    Trafilatura handles boilerplate removal, title, and OG-image extraction
    in one pass.  Site-specific functions call this first and only fall back
    to hand-coded BeautifulSoup selectors when needed.
    """
    text = trafilatura.extract(
        html,
        no_fallback=False,
        include_comments=False,
        include_tables=False,
    ) or ""

    meta = trafilatura.extract_metadata(html)
    title = ""
    image_url = None
    if meta:
        title = meta.title or ""
        image_url = getattr(meta, "image", None)

    return text, title, image_url


def _playwright_fetch(url: str, proxy_ip: str = None) -> str:
    """Fetch a JS-rendered page with Playwright's synchronous API.

    Safe to call from asyncio.to_thread() — sync_playwright() creates its own
    internal event loop and does not interfere with the outer async context.
    Replaces the old Selenium-based approach for skynewsarabia / almasryalyoum.
    """
    launch_kwargs = {"headless": True}
    if proxy_ip:
        launch_kwargs["proxy"] = {"server": f"http://{proxy_ip}"}

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="ar-EG,ar;q=0.9,en;q=0.8",
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            html = page.content()
        finally:
            browser.close()
    return html


# ──────────────────────────────────────────────
# ROUTER
# ──────────────────────────────────────────────

def init(url):
    """Route a URL to its site-specific scraper, or fall back to the default."""
    fetch_functions = {
        "skynewsarabia":    skynewsarabia,
        "english.ahram.org": english_ahram,
        "almasryalyoum":    almasryalyoum,
        "shorouknews":      shorouknews,
        "elwatannews":      elwatannews,
        "egyptindependent": egyptindependent,
        "dailynewsegypt":   dailynewsegypt,
        "masrawy":          masrawy,
        "madamasr":         madamasr,
        "egyptianstreets":  egyptianstreets,
        "bbc":              bbc,
        "cnn.com":          cnn,
        "aljazeera":        aljazeera,
        "youm7":            youm7,
        "albawabhnews":     albawabhnews,
        "foxnews":          foxnews,
        "theguardian":      theguardian,
        "reuters":          reuters,
        "codinghorror":     codinghorror,
    }

    for keyword, fetch_fn in fetch_functions.items():
        if keyword.lower() in url.lower():
            return fetch_fn(url)

    return defult(url)


# ──────────────────────────────────────────────
# HTTP HELPER (requests + ScrapeOps headers + proxy)
# ──────────────────────────────────────────────

def reqinti(method, url):
    middleware = ScrapeOpsFakeBrowserHeaderAgentMiddleware()
    request = requests.Request(method, url)
    middleware.process_request(request)

    use_proxy = os.getenv("USE_PROXY", "true").lower() == "true"
    max_retries = 3 if use_proxy else 1

    for attempt in range(max_retries):
        try:
            time.sleep(randint(1, 3))
            with requests.Session() as session:
                if use_proxy:
                    proxy_ip = get_random_proxy()
                    if proxy_ip:
                        proxies = {"http": f"http://{proxy_ip}", "https": f"http://{proxy_ip}"}
                        session.proxies.update(proxies)
                return session.send(request.prepare(), timeout=REQUEST_TIMEOUT)
        except Exception as e:
            print(f"[reqinti] Proxy attempt {attempt + 1} failed: {e}")

    with requests.Session() as session:
        return session.send(request.prepare(), timeout=REQUEST_TIMEOUT)


# ──────────────────────────────────────────────
# DEFAULT SCRAPER
# ──────────────────────────────────────────────

def defult(url):
    middleware = ScrapeOpsFakeBrowserHeaderAgentMiddleware()
    request = requests.Request("GET", url)
    middleware.process_request(request)

    use_proxy = os.getenv("USE_PROXY", "true").lower() == "true"
    max_retries = 3 if use_proxy else 1

    response = None
    for attempt in range(max_retries):
        try:
            time.sleep(randint(1, 3))
            with requests.Session() as session:
                if use_proxy:
                    proxy_ip = get_random_proxy()
                    if proxy_ip:
                        proxies = {"http": f"http://{proxy_ip}", "https": f"http://{proxy_ip}"}
                        session.proxies.update(proxies)
                response = session.send(request.prepare(), timeout=REQUEST_TIMEOUT)
                break
        except Exception as e:
            print(f"[defult] Proxy attempt {attempt + 1} failed: {e}")

    if not response:
        with requests.Session() as session:
            response = session.send(request.prepare(), timeout=REQUEST_TIMEOUT)

    return _trafilatura_extract(response.text)


# ──────────────────────────────────────────────
# SITE-SPECIFIC SCRAPERS
# ──────────────────────────────────────────────

def youm7(url):
    response = reqinti("GET", url)
    text, title, image_url = _trafilatura_extract(response.text)

    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        image_url = extract_og_image(soup)
        if not image_url:
            img_cont = soup.find("div", class_="img-cont")
            if img_cont:
                img_el = img_cont.find("img", class_="img-responsive")
                image_url = img_el["src"] if img_el else "https://img.youm7.com/images/graphics/logoyoum7.png"
            else:
                image_url = "https://img.youm7.com/images/graphics/logoyoum7.png"

    return text, title, image_url


def skynewsarabia(url):
    """JS-heavy — rendered with Playwright instead of Selenium."""
    if not url:
        return "", "", None

    use_proxy = os.getenv("USE_PROXY", "true").lower() == "true"
    proxy_ip = get_random_proxy() if use_proxy else None

    html = _playwright_fetch(url, proxy_ip)
    text, title, image_url = _trafilatura_extract(html)

    if not image_url:
        soup = BeautifulSoup(html, "html.parser")
        image_url = extract_og_image(soup)
    if not image_url:
        soup = BeautifulSoup(html, "html.parser")
        img_tag = soup.find("img", class_="main-image")
        image_url = img_tag["src"] if img_tag else None

    return text, title, image_url


def english_ahram(url):
    response = reqinti("GET", url)
    text, title, image_url = _trafilatura_extract(response.text)

    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        image_url = extract_og_image(soup)
    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        img_tag = soup.find("img", class_="img-fluid inner-main")
        image_url = img_tag["src"] if img_tag else None

    return text, title, image_url


def almasryalyoum(url):
    """JS-heavy — rendered with Playwright instead of Selenium."""
    if not url:
        return "", "", None

    use_proxy = os.getenv("USE_PROXY", "true").lower() == "true"
    proxy_ip = get_random_proxy() if use_proxy else None

    html = _playwright_fetch(url, proxy_ip)
    text, title, image_url = _trafilatura_extract(html)

    if not image_url:
        soup = BeautifulSoup(html, "html.parser")
        image_url = extract_og_image(soup)
    if not image_url:
        soup = BeautifulSoup(html, "html.parser")
        article_img_div = soup.find("div", class_="articleimg")
        if article_img_div:
            img_tag = article_img_div.find("img")
            image_url = img_tag["src"] if img_tag else None

    return text, title, image_url


def shorouknews(url):
    response = reqinti("GET", url)
    text, title, image_url = _trafilatura_extract(response.text)

    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        image_url = extract_og_image(soup)
    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        img_tag = soup.find("img", id="Body_Body_imageMain")
        image_url = img_tag["src"] if img_tag else None

    return text, title, image_url


def elwatannews(url):
    """Custom extractor — trafilatura misses the article-subject div on this site."""
    response = reqinti("GET", url)
    soup = BeautifulSoup(response.text, "html.parser")

    article_div = soup.find("div", class_="article-subject")
    title_tag = soup.find("h1")
    title = title_tag.text if title_tag else ""
    text = article_div.get_text(strip=True) if article_div else ""

    image_url = extract_og_image(soup)
    if not image_url:
        div_tag = soup.find("div", class_="article-subject-image")
        if div_tag and div_tag.find("img"):
            image_url = div_tag.find("img")["src"]

    return text, title, image_url


def egyptindependent(url):
    response = reqinti("GET", url)
    text, title, image_url = _trafilatura_extract(response.text)

    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        image_url = extract_og_image(soup)
    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        div_tag = soup.find("div", class_="featured-area-inner")
        if div_tag and div_tag.find("img"):
            image_url = div_tag.find("img")["src"]

    return text, title, image_url


def dailynewsegypt(url):
    response = reqinti("GET", url)
    text, title, image_url = _trafilatura_extract(response.text)

    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        image_url = extract_og_image(soup)
    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        div_tag = soup.find("div", class_="featured-lightbox-trigger")
        if div_tag and div_tag.find("img"):
            image_url = div_tag.find("img")["src"]
        else:
            image_url = "https://d1b3667xvzs6rz.cloudfront.net/2023/10/Dailynews-logo.png"

    return text, title, image_url


def masrawy(url):
    response = reqinti("GET", url)
    text, title, image_url = _trafilatura_extract(response.text)

    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        image_url = extract_og_image(soup)
    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        div_tag = soup.find("div", class_="image-wrap")
        if div_tag and div_tag.find("img"):
            image_url = div_tag.find("img")["src"]
        else:
            img_tag = soup.find("img", class_="img-responsive")
            image_url = img_tag["src"] if img_tag else "https://th.bing.com/th/id/OIP.vKF9uBSgjCZYXM-n28mBEAHaEK?rs=1&pid=ImgDetMain"

    return text, title, image_url


def madamasr(url):
    """Custom extractor — trafilatura misses the article_body div on this site."""
    response = reqinti("GET", url)
    soup = BeautifulSoup(response.text, "html.parser")

    body_div = soup.find("div", class_="article_body")
    text = body_div.get_text() if body_div else ""
    title_div = soup.find("div", class_="span12")
    title = title_div.get_text(strip=False) if title_div else ""

    image_url = extract_og_image(soup)
    if not image_url:
        div_tag = soup.find("div", class_="article_photo")
        if div_tag and div_tag.find("img"):
            image_url = div_tag.find("img")["src"]

    return text, title, image_url


def egyptianstreets(url):
    response = reqinti("GET", url)
    text, title, image_url = _trafilatura_extract(response.text)

    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        image_url = extract_og_image(soup)
    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        img_tag = soup.find("img", class_="wp-post-image")
        image_url = img_tag["src"] if img_tag else "https://egyptianstreets.com/wp-content/uploads/2022/07/egysinai.jpg"

    return text, title, image_url


def bbc(url):
    """Custom extractor — BBC uses data-component attributes, not standard article markup."""
    response = reqinti("GET", url)
    soup = BeautifulSoup(response.text, "html.parser")

    blocks = soup.find_all(attrs={"data-component": "text-block"})
    if not blocks:
        blocks = soup.find_all(attrs={"dir": "rtl"})
    text = " ".join(el.get_text(strip=False) for el in blocks)

    h1 = soup.find("h1")
    title = h1.get_text(strip=False) if h1 else ""

    img_classes = [
        "bbc-139onq", "sc-13b8515c-0 hbOWRP", "ssrcss-11yxrdo-Image",
        "p_holding_image", "sc-c-herospace__image", "holding_image",
    ]
    image_url = extract_og_image(soup)
    if not image_url:
        for cls in img_classes:
            img_tag = soup.find("img", class_=cls)
            if img_tag:
                if cls == "p_holding_image" and "srcset" in img_tag.attrs:
                    image_url = img_tag["srcset"]
                elif "src" in img_tag.attrs:
                    image_url = img_tag["src"]
                if image_url:
                    break
        if not image_url:
            image_url = "https://ichef.bbci.co.uk/news/1024/cpsprodpb/9A90/production/_97086593_defaultimage.png.webp"

    return text, title, image_url


def cnn(url):
    response = reqinti("GET", url)
    text, title, image_url = _trafilatura_extract(response.text)

    # CNN live-story pages embed content in a specific wrapper trafilatura may miss
    if not text:
        soup = BeautifulSoup(response.text, "html.parser")
        wrapper = soup.find("div", class_="live-story-post__wrapper")
        if wrapper:
            text = wrapper.get_text()

    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        image_url = extract_og_image(soup)
    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        for cls in ["flipboard-image", "vVA5xXbuV_", "image__dam-img", "image_live-story__dam-img"]:
            img_tag = soup.find("img", class_=cls)
            if img_tag:
                image_url = img_tag.get("src")
                if image_url:
                    break

    return text, title, image_url


def aljazeera(url):
    """Custom extractor — Al Jazeera's wysiwyg div is reliably structured."""
    response = reqinti("GET", url)
    soup = BeautifulSoup(response.text, "html.parser")

    article_body = soup.find("div", class_="wysiwyg")
    header = soup.find("header", class_="article-header")
    title = header.find("h1").get_text(strip=False) if header and header.find("h1") else ""

    text = ""
    if article_body:
        for child in article_body.children:
            if getattr(child, "name", None) not in ["section", "figure"]:
                text += "\n" + child.get_text()

    image_url = extract_og_image(soup)
    if not image_url:
        div_tag = soup.find("div", class_="responsive-image")
        if div_tag and div_tag.find("img"):
            image_url = "https://www.aljazeera.com/" + div_tag.find("img")["src"]

    return text, title, image_url


def albawabhnews(url):
    response = reqinti("GET", url)
    text, title, image_url = _trafilatura_extract(response.text)

    default_image = "https://www.albawabhnews.com/themes/bawaba/assets/images/logo.png"

    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        image_url = extract_og_image(soup)
    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        figure_tag = soup.find("figure", class_="main-img")
        img_tag = figure_tag.find("img") if figure_tag else None
        if img_tag and "srcset" in img_tag.attrs:
            image_url = "https://www.albawabhnews.com" + img_tag["srcset"].split(",")[0].split()[0]
        else:
            image_url = default_image

    return text, title, image_url


def foxnews(url):
    response = reqinti("GET", url)
    text, title, image_url = _trafilatura_extract(response.text)

    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        image_url = extract_og_image(soup)
    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        img_tag = soup.find("img")
        image_url = img_tag["src"] if img_tag else None

    return text, title, image_url


def theguardian(url):
    response = reqinti("GET", url)
    text, title, image_url = _trafilatura_extract(response.text)

    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        image_url = extract_og_image(soup)
    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        pic_tag = soup.find("picture")
        if pic_tag and pic_tag.find("source"):
            image_url = pic_tag.find("source").get("srcset")

    return text, title, image_url


def reuters(url):
    response = reqinti("GET", url)
    text, title, image_url = _trafilatura_extract(response.text)

    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        image_url = extract_og_image(soup)
    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        img_tag = soup.find("img")
        image_url = img_tag["src"] if img_tag else None

    return text, title, image_url


def codinghorror(url):
    default_image = "https://blog.codinghorror.com/assets/images/codinghorror-app-icon.png?v=c8e4b9197a"
    response = reqinti("GET", url)
    text, title, image_url = _trafilatura_extract(response.text)

    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        image_url = extract_og_image(soup)
    if not image_url:
        soup = BeautifulSoup(response.text, "html.parser")
        img_tag = soup.find("img")
        image_url = img_tag["src"] if img_tag else default_image

    return text, title, image_url
