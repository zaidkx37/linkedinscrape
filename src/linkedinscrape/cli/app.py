"""
Optional CLI for linkedinscrape.

Usage::

    python -m linkedinscrape.cli.app <username>
    python -m linkedinscrape.cli.app --file usernames.txt
    python -m linkedinscrape.cli.app --local response.json
    python -m linkedinscrape.cli.app <username> --format both
    python -m linkedinscrape.cli.app <username> --proxy http://host:port
    python -m linkedinscrape.cli.app <username> --proxy-file proxies.txt
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from ..client import LinkedIn
from ..exporter import Exporter
from ..models import LinkedInProfile


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="linkedinscrape",
        description="LinkedIn Profile Scraper SDK",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "username", nargs="?", help="LinkedIn vanity name (part after /in/)"
    )
    group.add_argument(
        "--file", "-f", type=str, help="Text file with one username per line"
    )
    group.add_argument(
        "--local", "-l", type=str, help="Parse a local response JSON file"
    )

    ap.add_argument(
        "--format", choices=["json", "csv", "both"], default="json",
        help="Output format (default: json)",
    )
    ap.add_argument("--output", "-o", type=str, default="output", help="Output directory")
    ap.add_argument(
        "--delay", type=float, default=1.5, help="Delay between requests (seconds)"
    )
    ap.add_argument(
        "--proxy", type=str, default=None,
        help="Proxy URL (e.g. http://user:pass@host:port)",
    )
    ap.add_argument(
        "--proxy-file", type=str, default=None,
        help="Text file with one proxy URL per line (rotated round-robin)",
    )
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--no-summary", action="store_true", help="Skip console summary")
    ap.add_argument(
        "--skip-check", action="store_true",
        help="Skip cookie validation on startup",
    )
    return ap


def main(argv: list[str] | None = None) -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

    ap = _build_parser()
    args = ap.parse_args(argv)
    _setup_logging(args.verbose)

    exporter = Exporter(args.output)
    profiles: list[LinkedInProfile] = []

    if args.local:
        profiles.append(LinkedIn.parse_local(args.local))
    else:
        with LinkedIn(
            delay=args.delay,
            proxy=args.proxy,
            proxy_file=args.proxy_file,
            validate=not args.skip_check,
        ) as client:
            if args.file:
                path = Path(args.file)
                if not path.exists():
                    print(f"Error: File not found: {path}")
                    sys.exit(1)
                usernames = path.read_text(encoding="utf-8").splitlines()
                profiles = client.scrape_batch(usernames)
            elif args.username:
                profiles.append(client.scrape(args.username))

    if not profiles:
        print("No profiles were scraped.")
        sys.exit(1)

    for profile in profiles:
        if not args.no_summary:
            exporter.print_summary(profile)

    if args.format in ("json", "both"):
        if len(profiles) == 1:
            exporter.to_json(profiles[0])
        else:
            exporter.to_json_batch(profiles)

    if args.format in ("csv", "both"):
        exporter.to_csv(profiles)

    print(f"Done. {len(profiles)} profile(s) exported to '{args.output}/'")


if __name__ == "__main__":
    main()
