"""
boem_loader.py — helpers for loading BOEM lease-sale and spatial data.

Each lease-sale directory should contain the fixed-width ASCII files
from one BOEM sale ZIP.  Two naming conventions are supported:

  Old style : BID.DAT, PREBID.DAT, COMPANY2.DAT, MAPS.dat
  New style : <sale>.BID, <sale>.COM, <sale>.TRT, <sale>.HST, <sale>.RES

Usage
-----
    from boem_loader import (load_sale, load_blocks, load_lease_history,
        load_lease_owners, load_master_sales, load_boreholes)

    sale   = load_sale("data/lease-sales/sale_198")
    blocks = load_blocks("data/shapefiles/blocks.shp")
    leases = load_lease_history("data/lease-sales/cleaned_lease_history.csv")
    owners = load_lease_owners("data/lease-sales/lseowndelimit.txt")
    sales  = load_master_sales("data/lease-sales/master_lease_sales.csv")
    wells  = load_boreholes("data/wells/mv_boreholes_all.txt")
"""

import fnmatch
import os
import re

import geopandas as gpd
import pandas as pd

# ── Fixed-width column specs (0-indexed [start, stop)) from FORMATS2.doc ────

_TRACT_SPECS = [(0, 5), (6, 13), (15, 21), (24, 31), (32, 43), (52, 54), (63, 65)]
_TRACT_NAMES = [
    "Lease_Number",
    "Protraction_ID",
    "Block_Number",
    "Acreage_raw",
    "Royalty_Rate",
    "Lease_Term",
    "Num_Bids",
]

_BID_SPECS = [(0, 7), (8, 15), (16, 26), (27, 32), (35, 43)]
_BID_NAMES = [
    "Sale_Number",
    "Lease_Number",
    "Bid_Amount",
    "Company_Number",
    "Bid_Percentage",
]

_COMPANY_SPECS = [(0, 5), (6, 76)]
_COMPANY_NAMES = ["Company_Number", "Company_Name"]

_MAPS_SPECS = [(0, 3), (4, 54), (54, 61)]
_MAPS_NAMES = ["Map_Number", "Map_Name", "Protraction_ID"]

# ── File-matching patterns (case-insensitive) ───────────────────────────────
# Order matters: first match wins.

_BID_PATTERNS = ["BID.DAT", "BID.TXT", "*.BID"]
_TRACT_PATTERNS = ["PREBID.DAT", "PREBID.TXT", "TRT.DAT", "*.TRT"]
_COMPANY_PATTERNS = ["COMPANY*.DAT", "COMPANY*.TXT", "COM.DAT", "*.COM"]
_MAPS_PATTERNS = ["MAPS.DAT", "MAPS.TXT", "MAP.DAT"]
_RESULTS_PATTERNS = ["RES.DAT", "RES.TXT", "*.RES"]
_HISTORY_PATTERNS = ["HST.DAT", "HST.TXT", "*.HST"]

UTM15N = "EPSG:26915"


# ── Helpers ──────────────────────────────────────────────────────────────────


def _find(sale_dir: str, patterns: list[str]) -> str | None:
    """Return the first file in *sale_dir* matching any pattern (case-insensitive)."""
    files = sorted(os.listdir(sale_dir))
    for pat in patterns:
        for f in files:
            if fnmatch.fnmatch(f.upper(), pat.upper()):
                return os.path.join(sale_dir, f)
    return None


def _strip_col(df: pd.DataFrame, col: str) -> None:
    """In-place: cast *col* to stripped string."""
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip()


# ── Sale-file loaders ───────────────────────────────────────────────────────


def load_tracts(sale_dir: str) -> pd.DataFrame:
    """Load tract / pre-bid file (PREBID.DAT or *.TRT) → DataFrame."""
    path = _find(sale_dir, _TRACT_PATTERNS)
    if path is None:
        raise FileNotFoundError(f"No PREBID/TRT file found in {sale_dir}")
    df = pd.read_fwf(path, colspecs=_TRACT_SPECS, names=_TRACT_NAMES)
    _strip_col(df, "Lease_Number")
    _strip_col(df, "Protraction_ID")
    _strip_col(df, "Block_Number")
    df["Acreage"] = pd.to_numeric(df["Acreage_raw"], errors="coerce") / 1000
    df["Lease_Term"] = pd.to_numeric(df["Lease_Term"], errors="coerce")
    df["Num_Bids"] = pd.to_numeric(df["Num_Bids"], errors="coerce")
    return df


