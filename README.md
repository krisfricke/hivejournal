# LJ Idol entries — page-turning reader

A static site: the same cover-anchored, scroll-driven reader as the articles portfolio, carrying LJ Idol
entries laid out in Word as magazine pages. Live, selectable text over the page art; pictures that
enlarge; and a plain-text version of every entry for screen readers, text-only browsers and search engines.

Everything is static files. No server-side code; a build step only to *change* it.

## Publish on GitHub Pages

1. Create a new public repository — `hivejournal` is what `_config.json` assumes (the name becomes the URL,
   `https://krisfricke.github.io/hivejournal/`). Any other name: change `base` in `_config.json` and rebuild.
2. Put the **contents of this folder** at the root of the repository and push.
3. Repository → Settings → Pages → Source **Deploy from a branch**, branch **main**, folder **/ (root)**.

Folders starting with an underscore (`_build/`, `_src/`, `_pdf/`, `_pics/`, the two `_*.json` files) are
ignored by GitHub Pages, so the Word files and build tooling can live in the repo without being served.

## The weekly entry

1. Lay the entry out in Word. Save the `.docx` into `_src/`, and **export a PDF of it into `_src/` as well**
   (File → Save As → PDF, or Print → Microsoft Print to PDF). The PDF is the layout exactly as Word drew it;
   the `.docx` is still read for the pictures and their alt text. Without a PDF the build renders the
   `.docx` with LibreOffice, which is close but wraps text around pictures a little differently.
2. Add it to `_entries_meta.json`:

        {
         "id": "s12-t1",                         used in URLs - keep it stable once published
         "title": "…",
         "vol": 12, "topic": 1,                  season and topic number - drives the folio line and "By season"
         "year": 2026, "month": 9, "day": 14,
         "tags": ["lj idol", "…"],               lower-case, as on Dreamwidth: the tag lane links to
                                                 https://aggienaut.dreamwidth.org/tag/<tag>
         "src": "Topic 1 - Whatever.docx",
         "pdf": "Topic 1 - Whatever.pdf",         the PDF Word exported (optional if it has the .docx's name)
         "lj": "https://emo-snal.livejournal.com/NNNNNN.html",    the Comment button and "Read on LiveJournal"
         "dw": "https://aggienaut.dreamwidth.org/NNNNNN.html"     "Read on Dreamwidth"
        }

3. Run, from this folder:

        python3 _build/build.py s12-t1

   Needs Python 3 with `pymupdf` (`pip install pymupdf`), and LibreOffice on the PATH as `soffice`
   (it does the Word → PDF step; on Windows set `SOFFICE` to the full path of `soffice.exe` if it is not).
4. Commit and push. Post the link in the topic-post comments.

If the week's topic post or the poll should be the "up" destination, change `up_url` / `up_label` in
`_config.json` and run `python3 _build/assemble.py` (ten seconds; no need to rebuild pages).

## Pictures, hover text and screen-reader text

Whatever you type in Word's **Alt Text** box becomes both the hover text and what a screen reader says.
To give the screen reader something fuller than the caption, either

- type both in Word, separated by two pipes: `Camels on Mt Sinai || Three camels resting in the shade
  of a rock wall on the path up Mount Sinai, a Bedouin handler crouched beside them` — or
- after the first build, edit the `"alt"` field in `_pics/<id>.json`. That file survives rebuilds; only
  new pictures are added to it.

A picture with no alt text at all is announced as "Picture", which is the worst outcome for a blind
reader — the build prints a reminder for each one. If a picture is purely decorative, give it alt text
of a single hyphen (`-`) and it will be marked decorative and skipped.

The enlarger opens the *original* image file from the Word document, so load pictures in at the size
you want them to enlarge to. A picture whose file is no bigger than it already appears on the page gets no
enlarger at all (there would be nothing to grow into) — in this entry that is the troll, the vineyard, the
red-sea coast and the Bundaberg mural; drop in larger originals if you want those to open.

## Links in the text

The hyperlinks are read out of the `.docx` and laid onto the page text by phrase, so it does not matter whether
the PDF route kept them (Print-to-PDF drops them; Save-As-PDF keeps them). The build reports how many of the
Word file's links it placed; a phrase it cannot find is usually one that was reworded after the link was made.

## Typography

- Body text renders in Liberation Serif, which is metrically identical to Times New Roman: the line
  breaks are Word's line breaks.
- The Liberation Serif files here carry an extra ligature: a comma or full stop next to a quotation
  mark (either order — `,"` `."` `",` `".` and the curly forms) is set with the point tucked beneath the
  quote. Nothing to do in Word; it happens in the font. `_build/commastack.py` rebuilds the fonts.
- Straight quotes in the Word file are set curly in the reader and the text version (the comma-stack
  ligature covers the curly forms). Word's own straight quotes are left alone.
- The beeswax frame (`frame_color`, `frame_inset_mm`, `frame_width_pt` in `_config.json`) is drawn
  *behind* the page, so a picture that bleeds to the edge sits over it.
- The folio line — `LJI · Vol. 12 · Topic 0` at the left, the page number at the right, in the bottom
  margin — is added by the build. Where a picture bleeds over its slot it is left off, as a magazine would.

## Layout

    index.html              the reader
    pages/<id>/N.html       one document per page: background JPEG + positioned live text + hotspots + folio
    pages/<id>/picK.*       the original pictures (for the enlarger and the text version)
    pages/<id>/text.json    extracted text and picture positions (source for the text versions)
    entry/<id>/index.html   plain-text version of each entry, pictures in reading order with their descriptions
    entry/index.html        text-only list of all entries
    assets/bee/             the masthead bee (the cursor is now the cat, drawn inline in index.html)
    assets/fonts/           Carlito, Liberation Serif (with the comma-stack ligature), TeX Gyre Pagella
    _src/  _pdf/  _pics/    Word sources, rendered PDFs, picture descriptions (not served)
    _build/                 the build scripts (`build.py` runs them all)

## The cat

On hover devices the pointer is the grey tabby. She walks after the pointer — in profile for sideways
movement, away from you for up, towards you for down — sits after two seconds still, and bats at anything
clickable (the paw tip is the pointer while she does). Dials are at the top of the cat block in
`_build/templates/index_script.html`: follow rate, sit delay, walk-cycle speed, how vertical a move must
be before she turns, batting tempo. Nothing on touch screens or under a reduced-motion setting.

The sky behind the pages: sunlit dust motes drifting up, eight bees each flying somewhere in particular,
a butterfly now and then, and a pink balloon let go at the foot of the last page.

## Where the edges go

- Left edge, and ← key: `emo_snal` on LiveJournal (`home`)
- North: the ▲ button above the first entry, or a deliberate pull past the top: the topic post (`up_url`).
  Scrolling *to* the top just stops with a bounce; from rest, a small nudge does nothing; about a screen's
  worth of wheel travel (or a real swipe on a phone) goes through, with a cue that fills as you pull.
- South: the same past the end of the last entry, or the button there: LiveJournal (`home`)
- Top bar: Read on LiveJournal / Dreamwidth (follow the open entry), Portfolio (`portfolio`)
- Comment, at the foot of every page: opens into LiveJournal / Dreamwidth (`lj` and `dw` in the entry's metadata),
  shown with the two sites' own favicons
