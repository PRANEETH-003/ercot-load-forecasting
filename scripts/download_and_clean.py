"""
ERCOT Grid Load & Price Analysis - data download and cleaning script.

What this script does
---------------------
1. LOAD: downloads ERCOT's official "Native Load" archive for 2025 (hourly
   load in MW for ERCOT's 8 weather zones plus the ERCOT total), reads the
   Excel file inside the zip, converts ERCOT's "Hour Ending" labels into
   normal hour-beginning timestamps, runs data-quality checks, and writes
   a clean CSV to data/clean/.

2. PRICES (optional): tries to download ERCOT's "Historical DAM Load Zone
   and Hub Prices" archive for 2025 (day-ahead settlement point prices,
   $/MWh) from ERCOT's Market Information System (MIS). If the file is
   already in data/raw/ (e.g. downloaded by hand in a browser), it cleans
   the hub prices and merges them with the load data instead.

Data sources (all public, no account or API key needed)
-------------------------------------------------------
- Hourly load:  ERCOT "Hourly Load Data Archives" page
  https://www.ercot.com/gridinfo/load/load_hist
  File used: Native_Load_2025.zip (contains Native_Load_2025.xlsx)
- DAM prices:   ERCOT data product NP4-180-ER "Historical DAM Load Zone
  and Hub Prices", file DAMLZHBSPP_2025, listed via the ERCOT MIS API.

Known data quirks (found while building this, they are real)
------------------------------------------------------------
- ERCOT labels hours by the hour ENDING, and the last hour of a day is
  labeled "24:00", which is not a valid clock time. We parse the label by
  hand: timestamp = date + (hour_ending - 1) hours.
- Daylight saving time: on the spring-forward day one local hour does not
  exist, and on the fall-back day one local hour happens twice. ERCOT's
  file has exactly 8,760 rows for 2025, and after parsing we see exactly
  one missing local hour and one duplicated local timestamp. The checks
  below report them instead of silently hiding them.

Only pandas + the Python standard library are used.
"""

import io
import json
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

# --------------------------------------------------------------------------
# Paths and source URLs
# --------------------------------------------------------------------------
PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
CLEAN_DIR = PROJECT_DIR / "data" / "clean"

YEAR = 2025

LOAD_ZIP_NAME = f"Native_Load_{YEAR}.zip"
LOAD_XLSX_NAME = f"Native_Load_{YEAR}.xlsx"
LOAD_URL = "https://www.ercot.com/files/docs/2025/02/11/Native_Load_2025.zip"

# ERCOT MIS endpoints for the historical day-ahead price archive.
MIS_LIST_URL = (
    "https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=13060"
)
MIS_DOWNLOAD_URL = "https://www.ercot.com/misapp/servlets/IceDocDownloadJsonWS?docid={}"
PRICE_FILE_STEM = f"DAMLZHBSPP_{YEAR}"  # ERCOT's name for the annual price file
HUBS = ["HB_NORTH", "HB_HOUSTON", "HB_SOUTH", "HB_WEST", "HB_PAN"]

USER_AGENT = {"User-Agent": "Mozilla/5.0 (student data project)"}


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def download(url, dest):
    """Download url to dest (a Path). Returns True if a real file arrived."""
    req = urllib.request.Request(url, headers=USER_AGENT)
    with urllib.request.urlopen(req, timeout=180) as response:
        data = response.read()
    if len(data) == 0:
        return False
    dest.write_bytes(data)
    return True


def report_checks(df, time_col="timestamp"):
    """Print basic data-quality checks for an hourly time series."""
    ts = df[time_col]
    print(f"  rows:              {len(df)}")
    print(f"  time range:        {ts.min()}  ->  {ts.max()}")
    print(f"  NaN cells:         {int(df.isna().sum().sum())}")

    dup_count = int(ts.duplicated().sum())
    print(f"  duplicated times:  {dup_count}")
    if dup_count:
        dups = ts[ts.duplicated(keep=False)].unique()
        print(f"    -> duplicated timestamp(s): {list(dups)} (fall DST day)")

    full_index = pd.date_range(ts.min(), ts.max(), freq="h")
    missing = full_index.difference(ts.unique())
    print(f"  missing hours:     {len(missing)}")
    if len(missing):
        print(f"    -> missing timestamp(s): {list(missing)} (spring DST day)")


