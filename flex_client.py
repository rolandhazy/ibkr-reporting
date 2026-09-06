"""IBKR Flex Web Service client and local file caching."""

import os
import time
import xml.etree.ElementTree as ET
import requests
from dotenv import load_dotenv

load_dotenv()

IBKR_FLEX_TOKEN = os.getenv("IBKR_FLEX_TOKEN")
IBKR_QUERY_ID = os.getenv("IBKR_QUERY_ID")
CACHE_FILE = "flex_report_cache.xml"
CACHE_MAX_AGE_SECONDS = 86400  # 1 day


def fetch_flex_report(token: str | None = None, query_id: str | None = None) -> str:
    """Fetch report from IBKR Flex Web Service and poll until generated."""
    token = token or IBKR_FLEX_TOKEN
    query_id = query_id or IBKR_QUERY_ID

    if not token or not query_id:
        raise ValueError("Missing IBKR_FLEX_TOKEN or IBKR_QUERY_ID environment variables.")

    flex_send_url = (
        f"https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService/SendRequest?"
        f"t={token}&q={query_id}&v=3"
    )

    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(flex_send_url, headers=headers)
    res.raise_for_status()
    root = ET.fromstring(res.text)

    if root.findtext("Status") != "Success":
        code = root.findtext("ErrorCode") or ""
        msg = root.findtext("ErrorMessage") or res.text
        raise RuntimeError(f"Flex Request Failed ({code}): {msg}")

    ref_code = root.findtext("ReferenceCode")
    base_get_url = (
        root.findtext("Url")
        or "https://gdcdyn.interactivebrokers.com/AccountManagement/FlexWebService/GetStatement"
    )
    get_url = f"{base_get_url}?q={ref_code}&t={token}&v=3"
    print(f"Flex statement request accepted (Reference: {ref_code}). Polling for completion...")

    for attempt in range(1, 15):
        time.sleep(10)
        stmt_res = requests.get(get_url, headers=headers)
        if "<FlexQueryResponse" in stmt_res.text or "<FlexStatements" in stmt_res.text:
            print("Flex statement successfully retrieved.")
            return stmt_res.text

        if "<ErrorCode>" in stmt_res.text:
            err_root = ET.fromstring(stmt_res.text)
            err_code = err_root.findtext("ErrorCode")
            err_msg = err_root.findtext("ErrorMessage")
            if err_code != "1019":  # 1019 = in progress
                raise RuntimeError(f"IBKR Error ({err_code}): {err_msg}")
            print(f"Statement still generating... (attempt {attempt}/14)")

    raise TimeoutError("IBKR Flex Statement generation timed out.")


def get_flex_report(
    cache_file: str = CACHE_FILE,
    max_age_seconds: int = CACHE_MAX_AGE_SECONDS
) -> str:
    """Get Flex report, using local cache if available and < max_age_seconds when not in CI."""
    is_ci = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"

    if not is_ci and os.path.exists(cache_file):
        file_age = time.time() - os.path.getmtime(cache_file)
        if file_age < max_age_seconds:
            hours_old = file_age / 3600
            print(f"Using local cached Flex report: {cache_file} ({hours_old:.1f} hours old)")
            with open(cache_file, "r", encoding="utf-8") as f:
                return f.read()
        print(f"Local cache expired ({file_age / 3600:.1f} hours old > 24h). Fetching fresh statement...")

    xml_data = fetch_flex_report()

    if not is_ci:
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(xml_data)
            print(f"Saved fresh Flex report to local cache: {cache_file}")
        except Exception as e:
            print(f"Warning: Failed to write cache: {e}")

    return xml_data
