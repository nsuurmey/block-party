# MVP 0: Signal Validation Study — Workplan

**Version:** 1.0 | **Date:** February 2026 | **Executor:** Single senior IC (data scientist)

---

## 1. Scope and Risks

### Goal of MVP 0 (restated)

- **Test four load-bearing assumptions** (adjacency, relinquishment, well activity, company archetypes) that underpin the entire block-party product before committing any engineering resources.
- **Produce an evidence-based go/no-go recommendation** for MVP 1 using only notebooks, flat files, and public BOEM data — no infrastructure, no pipelines, no deployment.
- **Validate against a held-out sale** (December 2025 OBBBA Sale 1) to confirm signals generalize across regulatory regimes.

### In Scope

| Item | Detail |
|------|--------|
| Four investigation notebooks | Q1 adjacency, Q2 relinquishment, Q3 well activity, Q4 archetype stability |
| Three sales | Sale 257 (Aug 2023), Sale 261 (Mar 2024), OBBBA Sale 1 (Dec 2025) |
| BOEM flat files | BID, COM, HST, RES, TRT per sale; lease data; well borehole data; relinquishment data; OCS block shapefile |
| Tooling | Jupyter, pandas, GeoPandas, matplotlib, folium, scipy, scikit-learn (K-means only) |
| Deliverables | 4 notebooks, 1 static map (PNG), 1 findings document |
| Statistical methods | Descriptive statistics, lift ratios, chi-square tests, monotonic gradient tests, K-means clustering, agreement rates |

### Out of Scope

| Item | Why |
|------|-----|
| Data pipelines, ETL, dbt | MVP 0 is notebooks only |
| PostGIS or any database | Flat files + GeoPandas only |
| Web app, FastAPI, UI | No deployment of any kind |
| Model training / hyperparameter tuning | Descriptive and lift analysis only |
| Company entity resolution | Use BOEM company names as-is |
| Data beyond the four BOEM sources | No third-party data |
| Production-quality code | Scripts are disposable investigation artifacts |

### Key Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| BOEM file format inconsistencies across sales | Medium | Day 1: download all three sales and verify schemas match before any analysis |
| December 2025 sale data not yet published or format differs (OBBBA vs legacy) | Medium | Check BOEM site immediately; if unavailable, use Sale 259 as validation and note limitation |
| Adjacency computation is slow on full block grid (~65K blocks) | Low | Pre-filter to blocks within planning areas that had any bids in the three target sales |
| Relinquishment data is not in a clean, downloadable table | Medium | Day 1: locate the exact BOEM source; if it requires scraping, timebox to 2 hours then fall back to lease-status delta method |
| Well borehole data lacks precise lat/lon for spatial radius queries | Low | BOEM well data includes surface lat/lon; verify field exists in download |
| Validation leakage — accidentally using Dec 2025 data to build features | High (if careless) | Strict code discipline: features built ONLY from Sales 257/261 data; Dec 2025 used ONLY in final evaluation cells clearly marked with `## VALIDATION — HELD-OUT` headers |

---

## 2. Hypotheses, Metrics, and Decision Rules (Q1–Q4)

### Q1: Adjacency Signal

| Element | Detail |
|---------|--------|
| **Hypothesis** | Companies holding an active lease on a block adjacent (queen contiguity, shared full edge) to an available block bid on that block at a meaningfully higher rate than companies without adjacency. |
| **Metric** | `lift = bid_rate_adjacent / bid_rate_non_adjacent` where `bid_rate = bids_placed / opportunities` |
| **Statistical test** | Chi-square test on 2x2 contingency table (adjacent vs. not x bid vs. no-bid); target p < 0.05 |
| **Decision rule** | Lift >= 3x, p < 0.05 → proceed as planned. Lift 1.5–3x → proceed but reweight. Lift < 1.5x or p > 0.05 → do NOT proceed with block-level prediction; test planning-area aggregation as fallback. |

### Q2: Relinquishment Signal

