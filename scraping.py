from responce_init import ScrapeOpsFakeBrowserHeaderAgentMiddleware
import requests
from goose3 import Goose
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from BrowserInit import ScrapeOpsFakeBrowserHeaderAgentMiddlewareSL
from random import randint
from urllib.parse import urlencode
import time
import os
from proxy_manager import get_random_proxy

# Default timeout for all HTTP requests (seconds)
REQUEST_TIMEOUT = 15
def init(url):
    """Route a URL to its site-specific scraper, or fall back to the default."""
    fetch_functions = {
        "skynewsarabia": skynewsarabia,
        "english.ahram.org": english_ahram,
        "almasryalyoum": almasryalyoum,
        "shorouknews": shorouknews,
        "elwatannews": elwatannews,
        "egyptindependent": egyptindependent,
        "dailynewsegypt": dailynewsegypt,
        "masrawy": masrawy,
        "madamasr": madamasr,
        "egyptianstreets": egyptianstreets,
        "bbc": bbc,
        "cnn.com": cnn,
        "aljazeera": aljazeera,
        "youm7": youm7,
        "albawabhnews": albawabhnews,
        "foxnews": foxnews,
        "theguardian": theguardian,
        "reuters": reuters,
        "codinghorror": codinghorror
    }

    # Find the matching scraper for this URL.
    # The original for/else logic had a Python gotcha: the else clause
    # ran on every non-matching iteration, not just when no match was found.
    for keyword, fetch_function in fetch_functions.items():
        if keyword.lower() in url.lower():
            cleaned, title, img = fetch_function(url)
            return cleaned, title, img

    # No keyword matched — use the default scraper
    return defult(url)

def reqinti(type, url):
    middleware = ScrapeOpsFakeBrowserHeaderAgentMiddleware()

    request = requests.Request(type, url)
    middleware.process_request(request)

    use_proxy = os.getenv("USE_PROXY", "true").lower() == "true"
    max_retries = 3 if use_proxy else 1

    for attempt in range(max_retries):
        try:
            # Timer for Rate Limiting
            time.sleep(randint(1, 3))
            with requests.Session() as session:
                if use_proxy:
                    proxy_ip = get_random_proxy()
                    if proxy_ip:
                        proxies = {'http': f"http://{proxy_ip}", 'https': f"http://{proxy_ip}"}
                        session.proxies.update(proxies)
                response = session.send(request.prepare(), timeout=REQUEST_TIMEOUT)
                return response
        except Exception as e:
            print(f"[reqinti] Proxy attempt {attempt+1} failed: {e}")
            pass

    # Safe fallback direct connection
    with requests.Session() as session:
        return session.send(request.prepare(), timeout=REQUEST_TIMEOUT)

def defult(url):
    middleware = ScrapeOpsFakeBrowserHeaderAgentMiddleware()

    request = requests.Request('GET', url)
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
                        proxies = {'http': f"http://{proxy_ip}", 'https': f"http://{proxy_ip}"}
                        session.proxies.update(proxies)
                response = session.send(request.prepare(), timeout=REQUEST_TIMEOUT)
                break
        except Exception as e:
            print(f"[defult] Proxy attempt {attempt+1} failed: {e}")
            pass

    if not response:
        with requests.Session() as session:
            response = session.send(request.prepare(), timeout=REQUEST_TIMEOUT)

    g = Goose()
    extract = g.extract(raw_html=response.text)
    return extract.cleaned_text, extract.title, "   "

def youm7(url):

    response = reqinti("GET",url)
    g = Goose()
    extract = g.extract(raw_html=response.text)
    soup = BeautifulSoup(response.text, 'html.parser')

    article_img = soup.find('div', class_="img-cont")
    if article_img:
        article_img=article_img.find("img",class_="img-responsive")["src"]
    else:
        article_img="https://img.youm7.com/images/graphics/logoyoum7.png"
   
    return extract.cleaned_text, extract.title, article_img

