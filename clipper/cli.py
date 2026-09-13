"""Command line entry point."""

from __future__ import annotations

import argparse
import os
import sys

from clipper import audio, twitch, video
from clipper.util import Candidate, MissingToolError, timecode


def _cmd_clips(args: argparse.Namespace) -> int:
    """Rank a Twitch channel's viewer-made clips, optionally rendering them."""
    found = twitch.top_clips(args.channel, days=args.days, limit=args.limit)
    if found is None:
        print(
            "No Twitch credentials found. Set TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET\n"
            "(register an app at https://dev.twitch.tv/console/apps), or use:\n"
            "    python -m clipper scan <vod-url>\n"
            "to fall back on loudness detection.",
            file=sys.stderr,
        )
        return 2
    if not found:
        print(f"No clips for {args.channel!r} in the last {args.days} days.")
        return 0

    for i, clip in enumerate(found, 1):
        print(f"{i:2d}. {clip.views:>7,} views  {clip.duration:5.1f}s  {clip.title}")
        print(f"     {clip.url}   (clipped by {clip.creator})")

    if not args.render:
        print("\nRe-run with --render to download these and reframe them for Shorts.")
        return 0

    os.makedirs(args.out, exist_ok=True)
    chosen = found[: args.render]
    for i, clip in enumerate(chosen, 1):
        print(f"\n[{i}/{len(chosen)}] {clip.title}")
        source = video.download(clip.url, os.path.join(args.out, "_source"))
        dur = video.probe_duration(source)
        cand = Candidate(0.0, dur, float(clip.views), "twitch clip")
        out = video.cut(source, cand, args.out, index=i, label=clip.title, mode=args.mode)
        print(f"      -> {out}")
    return 0


def _cmd_scan(args: argparse.Namespace) -> int:
    """Find loud moments in a VOD and cut the top ones."""
    source = args.source
    if "://" in source:
        print(f"Downloading {source} ...")
        source = video.download(source, os.path.join(args.out, "_source"))
        print(f"  -> {source}")
    if not os.path.exists(source):
        print(f"No such file: {source}", file=sys.stderr)
        return 2

    duration = video.probe_duration(source)
    print(f"Scanning {timecode(duration)} of audio for peaks ...")
    peaks = audio.find_candidates(
        source,
        percentile=args.percentile,
        min_gap=args.min_gap,
        limit=args.limit,
    )
    if not peaks:
        print("No peaks stood out -- try lowering --percentile.")
        return 0

    lead = args.length * args.lead_ratio
    tail = args.length - lead
    clips = [p.padded(lead, tail, ceiling=duration) for p in peaks]

    print(f"\n{len(clips)} candidate moments:")
    for i, c in enumerate(clips, 1):
        print(f"{i:2d}. {timecode(c.start)} -> {timecode(c.end)}  ({c.reason})")

    if args.dry_run:
        print("\nDry run -- nothing rendered. Drop --dry-run to cut these.")
        return 0

    print()
    for i, c in enumerate(clips, 1):
        out = video.cut(source, c, args.out, index=i, label=f"at-{timecode(c.start)}", mode=args.mode)
        print(f"[{i}/{len(clips)}] {timecode(c.start)} -> {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="clipper",
        description="Find and cut vertical Shorts from livestream VODs.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--out", default="clips", help="output directory (default: clips)")
    common.add_argument(
        "--mode", choices=("blur", "crop"), default="blur",
        help="blur: keep full frame on a blurred backdrop. crop: fill, losing the sides.",
    )

    c = sub.add_parser("clips", parents=[common], help="rank a Twitch channel's top viewer clips")
    c.add_argument("channel", help="Twitch login, e.g. itzrealmemc")
    c.add_argument("--days", type=int, default=30, help="look back this many days (default 30)")
    c.add_argument("--limit", type=int, default=20, help="how many to list (default 20)")
    c.add_argument(
        "--render", type=int, metavar="N", default=0,
        help="download and reframe the top N (default: list only)",
    )
    c.set_defaults(func=_cmd_clips)

    s = sub.add_parser("scan", parents=[common], help="detect loud moments in a VOD and cut them")
    s.add_argument("source", help="VOD/stream URL, or a local video file")
    s.add_argument("--limit", type=int, default=8, help="max clips to produce (default 8)")
    s.add_argument("--length", type=float, default=45.0, help="clip length in seconds (default 45)")
    s.add_argument(
        "--lead-ratio", type=float, default=0.6,
        help="fraction of the clip that sits before the peak (default 0.6)",
    )
    s.add_argument(
        "--percentile", type=float, default=97.0,
        help="loudness percentile that counts as a peak; lower finds more (default 97)",
    )
    s.add_argument(
        "--min-gap", type=float, default=60.0,
        help="minimum seconds between two picks (default 60)",
    )
    s.add_argument("--dry-run", action="store_true", help="list moments without rendering")
    s.set_defaults(func=_cmd_scan)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    length = getattr(args, "length", None)
    if length is not None and length > video.SHORTS_MAX_SECONDS:
        print(
            f"Warning: {length}s exceeds the {video.SHORTS_MAX_SECONDS}s Shorts limit.",
            file=sys.stderr,
        )
    try:
        return args.func(args)
    except MissingToolError as e:
        print(f"Missing dependency: {e}", file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        return 130
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
