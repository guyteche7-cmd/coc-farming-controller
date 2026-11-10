import urllib.request
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
detail_url = 'https://clashofclans-layouts.com/plans/th_15/war_155.html'
req = urllib.request.Request(detail_url, headers=headers)
with urllib.request.urlopen(req) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

img_tags = re.findall(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', html)
print("Detail page images:", img_tags)
