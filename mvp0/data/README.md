# MVP 0 Data Download Instructions

All data is freely available from [data.boem.gov](https://data.boem.gov). No accounts, licenses, or vendors required.

## Required Downloads

### 1. Bid Files (3 ZIPs)

Go to **data.boem.gov → Main → Leasing** and download the bid ZIP archive for each sale:

| Sale | File to download | Place in |
|------|-----------------|----------|
| Sale 257 (Aug 2023) | Sale 257 bid data ZIP | `mvp0/data/sale_257/` |
| Sale 261 (Mar 2024) | Sale 261 bid data ZIP | `mvp0/data/sale_261/` |
| Dec 2025 OBBBA Sale 1 | Dec 2025 bid data ZIP | `mvp0/data/sale_dec2025/` |

Each ZIP contains five fixed-width ASCII files:

- `*.BID` — All bids (company code, block ID, bid amount, joint bid indicator)
- `*.COM` — Company lookup (company code → company name)
- `*.TRT` — Tract info (block ID, area, water depth, acreage)
- `*.RES` — Results (high bids, accepted/rejected)
- `*.HST` — Block bid history summary

**Important:** These are fixed-width format files, not CSV. Use `pd.read_fwf()` — see `utils/process-lease-sale-BOEM-downloads.py` for column specs.

### 2. Lease Status Data

Go to **data.boem.gov → Main → Leasing** and query/download:

| Dataset | Place in |
|---------|----------|
| All active GOM leases (CSV or fixed-width) | `mvp0/data/leases/` |
| Lease owner/operator history | `mvp0/data/leases/` |

You need: lease number, block ID (protraction + block number), operator/company, lease effective date, lease expiration date, lease status.

### 3. Relinquishment / Expiration Data

From the same BOEM Leasing page, download expired/relinquished lease records:

| Dataset | Place in |
|---------|----------|
| Relinquished/expired leases (all GOM) | `mvp0/data/relinquishments/` |

You need: lease number, block ID, relinquishment/expiration date, former operator.

### 4. Well Borehole Data

Go to **data.boem.gov → Main → Well** and query/download:

| Dataset | Place in |
|---------|----------|
| GOM well borehole data (post-2010) | `mvp0/data/wells/` |

You need: API number or well ID, spud date, block location (protraction + block number) or lat/lon, well type, TVD.

### 5. OCS Block Shapefile

Go to **data.boem.gov → Main → Mapping** and download:

| Dataset | Place in |
|---------|----------|
| Gulf of Mexico Region — Blocks shapefile | `mvp0/data/shapefiles/` |

**Note:** A copy already exists in `data/shapefiles/` at the repo root. You can symlink or copy it:

```bash
cp -r ../../data/shapefiles/* mvp0/data/shapefiles/
```

## Directory Structure After Downloads

```
mvp0/data/
├── README.md              ← this file
├── sale_257/              ← Sale 257 bid files (unzipped)
│   ├── *.BID
│   ├── *.COM
│   ├── *.TRT
│   ├── *.RES
│   └── *.HST
├── sale_261/              ← Sale 261 bid files (unzipped)
│   └── (same five files)
├── sale_dec2025/          ← Dec 2025 OBBBA bid files (unzipped)
│   └── (same five files)
├── leases/                ← Active lease data, operator history
├── relinquishments/       ← Expired/relinquished lease records
├── wells/                 ← Well borehole data (post-2010)
└── shapefiles/            ← OCS block shapefile (GOM)
    ├── blocks.shp
    ├── blocks.shx
    ├── blocks.dbf
    ├── blocks.prj
    └── (other shapefile components)
```

## Coordinate Reference System

The OCS block shapefile ships in BOEM's protraction diagram CRS. **Reproject to EPSG:26915 (UTM Zone 15N)** before computing any distances:

```python
gdf = gdf.to_crs(epsg=26915)
```
