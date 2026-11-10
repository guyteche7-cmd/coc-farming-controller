import urllib.request
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
url = 'https://clashofclans-layouts.com/plans/th_15/war/'
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

# Print hrefs and onclicks
hrefs = re.findall(r'href="([^"]+)"', html)
base_pages = [h for h in hrefs if '/plan/' in h or 'th_15' in h]
print("Base pages:", base_pages[:10])

# Also check image tags and dimensions
img_tags = re.findall(r'<img[^>]+>', html)
for img in img_tags[:5]:
    print("IMG TAG:", img)