| Element | Detail |
|---------|--------|
| **Hypothesis** | Blocks adjacent to recently relinquished leases (within 36 months) receive bids at a lower rate than similar blocks with no adjacent relinquishments. Relinquishment is a visible negative geological signal. |
| **Metric** | `suppression_ratio = bid_rate_relinquishment_adjacent / bid_rate_no_relinquishment`, stratified by water depth bucket (shelf < 200m, deepwater 200–1500m, ultra-deepwater > 1500m) |
| **Statistical test** | Chi-square within each depth stratum; also test decay: 0–12 months vs. 13–36 months since relinquishment |
| **Decision rule** | Suppression ratio <= 0.50 → include as MVP 1 cold-zone feature. Ratio 0.50–0.80 → include but deprioritize in UI. Ratio > 0.80 → remove from MVP 1 entirely. |

### Q3: Well Activity Radius

| Element | Detail |
|---------|--------|
| **Hypothesis** | Available blocks within 10–25 km of a recently spudded well receive bids at a higher rate in the subsequent sale. This is the empirical basis for the Treasure Toggle. |
| **Metrics** | Bid rate per bin (`0 wells`, `1 well`, `2+ wells`) for each of 4 combinations: {10 km, 25 km} x {6-month, 18-month lookback}. Monotonic gradient test. |
| **Statistical test** | Chi-square trend test (Cochran-Armitage) for monotonic increase in bid rate across well-count bins; identify the strongest (radius, window) combination |
| **Lag test** | Compare predictive power of 0–6 month vs. 7–18 month spud windows to test whether signal is immediate or delayed |
| **Decision rule** | Clear monotonic gradient, p < 0.05 → lock in best (radius, window) as canonical feature. Weak gradient → keep Treasure Toggle with relaxed accuracy target (60% vs 70%). No gradient → remove Treasure Toggle from MVP 2; replace with simple "Recent Activity" visualization layer. |

### Q4: Company Archetype Stability

| Element | Detail |
|---------|--------|
| **Hypothesis** | Company behavioral archetypes (Aggressive Explorer / Selective Infiller / Dormant) derived from bid history are stable: the same company receives the same cluster label regardless of which sale computes it. |
| **Features** | `bid_frequency`, `win_rate`, `avg_bid_premium`, `water_depth_preference_mean` |
| **Method** | K-means (k=3) on Sale 257 features → labels_257. K-means (k=3) on Sale 261 features → labels_261. Resolve label permutation via Hungarian algorithm. Compute agreement rate. |
| **Decision rule** | Agreement >= 80% → use as predictive feature. 60–80% → descriptive UI label only, not a model feature. < 60% → drop clustering; expose raw behavioral metrics instead. |
| **Bonus** | Geographic signature: do archetypes cluster in specific water depths or planning areas? |

---

## 3. Two-Week Schedule

### Assumptions
- Single senior IC, full-time (~6–8 productive hours/day)
- All BOEM data is publicly available and downloadable
- Existing shapefile and Sale 198 example data in repo provide format reference

### Schedule

| Day | Phase | Tasks | Outputs |
|-----|-------|-------|---------|
| **D1** | Setup | Environment setup (venv, requirements.txt). Download all BOEM files for Sales 257, 261, Dec 2025. Verify file schemas match across sales. First exploratory parse of BID/TRT/COM files. | Working environment, raw data in `mvp0/data/`, schema validation notes |
| **D2** | Setup + Q1 start | Load shapefile, build block adjacency matrix (queen contiguity). Parse and join bid data for Sale 257 + 261. Verify join keys (Protraction_ID, Block_Number) align across bid files and shapefile. | Adjacency matrix (sparse), merged bid-block DataFrame |
| **D3** | Q1 deep | Build the company-block-adjacency lookup for Sales 257/261 (training). Compute bid_rate_adjacent vs. bid_rate_non_adjacent on training data as a sanity check. | Draft `01_adjacency_signal.ipynb` sections 1–4 |
| **D4** | Q1 validation | Run adjacency analysis on held-out Dec 2025 sale. Compute lift, chi-square test. Generate 2x2 contingency table and choropleth map. | Completed `01_adjacency_signal.ipynb` |
| **D5** | Q2 | Locate and download relinquishment data from BOEM. Parse relinquishment records, compute 36-month lookback window. Flag adjacent-relinquishment blocks. | Relinquishment DataFrame, adjacency flags |
| **D6** | Q2 validation | Compute stratified bid rates (by water depth bucket). Test decay (0–12 mo vs 13–36 mo). Validate on Dec 2025. Generate bar charts and decay curve. | Completed `02_relinquishment_signal.ipynb` |
| **D7** | Q3 | Download well borehole data. Parse spud dates and surface lat/lon. Reproject blocks and wells to UTM 15N. Compute well counts within 10 km and 25 km of each available block centroid for Dec 2025 sale. | Well DataFrame, spatial join results |
| **D8** | Q3 deep | Bin blocks by well count. Compute bid rates per bin for all 4 (radius, window) combinations. Run monotonic gradient tests. Test lag structure. | Draft `03_well_activity_signal.ipynb` |
| **D9** | Q3 finalize + Q4 start | Finalize well-activity notebook with heatmaps and Treasure Toggle preview map. Begin Q4: compute behavioral features for each company from Sale 257. | Completed `03_well_activity_signal.ipynb`, Q4 feature matrix (Sale 257) |
| **D10** | Q4 | Run K-means on Sale 257 features. Repeat for Sale 261. Resolve label permutation (Hungarian algorithm). Compute agreement rate. Investigate switchers. | Completed `04_archetype_stability.ipynb` |
| **D11** | Static map | Build the composite static signal map (PNG, 2400px+): block grid base, Dec 2025 bids, adjacency heatmap, relinquishment cold zones, well activity points. | `signal_map_dec2025.png` |
| **D12** | Findings | Write findings document: data quality observations, Q1–Q4 results, build recommendation, map feedback summary (placeholder if no user feedback yet). | `findings.md` |
| **D13** | Polish | Review all notebooks for reproducibility (top-to-bottom execution). Clean up code, add missing annotations. Final commit. | All deliverables final |
| **D14** | Buffer | Overflow day for any task that ran long. If on track: share map with 1–2 target users for verbatim feedback. | User feedback (optional) |

