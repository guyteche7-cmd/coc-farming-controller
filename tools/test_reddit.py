import urllib.request
import json
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for sub in ['COCBaseLayouts', 'ClashOfClans']:
    url = f'https://www.reddit.com/r/{sub}/search.json?q=TH15&restrict_sr=1&sort=top&limit=25'
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            children = data.get('data', {}).get('children', [])
            print(f"Subreddit r/{sub}: {len(children)} posts found")
            for post in children[:5]:
                pdata = post.get('data', {})
                title = pdata.get('title', '')
                post_url = pdata.get('url', '')
                print(f"  Title: {title[:60]} | URL: {post_url}")
    except Exception as e:
        print(f"r/{sub} Error: {e}")
