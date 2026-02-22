# block-party — MVP 0: Signal Validation Study
**Product Requirements Document | v1.0 | MVP 0 Only**
February 2026 | Open Source | `github.com/[org]/block-party`

---

## Overview

MVP 0 is not a product build. It is a **structured data investigation** designed to answer one question before any engineering resources are committed:

> *Does the spatial and behavioral signal in public BOEM data actually predict where companies bid?*

Everything in MVP 1 and MVP 2 rests on the assumption that adjacency, clustering, and company behavioral history are meaningfully predictive of future bid behavior. MVP 0 tests that assumption cheaply, in notebooks, on real data — before a single line of pipeline code is written.

**Duration:** 2–3 weeks  
**Tooling:** Jupyter notebooks, GeoPandas, pandas, matplotlib/folium. No PostGIS, no dbt, no FastAPI, no app.  
**Output:** A findings document and one static map. Nothing is deployed.

---

## The Four Questions MVP 0 Must Answer

These are the load-bearing assumptions underneath all of MVP 1. Each must be tested explicitly. A weak result on any one of them changes the build plan — it does not necessarily kill the project.

| # | Question | Why It Matters |
|---|----------|----------------|
| Q1 | Does **adjacency** predict bidding at a meaningful lift above the base rate? | The single most important feature in the MVP 1 feature set. If this is weak, the entire spatial model needs rethinking. |
| Q2 | Do **relinquishment signals** suppress bid probability on nearby blocks? | Determines whether cold zones are a real feature or a cosmetic one. |
| Q3 | Does **recent well activity** within a radius correlate with increased bidding on surrounding blocks? | The empirical foundation for the Treasure Toggle in MVP 2. |
| Q4 | Do **company behavioral archetypes** hold up consistently across multiple sales? | Determines whether company-level clustering is stable enough to be a predictive feature or just descriptive noise. |

---

## Data Acquisition

All data is freely available from BOEM. No licenses, no vendors, no scraping.

### Primary Datasets

| Dataset | Source URL | Format | Notes |
|---------|-----------|--------|-------|
| Bid files — all post-2010 sales | `data.boem.gov/Main/Leasing.aspx` | Fixed-format ASCII ZIP per sale | Download each sale's ZIP; 5 ASCII files per sale. Start with Sales 257, 259, 261, and the December 2025 OBBBA sale. |
| Lease data | `data.boem.gov/Main/Leasing.aspx` | ASCII / online query | Active leases, expiration dates, operators, water depth |
| Well borehole data | `data.boem.gov/Main/Well.aspx` | Online query, downloadable | Spud dates, TVD, well type, block location |
| Relinquishment data | Included in BOEM lease reports | ASCII | Leases relinquished or expired, with dates and former operators |
| OCS block shapefile | `data.boem.gov/Main/mapping.aspx` | Shapefile / GeoPackage | GOM OCS protraction block boundaries — the spatial backbone |

### Recommended Test Sales

Use **three sales** to allow a simple train/validate split:

| Role | Sale | Date | Rationale |
|------|------|------|-----------|
| Training reference | Sale 257 | August 2023 | Pre-OBBBA, IRA royalty regime (16.67%). Good baseline. |
| Training reference | Sale 261 | March 2024 | Also IRA era. Second data point for behavioral profiling. |
| Held-out validation | OBBBA Sale 1 | December 2025 | Most recent sale. OBBBA royalty regime (12.5%). Tests whether signals transfer across regulatory regimes. |

> ⚑ **Do not use the December 2025 sale for training.** It is the validation set. Build all features from Sales 257 and 261, then check predictions against December 2025 outcomes blind.

---

## Investigation 1: Adjacency Signal (Q1)

**Hypothesis:** Companies that hold an active lease on a block adjacent to an available block bid on that available block at a meaningfully higher rate than companies without an adjacent position.

### Method

1. For each available block in the December 2025 sale, build a binary lookup table: for each active company, does it hold an active lease on any edge-adjacent block? (Queen contiguity — shared full edge, not diagonal.)
2. Compute two bid rates from December 2025 actuals:
   - `bid_rate_adjacent` = bids placed / opportunities where company had an adjacent lease
   - `bid_rate_non_adjacent` = bids placed / opportunities where company had no adjacent lease