### Parallel Work Opportunities

| Stream A (can start Day 1) | Stream B (can start Day 1) | Dependency |
|----------------------------|----------------------------|------------|
| Download all BOEM files (Sales 257, 261, Dec 2025, wells, relinquishments) | Set up environment, parse existing Sale 198 example to validate parser | None — fully independent |
| Build adjacency matrix from shapefile (Day 2) | Parse well borehole data (Day 2, if download completed Day 1) | None — independent spatial vs. well data |
| Q2 relinquishment data acquisition (Day 5) | Q1 validation on Dec 2025 (Day 4) | None — different data sources |

---

## 4. Minimum Viable Data Slice

### Sales

| Sale | Role | Files Needed |
|------|------|-------------|
| Sale 257 (Aug 2023) | Training | BID, COM, HST, RES, TRT |
| Sale 261 (Mar 2024) | Training | BID, COM, HST, RES, TRT |
| OBBBA Sale 1 (Dec 2025) | Held-out validation | BID, COM, HST, RES, TRT |

### Supplementary BOEM Datasets

| Dataset | Minimum Slice | Used For |
|---------|--------------|----------|
| OCS Block Shapefile | Full GOM (already in repo at `data/shapefiles/`) | All questions — spatial backbone |
| Active lease table | All active leases as of each sale's bid deadline | Q1 (adjacency), Q2 (relinquishment) |
| Relinquishment / expired lease data | Leases relinquished within 36 months prior to each sale | Q2 |
| Well borehole data | Wells spudded within 18 months prior to Dec 2025 sale (and same window for Sales 257/261) | Q3 |

### Why Not More Sales?

Three sales is the minimum that allows a training set (2 sales) and a held-out validation (1 sale). Adding more sales would increase statistical power but also increase the data wrangling burden. The PRD explicitly recommends this slice. If Q4 archetype stability is borderline at 2 training sales, a stretch goal is to add Sale 259 (Nov 2023).

---

## 5. Data and Notebook Architecture

### Repository Structure

```
block-party/
├── mvp0/
│   ├── notebooks/
│   │   ├── 01_adjacency_signal.ipynb
│   │   ├── 02_relinquishment_signal.ipynb
│   │   ├── 03_well_activity_signal.ipynb
│   │   └── 04_archetype_stability.ipynb
│   ├── data/
│   │   ├── README.md              ← download instructions
│   │   ├── sale_257/              ← raw BOEM files for Sale 257
│   │   │   ├── *.BID
│   │   │   ├── *.COM
│   │   │   ├── *.HST
│   │   │   ├── *.RES
│   │   │   └── *.TRT
│   │   ├── sale_261/              ← raw BOEM files for Sale 261
│   │   │   └── (same 5 files)
│   │   ├── sale_obbba_dec2025/    ← raw BOEM files for Dec 2025
│   │   │   └── (same 5 files)
│   │   ├── leases/                ← active lease table(s)
│   │   │   └── active_leases.csv
│   │   ├── relinquishments/       ← relinquished/expired lease data
│   │   │   └── relinquished_leases.csv
│   │   └── wells/                 ← well borehole data
│   │       └── boreholes.csv
│   ├── outputs/                   ← generated artifacts
│   │   └── signal_map_dec2025.png
│   ├── requirements.txt
│   └── findings.md
├── data/
│   └── shapefiles/                ← already in repo (shared)
│       ├── blocks.shp
│       └── ...
├── utils/                         ← existing utility scripts
└── docs/
    └── block-party-MVP0.md        ← the PRD (source of truth)
```

