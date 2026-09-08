#!/usr/bin/env python3
"""Static, text-only front doors: entry/<id>/index.html, entry/index.html, sitemap.xml, robots.txt.
These are what search engines, screen readers, Lynx and anyone without JavaScript get - and for a
readership with many blind members they are the main door, not a side one. The pictures are in the
text, in reading order, each with its screen-reader description."""
import json, os, re, html, datetime
site=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg=json.load(open(os.path.join(site,'_config.json')))
meta=json.load(open(os.path.join(site,'_entries_meta.json')))
BASE=cfg['base']; AUTHOR=cfg['author']
MONTHS=['January','February','March','April','May','June','July','August','September','October','November','December']
E=lambda s:html.escape(s,quote=True)
def when(a): return ('%d '%a['day'] if a.get('day') else '')+MONTHS[a['month']-1]+' '+str(a['year'])
def sortkey(a): return (a['year'],a['month'],a.get('day',0))
CSS='''
:root{--ink:#14293b;--ink2:#3d6079;--gold:#f9c500;--green:%s}
body{margin:0;background:linear-gradient(180deg,#7db4dc,#a9d2ec 46%%,#d3e8f7) fixed;color:#1d1b16;font:18px/1.65 Georgia,'Times New Roman',serif}
main{max-width:760px;margin:0 auto;padding:28px 22px 60px}
.card{background:#faf8f2;border-radius:14px;padding:32px 36px;box-shadow:0 18px 50px rgba(20,60,90,.25);border:2px solid var(--green)}
h1{font:700 30px/1.2 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--ink);margin:0 0 6px}
h2{font:700 20px/1.3 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--ink);margin:30px 0 8px}
.by{color:var(--ink2);font:14px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin-bottom:14px}
a{color:#0f4b70}
.btn{display:inline-block;background:var(--gold);color:#111;font:700 14px/1 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;padding:11px 18px;border-radius:22px;text-decoration:none;margin:2px 8px 12px 0}
.btn.sec{background:#fff;border:1px solid #7ea9c6;color:#17313f}
.btn.cmt{background:#fff3d6;border:1px solid #d9a441;color:#5a3a00}
.tags{margin:6px 0 22px}
.tags a{display:inline-block;font:12px/1.7 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:#fff;border:1px solid #cfe0ee;border-radius:11px;padding:0 9px;margin:0 5px 5px 0;text-decoration:none;color:#17313f}
.pg{color:#8a8472;font:12px/1 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;letter-spacing:.12em;text-transform:uppercase;margin:26px 0 10px;border-top:1px dashed #cbb083;padding-top:10px}
p{margin:0 0 1em}
figure{margin:18px 0}
figure img{max-width:100%%;height:auto;display:block;border:1px solid #ddd;box-shadow:0 6px 18px rgba(0,0,0,.15)}
figcaption{font:13px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#5a5a5a;margin-top:6px}
.note{color:#6d6857;font:13px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin-top:28px;border-top:1px solid #e3dccb;padding-top:12px}
nav.top{font:14px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin-bottom:14px;color:#2b4d63}
ul.list{list-style:none;padding:0;margin:0}
ul.list li{margin:0 0 16px;padding-left:0}
ul.list li a.t{font:600 17px/1.3 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;text-decoration:none;color:var(--ink)}
ul.list li a.t:hover{text-decoration:underline}
ul.list li .c{font-size:14px;color:#3a3a3a;margin-top:2px}
.links li{font-size:14px;word-break:break-all}
'''%cfg.get('frame_color','#228B22')
def shell(title,body,canon,desc,up='../../'):
    return ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>%s</title><meta name="description" content="%s"><link rel="canonical" href="%s"><link rel="icon" type="image/png" href="%sassets/bee/favicon.png"><style>%s</style></head><body><main><div class="card">%s</div></main></body></html>')%(E(title),E(desc),E(canon),up,CSS,body)

