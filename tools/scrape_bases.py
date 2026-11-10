import os
import re
import urllib.request
import time

base_url = "https://clashofclans-layouts.com"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def get_links(th, kind):
    # kind can be 'war', 'farm', 'trophy'
    url = f"{base_url}/plans/th_{th}/{kind}/"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        # find preview image links e.g. /pics/th15_plans/war/preview/th15_war_155.jpg or full pics /pics/th15_plans/war/th15_war_155.jpg
        # usually full images are at /pics/th{th}_plans/{kind}/th{th}_{kind}_{num}.jpg
        matches = set(re.findall(r'/pics/th\d+_plans/[a-zA-Z0-9_]+/(?:preview/)?(th\d+_[a-zA-Z0-9_]+\.(?:jpg|png))', html))
        return list(matches)
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []

for th in [15, 16, 17]:
    war_imgs = get_links(th, 'war')
    farm_imgs = get_links(th, 'farm')
    print(f"TH{th}: Found {len(war_imgs)} war imgs, {len(farm_imgs)} farm imgs")
    if war_imgs:
        print(f"Sample TH{th} war: {war_imgs[:3]}")
