# Photos of James

Two ways to get James into the game.

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

Square-ish, face-centred crops look best — the portrait is a circle.
