# MVP 0 Study Plan — BOEM Signal Validation

**Duration:** 2–3 weeks
**Tooling:** Jupyter, Python, pandas, GeoPandas, matplotlib/folium
**Training sales:** 257 (Aug 2023), 261 (Mar 2024)
**Validation sale:** December 2025 OBBBA Sale 1

---

## 1. Work Plan (Week-by-Week)

### Week 1 — Data Acquisition and Spatial Foundation

- [ ] Download all required BOEM files (see Section 2 below).
- [ ] Parse fixed-width bid files for Sales 257, 261, and Dec 2025 using the existing `utils/process-lease-sale-BOEM-downloads.py` helper. Validate row counts against BOEM published summaries.
- [ ] Load OCS block shapefile using `utils/process-lease-sale-BOEM-block-shapefiles.py`. Reproject to **EPSG:26915** (UTM 15N). Confirm join keys (`Protraction_ID` + `Block_Number`) align between tabular and spatial data.
- [ ] Parse COMPANY2.DAT lookup tables for all three sales. Build a unified `company_code → company_name` mapping. (No entity resolution — use names as-is.)
- [ ] Download and parse lease status data (active leases, expiration dates, operators). Confirm you can identify which company holds which block at any given date.
- [ ] Download and parse relinquishment/expiration records. Extract relinquishment date and former operator for each lease.
- [ ] Download and parse well borehole data. Extract spud date, lat/lon (or block location), well type.
- [ ] Produce a "sanity check" base map: the full GOM block grid with Dec 2025 bid blocks highlighted. If this looks wrong, stop and fix data alignment before moving on.

### Week 2 — Run the Four Investigations (Q1–Q4)

- [ ] **Q1 — Adjacency Signal:** Build queen-contiguity adjacency matrix from shapefile. For each Dec 2025 available block, flag whether each active company holds an adjacent lease. Compute `bid_rate_adjacent` vs. `bid_rate_non_adjacent`, lift, and chi-square p-value. Generate choropleth and 2×2 contingency table.
- [ ] **Q2 — Relinquishment Signal:** Identify blocks relinquished within 36 months of Dec 2025 bid deadline. Flag available blocks with adjacent relinquishments. Compute bid rates stratified by `relinquishment_adjacent` and water-depth bucket (shelf / deepwater / ultra-deep). Compute decay curve (0–12 mo vs. 13–36 mo).
- [ ] **Q3 — Well Activity Radius:** Compute well counts within 10 km and 25 km of each available block centroid, for 6-month and 18-month lookback windows (four combos). Bin blocks by well count (0 / 1 / 2+). Compute bid rates per bin and test monotonic gradient. Identify strongest radius/window combination.
- [ ] **Q4 — Archetype Stability:** Compute per-company features from Sale 257 only (`bid_frequency`, `win_rate`, `avg_bid_premium`, `water_depth_preference_mean`). Run K-means (k=3). Repeat with Sale 261. Compute archetype agreement rate after resolving label permutation (Hungarian algorithm). Investigate switchers.

### Week 3 — Validation, Map, and Findings Document

- [ ] Cross-check Q1–Q3 predictions against Dec 2025 actual outcomes. All features must be built from Sales 257/261 data only — Dec 2025 is held-out.
- [ ] For Q4, check whether Sale 257/261 archetypes predict Dec 2025 bidding behavior directionally.
- [ ] Produce the **static signal map** (PNG, ≥ 2400 px wide): GOM block grid + Dec 2025 actual bids (colored by company) + adjacency heatmap + relinquishment cold zones + recent well activity markers.
- [ ] Write the **findings document** (3–5 pages): data quality observations, one paragraph per Q with key statistic + go/no-go call, overall build recommendation (proceed / proceed with modifications / pause and reframe).
- [ ] Final notebook cleanup: ensure each notebook runs top-to-bottom on raw BOEM files, add markdown annotations, confirm `requirements.txt` is accurate.

---

## 2. Minimum Data to Download

