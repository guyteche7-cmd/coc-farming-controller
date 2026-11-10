import urllib.request
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

url = 'https://clashcodes.com/bases/th15-war'
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=10) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

imgs = re.findall(r'<img[^>]+src="([^"]+)"', html)
print("All img src on page:")
for i in imgs:
    print(" ", i)