# --------------------------------------------------------------------------
# Part 1 - ERCOT hourly load
# --------------------------------------------------------------------------
def get_load_file():
    """Make sure the Native Load zip is in data/raw, downloading if needed."""
    zip_path = RAW_DIR / LOAD_ZIP_NAME
    if zip_path.exists() and zip_path.stat().st_size > 0:
        print(f"  found {LOAD_ZIP_NAME} already in data/raw, skipping download")
        return zip_path
    print(f"  downloading {LOAD_URL}")
    if not download(LOAD_URL, zip_path):
        raise RuntimeError("Load download returned an empty file.")
    return zip_path


def clean_load():
    print("PART 1 - ERCOT hourly load")
    zip_path = get_load_file()

    # The zip contains one Excel workbook with the hourly table.
    with zipfile.ZipFile(zip_path) as zf:
        excel_bytes = zf.read(LOAD_XLSX_NAME)
    raw = pd.read_excel(io.BytesIO(excel_bytes))
    print(f"  raw columns: {list(raw.columns)}")

    # --- Parse "Hour Ending" (e.g. "01/01/2025 24:00") ---------------------
    # Split into the date part and the hour-ending number (1..24), then
    # timestamp = midnight of that date + (hour_ending - 1) hours.
    # This handles the "24:00" label naturally.
    parts = raw["Hour Ending"].astype(str).str.split(" ", expand=True)
    day = pd.to_datetime(parts[0], format="%m/%d/%Y")
    hour_ending = parts[1].str.split(":").str[0].astype(int)
    timestamp = day + pd.to_timedelta(hour_ending - 1, unit="h")

    # --- Build the clean table --------------------------------------------
    zones = ["COAST", "EAST", "FWEST", "NORTH", "NCENT", "SOUTH", "SCENT", "WEST"]
    clean = pd.DataFrame({"timestamp": timestamp})
    for zone in zones:
        clean[f"{zone.lower()}_mw"] = raw[zone]
    clean["load_mw"] = raw["ERCOT"]  # ERCOT-wide total load

    # Put the total right after the timestamp, keep file order (chronological).
    cols = ["timestamp", "load_mw"] + [f"{z.lower()}_mw" for z in zones]
    clean = clean[cols].reset_index(drop=True)

    print("  data-quality checks (cleaned load):")
    report_checks(clean)
    peak_row = clean.loc[clean["load_mw"].idxmax()]
    print(f"  peak load:         {peak_row['load_mw']:,.1f} MW at {peak_row['timestamp']}")
    print(f"  mean load:         {clean['load_mw'].mean():,.1f} MW")
    print(f"  min load:          {clean['load_mw'].min():,.1f} MW")

    out_path = CLEAN_DIR / f"ercot_load_{YEAR}_clean.csv"
    clean.to_csv(out_path, index=False)
    print(f"  wrote {out_path} ({len(clean)} rows)")
    return clean


# --------------------------------------------------------------------------
# Part 2 - ERCOT day-ahead hub prices (optional)
# --------------------------------------------------------------------------
def get_price_file():
    """
    Return the Path of the DAMLZHBSPP zip/xlsx in data/raw, or None.

    First looks for a manually downloaded file, then tries ERCOT's MIS
    download service. Note (Oct 2026): from some networks the MIS list API
    answers but the file-download service returns 404 - in that case,
    download the file by hand from the NP4-180-ER data product page and
    put it in data/raw/ with its original name.
    """
    for ext in (".zip", ".xlsx"):
        candidate = RAW_DIR / f"{PRICE_FILE_STEM}{ext}"
        if candidate.exists() and candidate.stat().st_size > 0:
            print(f"  found {candidate.name} in data/raw")
            return candidate

    print("  price file not in data/raw - asking ERCOT MIS for the document list...")
    try:
        req = urllib.request.Request(MIS_LIST_URL, headers=USER_AGENT)
        with urllib.request.urlopen(req, timeout=120) as response:
            listing = json.loads(response.read().decode("utf-8"))
        docs = listing["ListDocsByRptTypeRes"]["DocumentList"]
        doc_id = None
        for doc in docs:
            d = doc["Document"]
            if d["FriendlyName"] == PRICE_FILE_STEM and d["Extension"] == "zip":
                doc_id = d["DocID"]
                break
        if doc_id is None:
            print("  could not find the file in ERCOT's document list")
            return None
        dest = RAW_DIR / f"{PRICE_FILE_STEM}.zip"
        print(f"  trying MIS download (docid {doc_id})...")
        if download(MIS_DOWNLOAD_URL.format(doc_id), dest):
            # A real zip starts with the bytes 'PK'; a 404 page does not.
            if dest.read_bytes()[:2] == b"PK":
                return dest
            dest.unlink()
        print("  MIS file download failed (server returned no file).")
    except Exception as err:  # network problems should not kill the script
        print(f"  MIS download attempt failed: {err}")
    print(
        "  -> To add prices later: open https://www.ercot.com/mp/data-products/"
        f"data-product-details?id=NP4-180-ER , download {PRICE_FILE_STEM}, "
        "and save it into data/raw/ with that name."
    )
    return None