### BOEM Files to Download Per Sale

For **each** of Sales 257, 261, and OBBBA Dec 2025, download the sale ZIP from `data.boem.gov/Main/Leasing.aspx`. Each ZIP contains:

| File Extension | Content | Used In |
|----------------|---------|---------|
| `*.BID` | All bids: company code, block ID, bid amount, joint bid % | Q1, Q2, Q3, Q4 |
| `*.COM` | Company lookup: code → name | Q4 (company names), all (labels) |
| `*.HST` | Block bid history summary | Q1 (historical context) |
| `*.RES` | Sale results: high bid, accepted/rejected | Q1, Q4 (win_rate) |
| `*.TRT` | Tract info: block ID, area, water depth, acreage | Q2 (depth strata), Q3 (block universe) |

Additional downloads:

| File | Source | Storage Path |
|------|--------|-------------|
| Active lease table | `data.boem.gov/Main/Leasing.aspx` → "Lease Owner" or "Active/Inactive Leases" query | `mvp0/data/leases/` |
| Relinquished leases | `data.boem.gov/Main/Leasing.aspx` → filter by lease status = "Relinquished" or "Expired" | `mvp0/data/relinquishments/` |
| Well borehole data | `data.boem.gov/Main/Well.aspx` → download all GOM wells or query by spud date range | `mvp0/data/wells/` |
| OCS Block Shapefile | Already in `data/shapefiles/` | Symlink or reference via relative path `../../data/shapefiles/` |

---

## 6. Notebook Specifications

### 01_adjacency_signal.ipynb

| Section | Content |
|---------|---------|
| **1. Setup & Data Loading** | Import libraries. Load shapefile from `../../data/shapefiles/blocks.shp`. Load BID, COM, TRT files for Sales 257, 261, and Dec 2025. Parse fixed-width formats using the utility script patterns. |
| **2. Build Block Adjacency Matrix** | Use `libpysal.weights.Queen.from_dataframe()` or manual shared-edge detection on the GeoDataFrame. Output: sparse adjacency dict `{block_id: [neighbor_ids]}`. Validate on a known block (e.g., MC 127 should have 4–8 neighbors). |
| **3. Build Active Lease Lookup** | For each company, identify which blocks they hold active leases on as of each sale's bid deadline. Cross-reference with adjacency matrix: for each available block, flag which companies have an adjacent active lease. |
| **4. Training Sanity Check (Sales 257/261)** | Compute `bid_rate_adjacent` and `bid_rate_non_adjacent` on the training sales. This is NOT validation — it's a sanity check that the adjacency variable is constructed correctly. If lift is exactly 1.0 here, something is wrong with the join. |
| **5. VALIDATION — HELD-OUT (Dec 2025)** | Compute the same bid rates on Dec 2025. Compute lift. Run chi-square test. Print 2x2 contingency table. |
| **6. Choropleth Map** | GOM grid colored by "number of companies with adjacent active lease" for Dec 2025 available blocks. Overlay actual Dec 2025 bids as colored dots (by company). |
| **7. Findings** | Markdown cell: lift value, p-value, interpretation per PRD decision rule, recommendation. |

**Key plots/tables:**
- 2x2 contingency table (adjacent/not x bid/no-bid)
- Choropleth map (adjacency density + actual bids)
- Lift summary bar chart

---

### 02_relinquishment_signal.ipynb

