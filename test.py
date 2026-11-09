from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from responce_init import ScrapeOpsFakeBrowserHeaderAgentMiddleware
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from goose3 import Goose
import requests
from random import randint
from urllib.parse import urlencode
from BrowserInit import ScrapeOpsFakeBrowserHeaderAgentMiddlewareSL
from langdetect import detect
import time


# def get_linkes(rss):
#     rss_feed_url=rss
#     middleware = ScrapeOpsFakeBrowserHeaderAgentMiddleware()
#
#     request = requests.Request('GET', rss_feed_url)
#
#     middleware.process_request(request)
#
#     with requests.Session() as session:
#         response = session.send(request.prepare())
#     soup = BeautifulSoup(response.content, 'xml')
#
#     items = soup.find_all('item')
#
#     links = [item.find('link').text for item in items]
#     return links
# urls=(get_linkes("https://www.youm7.com/rss/SectionRss?SectionID=245"))

urls=["https://www.almasryalyoum.com/news/details/3168220"]
count=0
def reqinti(type,url):
    middleware = ScrapeOpsFakeBrowserHeaderAgentMiddleware()
    url = url

    # Create your request object (assuming you're using requests library)
    request = requests.Request(type, url)

    # Process the request with the middleware
    middleware.process_request(request)

    # Create a session and send the request
    with requests.Session() as session:
        response = session.send(request.prepare())
    return response
for url in urls:
    if url:

        middleware = ScrapeOpsFakeBrowserHeaderAgentMiddlewareSL()
        options = Options()

        # Process request to add fake browser headers
        middleware.process_request(options)

        # Initialize the WebDriver with the custom options
        driver = webdriver.Chrome()

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
    # middleware = ScrapeOpsFakeBrowserHeaderAgentMiddlewareSL()
    # options = Options()
    #
    # # Process request to add fake browser headers
    # middleware.process_request(options)
    #
    # # Initialize the WebDriver with the custom options
    # driver = webdriver.Chrome(options=options)
    # # Wait for the main image to load
    # try:
    #     driver.get(url)
    #     WebDriverWait(driver, 20)
    #
    #     # Get the page source after the content has loaded
    #     html_content = driver.page_source
    #
    #     # Parse the HTML content with BeautifulSoup
    #     soup = BeautifulSoup(html_content, 'html.parser')
    #
    #     # Extract the main image
    #     img_tag = soup.find('img', class_='main-image') or soup.find('img', class_='img-fluid inner-main')
    #     img_src = img_tag['src'] if img_tag else "Image not found"
    #
    #     # Use Goose to extract the cleaned text
    #     g = Goose()
    #     extract = g.extract(raw_html=html_content)
    #     soup = BeautifulSoup(html_content, 'html.parser')
    #
    #     img_tag = soup.find('img', class_='img-fluid inner-main')
    #     img_src = img_tag['src'] if img_tag else None
    # finally:
    #     # Close the WebDriver
    #     driver.quit()
    count+=1
    end_time=time.time()
    print("*"*40)
    print(count)
    print(extract.cleaned_text,"\n tex \n", extract.title,"\n title \n",img_src,"Total Time",end_time)






