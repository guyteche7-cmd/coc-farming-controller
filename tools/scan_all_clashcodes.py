import urllib.request
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for th in [15, 16, 17, 18]:
    for cat in ['war', 'farming', 'legend', 'hybrid', '']:
        suffix = f"-{cat}" if cat else ""
        url = f"https://clashcodes.com/bases/th{th}{suffix}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                imgs = re.findall(r'/uploads/bases/[^"]+\.(?:jpg|png|webp)', html)
                print(f"TH{th}{suffix}: {len(imgs)} base images")
        except Exception as e:
            # print(f"TH{th}{suffix}: {e}")
            pass