| Section | Content |
|---------|---------|
| **1. Setup & Data Loading** | Load shapefile, bid data (all three sales), relinquishment data, TRT files (for water depth). |
| **2. Identify Relinquishments** | Filter relinquishment data to 36-month window prior to each sale's bid deadline. Join relinquished blocks to shapefile to get spatial locations. |
| **3. Flag Adjacent Relinquishments** | For each available block in Dec 2025, flag `relinquishment_adjacent = 1` if any queen-adjacent block was relinquished in the 36-month window. |
| **4. Stratify by Water Depth** | Assign each available block to a depth bucket: shelf (< 200m), deepwater (200–1500m), ultra-deepwater (> 1500m) using TRT water depth field. |
| **5. VALIDATION — HELD-OUT (Dec 2025)** | Compute bid rates for `relinquishment_adjacent = 1` vs. `= 0` within each depth stratum. Run chi-square per stratum. |
| **6. Decay Analysis** | Split the 36-month window: 0–12 months vs. 13–36 months since relinquishment. Compute suppression ratio for each sub-window. Plot decay curve. |
| **7. Findings** | Markdown cell: suppression ratios by stratum, decay pattern, interpretation, recommendation. |

**Key plots/tables:**
- Bar chart: bid rate by relinquishment adjacency, faceted by water depth
- Decay curve: suppression ratio vs. months since relinquishment
- Summary table: suppression ratio per stratum with chi-square p-values

---

### 03_well_activity_signal.ipynb

| Section | Content |
|---------|---------|
| **1. Setup & Data Loading** | Load shapefile, bid data, well borehole data. Reproject both to UTM Zone 15N (EPSG:26915) for distance computation. |
| **2. Compute Well Counts per Block** | For each available block in Dec 2025, count wells spudded within {10 km, 25 km} of block centroid in {6-month, 18-month} lookback windows. Result: 4 new columns per block. |
| **3. Bin Blocks by Well Count** | Create bins: `0 wells`, `1 well`, `2+ wells` for each of the 4 (radius, window) combinations. |
| **4. VALIDATION — HELD-OUT (Dec 2025)** | Compute bid rate per bin for each combination. Test monotonic gradient (Cochran-Armitage trend test). Identify the strongest combination. |
| **5. Lag Structure Test** | Compare predictive power of 0–6 month spud window vs. 7–18 month window. Is the signal immediate or delayed? |
| **6. Treasure Toggle Preview Map** | Pick a real historical well (from Sales 257/261 period). Show surrounding blocks. Color by "did this block receive a bid in the next sale?" Compare to what the model would predict. |
| **7. Heatmaps** | 2x2 heatmap: rows = radius {10, 25 km}, columns = window {6, 18 months}. Cell value = bid rate for `2+ wells` bin / bid rate for `0 wells` bin (i.e., lift). |
| **8. Findings** | Best (radius, window) combination, gradient strength, lag structure, Treasure Toggle viability recommendation. |

**Key plots/tables:**
- 2x2 heatmap of lift by (radius, window)
- Bar chart: bid rate by well-count bin for the best combination
- Lag curve: predictive power vs. lookback window
- Treasure Toggle preview map (single well example)

---

### 04_archetype_stability.ipynb

