"""IBKR Flex Web Service client and local file caching."""

import os
import time
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import requests
from dotenv import load_dotenv

load_dotenv()

IBKR_FLEX_TOKEN = os.getenv("IBKR_FLEX_TOKEN")
IBKR_QUERY_ID = os.getenv("IBKR_QUERY_ID")
CACHE_FILE = "flex_report_cache.xml"
CACHE_MAX_AGE_SECONDS = 86400  # 1 day

REQUEST_TIMEOUT = (10.0, 30.0)  # (connect_timeout, read_timeout)
MAX_SEND_RETRIES = 3
MAX_POLL_ATTEMPTS = 15

# Standard time slices configuration
TIME_SLICE_CONFIG = {
    "1d": {
        "label": "1D",
        "title": "Last Business Day",
        "cache_file": "flex_cache_1d.xml",
        "max_age_seconds": CACHE_MAX_AGE_SECONDS,
    },
    "7d": {
        "label": "7D",
        "title": "Last Week",
        "cache_file": "flex_cache_7d.xml",
        "max_age_seconds": CACHE_MAX_AGE_SECONDS,
    },
    "30d": {
        "label": "30D",
        "title": "Last 30 Days",
        "cache_file": "flex_cache_30d.xml",
        "max_age_seconds": CACHE_MAX_AGE_SECONDS,
    },
    "ytd": {
        "label": "YTD",
        "title": "Year-to-Date",
        "cache_file": "flex_report_cache.xml",
        "max_age_seconds": CACHE_MAX_AGE_SECONDS,
    },
}


def get_last_business_day(ref_date: datetime | None = None) -> str:
    """Return YYYYMMDD string for the last completed business day."""
    d = (ref_date or datetime.now()) - timedelta(days=1)
    while d.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        d -= timedelta(days=1)
    return d.strftime("%Y%m%d")


