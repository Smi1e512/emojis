#!/usr/bin/env python3
"""Collect public Yuexin Cat and PigHub metadata; image bytes are fetched later."""
import concurrent.futures as cf
import hashlib, html, json, re, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT/'.cache/pages'

def fetch(url):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE/hashlib.sha256(url.encode()).hexdigest()
    if path.exists(): return path.read_text()
    request = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(request, timeout=25) as response:
        text = response.read().decode('utf-8')
    path.write_text(text)
    return text

def nextdata(text):
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', text, re.S)
    return json.loads(match.group(1))['props']['pageProps']

def collect():
    items, failures = [], []
    def add(role, url, page, title, **extra):
        url = urllib.parse.quote(url.replace('http://','https://'), safe=':/?=&%')
        items.append(dict(role=role, url=url, page=page, title=title, **extra))

    author = 'https://www.sina.cn/media/5626763209'
    posts = []
    for url, chunk in re.findall(r'href="(/news/detail/\d+\.html)"(.*?)</article>', fetch(author), re.S):
        match = re.search(r'class="post-text">(.*?)</div>', chunk, re.S)
        title = html.unescape(re.sub('<[^>]+>', '', match.group(1))) if match else ''
        if any(t in title for t in ['表情','单图','无字幕']) and not any(t in title for t in ['人格头像','大家好，我叫','即将上线','企鹅已上线']):
            posts.append(('https://www.sina.cn'+url, title))
    posts += [('https://www.sina.cn/news/detail/'+i+'.html', '月薪喵公开表情合集')
              for i in ['5325095780484620','5312275783093411','5306513415734286','5304956685127999','5305178748355965']]
    def sina(post):
        page,title = post
        try:
            urls = re.findall(r'(?:src|data-src)=["\']([^"\']+sinaimg\.cn/[^"\']+)["\']', fetch(page))
            return [(u.replace('/middle/','/large/'), page, title) for u in dict.fromkeys(urls)
                    if '/middle/' in u or '/large/' in u or '/mw' in u]
        except Exception as error:
            failures.append(dict(page=page, error=str(error)))
            return []
    with cf.ThreadPoolExecutor(max_workers=6) as executor:
        for rows in executor.map(sina, posts):
            for url,page,title in rows: add('月薪猫', url, page, title)

    topic = nextdata(fetch('https://www.sigstick.com/topic/monthly-salary-cat'))
    packs = topic['packs']
    pack_page = 'https://www.sigstick.com/pack/CGfyH8JbrmzwWvcPidpu-%E6%9C%88%E8%96%AA%E5%96%B5'
    related = nextdata(fetch(pack_page))
    packs += [related['pack']] + related['discoverPacks']
    for pack in {p['id']:p for p in packs if any(t in p['title'].lower() for t in ['月薪','yue xin'])}.values():
        for index, sticker in enumerate(pack.get('stickers', []), 1):
            add('月薪猫', sticker['url'], 'https://www.sigstick.com/pack/'+pack['id'], pack['title']+' '+str(index))

    pig_data = json.loads(fetch('https://pighub.top/api/images?sort=2'))
    if pig_data.get('code') != 0: raise RuntimeError('PigHub API failed')
    for image in pig_data['data']:
        add('群友猪', urllib.parse.urljoin('https://pighub.top/', image['image_url']),
            'https://pighub.top/all', image['title'], source_id=image['id'])
    unique = list({item['url']:item for item in items}.values())
    (ROOT/'sources.json').write_text(json.dumps(unique, ensure_ascii=False, indent=2)+'\n')
    (ROOT/'collection-errors.json').write_text(json.dumps(failures, ensure_ascii=False, indent=2)+'\n')
    print(f'{len(unique)} source URLs, {len(failures)} metadata fetch failures')

if __name__ == '__main__': collect()