def skynewsarabia(url):
    

  if url:
    

    middleware = ScrapeOpsFakeBrowserHeaderAgentMiddlewareSL()
    options = Options()

    # Process request to add fake browser headers
    middleware.process_request(options)

    # Timer for Rate Limiting
    time.sleep(randint(1, 3))

    if os.getenv("USE_PROXY", "true").lower() == "true":
        proxy_ip = get_random_proxy()
        if proxy_ip:
            options.add_argument(f'--proxy-server=http://{proxy_ip}')

    # Initialize the WebDriver with the custom options
    driver = webdriver.Chrome(options=options)  

    # Open the webpage
    driver.get(url)
    article_text=""
    # Wait for the main image to load
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'img.main-image'))
        )

        # Get the page source after the content has loaded
        html_content = driver.page_source

        # Parse the HTML content with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract the main image
        img_tag = soup.find('img', class_='main-image')
        img_src = img_tag['src'] if img_tag else None

        # Use Goose to extract the cleaned text
        g = Goose()
        extract = g.extract(raw_html=html_content)
        article_text += "\n" + extract.cleaned_text


    finally:
        # Close the WebDriver
        driver.quit()
    return article_text, extract.title,img_src


def english_ahram(url):
    response = reqinti("GET", url)
    g = Goose()
    extract = g.extract(raw_html=response.text)
    soup = BeautifulSoup(response.text, 'html.parser')

    img_tag = soup.find('img', class_='img-fluid inner-main')
    img_src = img_tag['src'] if img_tag else None

    return extract.cleaned_text,extract.title,img_src


def almasryalyoum(url):
    if url:

        middleware = ScrapeOpsFakeBrowserHeaderAgentMiddlewareSL()
        options = Options()

        # Process request to add fake browser headers
        middleware.process_request(options)

        # Timer for Rate Limiting
        time.sleep(randint(1, 3))

        if os.getenv("USE_PROXY", "true").lower() == "true":
            proxy_ip = get_random_proxy()
            if proxy_ip:
                options.add_argument(f'--proxy-server=http://{proxy_ip}')

        # Initialize the WebDriver with the custom options
        driver = webdriver.Chrome(options=options)

        # Open the webpage
        driver.get(url)
        article_text = ""
        # Wait for the main image to load
        try:
            WebDriverWait(driver, 10)

            # Get the page source after the content has loaded
            html_content = driver.page_source

            # Parse the HTML content with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')

            g = Goose()
            extract = g.extract(raw_html=html_content)
            article_img_div = soup.find('div', class_='articleimg')
            img_tag = article_img_div.find('img')

            img_src = img_tag['src'] if img_tag else None
        finally:
            # Close the WebDriver
            driver.quit()
    return extract.cleaned_text, extract.title,img_src


def shorouknews(url):
    response = reqinti("GET", url)
    g = Goose()
    extract = g.extract(raw_html=response.text)
    soup = BeautifulSoup(response.text, 'html.parser')

    article_img = soup.find('img', id='Body_Body_imageMain')["src"]

    return extract.cleaned_text, extract.title,article_img


def elwatannews(url):
    response = reqinti("GET", url)
    soup = BeautifulSoup(response.text, 'html.parser')

    article_subject_div = soup.find('div', class_='article-subject')


    article_img = soup.find('div',class_="article-subject-image").find("img")["src"]

    title = soup.find('h1').text


    # Extract all text within the <div> and its descendants
    text_content = article_subject_div.get_text(strip=True)

    return text_content,title,article_img


def egyptindependent(url):
    response = reqinti("GET", url)
    g = Goose()
    extract = g.extract(raw_html=response.text)
    soup = BeautifulSoup(response.text, 'html.parser')

    article_img = soup.find('div',class_="featured-area-inner").find("img")["src"]



    return extract.cleaned_text,extract.title,article_img



