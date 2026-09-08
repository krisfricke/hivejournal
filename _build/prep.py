#!/usr/bin/env python3
"""Step 1 of the weekly build: the Word file becomes the page PDF.

  _src/<docx>  ->  _pdf/<id>.pdf      (LibreOffice render, then the forest-green frame drawn BEHIND the
                                       page content, so pictures that run to the edge sit on top of it)
               ->  _pics/<id>.json    (every picture: its file, size, hover text and screen-reader text,
                                       harvested from the alt text you typed in Word)
               ->  pages/<id>/pic<k>  (the original image files, for the enlarger)

Alt text: what you type in Word's Alt Text box becomes the hover text AND the screen-reader description.
To give the screen reader something different, either write  hover text || screen-reader text  in Word,
or edit the "alt" field in _pics/<id>.json (that file is kept between builds; only new pictures are added).
"""
import json, os, re, sys, zipfile, subprocess, shutil, html
import pymupdf as fitz

site=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg=json.load(open(os.path.join(site,'_config.json')))
meta=json.load(open(os.path.join(site,'_entries_meta.json')))
SOFFICE=os.environ.get('SOFFICE','soffice')

def hexrgb(h): h=h.lstrip('#'); return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))

def docx_pictures(path):
    """[(rId, media-name, hover, alt)] in document order, from the docx XML."""
    z=zipfile.ZipFile(path)
    doc=z.read('word/document.xml').decode('utf-8')
    rels=z.read('word/_rels/document.xml.rels').decode('utf-8')
    rmap=dict(re.findall(r'<Relationship [^>]*Id="([^"]+)"[^>]*Target="media/([^"]+)"',rels))
    rmap.update({b:a for a,b in re.findall(r'<Relationship [^>]*Target="media/([^"]+)"[^>]*Id="([^"]+)"',rels)})
    out=[]
    for m in re.finditer(r'<wp:(anchor|inline)\b.*?</wp:\1>',doc,re.S):
        b=m.group(0)
        emb=re.search(r'r:embed="([^"]+)"',b)
        if not emb or emb.group(1) not in rmap: continue
        dp=re.search(r'<wp:docPr [^>]*>',b).group(0)
        descr=html.unescape((re.search(r'descr="([^"]*)"',dp) or [None,''])[1])
        title=html.unescape((re.search(r'title="([^"]*)"',dp) or [None,''])[1])
        hover,alt=descr,descr
        if '||' in descr: hover,alt=[s.strip() for s in descr.split('||',1)]
        if title and not alt: alt=title
        out.append((emb.group(1),rmap[emb.group(1)],hover.strip(),alt.strip()))
    return z,out

def trim_last(d,pad=64):
    """The last page usually ends well above the foot. Cut it off a little below whatever is lowest on it
    (text or picture), leaving room for the folio line and the frame. Never shorter than half a page."""
    p=d[-1]; W,H=p.rect.width,p.rect.height
    tb=max((b['bbox'][3] for b in p.get_text('dict')['blocks'] if b['type']==0 and any(s['text'].strip() for l in b['lines'] for s in l['spans'])),default=0)
    ib=max((fitz.Rect(i['bbox']).y1 for i in p.get_image_info()),default=0)
    db=max((dr['rect'].y1 for dr in p.get_drawings() if dr['rect'].width<W*0.95),default=0)
    low=max(tb,ib,db)
    newH=max(H*0.5,min(H,low+pad))
    if H-newH<40: return None
    p.set_cropbox(fitz.Rect(p.cropbox.x0,p.cropbox.y0,p.cropbox.x0+W,p.cropbox.y0+newH))
    return newH

def frame(pdf_in,pdf_out,trim=True):
    d=fitz.open(pdf_in)
    cut=trim_last(d) if trim else None
    if cut: print('   last page trimmed to %.0f pt (%.0f mm)'%(cut,cut/72*25.4))
    ins=cfg['frame_inset_mm']/25.4*72; w=cfg['frame_width_pt']; col=hexrgb(cfg['frame_color'])
    for p in d:
        r=p.rect
        sh=p.new_shape(); sh.draw_rect(fitz.Rect(r.x0+ins,r.y0+ins,r.x1-ins,r.y1-ins))
        sh.finish(color=col,width=w,fill=None); sh.commit(overlay=False)      # behind everything already on the page
    import tempfile
    fd,tmp=tempfile.mkstemp(suffix='.pdf'); os.close(fd)
    d.save(tmp,garbage=3,deflate=True); d.close()
    shutil.copyfile(tmp,pdf_out); os.remove(tmp)      # write-then-copy: fitz unlinks first, which some mounts refuse

def run(entry):
    src=os.path.join(site,'_src',entry['src']); eid=entry['id']
    import tempfile; tmp=tempfile.mkdtemp(prefix='lji_')
    # the page PDF: the one Word exported if there is one (named in "pdf", or the .docx name with .pdf) -
    # that is the layout exactly as you saw it. Otherwise LibreOffice renders the .docx, which is close
    # but not identical (it wraps text around pictures a little differently).
    cand=[os.path.join(site,'_src',entry['pdf'])] if entry.get('pdf') else []
    cand.append(os.path.splitext(src)[0]+'.pdf')
    raw=next((c for c in cand if os.path.exists(c)),None)
    if raw: how='Word PDF: '+os.path.basename(raw)
    else:
        subprocess.run([SOFFICE,'--headless','--convert-to','pdf','--outdir',tmp,src],check=True,capture_output=True)
        raw=os.path.join(tmp,os.path.splitext(os.path.basename(src))[0]+'.pdf'); how='LibreOffice render of the .docx'
    out=os.path.join(site,'_pdf',eid+'.pdf'); frame(raw,out,trim=entry.get('trim_last',True)); shutil.rmtree(tmp,ignore_errors=True)
    # pictures: docx order, matched to the PDF's images by pixel size (LibreOffice keeps them as they were)
    z,pics=docx_pictures(src)
    pdir=os.path.join(site,'pages',eid); os.makedirs(pdir,exist_ok=True)
    jpath=os.path.join(site,'_pics',eid+'.json')
    old={p['file']:p for p in json.load(open(jpath))} if os.path.exists(jpath) else {}
    rec=[]
    for k,(rid,media,hover,alt) in enumerate(pics,1):
        ext=os.path.splitext(media)[1].lower().replace('.jpeg','.jpg')
        fn='pic%d%s'%(k,ext); data=z.read('word/media/'+media)
        open(os.path.join(pdir,fn),'wb').write(data)
        pm=fitz.Pixmap(data); w,h=pm.width,pm.height
        prev=old.get(fn,{})
        hv=hover or prev.get('hover','')          # Word's alt text, else what the last build had
        if prev.get('alt') and prev.get('alt')!=prev.get('hover') and not (alt and alt!=hover):
            al=prev['alt']                        # a hand-edited screen-reader text survives rebuilds
        else:
            al=alt or hv                          # otherwise Word's, else the previous build's
        rec.append({'file':fn,'media':media,'w':w,'h':h,'hover':hv,'alt':al})
    json.dump(rec,open(jpath,'w'),indent=1,ensure_ascii=False)
    d=fitz.open(out); n=d.page_count; W,H=d[0].rect.width,d[0].rect.height; d.close()
    print('%-10s %2d pages  %d pictures  -> %s   (%s)'%(eid,n,len(rec),os.path.relpath(out,site),how))
    missing=[p['file'] for p in rec if not p['alt']]
    if missing: print('   no alt text yet for:',', '.join(missing))

if __name__=='__main__':
    only=sys.argv[1:]
    for e in meta:
        if only and e['id'] not in only: continue
        run(e)