3. Compute **lift** = `bid_rate_adjacent / bid_rate_non_adjacent`
4. Run a chi-square test for statistical significance. Target: p < 0.05.

### Success Criteria

| Result | Interpretation | Action |
|--------|---------------|--------|
| Lift >= 3x, p < 0.05 | Strong signal. Adjacency is a real predictor. | Proceed to MVP 1 as planned. |
| Lift 1.5x–3x, p < 0.05 | Moderate signal. Useful but not dominant. | Proceed, but weight adjacency appropriately. Investigate whether other features compensate. |
| Lift < 1.5x or p > 0.05 | Weak or noisy signal. | Do not proceed to MVP 1 as written. Consider aggregating prediction unit to planning area level (see Contingency Plans). |

### Output

A 2x2 contingency table and a choropleth map of the GOM grid colored by "companies with adjacent position" vs. "no adjacent position" for the December 2025 sale, with actual bids overlaid as dots.

---

## Investigation 2: Relinquishment Signal (Q2)

**Hypothesis:** Blocks adjacent to recently relinquished leases receive bids at a lower rate than similar blocks with no adjacent relinquishments. Relinquishment is a visible negative geological signal.

### Method

1. Identify all blocks relinquished in the 36 months prior to each test sale's bid submission deadline.
2. For each available block in December 2025, flag whether it has one or more adjacent relinquishments in that window.
3. Compute bid rates for `relinquishment_adjacent = 1` vs. `= 0`, controlling for water depth bucket (shelf / deepwater / ultra-deepwater) to avoid confounding with the geographic distribution of relinquishments.
4. Also compute: does the relinquishment signal decay over time? Compare 0–12 months vs. 13–36 months since relinquishment.

### Success Criteria

| Result | Interpretation | Action |
|--------|---------------|--------|
| Adjacent-relinquishment blocks bid at <= 50% the rate of non-relinquishment blocks | Signal is real and usable as a cold-zone indicator | Include as MVP 1 feature as specified |
| Marginal difference (50%–80% of base rate) | Signal exists but is weak | Include, but do not surface as a prominent UI element in MVP 1. Revisit in MVP 2. |
| No meaningful difference | Signal does not exist in the data | Remove from MVP 1 feature set. Do not build cold-zone UI layer. |

### Output

Bar charts of bid rates by relinquishment adjacency and water depth bucket. A decay curve showing bid rate suppression as a function of time since relinquishment.

---

## Investigation 3: Well Activity Radius Signal (Q3)

**Hypothesis:** Available blocks within 10–25 km of a recently spudded well receive bids at a higher rate in the subsequent sale than blocks in quiet areas. This is the empirical basis for the MVP 2 Treasure Toggle.

### Method

1. For each available block in the December 2025 sale, count the number of wells spudded within 10 km and 25 km in the prior 6 months and 18 months (four combinations).
2. Bin blocks into `0 wells`, `1 well`, `2+ wells` within each radius/window combination.
3. Compute bid rates per bin.
4. Test whether the gradient is monotonic (more wells = higher bid rate) and statistically significant.
5. Identify the **strongest combination** of radius and lookback window — this becomes the canonical `active_finds` feature in MVP 1.

### Additional test — lag structure

This is the Treasure Toggle assumption: a well drilled *today* shifts bid behavior in the *next* sale. Test the lag explicitly:

- Does a well spudded 0–6 months before the sale have more predictive power than one spudded 7–18 months before?
- Or is the signal actually stronger with a delay (suggesting it takes time for geological interpretation to propagate into bid strategy)?

### Success Criteria

| Result | Interpretation | Action |
|--------|---------------|--------|
| Clear monotonic gradient, strongest combination p < 0.05 | Signal is real. Proceed with Treasure Toggle design as specified. | Lock in the best radius/window combo as the canonical feature. |
| Gradient exists but weak | Signal present but marginal. Treasure Toggle will show directional movement, not dramatic shifts. | Keep Treasure Toggle but revise its success metric — 70% directional accuracy target may need to drop to 60%. |
| No gradient | Well activity within radius does not predict bidding in the GOM at block level | Remove Treasure Toggle from MVP 2. Consider whether planning-area aggregation rescues the signal. |