def dailynewsegypt(url):
    response = reqinti("GET", url)
    g = Goose()
    extract = g.extract(raw_html=response.text)
    soup = BeautifulSoup(response.text, 'html.parser')

    article_img = soup.find('div',class_="featured-lightbox-trigger").find("img")
    if article_img:
        article_img=article_img["src"]
    else:
        article_img="https://d1b3667xvzs6rz.cloudfront.net/2023/10/Dailynews-logo.png"
    return extract.cleaned_text, extract.title,article_img


def masrawy(url):
    response = reqinti("GET", url)
    g = Goose()
    extract = g.extract(raw_html=response.text)
    soup = BeautifulSoup(response.text, 'html.parser')
    article_img = soup.find('div',class_="image-wrap")
    if article_img :    
        article_img=article_img.find("img")["src"]
    if not article_img:
        article_img = soup.find('img',class_="img-responsive")
        if article_img:
                article_img=article_img["src"]
    if not article_img:
        article_img="https://th.bing.com/th/id/OIP.vKF9uBSgjCZYXM-n28mBEAHaEK?rs=1&pid=ImgDetMain"
    
    return extract.cleaned_text, extract.title,article_img


def madamasr(url):
    response = reqinti("GET", url)
    soup = BeautifulSoup(response.text, 'html.parser')
    # Find the div with class "article_body"
    article_body = soup.find('div', class_='article_body').get_text()
    title = soup.find('div', class_='span12').get_text(strip=False)
    img = soup.find("div", class_="article_photo").find("img")["src"]
    return article_body, title,img


def egyptianstreets(url):
    response = reqinti("GET", url)
    g = Goose()
    extract = g.extract(raw_html=response.text)
    soup = BeautifulSoup(response.text, 'html.parser')
    article_img = soup.find('img', class_="wp-post-image")
    if article_img:
        article_img=article_img["src"]
    else:
        article_img="https://egyptianstreets.com/wp-content/uploads/2022/07/egysinai.jpg"
        
    return extract.cleaned_text, extract.title,article_img


def bbc(url):
    response = reqinti("GET", url)
    soup = BeautifulSoup(response.text, 'html.parser')
    # Find the div with class "article_body"
    article_body = soup.find_all(attrs={"data-component": "text-block"})
    if not article_body:
            article_body = soup.find_all(attrs={"dir": "rtl"})
    text = " ".join([element.get_text(strip=False) for element in article_body])

    title = soup.find('h1')
    if not title :
        title = soup.find('h1')
    title=title.get_text(strip=False)
    img_classes = [
    "bbc-139onq",
    "sc-13b8515c-0 hbOWRP",
    "ssrcss-11yxrdo-Image",
    "p_holding_image",
    "sc-c-herospace__image",
    "holding_image",
]
    img = None

# Iterate through the class names to find the image
    for class_name in img_classes:
     img_tag = soup.find("img", class_=class_name)
     if img_tag:
        # Check if the class name is "p_holding_image" and use "srcset" attribute
        if class_name == "p_holding_image" and "srcset" in img_tag.attrs:
            img = img_tag["srcset"]
        # Otherwise, use the "src" attribute
        elif "src" in img_tag.attrs:
            img = img_tag["src"]
        if img:
            break


    if not img:
        img = "https://ichef.bbci.co.uk/news/1024/cpsprodpb/9A90/production/_97086593_defaultimage.png.webp"



    return text, title,img


def cnn(url):
    response = reqinti("GET", url)
    g = Goose()
    extract = g.extract(raw_html=response.text)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    text=extract.cleaned_text
    if text=="":
        text = soup.find('div', class_="live-story-post__wrapper").get_text()

    default_image_url = "https://th.bing.com/th/id/OIP.RF2XLEe6X2ETeNwatxtogwHaEo?rs=1&pid=ImgDetMain"

    image_classes = [
    "flipboard-image",
    "vVA5xXbuV_",
    "image__dam-img",
    "image_live-story__dam-img"]
    article_img = None



    for class_name in image_classes:
        img_tag = soup.find('img', class_=class_name)
        if img_tag:
            article_img = img_tag.get("src")
            if article_img:
                break
    if not article_img:
        article_img = default_image_url

    return text, extract.title,article_img


