"""Main application entry point for IBKR report generation."""

import sys
from flex_client import get_flex_report
from parser import parse_xml_to_df, extract_statement_metadata
from report_generator import generate_html_report


def main() -> int:
    """Run full IBKR report generation pipeline."""
    try:
        print("1. Fetching / resolving Flex report...")
        xml_data = get_flex_report()

        print("2. Parsing Flex report XML and metadata...")
        metadata = extract_statement_metadata(xml_data)
        df = parse_xml_to_df(xml_data)

        period_str = ""
        if metadata.get("fromDate") and metadata.get("toDate"):
            period_str = f"Reporting Period: {metadata['fromDate']} to {metadata['toDate']}"
            print(f"   {period_str}")

        print("3. Generating dashboard HTML...")
        generate_html_report(df, output_path="public/index.html", period_str=period_str)

        print("Successfully built public/index.html")
        return 0
    except Exception as e:
        print(f"Error during report generation: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
