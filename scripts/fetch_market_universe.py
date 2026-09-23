#!/usr/bin/env python3
"""Download the latest official TWSE/TPEx closing snapshot for GitHub Pages."""

from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.request import Request, urlopen

SOURCES = {
    "TW": "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
    "TWO": "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes",
}
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "market-universe.json"


def get_json(url: str):
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "Taiwan-stock-pages-updater/1.0"})
    with urlopen(request, timeout=45) as response:
        data = json.load(response)
    if not isinstance(data, list):
        raise ValueError("official API returned an unexpected payload")
    return data


def first(row: dict, *keys: str):
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return ""


def number(value) -> float:
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return 0


def normalize(rows: list[dict], market: str):
    normalized = []
    for row in rows:
        code = str(first(row, "Code", "證券代號", "SecuritiesCompanyCode")).strip()
        name = str(first(row, "Name", "證券名稱", "CompanyName", "SecuritiesCompanyName")).strip()
        close = number(first(row, "ClosingPrice", "收盤價", "Close"))
        volume = number(first(row, "TradeVolume", "成交股數", "TradingShares"))
        turnover = number(first(row, "TradeValue", "成交金額", "TradingValue", "TransactionAmount"))
        if code and name and close > 0 and volume > 0:
            normalized.append({"code": code, "name": name, "market": market, "close": close, "volume": volume, "turnover": turnover})
    return normalized


def main():
    rows = []
    failed = []
    for market, url in SOURCES.items():
        try:
            rows.extend(normalize(get_json(url), market))
        except Exception as error:
            print(f"{market} download failed: {error}")
            failed.append(market)
    if not rows:
        raise RuntimeError("Both official market sources failed; keeping the previous published snapshot.")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "TWSE/TPEx official OpenAPI",
        "unavailable": failed,
        "rows": rows,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(rows)} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