### Output

Heatmaps showing bid rate as a function of `(radius, lookback_window)` combinations. A lag curve. One static "Treasure Toggle preview" map: pick a real historical well, show which surrounding blocks received bids in the following sale, and check whether the model would have predicted them.

---

## Investigation 4: Company Archetype Stability (Q4)

**Hypothesis:** Company behavioral archetypes (Aggressive Explorer / Selective Infiller / Dormant) derived from bid history are stable across consecutive sales — the same company falls in the same cluster regardless of which sale you use to compute it.

### Method

1. Compute behavioral features for each active company using Sale 257 data only: `bid_frequency`, `win_rate`, `avg_bid_premium`, `water_depth_preference_mean`.
2. Run K-means clustering (k=3) and label the resulting clusters.
3. Recompute the same features using Sale 261 data only and re-run clustering.
4. Compute the **archetype agreement rate**: percentage of companies assigned the same cluster label across both sales (after resolving label permutation).
5. For companies that switch archetypes between sales, investigate whether the switch is explained by a known event (M&A, major exploration result, commodity price crash).

### Success Criteria

| Result | Interpretation | Action |
|--------|---------------|--------|
| >= 80% agreement | Archetypes are stable. Use as a predictive feature. | Proceed with company archetyping as specified in MVP 1. |
| 60%–80% agreement | Moderate stability. Archetypes are descriptive but not reliably predictive across sales. | Use archetypes as a UI label (company intelligence panel) but do not include as a model feature. |
| < 60% agreement | Archetypes are unstable — too noisy to be useful. | Drop company_archetype from the MVP 1 feature set. Replace with raw behavioral metrics only. |

### Additional investigation

For each archetype, compute the **geographic signature** — do Aggressive Explorers cluster in specific water depths or planning areas? Do Selective Infillers systematically target adjacency opportunities? This tells us whether archetypes have spatial meaning (useful for the map UI) or are purely financial (useful only as model features).

### Output

Cluster scatter plots (bid frequency vs. win rate, colored by archetype). Agreement rate table by company. A labeled map showing which companies in each archetype bid in December 2025 and where.

---

## Contingency Plans

These are not failure states — they are the pivot triggers that prevent building the wrong thing for six months.

### If Q1 (Adjacency) is weak: Aggregate to Planning Area

If block-level adjacency doesn't predict, the prediction unit is probably wrong. The GOM is divided into ~20 named planning areas (Mississippi Canyon, Green Canyon, Walker Ridge, Keathley Canyon, etc.). Aggregating the prediction task to "Company X will bid somewhere in Planning Area Y in the next sale" sacrifices spatial precision but gains dramatically more signal — each planning area has enough historical bids for meaningful statistics.

Before abandoning MVP 1, run the adjacency test at the planning-area level. If lift is strong there, the MVP 1 PRD needs to be rewritten with planning area as the primary spatial unit. The front-end map still shows the block grid, but the heatmap is a planning-area heatmap, not a block-level one.

### If Q3 (Well Activity) is weak: Reconsider the Treasure Toggle

If well activity within radius doesn't correlate with subsequent bidding at the block level, the Treasure Toggle has no empirical grounding and should be removed from MVP 2. Do not build a feature that looks convincing but produces random outputs — it will undermine trust in the entire platform when a user tests it against historical data.

The alternative for MVP 2 becomes simpler: a "Recent Activity" layer that just visualizes where wells have been spudded, without modeling the downstream bid effect. Useful and honest. Build that instead.

### If Q4 (Archetypes) is unstable: Use raw features only

Drop `company_archetype` from the model and the UI company badge. Replace with the four underlying behavioral metrics displayed directly: bid frequency, win rate, average premium, water depth preference. These are interpretable without the clustering abstraction and are more honest if the clustering isn't stable.

