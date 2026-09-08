#!/usr/bin/env python3
"""The whole weekly build in one go:  python3 _build/build.py  [entry-id ...]

  prep.py        Word -> PDF (+ frame), pictures and alt text out of the .docx
  buildpages.py  PDF  -> pages/<id>/  (page art + live text + hotspots + folio)
  assemble.py    index.html
  static.py      entry/ text versions, sitemap, robots
  ogcard.py      the link-preview card (only when the entry list changed)
"""
import os, sys, subprocess, json, hashlib
here = os.path.dirname(os.path.abspath(__file__)); site = os.path.dirname(here)
def run(script, *args):
    print('==', script, ' '.join(args)); subprocess.run([sys.executable, os.path.join(here, script), *args], check=True, cwd=site)
ids = sys.argv[1:]
run('prep.py', *ids); run('buildpages.py', *ids); run('assemble.py'); run('static.py')
sig = hashlib.md5(json.dumps([(a['id'], a['vol']) for a in json.load(open(os.path.join(site, '_entries_meta.json')))]).encode()).hexdigest()
stamp = os.path.join(site, '_build', '.ogcard.sig')
if not os.path.exists(stamp) or open(stamp).read() != sig:
    run('ogcard.py'); open(stamp, 'w').write(sig)
print('done')
