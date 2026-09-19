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

## Fixing a typo without re-exporting

`_corrections.json` holds text corrections applied at build time, per entry:

        {"s12-t0": [["for me, its", "for me, it’s"]]}

Each pair is an exact phrase and its replacement (keep it within one line of the page, as printed); it is applied to the live text on the pages and to the text
version. Use it for a typo caught after the PDF was exported - and fix the Word file too, so the next export
does not need the patch.

## Footnotes as hover text

A superscript number (or * †) in the text that has a matching note - at the foot of the page or in a
numbered list at the end - shows that note when the pointer rests on it, when it is tapped, or when it takes
keyboard focus. Notes are found automatically: a line starting with the number, in sequence from 1 (or set
smaller than the body text), followed by a capital, a quote or a web address. Nothing to set up.

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


## A looping video on a page

The reader can lay a muted, looping video exactly over a picture in the Word layout (the picture becomes
the poster frame). Put a still from the video into the Word document where the video should play, build
as usual, then in `_pics/<id>.json` add to that picture's entry:

        "video": "../../assets/silkroad_loop.mp4"      path relative to pages/<id>/
        "webm":  "../../assets/silkroad_loop.webm"     optional second source

and rebuild. It autoplays silently and loops; readers with *reduce motion* set see the still instead.
`assets/silkroad_loop.mp4` (72 s, 1120x720, H.264) is the Silk Road caravan loop Samarkand -> Andijan ->
Kashgar -> Badakhshan -> Balkh -> Samarkand; `assets/silkroad_loop_poster.jpg` is its first frame.

## An illuminated border round an entry

An entry can wear a decorative border. Put a PNG with a transparent centre into `assets/`, then in
`_entries_meta.json` add to that entry:

        "frame": {"img": "assets/frame-silkroad.png", "bleed": 10}

The border is drawn **by the reader, not by the page**: it sits over each page in the reader and is allowed to
hang out past the paper by `bleed` mm, so its finials, gems and corner lions run off the edge into the sky
rather than being cut at the trim. (A border drawn inside a page document could only ever be clipped at the
paper's edge, which is why it lives in the shell.) It also covers the web-app page: there the game fills the
whole paper and a small pill in the bottom-right corner carries the "in its own window" link.

**Sizing it.** The text block is 25.4 mm in from the paper edge. Nothing opaque in the artwork may reach
further in than that once bled — and corner cartouches always reach further than the straight runs, so
measure the corners. To check a candidate: composite it over a page at the intended bleed and find the
smallest uniform margin whose inner rectangle contains no opaque pixel. `frame-silkroad.png` needs 30.5 mm
unbled and 23.5 mm at `bleed: 10`, which is what makes 10 the right number for it.

Because the border is the reader's, it does not appear in the standalone page files or the text version.

## Pictures that should not enlarge

A picture the reader would otherwise offer to grow (its file is bigger than it appears) can opt out - a
screenshot, say, where there is nothing more to see. In `_pics/<id>.json`:

        "noenlarge": true

Hand-added keys in that file (`video`, `webm`, `anim`, `phase`, `terrain`, `noenlarge`) survive rebuilds.

## An animated scene on a page

Instead of a video, a picture can be replaced by a live SVG scene drawn by the build. It stays crisp at
any zoom (a video softens), weighs a few KB rather than megabytes, and needs no media files at all.

Put a still where the scene should play in the Word document, build once, then in `_pics/<id>.json` add
to that picture's entry:

        "anim":    "caravan"      the scene; "caravan" is the Silk Road journeyScene
        "phase":   0              0 day, 1 dusk, 2 night, 3 dawn        (optional)
        "terrain": "desert"       settled | steppe | desert | harsh | mountain | rugged   (optional)

and rebuild. The scene is laid exactly over the still, sized to the same box, and cropped to fill it
(`xMidYMid slice`), so it works whatever shape the picture is. It sits **above the page art and below the
words**, so a title printed over the picture in Word still reads on top of the animation. Readers with
*reduce motion* set see the original still instead — the picture is still there in the page art underneath.

To add another scene, write a function returning one `<svg class="panim">` and register it in `ANIMS` at
the foot of `_build/buildpages.py`. Keep any `id` you use suffixed with the `uid` argument: two scenes can
share a page and duplicate ids would cross-wire their gradients.

## A web app as the last page

An entry can end on a page that *is* a live web page - the Silk Road game, playable in the reader. Add to the
entry in `_entries_meta.json`:

        "app": {
         "url":   "https://krisfricke.github.io/Silk-Road/",     what the page shows (add ?start=lji for the #LJI setting)
         "title": "The Silk Road",                               named in the page's top bar and the text version
         "note":  "play it here, or open it in its own window",  optional, italic, in the top bar
         "wmm": 210, "hmm": 297                                  optional page size; default A4 portrait
        }

and build as usual. The build appends one more page after the PDF's pages: the beeswax frame drawn in CSS at
the same inset, a top bar with the folio slug, the note, an "in its own window" link and the page number, and
the app filling the rest. It counts in the page total ("PAGE 11 / 11") and the text version ends with a
"Play ..." link. The app is loaded lazily, only when the reader scrolls down to it, and it keeps its own
saved games and leaderboard because it runs from its own site. Two things to know: the reader's cat cursor
stops at the app's edge (the pointer inside it belongs to the app), and the app's own scrolling takes the
wheel first - the page scrolls on once the app is at the end of what it can show.

