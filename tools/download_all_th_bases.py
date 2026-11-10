import urllib.request
import re
import os
import cv2
import numpy as np

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

TARGET_DIR = r"C:\Users\ayush\.gemini\antigravity\scratch\coc-farming-controller\assets\downloads"
os.makedirs(TARGET_DIR, exist_ok=True)

# We will collect candidates for each Town Hall 15, 16, 17, 18
for th in [15, 16, 17, 18]:
    candidates = []
    # Collect from war (predominantly maxed / competitive defense designs)
    # and farm / defence (often partially upgraded / farming designs)
    for cat in ['war', 'defence', 'farm']:
        url = f'https://clashofclans-layouts.com/plans/th_{th}/{cat}/'
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                matches = re.findall(r'alt\s*=\s*["\']([^"\']+)["\']\s+[^>]*src=["\'](/pics/th\d+_plans/[^"\']+)["\']', html)
                for alt, src in matches:
                    clean_src = src.split('?')[0]
                    if not clean_src.startswith('http'):
                        img_url = f"https://clashofclans-layouts.com{clean_src}"
                    else:
                        img_url = clean_src
                    if img_url not in [c['url'] for c in candidates]:
                        candidates.append({
                            'cat': cat,
                            'alt': alt,
                            'url': img_url
                        })
        except Exception as e:
            print(f"Error fetching TH{th} {cat}: {e}")

    print(f"\n--- Processing TH{th}: {len(candidates)} total candidates found ---")
    
    # War layouts are competitive fully maxed bases with max walls & anti-3/anti-2 layouts
    war_candidates = [c for c in candidates if c['cat'] == 'war']
    # Farm / general defence layouts feature farming, mixed resource storage, partial progression
    farm_candidates = [c for c in candidates if c['cat'] in ['farm', 'defence']]

    # 10 Max bases
    max_count = 0
    for idx, c in enumerate(war_candidates[:10], start=1):
        filename = f"th{th}_max_base_{idx:02d}.jpg"
        filepath = os.path.join(TARGET_DIR, filename)
        try:
            req = urllib.request.Request(c['url'], headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                with open(filepath, 'wb') as f:
                    f.write(data)
                max_count += 1
                print(f"  [SAVED MAX] {filename} ({len(data)} bytes) from {c['url']}")
        except Exception as e:
            print(f"  [ERROR] Failed {filename}: {e}")

    # If war had less than 10, fill from defence
    if max_count < 10:
        for idx in range(max_count + 1, 11):
            if farm_candidates:
                c = farm_candidates.pop(0)
                filename = f"th{th}_max_base_{idx:02d}.jpg"
                filepath = os.path.join(TARGET_DIR, filename)
                try:
                    req = urllib.request.Request(c['url'], headers=headers)
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = resp.read()
                        with open(filepath, 'wb') as f:
                            f.write(data)
                        max_count += 1
                        print(f"  [SAVED MAX FILL] {filename} ({len(data)} bytes)")
                except Exception as e:
                    print(f"  [ERROR] Failed {filename}: {e}")

    # 10 Partially Max bases
    part_count = 0
    for idx, c in enumerate(farm_candidates[:10], start=1):
        filename = f"th{th}_partially_max_base_{idx:02d}.jpg"
        filepath = os.path.join(TARGET_DIR, filename)
        try:
            req = urllib.request.Request(c['url'], headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                with open(filepath, 'wb') as f:
                    f.write(data)
                part_count += 1
                print(f"  [SAVED PARTIAL] {filename} ({len(data)} bytes) from {c['url']}")
        except Exception as e:
            print(f"  [ERROR] Failed {filename}: {e}")

print("\nAll downloads completed!")