| Section | Content |
|---------|---------|
| **1. Setup & Data Loading** | Load BID, COM, RES files for Sales 257 and 261. |
| **2. Compute Behavioral Features (Sale 257)** | For each company active in Sale 257: `bid_frequency` (# bids / # available blocks), `win_rate` (# high bids accepted / # bids), `avg_bid_premium` (mean bid amount / mean high-bid for same blocks), `water_depth_preference_mean` (average water depth of blocks bid on). Normalize features. |
| **3. K-Means Clustering (Sale 257)** | Run K-means (k=3). Label clusters (Aggressive Explorer, Selective Infiller, Dormant) based on feature centroids. Visualize with scatter plot (bid_frequency vs. win_rate, colored by cluster). |
| **4. Repeat for Sale 261** | Same feature computation and K-means on Sale 261 data. |
| **5. Agreement Rate** | Identify companies active in BOTH sales. Resolve label permutation using Hungarian algorithm (scipy `linear_sum_assignment` on confusion matrix). Compute agreement rate = % of shared companies with matching labels. |
| **6. Switcher Analysis** | For companies that switch archetypes: list them, note any known M&A events or commodity price shifts between Aug 2023 and Mar 2024. |
| **7. Geographic Signature** | For each archetype, plot the geographic distribution of bids. Do Aggressive Explorers cluster in specific depths/areas? Do Infillers target adjacency opportunities? |
| **8. VALIDATION — HELD-OUT (Dec 2025)** | Assign Dec 2025 bidders to archetypes using the Sale 261 model. Map archetype-colored bids onto the GOM grid. |
| **9. Findings** | Agreement rate, stability assessment, geographic signature presence, recommendation. |

**Key plots/tables:**
- Scatter plots: bid_frequency vs. win_rate, colored by archetype (one per sale)
- Agreement rate table by company
- Confusion matrix (Sale 257 clusters vs. Sale 261 clusters)
- Geographic map: Dec 2025 bids colored by archetype

---

## 7. Methods and Statistical Tests (Detail)

### Preventing Validation Leakage

This is the single most important methodological discipline in MVP 0.

**Rule:** December 2025 sale data is NEVER used to compute features, thresholds, or model parameters. It is used ONLY for evaluation.

**Implementation:**
1. Every notebook has a clear section boundary: sections before `## VALIDATION — HELD-OUT` use only Sales 257/261 data.
2. The adjacency matrix, active lease lookup, relinquishment flags, and well counts are all computed relative to the Dec 2025 sale's bid deadline — but the bid *outcomes* (who actually bid, what they bid) are only revealed in the validation section.
3. In Q4 (archetypes), the K-means model is fit on Sales 257 and 261. Dec 2025 bidders are assigned to clusters using the Sale 261 centroid model (`kmeans.predict()`), not re-clustered.
4. No threshold or cutoff (e.g., "lift >= 3x is strong") is tuned on Dec 2025 data. All thresholds come from the PRD, set before seeing the results.

### Q1: Adjacency — Step-by-Step Method

1. **Population**: All (company, available_block) pairs for a given sale. A block is "available" if it appears in the TRT file for that sale.
2. **Treatment group**: Pairs where the company holds an active lease on a queen-adjacent block as of the sale's bid deadline.
3. **Control group**: Pairs where the company does NOT hold an adjacent lease.
4. **Outcome**: Binary — did the company submit a bid on that block? (from BID file)
5. **Statistics**:
   - `bid_rate_adjacent = sum(bid=1 | adjacent=1) / count(adjacent=1)`
   - `bid_rate_non_adjacent = sum(bid=1 | adjacent=0) / count(adjacent=0)`
   - `lift = bid_rate_adjacent / bid_rate_non_adjacent`
   - Chi-square test on the 2x2 table
6. **Plots**: Contingency table, bar chart of bid rates, choropleth

### Q2: Relinquishment — Step-by-Step Method

1. **Population**: All available blocks in Dec 2025 sale.
2. **Treatment group**: Blocks with at least one queen-adjacent block relinquished in the prior 36 months.
3. **Control group**: Blocks with no adjacent relinquishments in that window.
4. **Confound control**: Stratify by water depth bucket (shelf / deepwater / ultra-deepwater) since relinquishments may cluster geographically.
5. **Statistics**:
   - `suppression_ratio = bid_rate_treatment / bid_rate_control` per stratum
   - Chi-square per stratum
   - Decay: repeat with 0–12 month and 13–36 month sub-windows
6. **Plots**: Stratified bar chart, decay curve, summary table

### Q3: Well Activity — Step-by-Step Method

1. **Population**: All available blocks in Dec 2025 sale.
2. **Treatment definition**: Number of wells spudded within radius R of block centroid in lookback window W. Four combinations: (10km, 6mo), (10km, 18mo), (25km, 6mo), (25km, 18mo).
3. **Bins**: `0 wells`, `1 well`, `2+ wells` per combination.
4. **Statistics**:
   - Bid rate per bin for each (R, W) combination
   - Cochran-Armitage trend test for monotonic increase
   - Identify the combination with the strongest lift and lowest p-value
5. **Lag test**: Split the 18-month window into 0–6 mo and 7–18 mo. Compute bid rate lift for `2+ wells` vs `0 wells` in each sub-window. Compare to determine if signal is immediate or delayed.
6. **Plots**: 2x2 heatmap, bar charts by bin, lag curve, Treasure Toggle preview map

### Q4: Archetype Stability — Step-by-Step Method

1. **Population**: Companies that submitted at least 1 bid in both Sale 257 AND Sale 261.
2. **Features** (per company per sale):
   - `bid_frequency` = number of bids / number of available blocks
   - `win_rate` = accepted high bids / total bids
   - `avg_bid_premium` = mean(bid_amount) / mean(winning_bid for same blocks)
   - `water_depth_preference_mean` = mean water depth of blocks bid on
3. **Clustering**: StandardScaler → K-means (k=3) on Sale 257 features. Repeat independently on Sale 261.
4. **Label alignment**: Build a 3x3 confusion matrix of (Sale 257 label, Sale 261 label) for shared companies. Use Hungarian algorithm (`scipy.optimize.linear_sum_assignment`) on the negative confusion matrix to find the optimal label permutation.
5. **Agreement rate**: After relabeling, `agreement = matching / total_shared_companies`.
6. **Plots**: Scatter plots, confusion matrix heatmap, agreement table, geographic map

---

## 8. Deliverables Checklist

- [ ] `mvp0/notebooks/01_adjacency_signal.ipynb` — self-contained, annotated, runs top-to-bottom
- [ ] `mvp0/notebooks/02_relinquishment_signal.ipynb` — same criteria
- [ ] `mvp0/notebooks/03_well_activity_signal.ipynb` — same criteria
- [ ] `mvp0/notebooks/04_archetype_stability.ipynb` — same criteria
- [ ] `mvp0/outputs/signal_map_dec2025.png` — composite static map, 2400px+ wide, labeled "What block-party would have shown you before the December 2025 sale"
- [ ] `mvp0/findings.md` — 3–5 pages covering data quality, Q1–Q4 results, build recommendation, map feedback summary
- [ ] `mvp0/requirements.txt` — pinned versions of all Python dependencies
- [ ] `mvp0/data/README.md` — exact download instructions for all BOEM files

---

## 9. Decision Framework: Outcome Matrix

### Per-Question Outcomes and Implications

| Question | Strong Signal | Moderate Signal | Weak/No Signal |
|----------|--------------|-----------------|----------------|
| **Q1 Adjacency** | Lift >= 3x, p < 0.05. **MVP 1 proceeds as written.** Block-level prediction is viable. | Lift 1.5–3x, p < 0.05. **Proceed but reweight** adjacency in feature set. Investigate complementary features. | Lift < 1.5x or p > 0.05. **Do NOT build block-level prediction.** Test planning-area aggregation as fallback. If that also fails, pause and reframe the entire product concept. |
| **Q2 Relinquishment** | Suppression <= 50%. **Include cold-zone layer** in MVP 1 as specified. | Suppression 50–80%. **Include but deprioritize** — do not surface as prominent UI element. Revisit in MVP 2. | No meaningful difference. **Remove cold zones** from MVP 1 feature set entirely. Do not build cold-zone UI layer. |
| **Q3 Well Activity** | Clear monotonic gradient, p < 0.05. **Lock in best (radius, window)** as canonical feature. Treasure Toggle proceeds. | Gradient exists but weak. **Keep Treasure Toggle** but relax accuracy target from 70% to 60%. | No gradient. **Remove Treasure Toggle** from MVP 2. Replace with simple "Recent Activity" visualization layer — honest and useful. |
| **Q4 Archetypes** | Agreement >= 80%. **Use archetypes as predictive feature** in model + UI badge. | Agreement 60–80%. **Use as descriptive UI label** (company panel) but NOT as model feature. | Agreement < 60%. **Drop clustering.** Expose raw behavioral metrics (bid frequency, win rate, premium, depth preference) directly. |

### Aggregate Recommendation Logic

| Scenario | Recommendation |
|----------|---------------|
| Q1 strong + at least 2 of Q2/Q3/Q4 strong or moderate | **Proceed as planned.** MVP 1 PRD is validated. Begin pipeline engineering. |
| Q1 moderate + mixed results on Q2–Q4 | **Proceed with modifications.** List specific PRD changes (e.g., planning-area fallback, drop Treasure Toggle) and update PRD before starting MVP 1. |
| Q1 weak (even after planning-area fallback) | **Pause and reframe.** Core spatial prediction assumption is not validated. Consider alternative product directions before committing to build. |
| Q1 strong but Q2+Q3+Q4 all weak | **Proceed with stripped-down MVP 1.** Adjacency-only model is still valuable. Remove cold zones, Treasure Toggle, and archetype badges. Simpler product, potentially stronger. |

---

## 10. Day-1 and Week-1 Detailed Plan

### Day 1: Environment + Data Acquisition

**Morning (3 hours):**

1. **Create Python virtual environment**
   ```bash
   cd block-party/mvp0
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Verify existing data**
   - Load `data/shapefiles/blocks.shp` in a scratch notebook
   - Confirm columns: `PROT_NUMBE`, `BLOCK_NUMB`, `AREA_CODE`, `MMS_PLAN_A`
   - Confirm CRS is NAD27 (EPSG:4267); test reprojection to UTM 15N (EPSG:26915)
   - Count total blocks (expect ~60,000+)

3. **Download BOEM sale files**
   - Go to `data.boem.gov/Main/Leasing.aspx`
   - Download ZIP archives for Sale 257, Sale 261, and OBBBA Dec 2025
   - Extract each to `mvp0/data/sale_257/`, `sale_261/`, `sale_obbba_dec2025/`
   - Verify each ZIP has 5 files: BID, COM, HST, RES, TRT

**Afternoon (3 hours):**

4. **Schema validation across sales**
   - Adapt `utils/process-lease-sale-BOEM-downloads.py` for each sale
   - Parse BID files from all three sales with the same fixed-width specs
   - Compare column counts, field widths, value ranges
   - **Key check**: Does the Dec 2025 (OBBBA) sale use the same format as legacy sales? If not, document differences immediately.

5. **First exploratory join**
   - Join Sale 257 BID → COM (company names)
   - Join Sale 257 BID → TRT (block details, water depth)
   - Join TRT → shapefile (via Protraction_ID + Block_Number)
   - Verify join rates: aim for 95%+ match on all three joins
   - If join rates are low, investigate key formatting issues (G-prefix, padding, etc.)

6. **Download supplementary data**
   - Active lease table from BOEM
   - Well borehole data (filter: GOM, spud date >= 2022-01-01)
   - Relinquishment data (try to locate the specific BOEM source)

**Day 1 Deliverables:**
- [ ] Working Python environment with all dependencies
- [ ] All raw BOEM files downloaded and stored in correct directories
- [ ] Schema validation notes (any cross-sale differences documented)
- [ ] First successful BID → COM → TRT → shapefile join for Sale 257
- [ ] Data README drafted with exact download URLs

---

### Day 2: Adjacency Matrix + First Signal Test

**Morning:**
1. Build queen-contiguity adjacency matrix from shapefile
   - Use `libpysal.weights.Queen.from_dataframe(gdf)` OR manual shared-edge detection
   - Validate: spot-check 3–5 known blocks for correct neighbor counts
   - Store as dict: `{(protraction_id, block_number): [(neighbor_prot, neighbor_block), ...]}`

2. Build active lease lookup for Sale 257 bid deadline
   - From the active lease table: which companies held active leases on which blocks as of Aug 2023?
   - Cross-reference with adjacency matrix: for each available block in Sale 257, which companies had adjacent active leases?

**Afternoon:**
3. First adjacency lift calculation (Sale 257 — training, sanity check only)
   - Compute bid_rate_adjacent vs. bid_rate_non_adjacent
   - If lift is near 1.0: debug the join (likely a key alignment issue)
   - If lift is high (3x+): promising — proceed to validation
   - This is NOT the result that matters. Dec 2025 validation is the result.

---

### Week 1 Priorities (Days 3–5)

| Priority | Rationale |
|----------|-----------|
| **Finish Q1 (adjacency) first** | It is the most important signal. If this fails, the entire product concept needs rethinking. De-risk it before investing in Q2–Q4. |
| **Start Q2 (relinquishment) only after Q1 validation is complete** | Q2 reuses the adjacency matrix, so there's code reuse. But the relinquishment data source is the biggest unknown — start the download/parsing early even while Q1 analysis runs. |
| **Prototype Q3 well download in parallel** | Well data download can run in background while Q1 analysis proceeds. |

### Which Question to Prototype First?

**Q1 (Adjacency) — unambiguously.** Reasons:

1. It is the "load-bearing wall" of the entire product. The PRD says: *"If this is weak, the entire spatial model needs rethinking."*
2. It has the cleanest data requirements (shapefile + lease table + bid files — all well-understood formats).
3. The adjacency matrix is reused by Q2 (relinquishment adjacency).
4. It has the most clearly defined metric (lift ratio) and decision rule.
5. If Q1 fails, you want to know on Day 4, not Day 12 — it changes the priority of everything else.
