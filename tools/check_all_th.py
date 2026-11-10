import urllib.request
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for th in [15, 16, 17, 18]:
    url = f'https://clashofclans-layouts.com/plans/th_{th}/'
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            pics = re.findall(r'src=["\'](/pics/th\d+_plans/[^"\']+)["\']', html)
            print(f"TH{th} main page pics: {len(pics)}")
            for p in pics[:5]:
                print(f"  {p}")
    except Exception as e:
        print(f"TH{th} main page error: {e}")
