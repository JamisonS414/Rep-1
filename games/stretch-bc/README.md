# Stretch BC

An arcade taffy-pull built for a friend named BC.

BC's shoes are glued to the boardwalk. Drag his head around the pier to snag
candy — but the farther you pull, the faster his **strain** meter fills. Ease
off before it tops out or BC snaps. Three snaps ends the round; so does the
60-second clock.

- **Combo** climbs while you keep collecting inside 2.7 seconds.
- **Risky grabs** — candy taken with the meter in the red — score double.
- **Gold candy** appears every 9–15 seconds, sits out near the edges of his
  reach, and is worth 500 before it vanishes.
- Every candy warms the taffy, temporarily buying a little extra safe length.

## BC's face

BC ships with a blank head. **Give BC a face** under the stage opens a picture
from your device (or drop one straight onto the stage), then a circular framer
— drag or arrow-key to move, slide to zoom. The picture rides on his head and
squashes and tilts along with him.

The face is downscaled to 256x256 and kept in `localStorage`, so it lives on
that browser only: it is never uploaded anywhere, and anyone else opening the
page sees the blank head until they add their own. **Remove** clears it.

Open `index.html` in a browser. No build step, no dependencies — one file,
canvas rendering, mouse/touch drag or arrow-key steering.
