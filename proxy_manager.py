import requests
import random
import time

PROXY_API_URL = 'https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all'
_cached_proxies = []
_last_fetch_time = 0
CACHE_TTL = 3600  # 1 hour

def get_random_proxy():
    """
    Returns a random HTTP proxy in the format 'IP:PORT'.
    Automatically fetches and caches proxies from ProxyScrape.
    """
    global _cached_proxies, _last_fetch_time
    
    current_time = time.time()
    
    # Fetch new proxies if cache is empty or older than TTL
    if not _cached_proxies or (current_time - _last_fetch_time) > CACHE_TTL:
        try:
            print("Fetching fresh free proxies from ProxyScrape...")
            response = requests.get(PROXY_API_URL, timeout=10)
            if response.status_code == 200:
                raw_proxies = response.text.strip().split('\r\n')
                # Filter out empty strings
                _cached_proxies = [p for p in raw_proxies if p]
                _last_fetch_time = current_time
                print(f"Successfully loaded {len(_cached_proxies)} free proxies.")
        except Exception as e:
            print(f"Failed to fetch proxies: {e}")
            
    if not _cached_proxies:
        return None
        
    return random.choice(_cached_proxies)

if __name__ == '__main__':
    # Test
    print("Random Proxy:", get_random_proxy())