def load_bids(sale_dir: str) -> pd.DataFrame:
    """Load bid file (BID.DAT or *.BID) → DataFrame."""
    path = _find(sale_dir, _BID_PATTERNS)
    if path is None:
        raise FileNotFoundError(f"No BID file found in {sale_dir}")
    df = pd.read_fwf(path, colspecs=_BID_SPECS, names=_BID_NAMES)
    # Strip 'G' prefix from lease numbers
    df["Lease_Number"] = (
        df["Lease_Number"]
        .astype(str)
        .str.replace(r"\D", "", regex=True)
        .str.strip()
    )
    df["Company_Number"] = df["Company_Number"].astype(str).str.strip().str.zfill(5)
    df["Sale_Number"] = pd.to_numeric(df["Sale_Number"], errors="coerce")
    df["Bid_Amount"] = pd.to_numeric(df["Bid_Amount"], errors="coerce")
    df["Bid_Percentage"] = pd.to_numeric(df["Bid_Percentage"], errors="coerce")
    return df


def load_companies(sale_dir: str) -> pd.DataFrame:
    """Load company file (COMPANY*.DAT or *.COM) → DataFrame."""
    path = _find(sale_dir, _COMPANY_PATTERNS)
    if path is None:
        raise FileNotFoundError(f"No COMPANY/COM file found in {sale_dir}")
    df = pd.read_fwf(path, colspecs=_COMPANY_SPECS, names=_COMPANY_NAMES)
    df["Company_Number"] = df["Company_Number"].astype(str).str.strip().str.zfill(5)
    df["Company_Name"] = df["Company_Name"].astype(str).str.strip()
    return df


def load_maps(sale_dir: str) -> pd.DataFrame | None:
    """Load maps/protraction translation file → DataFrame.  None if absent."""
    path = _find(sale_dir, _MAPS_PATTERNS)
    if path is None:
        return None
    df = pd.read_fwf(path, colspecs=_MAPS_SPECS, names=_MAPS_NAMES)
    _strip_col(df, "Protraction_ID")
    df["Map_Name"] = df["Map_Name"].astype(str).str.strip()
    return df


def load_results(sale_dir: str) -> pd.DataFrame | None:
    """Load sale results file (*.RES) → DataFrame.  None if absent."""
    path = _find(sale_dir, _RESULTS_PATTERNS)
    if path is None:
        return None
    # RES column layout varies; fall back to auto-detect
    return pd.read_fwf(path)


def load_history(sale_dir: str) -> pd.DataFrame | None:
    """Load block bid-history file (*.HST) → DataFrame.  None if absent."""
    path = _find(sale_dir, _HISTORY_PATTERNS)
    if path is None:
        return None
    return pd.read_fwf(path)


def load_sale(sale_dir: str) -> dict[str, pd.DataFrame]:
    """Load all available files for one sale → dict of DataFrames.

    Keys: 'tracts', 'bids', 'companies', 'maps', 'results', 'history'.
    Missing files are omitted from the dict (no error).
    """
    sale_dir = os.path.expanduser(sale_dir)
    data: dict[str, pd.DataFrame | None] = {
        "tracts": load_tracts(sale_dir),
        "bids": load_bids(sale_dir),
        "companies": load_companies(sale_dir),
        "maps": load_maps(sale_dir),
        "results": load_results(sale_dir),
        "history": load_history(sale_dir),
    }
    return {k: v for k, v in data.items() if v is not None}


# ── Supplemental BOEM datasets ───────────────────────────────────────────────

# -- Lease history (cleaned CSV from BOEM Lease List) -------------------------

_STATUS_RE = re.compile(r"([A-Z]+)\s*(\d{2}/\d{2}/\d{4})?")


