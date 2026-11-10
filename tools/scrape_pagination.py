import urllib.request
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for th in [15, 16, 17, 18]:
    for cat in ['war', 'farm', 'defence']:
        for page in ['', 'page_2.html', 'page_3.html']:
            p_suffix = f"{page}" if page else ""
            url = f'https://clashofclans-layouts.com/plans/th_{th}/{cat}/{p_suffix}'
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    html = resp.read().decode('utf-8', errors='ignore')
                    pics = re.findall(r'src=["\'](/pics/th\d+_plans/[^"\']+)["\']', html)
                    if pics:
                        print(f"TH{th} {cat} {page}: {len(pics)} pics")
            except Exception as e:
                pass