def read_price_workbook(path):
    """
    Read the DAMLZHBSPP workbook into one long DataFrame.

    ERCOT publishes this file in one of two layouts, so we detect which:
      A) long format: columns like Date / Hour Ending / Settlement Point /
         Price (possibly one sheet per month)
      B) wide format: a date-time first column and one column per hub
    If neither layout is recognized we print what we found and stop,
    rather than guessing silently.
    """
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as zf:
            names = [n for n in zf.namelist() if n.endswith(".xlsx")]
            excel_bytes = zf.read(names[0])
        sheets = pd.read_excel(io.BytesIO(excel_bytes), sheet_name=None)
    else:
        sheets = pd.read_excel(path, sheet_name=None)

    frames = []
    for sheet_name, df in sheets.items():
        cols = {str(c).strip().lower(): c for c in df.columns}
        if "price" in cols and any("settlement" in c for c in cols):
            frames.append(df)  # layout A sheet
    if frames:
        return pd.concat(frames, ignore_index=True), "A"

    # Layout B check: any sheet with hub names among its columns?
    for sheet_name, df in sheets.items():
        upper_cols = [str(c).strip().upper() for c in df.columns]
        if any(hub in upper_cols for hub in HUBS):
            return df, "B"

    print("  price workbook layout not recognized. Sheets found:")
    for sheet_name, df in sheets.items():
        print(f"    sheet '{sheet_name}': shape {df.shape}, columns {list(df.columns)[:8]}")
    return None, None


def clean_prices(load_df):
    print("PART 2 - ERCOT day-ahead hub prices (optional)")
    path = get_price_file()
    if path is None:
        print("  skipping prices - load-only dataset this run")
        return None

    data, layout = read_price_workbook(path)
    if data is None:
        print("  skipping prices - workbook could not be parsed")
        return None

    if layout == "A":
        cols = {str(c).strip().lower(): c for c in data.columns}
        date_col = next(c for c in cols if "date" in c)
        hour_col = next(c for c in cols if "hour" in c)
        point_col = next(c for c in cols if "settlement" in c)
        price_col = cols["price"]

        day = pd.to_datetime(data[date_col])
        hour_ending = (
            data[hour_col].astype(str).str.extract(r"(\d+)")[0].astype(int)
        )
        prices = pd.DataFrame(
            {
                "timestamp": day + pd.to_timedelta(hour_ending - 1, unit="h"),
                "point": data[point_col].astype(str).str.strip(),
                "price": pd.to_numeric(data[price_col], errors="coerce"),
            }
        )
        prices = prices[prices["point"].isin(HUBS)]
        wide = prices.pivot_table(
            index="timestamp", columns="point", values="price", aggfunc="mean"
        ).reset_index()
    else:  # layout B
        time_col = data.columns[0]
        wide = data.rename(columns={time_col: "timestamp"})
        wide["timestamp"] = pd.to_datetime(wide["timestamp"])
        keep = ["timestamp"] + [c for c in wide.columns if str(c).strip().upper() in HUBS]
        wide = wide[keep]

    rename = {hub: hub.lower() + "_dam_usd_mwh" for hub in HUBS if hub in wide.columns}
    wide = wide.rename(columns=rename).sort_values("timestamp").reset_index(drop=True)

    print("  data-quality checks (cleaned hub prices):")
    report_checks(wide)
    out_path = CLEAN_DIR / f"ercot_dam_hub_prices_{YEAR}_clean.csv"
    wide.to_csv(out_path, index=False)
    print(f"  wrote {out_path} ({len(wide)} rows)")

    # Merge with load on the timestamp (inner join = only hours in both).
    merged = load_df.merge(wide, on="timestamp", how="inner")
    merged_path = CLEAN_DIR / f"ercot_load_price_{YEAR}_clean.csv"
    merged.to_csv(merged_path, index=False)
    print(f"  wrote {merged_path} ({len(merged)} rows matched on timestamp)")
    return wide


# --------------------------------------------------------------------------
def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    load_df = clean_load()
    print()
    clean_prices(load_df)
    print("\nDone.")


if __name__ == "__main__":
    main()
