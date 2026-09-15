#!/usr/bin/env python3
"""Bake photos into index.html so they ship with the page.

    python3 tools-embed-photo.py james.jpg [more.jpg ...]

Each image is downscaled to 620px on its long edge, encoded as a JPEG data URI,
and written into the DEFAULT_PHOTOS array. The first one becomes the portrait
James opens on. Re-running replaces the whole list.

Needs Pillow (pip install Pillow); without it, images are embedded as-is.
"""
import base64, io, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
PAGE = HERE / "index.html"


def encode(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(raw))
        im = im.convert("RGB")
        w, h = im.size
        scale = min(1.0, 620 / max(w, h))
        if scale < 1.0:
            im = im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=84, optimize=True)
        raw = buf.getvalue()
    except ImportError:
        print("  (Pillow missing — embedding %s at full size)" % path.name)
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode()


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    uris = []
    for arg in argv:
        p = pathlib.Path(arg)
        if not p.is_file():
            print("no such file: %s" % p)
            return 1
        uris.append(encode(p))
        print("  embedded %s" % p.name)

    body = ",\n".join('    "%s"' % u for u in uris)
    src = PAGE.read_text(encoding="utf-8")
    new, n = re.subn(
        r"var DEFAULT_PHOTOS = \[.*?\];",
        "var DEFAULT_PHOTOS = [\n%s\n  ];" % body,
        src,
        count=1,
        flags=re.S,
    )
    if not n:
        print("could not find DEFAULT_PHOTOS in index.html")
        return 1
    PAGE.write_text(new, encoding="utf-8")
    print("wrote %d photo(s) into %s (%.0f KB)" % (len(uris), PAGE.name, len(new) / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
