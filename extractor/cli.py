"""CLI entry point for hospital sticker data extraction."""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="sticker-extract",
        description="Extract patient data from hospital admission sticker photos.",
    )
    parser.add_argument(
        "images",
        nargs="+",
        help="Path(s) to sticker photo(s). Supports JPEG, PNG, HEIC.",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output JSON file path (default: prints to stdout).",
    )
    parser.add_argument(
        "--csv",
        help="Also export results to this CSV file path.",
    )
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-20250514",
        help="Claude model to use (default: claude-sonnet-4-20250514).",
    )
    parser.add_argument(
        "--api-key",
        help="Anthropic API key (default: reads ANTHROPIC_API_KEY env var).",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress progress output.",
    )

    args = parser.parse_args()

    # Resolve API key
    api_key = args.api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "Error: No API key provided. Either:\n"
            "  1. Set ANTHROPIC_API_KEY in your .env file\n"
            "  2. Export ANTHROPIC_API_KEY in your shell\n"
            "  3. Pass --api-key YOUR_KEY\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate image paths
    image_paths = []
    for p in args.images:
        path = Path(p).expanduser().resolve()
        if not path.exists():
            print(f"Error: File not found: {p}", file=sys.stderr)
            sys.exit(1)
        image_paths.append(path)

    # Import here to avoid slow startup when just checking --help
    from .extract import extract_batch
    from .export import to_json, save_json, save_csv, print_record

    # Progress callback
    def on_progress(i, total, filename):
        if not args.quiet:
            print(f"[{i}/{total}] Processing {filename}...", file=sys.stderr)

    # Extract
    results = extract_batch(
        image_paths,
        api_key=api_key,
        model=args.model,
        on_progress=on_progress,
    )

    # Print results
    if not args.quiet:
        print("\n" + "=" * 60, file=sys.stderr)
        print(f"Extracted {len(results)} record(s)\n", file=sys.stderr)
        for record in results:
            print_record(record, file=sys.stderr)

    # Output JSON
    if args.output:
        save_json(results, args.output)
        if not args.quiet:
            print(f"JSON saved to: {args.output}", file=sys.stderr)
    else:
        print(to_json(results))

    # Output CSV
    if args.csv:
        save_csv(results, args.csv)
        if not args.quiet:
            print(f"CSV saved to: {args.csv}", file=sys.stderr)

    # Summary
    success = sum(1 for r in results if r.get("_status") == "success")
    errors = len(results) - success
    if errors and not args.quiet:
        print(f"\n{errors} image(s) had extraction errors.", file=sys.stderr)

    sys.exit(1 if errors == len(results) else 0)


if __name__ == "__main__":
    main()