All data is free from [data.boem.gov](https://data.boem.gov).

### Bid Files (one ZIP per sale)

| File | Source | What you get |
|------|--------|-------------|
| Sale 257 bid ZIP | `data.boem.gov/Main/Leasing.aspx` → Sale 257 | `*.BID`, `*.COM`, `*.HST`, `*.RES`, `*.TRT` — bids, companies, results, tract info |
| Sale 261 bid ZIP | Same page → Sale 261 | Same five files |
| Dec 2025 OBBBA Sale 1 bid ZIP | Same page → most recent sale | Same five files |

From each ZIP you need at minimum:
- `*.BID` — all bids (company code, block ID, bid amount)
- `*.COM` — company code → name lookup
- `*.TRT` — tract/block info (water depth, acreage, protraction area)
- `*.RES` — high bids and accepted/rejected status

### Lease Status Data

| File | Source | Purpose |
|------|--------|---------|
| Active lease file (all GOM) | `data.boem.gov/Main/Leasing.aspx` → Lease query | Identifies which company holds which block at each sale date. Needed for Q1 adjacency and Q2 relinquishment. |
| Lease owner/operator history | Same source | Company-to-block assignment over time |

### Relinquishment / Expiration Data

| File | Source | Purpose |
|------|--------|---------|
| Relinquished/expired leases | Included in BOEM lease reports (`data.boem.gov/Main/Leasing.aspx`) | Lease end date, block ID, former operator. Needed for Q2. |

### Well Borehole Data

| File | Source | Purpose |
|------|--------|---------|
| Well data (GOM, post-2010) | `data.boem.gov/Main/Well.aspx` → Borehole query | Spud date, block location (or lat/lon), well type. Needed for Q3 radius analysis. |

### Spatial Data

| File | Source | Purpose |
|------|--------|---------|
| GOM OCS Protraction Block shapefile | `data.boem.gov/Main/mapping.aspx` → "Gulf of Mexico Region — Blocks" | Block polygon geometries. The spatial backbone for all four notebooks. Already in `data/shapefiles/`. |

### Summary: 7 downloads minimum

1. Sale 257 bid ZIP
2. Sale 261 bid ZIP
3. Dec 2025 OBBBA Sale 1 bid ZIP
4. Active lease file (all GOM, CSV or fixed-width)
5. Relinquished/expired lease file
6. Well borehole data (GOM, post-2010)
7. OCS block shapefile *(already in repo at `data/shapefiles/`)*

---

## 3. Notebook Descriptions (Q1–Q4)

### Notebook 1: `01_adjacency_signal.ipynb` — Does adjacency predict bidding?

- **Inputs:** Dec 2025 bid file, active lease file (as of Dec 2025 bid deadline), OCS block shapefile.
- **Step 1:** Load shapefile, reproject to EPSG:26915, build queen-contiguity adjacency matrix (shared full edge, not diagonal) using `libpysal.weights.Queen` or a manual approach on the GeoDataFrame.
- **Step 2:** For each available block in Dec 2025, determine which companies hold active leases on adjacent blocks. Produce a binary matrix: `(company, block) → has_adjacent_lease`.
- **Step 3:** Join against actual Dec 2025 bids. Compute:
  - `bid_rate_adjacent` = bids placed where company had adjacent lease / total such opportunities
  - `bid_rate_non_adjacent` = bids placed where company had no adjacent lease / total such opportunities
  - `lift` = `bid_rate_adjacent / bid_rate_non_adjacent`
- **Step 4:** Run chi-square test on the 2×2 contingency table. Report lift, p-value, and sample sizes.
- **Step 5:** Produce a choropleth: blocks colored by "number of companies with adjacent position," with actual Dec 2025 bids overlaid as colored dots.
- **Go/no-go:** Lift ≥ 3× and p < 0.05 → strong signal. Lift 1.5–3× → moderate. Lift < 1.5× or p > 0.05 → weak.

### Notebook 2: `02_relinquishment_signal.ipynb` — Do relinquishments reduce nearby bidding?

- **Inputs:** Dec 2025 bid file, relinquishment/expiration records (36 months prior to Dec 2025), OCS block shapefile, tract file (for water depth).
- **Step 1:** Load relinquishment records. Filter to leases relinquished within 36 months before the Dec 2025 bid submission deadline. Map each to its block via Protraction_ID + Block_Number.
- **Step 2:** For each available block in Dec 2025, flag `relinquishment_adjacent = 1` if any edge-adjacent block was relinquished in the window.
- **Step 3:** Assign water-depth buckets using TRT file or shapefile attributes: shelf (< 200 m), deepwater (200–1500 m), ultra-deepwater (> 1500 m).
- **Step 4:** Compute bid rates for `relinquishment_adjacent = 1` vs. `= 0`, stratified by water-depth bucket. This controls for the confound that relinquishments cluster geographically.
- **Step 5:** Compute temporal decay: split relinquishments into 0–12 months vs. 13–36 months. Plot bid-rate suppression as a function of time-since-relinquishment.
- **Outputs:** Bar charts (bid rate by relinquishment adjacency × water depth), decay curve.
- **Go/no-go:** Adjacent-relinquishment blocks bid at ≤ 50% the rate → strong. 50–80% → marginal. No difference → signal absent.

### Notebook 3: `03_well_activity_signal.ipynb` — Does recent well activity increase nearby bidding?

- **Inputs:** Dec 2025 bid file, well borehole data (spud dates, locations), OCS block shapefile.
- **Step 1:** Load well data. Filter to wells spudded before the Dec 2025 bid deadline. Geocode wells to block centroids (or use lat/lon directly). Reproject to EPSG:26915 for distance calculations.
- **Step 2:** For each available block in Dec 2025, compute its centroid. Count wells within 10 km and 25 km, for lookback windows of 6 months and 18 months (four combinations).
- **Step 3:** Bin blocks: `0 wells`, `1 well`, `2+ wells` for each radius/window combo.
- **Step 4:** Compute bid rates per bin. Test whether the gradient is monotonic and statistically significant (chi-square or Cochran-Armitage trend test).
- **Step 5 — Lag analysis:** Compare predictive power of wells spudded 0–6 months before the sale vs. 7–18 months before. Does the signal improve with a delay?
- **Step 6:** Identify the strongest radius/window combination — this becomes the canonical `active_finds` feature for MVP 1.
- **Outputs:** Heatmap of bid rates by (radius, lookback window), lag curve, one "Treasure Toggle preview" map: pick a real historical well, show surrounding blocks that received bids, check if the model would have predicted them.
- **Go/no-go:** Clear monotonic gradient with p < 0.05 → strong. Gradient exists but weak → moderate. No gradient → signal absent.

### Notebook 4: `04_archetype_stability.ipynb` — Are company archetypes stable across sales?

- **Inputs:** Sale 257 bid file, Sale 261 bid file, company lookup tables, tract files (for water depth).
- **Step 1:** Compute per-company behavioral features from Sale 257 only:
  - `bid_frequency` — number of blocks bid on
  - `win_rate` — fraction of bids that were high bid and accepted
  - `avg_bid_premium` — mean (bid amount / minimum bid) or mean bid per acre
  - `water_depth_preference_mean` — mean water depth of blocks bid on
- **Step 2:** Filter to companies that bid in both Sales 257 and 261 (need overlap for comparison). Run K-means (k=3) on Sale 257 features (standardized). Label clusters descriptively (Aggressive Explorer, Selective Infiller, Dormant).
- **Step 3:** Repeat Step 1–2 for Sale 261 features independently.
- **Step 4:** Resolve label permutation using the Hungarian algorithm (minimize mismatches). Compute **archetype agreement rate** = % of companies assigned the same cluster across both sales.
- **Step 5:** Investigate switchers: which companies changed archetype, and is there a plausible explanation (M&A, commodity price shift, strategic pivot)?
- **Step 6 — Geographic signature:** For each archetype, plot the geographic distribution of bids. Do Aggressive Explorers cluster in specific water depths or planning areas? Do Selective Infillers target adjacency opportunities?
- **Outputs:** Scatter plots (bid frequency vs. win rate, colored by archetype), agreement rate table, labeled map of Dec 2025 bids colored by company archetype.
- **Go/no-go:** ≥ 80% agreement → stable, use as predictive feature. 60–80% → descriptive only. < 60% → unstable, drop clustering.

---

## 4. Final Outputs (Three Deliverables)

### Deliverable 1: Four Investigation Notebooks

```
mvp0/
├── notebooks/
│   ├── 01_adjacency_signal.ipynb
│   ├── 02_relinquishment_signal.ipynb
│   ├── 03_well_activity_signal.ipynb
│   └── 04_archetype_stability.ipynb
```

Each notebook is self-contained: runs top-to-bottom on raw BOEM files, includes markdown annotations explaining each step and what the result means for the build decision. No external dependencies beyond `requirements.txt`.

### Deliverable 2: Static Signal Map

A single PNG image (≥ 2400 px wide), saved to `mvp0/outputs/signal_map_dec2025.png`.

**Layers:**
1. GOM OCS block grid (base layer, light gray edges)
2. Actual December 2025 bids (colored dots/fills by company)
3. Adjacency-based "predicted high-interest zones" (warm-color heatmap)
4. Relinquishment cold zones (distinct cool color, e.g., blue hatching)
5. Recent well activity in the prior 18 months (point symbols)

**Label:** *"What block-party would have shown you before the December 2025 sale."*

Generated in Notebook 01 (or a dedicated cell at the end of the Q1 notebook, since it composites information from all four investigations).

### Deliverable 3: Findings Document

A 3–5 page markdown file at `mvp0/outputs/findings.md`, covering:

1. **Data quality observations** — what was messier than expected, what was cleaner, gaps or surprises in BOEM source files.
2. **Q1–Q4 results** — one paragraph each with the key statistic and the per-question go/no-go recommendation.
3. **Build recommendation** — one of:
   - *Proceed as planned:* MVP 1 PRD is validated.
   - *Proceed with modifications:* List specific changes needed before starting MVP 1.
   - *Pause and reframe:* Core assumptions not validated. Recommend a different direction.
4. **Map feedback summary** — if the static map was shown to any target users, include verbatim reactions.

---

## 5. Sequencing Summary

```
Week 1:  Data download → Parse & validate → Spatial join sanity check
Week 2:  Q1 notebook → Q2 notebook → Q3 notebook → Q4 notebook
Week 3:  Cross-validation against Dec 2025 → Static map → Findings doc → Cleanup
```

**Critical path:** The shapefile join (Protraction_ID + Block_Number alignment between tabular and spatial data) is the single riskiest step. If the keys don't align cleanly, everything downstream breaks. Do this first and verify it visually before moving on.
