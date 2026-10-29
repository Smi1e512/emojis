#!/usr/bin/env python3
"""Create reproducible download bundles and an offline gallery from manifest.json."""
import hashlib, json, zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 3 * 1024 * 1024

def write_zip(path, rows):
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for row in rows:
            info=zipfile.ZipInfo(row['path'], date_time=(2026,10,29,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644 << 16
            archive.writestr(info, (ROOT/row['path']).read_bytes(), compresslevel=9)

def package():
    rows=json.loads((ROOT/'manifest.json').read_text())
    bundles=[]
    for role in ['月薪猫','群友猪']:
        directory=ROOT/'packs'/role
        directory.mkdir(parents=True, exist_ok=True)
        for old in directory.glob('*.zip'): old.unlink()
        for animated in [True,False]:
            selected=[r for r in rows if r['role']==role and r['animated']==animated]
            part, group, size=1,[],0
            for row in selected+[None]:
                if group and (row is None or size+row['bytes']>LIMIT):
                    name=f"{'动图' if animated else '静态图'}-{part:02d}.zip"
                    path=directory/name
                    write_zip(path,group)
                    bundles.append(dict(path=path.relative_to(ROOT).as_posix(),count=len(group),
                        bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
                    part+=1;group=[];size=0
                if row is not None:group.append(row);size+=row['bytes']
    (ROOT/'packs/index.json').write_text(json.dumps(bundles,ensure_ascii=False,indent=2)+'\n')
    data=[{k:row[k] for k in ['path','role','title','animated','bytes','output_frames','duration_ms']} for row in rows]
    gallery='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>月薪猫 × 群友猪 · 128×128 表情库</title>
<style>body{margin:0;background:#f4f5f8;color:#1b2331;font:15px system-ui,sans-serif}main{max-width:1200px;margin:auto;padding:28px 20px}h1{margin:0 0 8px;font-size:28px}p{color:#596475;line-height:1.6}.filters{display:flex;gap:10px;flex-wrap:wrap;margin:24px 0 12px}input,select,button{padding:10px 14px;border:1px solid #ccd2dc;border-radius:8px;background:white;font:inherit}input{flex:1;min-width:150px}button{cursor:pointer}button:disabled{opacity:.4}#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(154px,1fr));gap:14px;margin:18px 0}.card{background:#fff;border-radius:12px;padding:14px;box-shadow:0 2px 12px #13264408}.picture{display:flex;justify-content:center;background:repeating-conic-gradient(#f1f1f1 0% 25%,#fff 0% 50%) 0/16px 16px;border-radius:8px}img{width:128px;height:128px;object-fit:contain}.name{font-size:13px;height:38px;overflow:hidden;margin:10px 0 6px;line-height:19px}.meta{font-size:12px;color:#6d7480}a{color:#285cc4;text-decoration:none}.pager{display:flex;align-items:center;justify-content:center;gap:16px;margin:28px 0}.note{font-size:13px}#count{font-size:13px;color:#596475}</style>
<main><h1>月薪猫 × 群友猪</h1><p>128×128 聊天表情库 · 动图 GIF / 静态 PNG · 等比例缩放</p><p class="note">下载整个仓库后，如图片目录尚未展开，请先运行 <code>python tools/unpack.py</code>。动图请下载原文件。</p>
<div class="filters"><input id="query" placeholder="搜索表情标题或关键词" aria-label="搜索"><select id="role" aria-label="角色"><option value="">全部角色</option><option>月薪猫</option><option>群友猪</option></select><select id="kind" aria-label="类型"><option value="">全部类型</option><option value="gif">动图 GIF</option><option value="png">静态 PNG</option></select></div><div id="count"></div><div id="grid"></div><div class="pager"><button id="prev">上一页</button><span id="page"></span><button id="next">下一页</button></div><p class="note">来源与校验信息见 manifest.json。图片和角色版权归各自权利人所有。</p></main>
<script>const data=__DATA__;let current=0;const perPage=60;const el=id=>document.getElementById(id);function render(){const q=el('query').value.trim().toLowerCase(),r=el('role').value,k=el('kind').value;const rows=data.filter(x=>(!r||x.role===r)&&(!k||(k==='gif')===x.animated)&&(!q||(x.title+' '+x.role).toLowerCase().includes(q)));const pages=Math.max(1,Math.ceil(rows.length/perPage));current=Math.min(current,pages-1);el('count').textContent=`共 ${rows.length} 张 · 全部图片均为 128×128`;el('grid').replaceChildren();for(const x of rows.slice(current*perPage,(current+1)*perPage)){const card=document.createElement('article');card.className='card';const pic=document.createElement('div');pic.className='picture';const img=document.createElement('img');img.src=x.path;img.alt=x.title;img.loading='lazy';pic.append(img);const name=document.createElement('div');name.className='name';name.textContent=x.title;name.title=x.title;const meta=document.createElement('div');meta.className='meta';meta.textContent=`${x.animated?'GIF · '+x.output_frames+' 帧':'PNG'} · ${Math.round(x.bytes/1024)} KB`;const link=document.createElement('a');link.href=x.path;link.download=x.path.split('/').pop();link.textContent='下载图片';card.append(pic,name,meta,link);el('grid').append(card)}el('page').textContent=`${current+1} / ${pages}`;el('prev').disabled=current===0;el('next').disabled=current>=pages-1}for(const id of ['query','role','kind'])el(id).addEventListener('input',()=>{current=0;render()});el('prev').onclick=()=>{current--;render();window.scrollTo(0,0)};el('next').onclick=()=>{current++;render();window.scrollTo(0,0)};render();</script></html>'''
    (ROOT/'index.html').write_text(gallery.replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('</','<\\/')))
    count=Counter((r['role'],r['animated']) for r in rows)
    total_bytes=sum(r['bytes'] for r in rows)
    failures=json.loads((ROOT/'failures.json').read_text())
    source_count=len(json.loads((ROOT/'sources.json').read_text()))
    readme=f'''# 月薪猫 × 群友猪 · 128×128 表情合集

收集公开来源的月薪喵、群友猪表情，统一到 **128×128**。静态图为无损 PNG，动图为 GIF。

| 角色 | 动图 | 静态图 | 合计 |
| --- | ---: | ---: | ---: |
| 月薪猫 | {count['月薪猫',True]} | {count['月薪猫',False]} | {sum(r['role']=='月薪猫' for r in rows)} |
| 群友猪 | {count['群友猪',True]} | {count['群友猪',False]} | {sum(r['role']=='群友猪' for r in rows)} |
| 合计 | {sum(r['animated'] for r in rows)} | {sum(not r['animated'] for r in rows)} | {len(rows)} |

图片文件总计约 **{total_bytes/1024/1024:.1f} MiB**。以上数量依据本次实际生成并校验成功的文件统计。

## 下载与浏览

- [下载整个仓库 ZIP](https://github.com/Smi1e512/emojis/archive/refs/heads/main.zip)
- [月薪猫分包](./packs/月薪猫/) · [群友猪分包](./packs/群友猪/)，每个 ZIP 可独立解压，多个分包解压到同一目录。
- 单张图片按 `月薪猫/动图`、`月薪猫/静态图`、`群友猪/动图`、`群友猪/静态图` 分类。
- 下载整个仓库后，运行 `python tools/unpack.py` 可一次性解压全部分包并核对每张图的 SHA-256；GitHub Actions 也会自动将图片展开到仓库。
- 双击 **index.html**，可离线按角色、动静类型、标题搜索并分页浏览。

## 画质与动画处理

- 使用 Lanczos 等比例缩放并居中补透明边，不拉伸、不裁切。
- PNG 保留完整颜色及透明通道；GIF 每帧使用最多 255 色及独立透明色，保留动画内容和循环设置，不主动抽帧。
- GIF 不支持半透明，半透明边缘以白底融合；完全透明区域保留。GIF 时间精度为 10ms，因此非整十毫秒帧时长就近取整、最短 10ms。
- 无损优化 GIF 调色板和存储布局。完全一致的缩放后像素、时长和循环设置去重；配字、背景、速度或画面不同的版本保留。
- 逐张校验哈希，逐帧校验 128×128 尺寸，并核对输出帧数、总时长和循环设置。`manifest.json` 记录源尺寸、源帧数、输出信息和来源；编码器可能合并相邻相同帧，播放内容及时长不变。

## 来源与范围

整理日期：2026-10-29。候选地址 {source_count} 个，成功输出 {len(rows)} 张去重后的图片；本次未能转换的地址 {len(failures)} 个，详见 [failures.json](./failures.json)。

- [月薪喵作者公开页面](https://www.sina.cn/media/5626763209)：系列表情、幼年篇、新年篇、爱意篇及补充合集。
- [SigStick 月薪喵专区](https://www.sigstick.com/topic/monthly-salary-cat)：社区分享的多个表情版本。
- [PigHub 公开图库](https://pighub.top/all)：群友猪社区投稿，包含谷歌猪的二创和其他少量猪形象。

本次覆盖上述可访问公开来源，不能保证全网无遗漏。已排除与群友猪不符的真实动物合集，以及作者页面中的头像、宣传类帖子。来源地址全部保存在 [sources.json](./sources.json)，每张输出图的来源对应关系保存在 [manifest.json](./manifest.json)。

## 用代码一次性处理

需要 Python 3.10+。只解压已有图片不需要第三方依赖。

```bash
python -m pip install -r requirements.txt
# 按本次固定来源重新下载、转换和去重
python tools/normalize.py sources.json --output .
python tools/verify.py
python tools/package.py
```

刷新公开来源列表可先运行 `python tools/collect_sources.py`。再次生成分包会刷新 `packs` 中对应的文件；更新前请备份自己的额外文件。

图片及角色版权归各自权利人所有；整理与尺寸转换不代表获得图片再授权，也不为第三方图片授予开源许可。如涉及权利问题，可通过仓库 Issue 提出处理请求。
'''
    (ROOT/'README.md').write_text(readme)
    print(f'Packaged {len(rows)} images into {len(bundles)} archives; {sum(b["bytes"] for b in bundles)/1024/1024:.1f} MiB compressed.')

if __name__ == '__main__': package()
