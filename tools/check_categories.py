import urllib.request
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

url = 'https://clashofclans-layouts.com/plans/th_15/'
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=5) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

# find navigation / categories
nav = re.findall(r'href="(/plans/th_15/[^"]+)"', html)
print("TH15 categories:", sorted(list(set(nav))))
