# clipper

Finds candidate moments in a long livestream VOD and cuts them into vertical
1080x1920 MP4s ready to upload as YouTube Shorts.

It does not decide what is *funny* — nothing automated does. It narrows hours of
VOD down to a handful of timestamps worth your attention, and does the tedious
part (downloading, cutting, reframing, encoding to spec) once you've picked.

## Install

```bash
pip install -r requirements.txt          # yt-dlp
# plus ffmpeg + ffprobe on PATH:
#   macOS    brew install ffmpeg
#   Debian   sudo apt install ffmpeg
#   Windows  winget install Gyan.FFmpeg
```

## Two ways to find moments

### 1. Twitch viewer clips (best signal)

If the streamer is on Twitch, viewers have already clipped the good parts and
view counts rank them. Real humans beat any heuristic.

```bash
export TWITCH_CLIENT_ID=...       # register at dev.twitch.tv/console/apps
export TWITCH_CLIENT_SECRET=...

python -m clipper clips <channel> --days 30          # list the top 20
python -m clipper clips <channel> --render 5         # cut the top 5
```

### 2. Loudness scan (no credentials, any platform)

For a YouTube VOD, a Twitch VOD, or a local file. ffmpeg's `ebur128` filter
reports momentary loudness every ~100ms; sustained peaks track reactions —
shouting, fight audio, clutch moments.

```bash
python -m clipper scan <url-or-file> --dry-run       # just list timestamps
python -m clipper scan <url-or-file> --limit 8       # cut the top 8
```

Start with `--dry-run`. It prints source timestamps, so you can skim those spots
in the VOD and only render what actually lands.

## Framing

`--mode blur` (default) keeps the entire 16:9 frame on a blurred blow-up of
itself — nothing is cropped away, which matters for gameplay where the hotbar
and health sit at the frame edges.

`--mode crop` fills the whole vertical frame but shaves the sides. Better for
face-cam or centred action, worse for HUD-heavy gameplay.

## Tuning the scan

| Flag | Default | Effect |
|---|---|---|
| `--percentile` | 97 | Lower finds more, noisier candidates |
| `--min-gap` | 60 | Minimum seconds between picks, so one long fight doesn't fill the list |
| `--length` | 45 | Clip length in seconds |
| `--lead-ratio` | 0.6 | Fraction of the clip before the peak — the build-up usually matters more than the aftermath |

If a scan returns nothing, the stream's audio is probably evenly mixed; drop
`--percentile` to 90 and re-run.

## Output

`clips/NN-<label>-<timestamp>.mp4` — H.264 high profile, yuv420p, 30fps, AAC
192k @ 48kHz, `+faststart`. Source downloads land in `clips/_source/` and can be
deleted once you're happy with the cuts.

Shorts accepts up to 180 seconds; the CLI warns past that.

## Before you post someone else's stream

Clipping another creator's stream is their call, not the tool's:

- Check their channel About page, panels, or Discord for a clipping policy —
  many creators explicitly allow clip channels, some require credit, some say no.
- Credit them by name and link the source VOD or clip in every description.
- Reuploading someone else's footage can trip YouTube's Content ID and its
  reused-content rules for monetisation, regardless of permission.

When in doubt, ask the streamer first. Most say yes.

## James Clicker

An idle clicker game about one guy, in `james-clicker/`. Open
`james-clicker/index.html` in a browser, add a few photos of James, and click him.
See `james-clicker/photos/README.md` for the ways to load photos.

Players enter a name before their first click. Scores travel as short `JC1-`
codes: a player copies their code, sends it over, and whoever keeps the board
pastes it in. Each browser stores the board it has been given, so the page needs
no backend and can be shared with anyone. Scores are self-reported.
