# MVP 0 Data — Download Instructions

All data is freely available from BOEM. No licenses, no API keys, no scraping required.

## Directory Layout

After downloading, your `mvp0/data/` directory should look like:

```
data/
├── README.md              ← this file
├── sale_257/              ← Sale 257 (August 2023)
│   ├── *.BID
│   ├── *.COM
│   ├── *.HST
│   ├── *.RES
│   └── *.TRT
├── sale_261/              ← Sale 261 (March 2024)
│   ├── *.BID
│   ├── *.COM
│   ├── *.HST
│   ├── *.RES
│   └── *.TRT
├── sale_obbba_dec2025/    ← OBBBA Sale 1 (December 2025) — HELD-OUT VALIDATION
│   ├── *.BID
│   ├── *.COM
│   ├── *.HST
│   ├── *.RES
│   └── *.TRT
├── leases/
│   └── active_leases.csv
├── relinquishments/
│   └── relinquished_leases.csv
└── wells/
    └── boreholes.csv
```

## 1. Lease Sale Files (BID, COM, HST, RES, TRT)

**Source:** https://data.boem.gov/Main/Leasing.aspx

Navigate to "Sale/Bid Data" and download the ZIP archive for each sale:

| Sale | Number | Date | ZIP Filename (typical) |
|------|--------|------|----------------------|
| Sale 257 | 257 | August 2023 | `257.zip` or similar |
| Sale 261 | 261 | March 2024 | `261.zip` or similar |
| OBBBA Sale 1 | TBD | December 2025 | Check BOEM for the latest OBBBA sale listing |

**Steps:**
1. Download each ZIP file
2. Extract contents into the corresponding `sale_XXX/` directory
3. Each ZIP should contain 5 fixed-width ASCII files: `*.BID`, `*.COM`, `*.HST`, `*.RES`, `*.TRT`
4. A format document (e.g., `FORMATS2.doc`) may also be included — keep it for reference

**Format notes:**
- These are fixed-width files, NOT CSV. Use `pd.read_fwf()` with explicit `colspecs`.
- Lease numbers in BID files may have a "G" prefix that must be stripped for joins.
- See `utils/process-lease-sale-BOEM-downloads.py` for a working parser.

## 2. Active Lease Table

**Source:** https://data.boem.gov/Main/Leasing.aspx

Navigate to the lease query interface and download a table of all active GOM leases. You need:
- Lease number
- Operator / company code
- Block (protraction diagram + block number)
- Lease effective date and expiration date
- Lease status (Active, Expired, Relinquished, etc.)

**Storage:** `data/leases/active_leases.csv`

**Alternative:** If BOEM provides a bulk download, use that. The key requirement is a table that tells you which company held which block as of each sale's bid deadline.

## 3. Relinquishment Data

**Source:** https://data.boem.gov/Main/Leasing.aspx (filter by lease status)

Download leases with status = "Relinquished" or "Expired" for the GOM region. You need:
- Lease number
- Block (protraction + block number)
- Relinquishment / expiration date
- Former operator

**Storage:** `data/relinquishments/relinquished_leases.csv`

**Note:** If a single downloadable table isn't available, you can derive relinquishment records from the full lease table by filtering on status and effective/expiration dates.

**Lookback window:** We need relinquishments going back 36 months from each sale's bid deadline:
- For Dec 2025 sale: relinquishments from Dec 2022 – Dec 2025
- For Sale 261 (Mar 2024): relinquishments from Mar 2021 – Mar 2024
- For Sale 257 (Aug 2023): relinquishments from Aug 2020 – Aug 2023

## 4. Well Borehole Data

**Source:** https://data.boem.gov/Main/Well.aspx

Download well data for the GOM. You need:
- Well API number
- Surface latitude and longitude
- Spud date
- Well type (exploration, development, etc.)
- Block location (protraction + block number)
- Total vertical depth (TVD)

**Storage:** `data/wells/boreholes.csv`

**Lookback window:** We need wells spudded within 18 months of each sale's bid deadline:
- For Dec 2025 sale: wells spudded Jun 2024 – Dec 2025
- For Sale 261 (Mar 2024): wells spudded Sep 2022 – Mar 2024
- For Sale 257 (Aug 2023): wells spudded Feb 2022 – Aug 2023

To be safe, download all wells with spud dates from 2020-01-01 onward.

## 5. OCS Block Shapefile

**Already in repo:** `../../data/shapefiles/blocks.shp`

No additional download needed. This shapefile contains GOM OCS block boundaries with columns:
- `PROT_NUMBE` — Protraction diagram number (join key)
- `BLOCK_NUMB` — Block number within protraction (join key)
- `AREA_CODE` — Named area abbreviation (e.g., MC, GC, WR, KC)
- `MMS_PLAN_A` — Planning area (WGM, CGM, EGM)

**Projection:** NAD 1927 Geographic (EPSG:4267). Reproject to UTM Zone 15N (EPSG:26915) for all distance calculations.

## Important Notes

- **Do NOT use December 2025 sale data for feature engineering.** It is the held-out validation set.
- All files should be kept as downloaded — do not modify raw data files. Create processed versions in the notebooks.
- The `data/` directory is .gitignored to avoid committing large files to the repo.
