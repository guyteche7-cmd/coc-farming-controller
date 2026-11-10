import urllib.request
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for th in [15, 16, 17, 18]:
    all_pics = set()
    for cat in ['war', 'defence', 'farm']:
        url = f'https://clashofclans-layouts.com/plans/th_{th}/{cat}/'
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                pics = re.findall(r'src=["\'](/pics/th\d+_plans/[^"\']+)["\']', html)
                for p in pics:
                    clean_p = p.split('?')[0]
                    all_pics.add(clean_p)
        except Exception as e:
            pass
    print(f"TH{th} unique base layouts available across categories: {len(all_pics)}")
    print("  Sample:", list(all_pics)[:3])