def load_lease_history(path: str) -> pd.DataFrame:
    """Load cleaned_lease_history.csv → DataFrame with parsed status + date.

    Columns returned
    ----------------
    Lease_Number   : str   — 7-digit padded lease number (no G prefix)
    Lease_Type     : str   — e.g. "O&G", "SLF"
    Area_Code      : str   — protraction abbreviation (GC, MC, WR …)
    Block_Number   : str   — block within the protraction area
    Lease_Status   : str   — RELINQ | EXPIR | TERMED | PRIMRY | PROD | …
    Status_Date    : datetime or NaT — date extracted from status field
    Col_1          : int   — kept as-is (meaning TBD)
    Col_6          : float — kept as-is (meaning TBD)
    """
    df = pd.read_csv(path, dtype=str)

    # Rename known columns
    df = df.rename(columns={
        "Col_2": "Lease_Type",
        "Col_3": "Area_Code",
        "Col_4": "Block_Number",
    })

    # Parse Col_5 → Lease_Status + Status_Date
    parsed = df["Col_5"].apply(_parse_status)
    df["Lease_Status"] = parsed.str[0]
    df["Status_Date"] = pd.to_datetime(parsed.str[1], format="%m/%d/%Y", errors="coerce")
    df = df.drop(columns=["Col_5"])

    # Clean up types
    df["Lease_Number"] = df["Lease_Number"].str.strip().str.zfill(7)
    df["Area_Code"] = df["Area_Code"].str.strip()
    df["Block_Number"] = df["Block_Number"].str.strip()
    df["Col_1"] = pd.to_numeric(df["Col_1"], errors="coerce")
    df["Col_6"] = pd.to_numeric(df["Col_6"], errors="coerce")

    return df


def _parse_status(raw: str) -> tuple[str, str]:
    """Extract (status_code, date_string|'') from e.g. 'RELINQ09/09/2014'."""
    m = _STATUS_RE.match(str(raw).strip())
    if m:
        return m.group(1), m.group(2) or ""
    return str(raw).strip(), ""


# -- Lease owner (delimited raw download from BOEM) ---------------------------

_LSEOWN_NAMES = [
    "Owner_Aliquot",   # 1 = full lease, A-Z = partial aliquot
    "SN_Lse_Owner",    # unique record ID per ownership instance
    "Asgn_Aprv_Date",  # assignment approval date
    "Asgn_Eff_Date",   # assignment effective date
    "Company_Number",  # MMS company number
    "Lease_Number",    # lease ID (G-prefix for newer leases)
    "Asgn_Status",     # T = terminated/inactive, C = current
    "_unused",
    "Aliquot_Echo",    # mirrors Owner_Aliquot (blank when '1')
    "Pct_Own",         # ownership percentage
    "Eff_Date",        # effective/recording date
]


def load_lease_owners(path: str) -> pd.DataFrame:
    """Load lseowndelimit.txt (BOEM lease-owner history) → DataFrame.

    Key columns
    -----------
    Lease_Number     : str      — with G-prefix preserved
    Company_Number   : str      — 5-digit zero-padded
    Asgn_Status      : str      — 'C' (current) or 'T' (terminated)
    Pct_Own          : float    — ownership percentage
    Asgn_Aprv_Date   : datetime — assignment approval date
    Asgn_Eff_Date    : datetime — assignment effective date
    Owner_Aliquot    : str      — '1' = full, 'A'-'Z' = partial
    """
    df = pd.read_csv(
        path,
        header=None,
        names=_LSEOWN_NAMES,
        dtype=str,
        skipinitialspace=True,
    )

    # Clean join keys
    df["Lease_Number"] = df["Lease_Number"].str.strip()
    df["Company_Number"] = df["Company_Number"].str.strip().str.zfill(5)
    df["Owner_Aliquot"] = df["Owner_Aliquot"].str.strip()
    df["Asgn_Status"] = df["Asgn_Status"].str.strip()

    # Parse dates
    for col in ["Asgn_Aprv_Date", "Asgn_Eff_Date", "Eff_Date"]:
        df[col] = pd.to_datetime(df[col].str.strip(), format="%Y%m%d", errors="coerce")

    # Numeric
    df["Pct_Own"] = pd.to_numeric(df["Pct_Own"], errors="coerce")

    # Drop empty/redundant columns
    df = df.drop(columns=["_unused", "Aliquot_Echo"])

    return df


# -- Master lease sales (pre-merged bid+tract CSV) ----------------------------