---

## Deliverables

MVP 0 produces exactly three artifacts. Nothing else.

### Deliverable 1: Four Investigation Notebooks

One Jupyter notebook per investigation (Q1–Q4). Each notebook must be:

- **Self-contained:** Running it from top to bottom on the raw BOEM source files produces all outputs with no external dependencies beyond standard Python data science libraries.
- **Annotated:** Markdown cells explaining each step, the result, and what it means for the build decision.
- **Reproducible:** A `requirements.txt` and a `data/README.md` describing exactly which BOEM files to download and where to place them.

File structure:
```
block-party/
├── mvp0/
│   ├── notebooks/
│   │   ├── 01_adjacency_signal.ipynb
│   │   ├── 02_relinquishment_signal.ipynb
│   │   ├── 03_well_activity_signal.ipynb
│   │   └── 04_archetype_stability.ipynb
│   ├── data/
│   │   └── README.md          ← download instructions for BOEM files
│   └── requirements.txt
```

### Deliverable 2: Static Signal Map

A single map image (PNG, minimum 2400px wide) showing the December 2025 sale with:

- GOM OCS block grid as the base layer
- Actual December 2025 bids overlaid (colored by company)
- Adjacency-based "predicted high-interest zones" shown as a heatmap
- Relinquishment cold zones shown in a distinct color
- Recent well activity (prior 18 months) marked as point symbols

This map is the primary user validation tool. It should be legible to someone who has never seen the product before. Label it: *"What block-party would have shown you before the December 2025 sale."*

### Deliverable 3: Findings Document

A 3–5 page document (this can be a notebook converted to PDF, or a standalone markdown file) covering:

1. **Data quality observations** — what was messier than expected, what was cleaner, any gaps or surprises in the BOEM source files.
2. **Q1–Q4 results** — one paragraph per question with the key statistic and the go/no-go recommendation.
3. **Build recommendation** — one of three outcomes:
   - *Proceed as planned:* MVP 1 PRD is validated. Begin pipeline engineering.
   - *Proceed with modifications:* Specific features or the prediction unit need to change. List the changes and update the PRD before starting MVP 1.
   - *Pause and reframe:* Core signal assumptions are not validated. Recommend a different product direction before committing to build.
4. **The static map feedback summary** — if the map was shown to any target users, include their verbatim reactions and what they revealed about user mental models.

---

## Success Criteria for MVP 0 as a Whole

MVP 0 is successful if it produces a clear, evidence-based answer to "should we build MVP 1 as written?" — regardless of whether that answer is yes, yes-with-changes, or no.

MVP 0 fails only if it is inconclusive: if the notebooks are incomplete, the validation test is contaminated by training data, or the findings document hedges without making a recommendation.

A "no" result from MVP 0 is not a failure. It is the cheapest possible version of learning that the product needs to be different. Four failed MVPs over seven years suggests the cost of that lesson has historically been very high. MVP 0 exists to make it cheap.

---

## Out of Scope for MVP 0

- Any data pipeline or automated ETL
- Any web application or UI
- PostGIS or any database setup — flat files and GeoPandas only
- Model training or hyperparameter tuning — descriptive statistics and lift analysis only
- Company entity resolution — use BOEM company names as-is for this investigation
- Any data beyond the four BOEM sources listed above

---

## Appendix: Key BOEM File Reference

BOEM bid files are delivered as ZIP archives, one per sale. Each ZIP contains five fixed-format ASCII files:

| File | Content |
|------|---------|
| `*.BID` | All bids: company code, block ID, bid amount, joint bid indicator |
| `*.COM` | Company lookup: company code → company name |
| `*.HST` | Block bid history summary |
| `*.RES` | Sale results: high bids, accepted/rejected status |
| `*.TRT` | Tract information: block ID, area, water depth, available acreage |

Record layouts are published in each sale's ZIP as a companion document. Field widths are fixed — do not use a CSV parser.

The OCS block shapefile uses BOEM's protraction diagram coordinate system. Reproject to **UTM Zone 15N (EPSG:26915)** before computing any distances.
