"""Main application entry point for IBKR report generation."""

import argparse
import sys
from flex_client import get_flex_report, get_time_slice_reports, TIME_SLICE_CONFIG
from parser import parse_xml_to_df, extract_statement_metadata
from report_generator import generate_html_report


def main(argv: list[str] | None = None, sample_rate: float | None = None) -> int:
    """Run full IBKR report generation pipeline with multi-time-slice support."""
    arg_parser = argparse.ArgumentParser(description="IBKR report generation pipeline.")
    arg_parser.add_argument(
        "--slices",
        type=str,
        default="1d,7d,30d,ytd",
        help="Comma-separated time slices to generate (default: '1d,7d,30d,ytd').",
    )
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
        requested_slices = [s.strip().lower() for s in args.slices.split(",") if s.strip()]

        print(f"1. Fetching / resolving Flex reports for slices: {', '.join(requested_slices)}...")
        slice_xmls = get_time_slice_reports(requested_slices=requested_slices)

        if not slice_xmls:
            print("Notice: No time-slice reports retrieved. Falling back to default Flex report...")
            xml_data = get_flex_report()
            slice_xmls = {"ytd": xml_data}

        print("2. Parsing Flex reports and extracting metadata...")
        slices_data = {}
        for slice_key, xml_data in slice_xmls.items():
            meta = extract_statement_metadata(xml_data)
            df_slice = parse_xml_to_df(xml_data, sample_rate=effective_sample_rate, random_state=args.seed)

            cfg = TIME_SLICE_CONFIG.get(slice_key, {})
            period_str = ""
            if meta.get("fromDate") and meta.get("toDate"):
                period_str = f"Reporting Period: {meta['fromDate']} to {meta['toDate']}"

            slices_data[slice_key] = {
                "label": cfg.get("label", slice_key.upper()),
                "title": cfg.get("title", slice_key.upper()),
                "period": period_str,
                "df": df_slice,
            }
            print(f"   [{cfg.get('label', slice_key.upper())}] {len(df_slice)} assets | {period_str}")

        print("3. Generating dashboard HTML...")
        default_slice = "ytd" if "ytd" in slices_data else next(iter(slices_data.keys()))
        generate_html_report(slices_data, output_path=args.output, default_slice=default_slice)

        print(f"Successfully built {args.output}")
        return 0
    except Exception as e:
        print(f"Error during report generation: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

