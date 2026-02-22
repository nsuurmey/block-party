"""
boem_loader.py — helpers for loading BOEM lease-sale and spatial data.

Each lease-sale directory should contain the fixed-width ASCII files
from one BOEM sale ZIP.  Two naming conventions are supported:

  Old style : BID.DAT, PREBID.DAT, COMPANY2.DAT, MAPS.dat
  New style : <sale>.BID, <sale>.COM, <sale>.TRT, <sale>.HST, <sale>.RES

Usage
-----
    from boem_loader import load_sale, load_blocks

    sale = load_sale("data/lease-sales/sale_198")
    blocks = load_blocks("data/shapefiles/blocks.shp")
"""

import fnmatch
import os

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


# ── Supplemental BOEM datasets (CSV / delimited) ────────────────────────────


def load_leases(path: str) -> pd.DataFrame:
    """Load a BOEM active-lease CSV export → DataFrame."""
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    return df


def load_wells(path: str) -> pd.DataFrame:
    """Load a BOEM well/borehole CSV export → DataFrame."""
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    return df


def load_relinquishments(path: str) -> pd.DataFrame:
    """Load a BOEM relinquishment/expiration CSV export → DataFrame."""
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    return df


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
