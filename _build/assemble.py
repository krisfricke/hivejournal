#!/usr/bin/env python3
"""Assemble index.html from the template halves, the entry metadata, the config and the bee geometry."""
import json, os
site=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tpl=os.path.join(site,'_build','templates')
cfg=json.load(open(os.path.join(site,'_config.json')))
meta=json.load(open(os.path.join(site,'_entries_meta.json')))
bee=json.load(open(os.path.join(site,'assets/bee/meta.json')))
KEEP=('id','title','vol','topic','year','month','day','tags','n','mm','pmm','lj','dw')
arts=[{k:a.get(k) for k in KEEP if k in a} for a in meta]
head=open(os.path.join(tpl,'index_head.html'),encoding='utf-8').read()
scr=open(os.path.join(tpl,'index_script.html'),encoding='utf-8').read()
def pct(p): return '%.1f%% %.1f%%'%(p[0]/bee['w']*100,p[1]/bee['h']*100)
head=head.replace('WL_ORIGIN',pct(bee['roots']['wl'])).replace('WR_ORIGIN',pct(bee['roots']['wr']))
head=head.replace('width:64px;height:47px','width:64px;height:%dpx'%round(64*bee['h']/bee['w']))
def sub(t):
    for k,v in (('__BASE__',cfg['base']),('__HOME__',cfg['home']),('__HOME_LABEL__',cfg.get('home_label','the journal')),
                ('__UP_URL__',cfg['up_url']),('__UP_LABEL__',cfg.get('up_label','the topic post')),
                ('__PORTFOLIO__',cfg.get('portfolio','')),('__DW_TAG_BASE__',cfg.get('dw_tag_base',''))):
        t=t.replace(k,v.replace("'","\\'") if t is scr else v)
    return t
head=sub(head); scr=sub(scr).replace('__ARTS__',json.dumps(arts,ensure_ascii=False,separators=(',',':')))
out=head+scr
open(os.path.join(site,'index.html'),'w',encoding='utf-8').write(out)
print('index.html',len(out),'bytes,',len(arts),'entries')
