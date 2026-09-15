# Photos of James

Three ways to get James into the game.

**1. In the browser (easiest).** Open the game and use **+ Add photos of James**, or
drag photos onto the portrait. They are downscaled to 620px, stored in that browser
only, and never uploaded anywhere. Up to 16 at a time; he shuffles on every click.

**2. Committed to the repo.** Drop image files in this folder and list them in
`photos.json` next to them:

```json
["james-01.jpg", "james-02.jpg", "james-03.jpg"]
```

The game fetches `photos/photos.json` on load and uses those when the browser has no
photos saved yet. This path needs the page served over http (`python3 -m http.server`),
since `fetch` is blocked for `file://` URLs.

**3. Baked into the page (what everyone sees).** From `james-clicker/`, run:

```
python3 tools-embed-photo.py photos/james-main.jpg
```

It downscales each image and writes it into the `DEFAULT_PHOTOS` array in
`index.html`, so the photo ships with the page — it works over `file://`, in the
repo, and for anyone opening a published link, with no fetch involved. The first
file given is the portrait James opens on. Anything a viewer adds or removes in
their own browser still wins over this list.

Square-ish, face-centred crops look best — the portrait is a circle.
