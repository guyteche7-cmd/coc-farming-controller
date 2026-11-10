import urllib.request
import re
import cv2
import numpy as np

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def test_source(url):
    print(f"Testing {url}...")
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            urls = re.findall(r'https?://[^\s"\'<>]+\.(?:jpg|png|jpeg)', html)
            print(f"Found {len(urls)} image URLs")
            for u in urls[:10]:
                print("  ", u)
    except Exception as e:
        print("  Error:", e)

test_source('https://www.clashchamps.com/i-need-a-base/?searchKeyword=&townhall=15&baseType=0')
