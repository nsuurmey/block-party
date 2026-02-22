# block-party
## GOM OCS Lease Bidding Intelligence Platform
**Product Requirements Document | v3.0 | MVP 1 & 2**
February 2026 | Open Source | `github.com/[org]/block-party`

---

## Overview

block-party is an open-source GOM OCS lease bidding intelligence platform. It transforms public BOEM data into a machine-learning-ready feature matrix and surfaces bid probability predictions through an interactive web-based GIS map.

This PRD covers **MVP 1 and MVP 2 only**. Future milestones (infrastructure proximity, FMV rejection risk, manual data entry, proprietary seismic integration) are out of scope and listed in [Appendix B](#appendix-b-out-of-scope-for-mvp-1-and-mvp-2).

### MVP Roadmap

| Milestone | Timeframe | Scope |
|-----------|-----------|-------|
| MVP 1 | Months 1–3 | Core data pipeline, bid/no-bid prediction across all GOM blocks, single-company competitor map, relinquishment signals, company archetyping |
| MVP 2 | Months 4–6 | Treasure Toggle (hypothetical well-activity scenario), time-travel playback slider, regulatory calendar and Federal Register alert feed |

### Scope Constraints (MVP 1 & 2)

- **Training data window:** Post-2010 only. Aligns with the era of modern wide-azimuth and full-azimuth seismic availability across the GOM basin, reducing structural non-stationarity in behavioral signals.
- **Entity resolution:** Clean, normalized company data is assumed as pipeline input. Corporate parent mapping (e.g., BHP→Woodside, CGG→Viridien) is handled by a dedicated upstream data science workflow outside the scope of these PRDs.
- **JV bids:** Treated on equal footing with standalone bids. Each listed company is credited individually. Full JV disaggregation is a future milestone.
- **Proprietary seismic:** Platform is built entirely on public BOEM/BSEE data. Private seismic interpretation is an acknowledged gap and a future milestone.

---

## PRD 1: Spatial-Temporal Feature Engineering Engine

> Back-end data pipeline: From raw BOEM public data to an ML-ready feature matrix

### 1.1 Purpose and Scope

The Feature Engineering Engine is the data foundation of the entire platform. Its sole output is a **Master Feature Table** — a clean, time-indexed, spatially-aware matrix where every row represents a unique combination of `[Company_ID, Block_ID, Sale_Date]`. The target variable is a binary `Did_Bid` flag (1 = company submitted a bid on this block at this sale; 0 = did not). All downstream ML models and the front-end application consume this table exclusively.

The engine must be reproducible, auditable, and designed to prevent data leakage — no feature for a given row may include information that would not have been publicly available before the bid submission deadline for that sale.

### 1.2 Primary Data Sources

| Source | Content | Key Identifiers |
|--------|---------|-----------------|
| BOEM Bid Files (all post-2010 sales) | Company names, bonus bid amounts, block IDs, acceptance/rejection status, high-bid flags per sale | Block ID, Company ID, Sale Date |
| BOEM Lease Data | Lease numbers, effective/expiration dates, royalty rates, operator history, water depth, acreage | Block ID, Operator ID, Lease Date |
| BOEM Well Data (Borehole) | API numbers, spud dates, TVD, well type (exploratory/development), borehole status, water depth | API Number, Block ID, Spud Date |
| BOEM Production Data | Oil, gas, and water volumes by lease and well; monthly and annual | Lease ID, Well API, Report Date |
| BOEM Relinquishment Data | Leases relinquished, terminated, or expired with dates and former operator | Block ID, Former Operator, Relinquishment Date |
| Federal Register (NOS filings) — *MVP 2* | Proposed and Final Notice of Sale dates, royalty rates, lease terms per sale | Sale Number, Publication Date |

> ⚑ **Data latency note:** BOEM public data exhibits significant latency — production data typically runs 2–6 months behind operations; Well Activity Reports (BSEE-0133 WARs) are not fully public in real time. Every feature in the Master Feature Table must carry a `data_as_of_date` metadata field recording the latest observation date used in each pipeline run. This is a hard requirement from MVP 1, not a future enhancement.

### 1.3 Core Data Alignment Logic

#### Time-Slicing (Anti-Leakage)

For every row `[Company_ID, Block_ID, Sale_Date]`, all features must be computed using only data with an observation date **strictly before the bid submission deadline** for that sale. The bid submission deadline is the anchor point — not the sale announcement date, not the bid-opening date. This rule is non-negotiable and must be enforced by pipeline design, not by convention.

#### Lookback Windows

Features are calculated over rolling lookback windows relative to each sale's bid submission deadline. Three windows are supported in MVP 1:

| Window | Rationale |
|--------|-----------|
| 6 months | Short-term capital deployment signals; captures momentum from the most recent sale cycle |
| 18 months | Covers the typical lag between a neighboring exploration well result and follow-on bid activity on surrounding blocks |
| 36 months | Full exploration program cycles and company strategic pivots across multiple sale cycles |

#### Spatial Alignment

All data types are joined to GOM OCS protraction block geometries using the BOEM block coordinate system as the canonical spatial reference. Block IDs are the primary spatial key. All distance calculations must use projected coordinates (**UTM Zone 15N**) to ensure accurate metric distances.

#### Class Imbalance

GOM OCS areawide leasing means roughly 14,000 blocks are available per sale, but typically fewer than 500 receive any bid and fewer than 30 attract competing bids (e.g., December 2025 sale). The `did_bid=0` class dominates at approximately **30:1**. The pipeline must support calibrated probability outputs and undersampling strategies rather than simple binary classification. This is a first-class design constraint.

### 1.4 Feature Definitions

#### 1.4.1 Spatial / Geometric Features [MVP 1]

| Feature | Definition | Notes |
|---------|-----------|-------|
| `proximity_owned_km` | Distance (km) from target block to nearest block where Company X holds an active lease | PostGIS `ST_DWithin` |
| `is_adjacent_owned` | Binary flag: 1 if Company X holds an active lease on any block sharing a full edge with the target block | Queen contiguity |
| `active_finds_radius_10km` | Count of blocks within 10 km where a new well was spudded or completed in the lookback window | Configurable radius |
| `active_finds_radius_25km` | Same as above at 25 km radius | |
| `relinquishment_adjacent` | Binary flag: 1 if any company relinquished a lease on an adjacent block within the lookback window | Negative signal |
| `relinquishment_radius_count` | Count of relinquished leases within 25 km in the lookback window | Cold zone indicator |

#### 1.4.2 Company Behavioral / Archetype Features [MVP 1]

| Feature | Definition | Notes |
|---------|-----------|-------|
| `bid_frequency_L6` | Number of blocks bid on by Company X in the 6 months prior to sale | Capital activity proxy |
| `bid_frequency_L18` | Same, 18-month lookback | |
| `win_rate_L18` | Ratio of high bids to total bids submitted by Company X in the past 18 months | Aggressiveness proxy |
| `avg_bid_premium` | Company X's average bid relative to the second-highest bid on contested blocks (post-2010) | Risk appetite indicator |
| `water_depth_preference_mean` | Mean water depth of blocks bid on by Company X in the past 36 months | Play-type proxy |
| `water_depth_preference_std` | Standard deviation of water depth of blocks bid on by Company X in the past 36 months | Specialization proxy |
| `company_archetype` | Categorical label from clustering on bid frequency, win rate, avg bid premium. Labels: `Aggressive Explorer` / `Selective Infiller` / `Dormant` | K-means or rules-based |
| `days_since_last_bid` | Calendar days since Company X last submitted any bid in a GOM sale | Capital cycle signal |
| `relinquishment_rate_L36` | Ratio of blocks relinquished to total blocks ever leased by Company X in the past 36 months | Portfolio quality signal |

#### 1.4.3 Block-Level Contextual Features [MVP 1]

| Feature | Definition | Notes |
|---------|-----------|-------|
| `water_depth_m` | Water depth at block centroid in meters, from BOEM lease data | Static |
| `prior_bid_count` | Number of times this block has received any bid across all post-2010 sales | Competition history |
| `ever_held_lease` | Binary: 1 if this block has ever held an active lease post-2010 | Exploration maturity |
| `days_since_last_relinquishment` | Days since any company relinquished this specific block | Negative geological signal |
| `neighbor_production_boe_L18` | Total production (BOE) from wells on directly adjacent blocks in the past 18 months | Drainage proximity |
| `neighbor_well_spud_L6` | Binary: 1 if any well was spudded on an adjacent block in the past 6 months | Exploration activity signal |
| `oil_price_at_sale_usd` | WTI crude 30-day average price ending on the bid submission deadline | Economic context |
| `royalty_rate_pct` | Applicable royalty rate for this sale from the Final NOS. Varies: 12.5% pre-IRA, 16.67% IRA era, 12.5% OBBBA era | Critical economic normalizer |
| `lease_term_years` | Primary lease term (years) for this block's water depth at time of sale: 5, 7, or 10 years | Depth-tiered |

### 1.5 Output: Master Feature Table

Schema of the output table:

| Column | Type | Description |
|--------|------|-------------|
| `company_id` | STRING | Normalized parent-company identifier (resolved upstream) |
| `block_id` | STRING | BOEM OCS protraction block identifier |
| `sale_date` | DATE | Bid submission deadline for the relevant lease sale |
| `data_as_of_date` | DATE | Latest observation date used in feature calculation — required for latency tracking |
| `did_bid` | INT (0/1) | **TARGET:** 1 if Company X submitted a bid on Block Y at Sale Z |
| `bid_amount_usd_per_acre` | FLOAT (nullable) | Actual bonus bid if `did_bid = 1`; null otherwise |
| `was_high_bid` | INT (0/1, nullable) | 1 if this bid was the high bid for the block |
| `...feature columns...` | FLOAT / INT | All features defined in Section 1.4 |

### 1.6 Technical Stack

- **Python / GeoPandas / Shapely** for all spatial feature calculations
- **PostGIS-enabled PostgreSQL** as the primary spatial database. Core spatial functions: `ST_DWithin`, `ST_Intersects`, `ST_Distance`
- **dbt (data build tool)** for lineage-tracked, version-controlled feature transformation logic
- **BOEM ETL parsers** using fixed-format ASCII record layouts as published by BOEM for each data type
- **Pipeline logging** must record `data_as_of_date` for every input dataset on every run

---

## PRD 2: "The Prospector" Predictive Map Application

> Front-end web application: Bid probability visualization, competitor intelligence, and scenario analysis

### 2.1 Purpose and Primary Users

The Prospector is a web-based GIS application for exploring predicted bid probabilities across the GOM OCS block grid, understanding competitor behavior patterns, and modeling how hypothetical new well activity might shift competitive dynamics in a given area.

**Primary users:** Land and acreage professionals, exploration managers, and business development teams at E&P companies participating in or monitoring GOM OCS lease sales. Key user questions this tool answers:
- "Who is likely to bid against us on Block X in the next sale?"
- "What happened to bid behavior after the last well was drilled near our acreage position?"

Users are comfortable with GIS interfaces and familiar with BOEM block grid conventions.

### 2.2 MVP 1 — Core Map and Competitor Intelligence

> **MVP 1:** Deployable prototype. Historical bid visualization and single-company bid probability prediction across all available GOM blocks.

#### Interactive Map Canvas

- **Block grid layer:** Vector-based GOM OCS protraction block grid rendered as a clickable checkerboard over a satellite or nautical chart basemap.
  - Blocks colored by current lease status: `unleased` (available), `active lease`, `relinquished` (within 36 months), `expired`
  - Relinquished blocks rendered in a distinct cold-zone color — a first-class geological signal in the visual design, not a filter
- **Heatmap overlay:** Continuous probability heatmap showing the predicted likelihood that the selected company bids on each available block in the next sale.
  - Color scale: cool (low probability) → warm (high probability). Configurable threshold for "High Probability Zone" highlight
  - Heatmap must refresh in **under 2 seconds** when a new company is selected

#### Company Intelligence Panel

- **Single-company dropdown:** User selects one company from all post-2010 GOM bidders (normalized to corporate parents).
  - Map updates to show the selected company's current acreage position and historical bid footprint
  - JV bids attributed equally to each listed partner company
- **Company archetype badge:** Displays the selected company's current archetype label (`Aggressive Explorer` / `Selective Infiller` / `Dormant`) derived from behavioral clustering
- **Activity summary:** Key stats — bid frequency (L6, L18), win rate (L18), mean water depth preference, days since last bid

#### Block Detail Sidebar

On block click, display:

- **Block metadata:** Block ID, water depth, current lease status, primary term remaining if currently leased
- **Top-5 predicted bidders** for this block with probability scores
- **Prediction rationale per company**, e.g.:
  - `"Adjacency to owned Block X-123"`
  - `"Active cluster — 3 wells spudded within 25 km (18 months)"`
  - `"Relinquished by Competitor Y — negative result signal"`
- **Historical bid record:** All post-2010 bids on this block — amounts, companies, winners, BOEM acceptance/rejection outcomes
- **Relinquishment history:** Any company that has previously relinquished this specific block, with date and former operator

#### Map Filters

- **Water depth range:** Shelf / Deepwater / Ultra-deepwater presets with custom range input
- **Hot Zones:** Highlight blocks in the top quartile of bid probability summed across all companies
- **Cold Zones:** Highlight blocks with one or more adjacent relinquishments in the past 36 months
- **Company footprint:** Toggle to show only blocks adjacent to or within 25 km of the selected company's current acreage

### 2.3 MVP 2 — Treasure Toggle and Temporal Navigation

> **MVP 2:** Adds hypothetical scenario modeling and time-based playback. Builds on MVP 1 without changes to the core data pipeline architecture.

#### Time-Travel Slider

- Playback bar anchored to historical GOM sale dates (post-2010).
  - **Sliding left:** Shows the actual historical bid footprint as of each past sale — who bid, who won, which blocks were active
  - **Sliding right (future):** Shows the model's predicted bid probabilities for the next scheduled sale(s) under the OBBBA mandated sale schedule
  - Pausing on any past sale date updates the full map — block status, heatmap, and Block Detail Sidebar — to reflect conditions as of that sale

#### Treasure Toggle — Hypothetical Well Activity

Users can drop a hypothetical new well spud onto any available block to model how it would shift bid probabilities in the surrounding area.

> **Design assumption (MVP 2):** A dropped well is treated as a spud event only. No attempt is made to model well results, reservoir quality, or seismic reprocessing implications. The feature models the observable public signal (a well spudded within radius), not the private signal (what the well found). This simplification is intentional and clearly communicated in the UI as: *"Hypothetical Activity — simplified model. Well result and seismic implications not modeled."*

- **Activation:** A "Toggle Well Activity" button enters scenario mode. User clicks any block to place a hypothetical well spud.
- **Model update:** Pipeline re-evaluates `active_finds_radius_10km` and `active_finds_radius_25km` with the hypothetical well included. Heatmap updates within **5 seconds**.
- **Capacity:** Up to 3 simultaneous hypothetical wells. Each is visually distinct on the map (numbered pin icon).
- **Reset:** A "Clear Scenario" button removes all hypothetical wells and restores base probabilities immediately.
- **Scenario labeling:** Page header shows `SCENARIO MODE — HYPOTHETICAL ACTIVITY` while any wells are active. All probability values in scenario mode have a distinct visual treatment to prevent confusion with base model outputs.

#### Regulatory Calendar Feed

A sidebar panel displaying upcoming BOEM lease sale milestones drawn from Federal Register monitoring and the OBBBA 30-sale mandate schedule.

- **Milestones tracked:** Call for Nominations, Draft Notice of Sale, Final Notice of Sale publication, Bid Submission Deadline, Bid Opening, Phase 1 / Phase 2 acceptance results
- **Alert trigger:** When a Final NOS is published, an alert badge appears in the app header. The Final NOS is the binding document specifying royalty rate, minimum bid, and lease terms for the sale.
- **Royalty rate flag:** Current applicable royalty rate (12.5% under OBBBA as of February 2026) displayed prominently on the calendar and in the Block Detail Sidebar. Any regulatory change triggers an alert.
- **Calendar data refresh:** Federal Register parser runs daily. BOEM sale pages checked weekly.

### 2.4 Non-Functional Requirements

| Requirement | Specification |
|-------------|---------------|
| Heatmap update latency | < 2 seconds for company filter toggle and single-variable refresh. Treasure Toggle scenario re-run < 5 seconds. |
| Map performance | Smooth pan and zoom over the full GOM block grid (~6,500 OCS blocks) with heatmap overlay active on standard desktop hardware |
| Data freshness | BOEM public data pipeline runs on a weekly refresh cycle. Federal Register feed parsed daily. |
| Browser support | Chrome 110+, Firefox 115+, Safari 16+. Desktop-only for MVP 1 and 2. |
| Open source license | MIT License. All BOEM source data is US government public domain. No proprietary data included in the repository. |

### 2.5 Success Metrics

| MVP | Metric | Target |
|-----|--------|--------|
| 1 | Bid/No-Bid Recall @ Top-3 | For blocks that received a bid in a held-out sale, the actual bidder appears in the model's top-3 predicted companies >= 55% of the time. Baseline: random selection yields ~15% for a pool of 20 active bidders. |
| 1 | Heatmap update latency | P95 < 2 seconds on company filter toggle |
| 1 | Archetype stability | >= 80% of companies assigned the same archetype label across two consecutive sales when behavior has not materially changed |
| 2 | Treasure Toggle directional accuracy | After placing a hypothetical well on Block X, bid probability increases on >= 70% of blocks that historically received bids within 25 km of an actual well in the validation set |
| 2 | Calendar alert timeliness | Final NOS alert appears in the app within 24 hours of Federal Register publication |

### 2.6 Technical Stack

- **Frontend:** React with MapLibre GL JS for the interactive map canvas. Tailwind CSS for layout.
- **Tile server:** Vector tiles from PostGIS via `pg_tileserv` for the block grid layer. Pre-computed raster tiles for the probability heatmap overlay.
- **Backend API:** FastAPI (Python) serving model inference endpoints. Model artifacts tracked with MLflow or equivalent.
- **Deployment:** Containerized (Docker). Cloud-agnostic. AWS assumed as initial environment (RDS PostgreSQL + PostGIS, ECS for API, S3 for static assets).

---

## Appendix A: Key Risks and Open Questions

| Risk | Severity | Description | Mitigation |
|------|----------|-------------|------------|
| Class imbalance in training data | High | ~14,000 blocks available per sale; ~500 receive bids; ~30 receive competing bids (Dec 2025 sale). The `did_bid=0` class dominates at ~30:1. | Calibrated probability outputs, negative-class undersampling, block-cluster stratification in train/test splits |
| Private seismic information gap | High | The most material input to any company's bid — proprietary seismic interpretation — is unobservable from public data. | Frame product as competitive surveillance and scenario planning, not a bid prediction oracle. Seismic integration is a future milestone. |
| Regulatory non-stationarity | Medium | Royalty rates flipped from 12.5% → 16.67% (IRA, 2022) → 12.5% (OBBBA, 2025). Bid behavior not directly comparable across regimes. | Include `royalty_rate_pct` as an explicit feature. Consider training separate model instances per regulatory regime post-MVP. |
| Company strategy shifts | Medium | M&A activity and energy-transition commitments cause behavioral changes not captured in trailing features. | Recency-weighted features, `days_since_last_bid`. Flag companies with known recent M&A events in the UI. |
| Public data latency | Medium | Production data lags 2–6 months. Well activity reports not fully public in real time. | `data_as_of_date` metadata on all features (MVP 1). Data freshness indicator in UI. |
| BOEM data format heterogeneity | Low–Medium | Fixed-format ASCII files, PDFs, and online query interfaces with inconsistent schemas across sale eras. | Schema-versioned ETL parsers per data type. Post-2010 window limits era-span of format variation. |
| Treasure Toggle model gap | Low | Toggle assumes well activity = increased bid interest, ignoring well result. A dry hole should suppress surrounding bid probability, not increase it. | Clearly labeled "Hypothetical Activity" with simplified model disclaimer. Well result modeling is a future milestone. |

---

## Appendix B: Out of Scope for MVP 1 and MVP 2

The following are explicitly deferred and should not be treated as implied requirements:

- **Infrastructure proximity layer** (tieback potential to existing platforms) — future milestone
- **BOEM FMV bid rejection risk estimator** — future milestone
- **Manual data entry** for operator-supplied well results or prospect locations — future milestone
- **Proprietary seismic data** ingestion, display, or interpretation — future milestone
- **JV partnership graph** and co-bidding network analysis — future milestone
- **Integration with commercial platforms** (S&P Global, Wood Mackenzie, Enverus, Rystad) — potential future partnership/API work
- **Atlantic, Pacific, Alaska OCS, and Cook Inlet regions** — GOM-only for MVP 1 and 2
- **Bid amount optimization** or recommended $/acre calculation
- **Mobile-responsive layout** — desktop-only for MVP 1 and 2
- **Real-time BSEE Well Activity Report ingestion** — WAR data is not fully public; addressed in a future milestone
- **Onshore or state-water acreage** — federal OCS blocks only