def aljazeera(url):
    response = reqinti("GET", url)
    text = ""
    soup = BeautifulSoup(response.text, 'html.parser')
    # Find the div with class "article_body"
    article_body = soup.find('div', class_='wysiwyg')
    title = soup.find('header', class_='article-header').find("h1").get_text(strip=False)
    # Iterate over each child element inside the article_body
    for child in article_body.children:
        # Check if the child is a Tag (HTML element)
        if child.name not in ["section", "figure"]:
            # Extract the text of the child element, preserving white spaces
            text += "\n" + child.get_text()
    img = soup.find("div", class_="responsive-image").find("img")["src"]
    img = f"https://www.aljazeera.com/{img}"
    return text, title,img
    
def albawabhnews(url):
    response = reqinti("GET", url)
    g = Goose()
    extract = g.extract(raw_html=response.text)
    soup = BeautifulSoup(response.text, 'html.parser')
    article_img=None

    text=extract.cleaned_text
    

    default_image_url = "https://www.albawabhnews.com/themes/bawaba/assets/images/logo.png"



    figure_tag = soup.find('figure', class_="main-img")
    if figure_tag:
        img_tag = figure_tag.find('img')
    if img_tag:
        article_img = img_tag['srcset'].split(',')[0].split()[0]
        article_img = "https://www.albawabhnews.com" + article_img
    else :
        article_img=default_image_url
    return (text, extract.title,article_img)
    
def foxnews(url):
    response = reqinti("GET", url)
    g = Goose()
    extract = g.extract(raw_html=response.text)
    soup = BeautifulSoup(response.text, 'html.parser')
    article_img=None

    text=extract.cleaned_text
    

    default_image_url = "data:image/jpeg;base64,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"


    article_img = soup.find('img')
    if article_img:
        article_img = article_img['src']
    else:
        article_img=default_image_url

    
    return (text, extract.title,article_img)
 
 
def theguardian(url):
    response = reqinti("GET", url)
    g = Goose()
    extract = g.extract(raw_html=response.text)
    soup = BeautifulSoup(response.text, 'html.parser')
    article_img=None

    text=extract.cleaned_text

    default_image_url = "data:image/jpeg;base64,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"


    article_img = soup.find('picture')
    if article_img:
        article_img=article_img.find("source")
        article_img = article_img['srcset']
    else:
        article_img=default_image_url
    return (text, extract.title,article_img)
 
 
def reuters(url):
    response = reqinti("GET", url)
    g = Goose()
    extract = g.extract(raw_html=response.text)
    soup = BeautifulSoup(response.text, 'html.parser')
    article_img=None

    text=extract.cleaned_text
    

    default_image_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTQgZeakdB4XramCkFj55d-nfcb7ybVmjwZaVeHXCiBSqUzpkisHpFWhqM5FA2jNkDjugI&usqp=CAU"

    
    article_img = soup.find('img')
    if article_img:
        article_img = article_img['src']
    else:
        default_image_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTQgZeakdB4XramCkFj55d-nfcb7ybVmjwZaVeHXCiBSqUzpkisHpFWhqM5FA2jNkDjugI&usqp=CAU"

    return (text, extract.title,article_img)
 
def codinghorror(url):
    response = reqinti("GET", url)
    g = Goose()
    extract = g.extract(raw_html=response.text)
    soup = BeautifulSoup(response.text, 'html.parser')
    article_img=None

    text=extract.cleaned_text
    

    default_image_url = "https://blog.codinghorror.com/assets/images/codinghorror-app-icon.png?v=c8e4b9197a"


   
    article_img = soup.find('img')
    if article_img:
        article_img = article_img['src']
    else:
        article_img=default_image_url
    return text ,extract.title,article_img