def reading_order(a,tj):
    """Each page as a list of ('h'|'p'|'img', payload) in reading order: full-width blocks divide the page
    into bands; within a band, left column then right, each top to bottom. Pictures slot in by position."""
    W=tj['pt'][0]; out=[]
    xs=[p['x'] for pg in tj['pages'] for p in pg['paras'] if p['t'].strip()]
    L=min(xs) if xs else 72.0; TW=W-2*L               # the entry's own text margin, not a guessed one
    title_k=re.sub(r'\W+','',a['title']).lower()
    for n,pg in enumerate(tj['pages'],1):
        items=[]
        for p in pg['paras']:
            t=p['t'].strip()
            if not t: continue
            full=(p.get('w',0)>TW*0.55) or (p['x']>L+TW*0.25 and p['x']<L+TW*0.4 and p.get('w',0)>TW*0.3)
            items.append({'k':'p','t':t,'x':p['x'],'y':p['y'],'full':full,'size':p['size']})
        for pic in tj.get('pics',[]):
            if pic['page']!=n: continue
            items.append({'k':'img','pic':pic,'x':pic['x'],'y':pic['y'],'full':pic['w']>TW*0.55})
        sizes=sorted(i['size'] for i in items if i['k']=='p' and len(i['t'])>80); body=sizes[len(sizes)//2] if sizes else 12
        fulls=sorted(i['y'] for i in items if i['full'])
        def band(y): return sum(1 for fy in fulls if fy<=y)
        items.sort(key=lambda i:(band(i['y'])+(0 if i['full'] else 1)*0, -1 if i['full'] else (0 if i['x']<W/2 else 1), i['y']))
        seq=[]; pend=None
        for i in items:
            if i['k']=='img': seq.append(('img',i['pic'])); continue
            t=i['t']; k=re.sub(r'\W+','',t).lower()
            if len(t)<=2 and t.isalpha(): pend=t; continue                 # a drop cap
            if pend: t=pend+t; pend=None
            if k==title_k: seq.append(('h',t)); continue
            if i['size']>body*1.3 and len(t)<90: seq.append(('h',t)); continue
            # a paragraph continued in a text box (or past a picture) arrives as a second block: an
            # unfinished sentence followed by a lower-case start is one paragraph
            if seq and seq[-1][0]=='p' and t[:1].islower() and not re.search(r'[.!?:”"’\')\]]\s*$',seq[-1][1]):
                seq[-1]=('p',seq[-1][1].rstrip()+' '+t); continue
            seq.append(('p',t))
        out.append(seq)
    return out

adir=os.path.join(site,'entry'); os.makedirs(adir,exist_ok=True)
urls=[BASE, BASE+'entry/']
ordered=sorted(meta,key=sortkey,reverse=True)
for a in ordered:
    tj=json.load(open(os.path.join(site,'pages',a['id'],'text.json')))
    pages=reading_order(a,tj)
    reader='../../index.html#/read/'+a['id']
    parts=['<nav class="top"><a href="../index.html">All entries</a> &rsaquo; LJ Idol Season %s, Topic %s</nav>'%(a['vol'],a['topic'])]
    parts.append('<h1>%s</h1><div class="by">by %s &middot; LJ Idol Season %s &middot; Topic %s &middot; %s</div>'%(E(a['title']),E(AUTHOR),a['vol'],a['topic'],E(when(a))))
    if a.get('lj'): parts.append('<a class="btn cmt" href="%s">Comment on this entry (LiveJournal)</a>'%E(a['lj']))
    parts.append('<a class="btn" href="%s">Read the pages as laid out</a>'%reader)
    if a.get('lj'): parts.append('<a class="btn sec" href="%s">Read on LiveJournal</a>'%E(a['lj']))
    if a.get('dw'): parts.append('<a class="btn sec" href="%s">Read on Dreamwidth</a>'%E(a['dw']))
    parts.append('<div class="tags">'+''.join('<a href="../../index.html#/topic/%s">%s</a>'%(E(t.lower()),E(t)) for t in a['tags'])+'</div>')
    parts.append('<h2 id="text">Text of the entry</h2>')
    manual=list(a.get('links',[]))+list(tj.get('doclinks',[]))    # the Word file's hyperlinks, as placed on the pages
    def phrase_re(text):
        """a pattern tolerant of the page's curly quotes, its line-end hyphens and its spacing"""
        out=[]; prev_sp=False
        for ch in text:
            if ch.isspace():
                if not prev_sp: out.append(r'\s+')
                prev_sp=True; continue
            prev_sp=False
            if ch in '"“”': out.append('(?:&quot;|["“”])')
            elif ch in "'‘’": out.append("(?:&#x27;|['‘’])")
            elif ch in '-\u2010\u2011': out.append(r'[-\u2010\u2011]?\s*')
            elif ch=='&': out.append('&amp;')
            elif ch=='<': out.append('&lt;')
            elif ch=='>': out.append('&gt;')
            else: out.append(re.escape(ch))
        return re.compile(''.join(out),re.I)
    for n,body in enumerate(pages,1):
        parts.append('<div class="pg">Page %d of %d</div>'%(n,a['n']))
        for kind,t in body:
            if kind=='img':
                if t.get('deco'): continue
                cap=t.get('hover') or ''
                parts.append('<figure><img src="../../pages/%s/%s" alt="%s" loading="lazy">%s</figure>'%(a['id'],t['file'],E(t.get('alt') or cap or 'Picture'),('<figcaption>%s</figcaption>'%E(cap)) if cap else ''))
                continue
            h=E(t)
            # find every phrase in the plain text first, then wrap - so a later phrase can never land
            # inside an anchor already written (e.g. a name that is also part of an earlier link's URL)
            found=[]
            for spec in manual:
                if spec.get('page')!=n or spec.get('_done'): continue
                m=phrase_re(spec['text']).search(h)
                if not m or not m.group(0).strip(): continue
                if any(s0<m.end() and m.start()<e0 for s0,e0,_ in found): continue
                found.append((m.start(),m.end(),spec)); spec['_done']=True
            found.sort(key=lambda f:f[0]); out=[]; pos=0
            for s0,e0,spec in found:
                out.append(h[pos:s0]); out.append('<a href="%s">%s</a>'%(E(spec['url']),h[s0:e0])); pos=e0
            out.append(h[pos:]); h=''.join(out)
            parts.append(('<h2>%s</h2>' if kind=='h' else '<p>%s</p>')%h)
    miss=[x for x in manual if not x.get('_done')]
    if miss: print('   text version: %d link phrase(s) not matched: %s'%(len(miss),'; '.join(repr(x['text'][:40]) for x in miss[:5])))
    if tj.get('links'):
        parts.append('<h2>Links in the entry</h2><ul class="links">'+''.join('<li><a href="%s" rel="noopener">%s</a></li>'%(E(u),E(u)) for u in tj['links'])+'</ul>')
    parts.append('<p class="note">This is the plain-text version, extracted from the laid-out pages for readers who use screen readers, text-only browsers, or prefer reflowable text. The typeset pages are in the <a href="%s">reader</a>; the same entry is on <a href="%s">LiveJournal</a>%s.</p>'%(reader,E(a.get('lj','#')),(' and <a href="%s">Dreamwidth</a>'%E(a['dw'])) if a.get('dw') else ''))
    desc='%s — LJ Idol Season %s, Topic %s, %s. By %s.'%(a['title'],a['vol'],a['topic'],when(a),AUTHOR)
    d=os.path.join(adir,a['id']); os.makedirs(d,exist_ok=True)
    open(os.path.join(d,'index.html'),'w',encoding='utf-8').write(shell(a['title']+' — LJ Idol — '+AUTHOR,''.join(parts),BASE+'entry/'+a['id']+'/',desc))
    urls.append(BASE+'entry/'+a['id']+'/')
# hub
seasons={}
for a in ordered: seasons.setdefault(a['vol'],[]).append(a)
hub=['<nav class="top"><a href="../index.html">Open the reader</a></nav><h1>LJ Idol entries by %s</h1><div class="by">%d %s &middot; newest first &middot; each links to its plain-text version; the <a href="../index.html">reader</a> shows the pages as laid out.</div>'%(E(AUTHOR),len(meta),'entry' if len(meta)==1 else 'entries')]
for v,items in sorted(seasons.items(),reverse=True):
    hub.append('<h2>Season %s</h2><ul class="list">'%v)
    for a in items:
        hub.append('<li><a class="t" href="%s/index.html">%s</a><div class="c">Topic %s &middot; %s</div></li>'%(a['id'],E(a['title']),a['topic'],E(when(a))))
    hub.append('</ul>')
open(os.path.join(adir,'index.html'),'w',encoding='utf-8').write(shell('LJ Idol entries by '+AUTHOR,''.join(hub),BASE+'entry/','All LJ Idol entries by %s, with plain-text versions.'%AUTHOR,up='../'))
today=datetime.date.today().isoformat()
open(os.path.join(site,'sitemap.xml'),'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join('  <url><loc>%s</loc><lastmod>%s</lastmod></url>\n'%(E(u),today) for u in urls)+'</urlset>\n')
open(os.path.join(site,'robots.txt'),'w').write('User-agent: *\nAllow: /\n\nSitemap: %ssitemap.xml\n'%BASE)
print('wrote',len(meta),'entry pages, hub, sitemap (%d urls), robots'%len(urls))
