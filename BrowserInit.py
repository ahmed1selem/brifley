import os
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

class ScrapeOpsFakeBrowserHeaderAgentMiddlewareSL:
    def __init__(self, scrapeops_num_results=None):
        self.scrapeops_api_key = os.getenv("SCRAPEOPS_API_KEY", "483dd2ae-8c6f-4f6a-82a6-82317e7d0ac0")
        self.scrapeops_endpoint = 'http://headers.scrapeops.io/v1/browser-headers'
        self.scrapeops_num_results = scrapeops_num_results
        self.headers_list = []
        self._get_headers_list()

    def _get_headers_list(self):
        payload = {'api_key': self.scrapeops_api_key}
        if self.scrapeops_num_results is not None:
            payload['num_results'] = self.scrapeops_num_results
        response = requests.get(self.scrapeops_endpoint, params=urlencode(payload))
        json_response = response.json()
        self.headers_list = json_response.get('result', [])

    def _get_random_browser_header(self):
        random_index = randint(0, len(self.headers_list) - 1)
        return self.headers_list[random_index]

    def process_request(self, options):
        random_browser_header = self._get_random_browser_header()

        # Add headers to Selenium options
        for header, value in random_browser_header.items():
            if header and value:
                options.add_argument(f'{header}={value}')
                print(header)
