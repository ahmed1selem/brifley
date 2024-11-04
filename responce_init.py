import requests
from random import randint
from urllib.parse import urlencode


class ScrapeOpsFakeBrowserHeaderAgentMiddleware:
    def __init__(self, scrapeops_num_results=None):
        self.scrapeops_api_key = '483dd2ae-8c6f-4f6a-82a6-82317e7d0ac0'
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

    def process_request(self, request):
        random_browser_header = self._get_random_browser_header()

        headers = {
            'accept-language': random_browser_header['accept-language'],
            'sec-fetch-user': random_browser_header['sec-fetch-user'],
            'sec-fetch-mod': random_browser_header.get('sec-fetch-mod', 'navigate'),
            'sec-fetch-site': random_browser_header['sec-fetch-site'],
            'sec-ch-ua-platform': random_browser_header['sec-ch-ua-platform'],
            'sec-ch-ua-mobile': random_browser_header['sec-ch-ua-mobile'],
            'sec-ch-ua': random_browser_header['sec-ch-ua'],
            'accept': random_browser_header['accept'],
            'user-agent': random_browser_header['user-agent'],
            'upgrade-insecure-requests': random_browser_header.get('upgrade-insecure-requests')
        }
        request.headers.update(headers)
