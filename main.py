"""Main application entry point for IBKR report generation."""

import argparse
import sys
from flex_client import get_flex_report
from parser import parse_xml_to_df, extract_statement_metadata
from report_generator import generate_html_report


def main(argv: list[str] | None = None, sample_rate: float | None = None) -> int:
    """Run full IBKR report generation pipeline."""
    arg_parser = argparse.ArgumentParser(description="IBKR report generation pipeline.")
    arg_parser.add_argument(
        "--sample-rate",
        type=float,
        nargs="?",
        const=0.3,
        default=None,
        metavar="RATE",
        help="Fraction of portfolio to randomly sample (0.0 to 1.0, default: 0.3 if flag passed without value).",
    )
    arg_parser.add_argument(
        "--output",
        type=str,
        default="public/index.html",
        help="Destination path for HTML dashboard (default: public/index.html).",
    )
    arg_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        metavar="INT",
        help="Random seed for reproducible sampling (default: None for fresh randomness each run).",
    )
    args = arg_parser.parse_args(argv)

    effective_sample_rate = sample_rate if sample_rate is not None else args.sample_rate

    try:
        print("1. Fetching / resolving Flex report...")
        xml_data = get_flex_report()

        print("2. Parsing Flex report XML and metadata...")
        metadata = extract_statement_metadata(xml_data)
        df = parse_xml_to_df(xml_data, sample_rate=effective_sample_rate, random_state=args.seed)

        period_str = ""
        if metadata.get("fromDate") and metadata.get("toDate"):
            period_str = f"Reporting Period: {metadata['fromDate']} to {metadata['toDate']}"
            print(f"   {period_str}")

        print("3. Generating dashboard HTML...")
        generate_html_report(df, output_path=args.output, period_str=period_str)

        print(f"Successfully built {args.output}")
        return 0
    except Exception as e:
        print(f"Error during report generation: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