def _send_request_with_retry(url: str, headers: dict) -> requests.Response:
    """Send initial request to IBKR Flex Web Service with retry on 5xx and connection errors."""
    for attempt in range(1, MAX_SEND_RETRIES + 1):
        try:
            res = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if res.status_code in (500, 502, 503, 504):
                if attempt < MAX_SEND_RETRIES:
                    wait_time = 2.0 * attempt
                    print(f"IBKR returned HTTP {res.status_code}. Retrying initial request ({attempt}/{MAX_SEND_RETRIES}) in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
            res.raise_for_status()
            return res
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if attempt < MAX_SEND_RETRIES:
                wait_time = 2.0 * attempt
                print(f"Network error ({e}). Retrying initial request ({attempt}/{MAX_SEND_RETRIES}) in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
    raise RuntimeError("Failed to send Flex request after multiple retries.")


def fetch_flex_report(
    token: str | None = None,
    query_id: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    period_days: int | None = None,
) -> str:
    """Fetch report from IBKR Flex Web Service and poll until generated with exponential backoff and 5xx retries.

    Supports date range overrides (&fd=YYYYMMDD&td=YYYYMMDD) or period overrides (&p=DAYS).
    """
    token = token or IBKR_FLEX_TOKEN
    query_id = query_id or IBKR_QUERY_ID

    if not token or not query_id:
        raise ValueError("Missing IBKR_FLEX_TOKEN or IBKR_QUERY_ID environment variables.")

    flex_send_url = (
        f"https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService/SendRequest?"
        f"t={token}&q={query_id}&v=3"
    )
    if from_date and to_date:
        flex_send_url += f"&fd={from_date}&td={to_date}"
        print(f"Requesting date range: {from_date} to {to_date}")
    elif period_days:
        flex_send_url += f"&p={period_days}"
        print(f"Requesting rolling period: {period_days} days")

    headers = {"User-Agent": "Mozilla/5.0"}
    res = _send_request_with_retry(flex_send_url, headers=headers)
    print(f"Flex request initiated (HTTP {res.status_code})")
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

    consecutive_5xx = 0
    for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        sleep_time = min(30.0, 5.0 * (1.5 ** attempt))
        print(f"Waiting {sleep_time:.1f}s before polling attempt {attempt}/{MAX_POLL_ATTEMPTS}...")
        time.sleep(sleep_time)

        try:
            stmt_res = requests.get(get_url, headers=headers, timeout=REQUEST_TIMEOUT)
            print(f"Polling attempt {attempt}/{MAX_POLL_ATTEMPTS} completed (HTTP {stmt_res.status_code})")
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            print(f"Network error on polling attempt {attempt}/{MAX_POLL_ATTEMPTS}: {e}. Retrying...")
            continue

        if stmt_res.status_code in (500, 502, 503, 504):
            consecutive_5xx += 1
            print(f"Warning: IBKR server error HTTP {stmt_res.status_code} on attempt {attempt}/{MAX_POLL_ATTEMPTS} ({consecutive_5xx} in a row).")
            if consecutive_5xx >= 5:
                raise RuntimeError(f"IBKR Flex Service continuously unavailable (HTTP {stmt_res.status_code}).")
            continue
        else:
            consecutive_5xx = 0

        if stmt_res.status_code == 200:
            if "<FlexQueryResponse" in stmt_res.text or "<FlexStatements" in stmt_res.text:
                print("Flex statement successfully retrieved.")
                return stmt_res.text

            if "<ErrorCode>" in stmt_res.text:
                err_root = ET.fromstring(stmt_res.text)
                err_code = err_root.findtext("ErrorCode")
                err_msg = err_root.findtext("ErrorMessage")
                if err_code != "1019":  # 1019 = in progress
                    raise RuntimeError(f"IBKR Error ({err_code}): {err_msg}")
                print(f"Statement still generating... (attempt {attempt}/{MAX_POLL_ATTEMPTS})")
        else:
            print(f"Warning: Unexpected HTTP response received: {stmt_res.status_code}")

    raise TimeoutError("IBKR Flex Statement generation timed out.")


def get_flex_report(
    cache_file: str = CACHE_FILE,
    max_age_seconds: int = CACHE_MAX_AGE_SECONDS,
    from_date: str | None = None,
    to_date: str | None = None,
    period_days: int | None = None,
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
        print(f"Local cache expired ({file_age / 3600:.1f} hours old > {max_age_seconds / 3600:.0f}h). Fetching fresh statement...")

    try:
        xml_data = fetch_flex_report(
            from_date=from_date,
            to_date=to_date,
            period_days=period_days,
        )
    except Exception as e:
        # If fetch fails but we have an existing cache file (even expired), use it as fallback
        if not is_ci and os.path.exists(cache_file):
            print(f"Warning: Fetch failed ({e}). Falling back to existing cache {cache_file}...")
            with open(cache_file, "r", encoding="utf-8") as f:
                return f.read()
        raise

    if not is_ci:
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(xml_data)
            print(f"Saved fresh Flex report to local cache: {cache_file}")
        except Exception as e:
            print(f"Warning: Failed to write cache: {e}")

    return xml_data


def get_time_slice_reports(
    requested_slices: list[str] | None = None,
) -> dict[str, str]:
    """Fetch or load cached Flex reports for multiple time slices: 1d, 7d, 30d, ytd."""
    slices_to_fetch = requested_slices or ["1d", "7d", "30d", "ytd"]
    now = datetime.now()
    results = {}

    for idx, slice_key in enumerate(slices_to_fetch):
        if slice_key not in TIME_SLICE_CONFIG:
            print(f"Warning: Unknown time slice '{slice_key}', skipping.")
            continue

        cfg = TIME_SLICE_CONFIG[slice_key]
        cache_file = cfg["cache_file"]
        max_age = cfg["max_age_seconds"]
        from_date = None
        to_date = None
        period_days = None

        if slice_key == "1d":
            biz_day = get_last_business_day(now)
            from_date = biz_day
            to_date = biz_day
        elif slice_key == "7d":
            period_days = 7
        elif slice_key == "30d":
            period_days = 30
        elif slice_key == "ytd":
            from_date = f"{now.year}0101"
            to_date = get_last_business_day(now)

        print(f"\n--- Resolving Slice [{cfg['label']}] {cfg['title']} ---")
        try:
            xml_data = get_flex_report(
                cache_file=cache_file,
                max_age_seconds=max_age,
                from_date=from_date,
                to_date=to_date,
                period_days=period_days,
            )
            results[slice_key] = xml_data
        except Exception as e:
            # Omit the failed slice instead of substituting data from another period
            # (previously: the YTD cache was served under a failed slice's label, e.g. "1D").
            # main.py only renders slices that resolved successfully, so the dashboard
            # simply shows no tab for a missing slice.
            print(f"Error fetching slice '{slice_key}': {e}. Omitting this slice from the report.")

        # Add brief pause between sequential IBKR requests to avoid rate limits
        if idx < len(slices_to_fetch) - 1:
            time.sleep(2.0)

    return results