def load_master_sales(path: str, sale_number: int | None = None) -> pd.DataFrame:
    """Load master_lease_sales.csv → DataFrame.

    Columns: Sale_Number, Lease_Number, Bid_Amount, Company_Number,
             Protraction_ID, Block_Number, Acreage, Source_Sale.
    If *sale_number* is given, filter to that sale only.
    """
    df = pd.read_csv(path, dtype=str)
    df.columns = df.columns.str.strip()
    df["Sale_Number"] = pd.to_numeric(df["Sale_Number"], errors="coerce").astype("Int64")
    df["Bid_Amount"] = pd.to_numeric(df["Bid_Amount"], errors="coerce")
    df["Acreage"] = pd.to_numeric(df["Acreage"], errors="coerce")
    _strip_col(df, "Lease_Number")
    _strip_col(df, "Company_Number")
    _strip_col(df, "Protraction_ID")
    _strip_col(df, "Block_Number")
    if sale_number is not None:
        df = df[df["Sale_Number"] == sale_number].copy()
    return df


# -- Boreholes (BOEM well data) -----------------------------------------------

from shapely.geometry import Point  # noqa: E402


def load_boreholes(
    path: str,
    region: str = "G",
    to_utm: bool = True,
) -> gpd.GeoDataFrame:
    """Load mv_boreholes_all.txt → GeoDataFrame with point geometries.

    Parameters
    ----------
    path   : path to the BOEM borehole CSV/TXT download
    region : filter to this REGION_CODE ('G' = GOM).  None to keep all.
    to_utm : reproject to UTM 15N (EPSG:26915) for distance calculations

    Key columns
    -----------
    Spud_Date        : datetime — well spud date
    Area_Code        : str     — 2-letter protraction abbreviation
    Block_Number     : str     — block within protraction area
    Water_Depth      : float   — in feet
    Well_Type        : str     — D=Development, E=Exploration
    Borehole_Status  : str     — PA, ST, COM, TA, CNL …
    Company_Name     : str     — operator name
    geometry         : Point   — surface location (UTM or lon/lat)
    """
    df = pd.read_csv(path, dtype=str)
    df.columns = df.columns.str.strip()

    if region is not None:
        df = df[df["REGION_CODE"].str.strip() == region].copy()

    # Parse key columns
    df["Spud_Date"] = pd.to_datetime(df["WELL_SPUD_DATE"], format="mixed", errors="coerce")
    df["Water_Depth"] = pd.to_numeric(df["WATER_DEPTH"], errors="coerce")
    df["Area_Code"] = df["BOTM_AREA_CODE"].str.strip()
    df["Block_Number"] = df["BOTM_BLOCK_NUMBER"].str.strip()
    df["Well_Type"] = df["WELL_TYPE_CODE"].str.strip()
    df["Borehole_Status"] = df["BOREHOLE_STAT_CD"].str.strip()
    df["Company_Name"] = df["COMPANY_NAME"].str.strip()

    # Build point geometry from surface lat/lon
    lat = pd.to_numeric(df["SURF_LATITUDE"], errors="coerce")
    lon = pd.to_numeric(df["SURF_LONGITUDE"], errors="coerce")
    geometry = gpd.points_from_xy(lon, lat, crs="EPSG:4326")

    # Keep useful columns only
    keep = [
        "API_WELL_NUMBER", "WELL_NAME", "Spud_Date", "Area_Code",
        "Block_Number", "Water_Depth", "Well_Type", "Borehole_Status",
        "Company_Name", "SURF_LATITUDE", "SURF_LONGITUDE",
    ]
    gdf = gpd.GeoDataFrame(df[keep].copy(), geometry=geometry)

    if to_utm:
        gdf = gdf.to_crs(UTM15N)

    return gdf


# ── Spatial ──────────────────────────────────────────────────────────────────


def load_blocks(shp_path: str, to_utm: bool = True) -> gpd.GeoDataFrame:
    """Load OCS block shapefile → GeoDataFrame.

    Standardizes column names (Protraction_ID, Block_Number, Planning_Area).
    If *to_utm* is True (default), reprojects to UTM Zone 15N (EPSG:26915).
    """
    gdf = gpd.read_file(shp_path)

    rename = {
        "PROT_NUMBE": "Protraction_ID",
        "BLOCK_NUMB": "Block_Number",
        "MMS_PLAN_A": "Planning_Area",
        "AC_LAB": "Area_Block_Label",
    }
    gdf = gdf.rename(columns={k: v for k, v in rename.items() if k in gdf.columns})

    _strip_col(gdf, "Protraction_ID")
    _strip_col(gdf, "Block_Number")

    if to_utm:
        gdf = gdf.to_crs(UTM15N)

    return gdf
