# Block-Party: Data Validation Study for BOEM Lease Bidding Intelligence

Block-Party is a data validation study designed to test whether spatial and behavioral signals in public Bureau of Energy Management (BOEM) datasets can predict future company bidding behavior on Gulf of Mexico (GOM) OCS leases.

## Overview

This MVP 0 phase focuses on validating load-bearing assumptions before committing engineering resources to future product development. The study investigates four core questions to determine whether signals in BOEM data can reliably indicate bidding interest.

**Duration:** 2–3 weeks | **Tooling:** Jupyter notebooks, GeoPandas, pandas, matplotlib/folium

---

## MVP 0: Core Questions & Goals

### 1. **Adjacency Signal (Q1)**
Does holding an active lease on adjacent blocks predict higher bid rates?
**Target:** 3x+ lift at p < 0.05

### 2. **Relinquishment Signal (Q2)**
Do blocks near recently relinquished leases receive fewer bids as a negative geological indicator?

### 3. **Well Activity Signal (Q3)**
Does recent well activity within a 10–25 km radius correlate with increased bidding?
*This grounds the proposed "Treasure Toggle" feature.*

### 4. **Archetype Stability (Q4)**
Are company behavioral clusters (Aggressive Explorer, Selective Infiller, Dormant) consistent across multiple sales?
**Target:** ≥80% agreement

---

## Data Sources

All data comes freely from BOEM (no licenses, no vendors):

- Bid files (post-2010 sales)
- Lease and well borehole data
- Relinquishment records
- OCS block shapefiles

**Test Sales:**
- Sales 257 (Aug 2023) and 261 (Mar 2024) for training
- December 2025 OBBBA sale as held-out validation

---

## MVP 0 Deliverables

1. **Four self-contained Jupyter notebooks** (one per investigation with reproducibility instructions)
2. **Single static map** showing December 2025 sale with bids, predicted high-interest zones, cold zones, and recent well activity
3. **Findings document** (3–5 pages) with data quality notes, results, and go/no-go/modify recommendation

---

## Getting Started

### Prerequisites

- Python 3.8+
- Jupyter Notebook or JupyterLab

### Installation

1. Clone this repository:
```bash
git clone https://github.com/nsuurmey/block-party.git
cd block-party
```

2. Install dependencies:
```bash
pip install -r mvp0/requirements.txt
```

### Running MVP 0 Analysis

1. **Start Jupyter Notebook:**
```bash
jupyter notebook
```

2. **Navigate to the notebooks directory:**
```
mvp0/notebooks/
```

3. **Run notebooks in order:**
   - `00_data_loading.ipynb` - Load and prepare BOEM data
   - `01_adjacency_signal.ipynb` - Test adjacency signal (Q1)
   - `02_relinquishment_signal.ipynb` - Test relinquishment signal (Q2)
   - `03_well_activity_signal.ipynb` - Test well activity signal (Q3)
   - `05_combined_score.ipynb` - Test archetype stability (Q4) and generate visualizations

4. **Each notebook includes:**
   - Full reproducibility instructions
   - Data loading and preprocessing
   - Statistical analysis
   - Visualization outputs

### Required Data

BOEM data files should be placed in the `data/` directory. The `mvp0/boem_loader.py` module handles data loading and can be imported in notebooks.

---

## Success Criteria

MVP 0 succeeds by providing a definitive, evidence-based decision on whether to proceed with full MVP 1 development—even if that decision is "no." Results are inconclusive only if we cannot establish statistical significance on the core assumptions.

---

## Documentation

- `docs/block-party-MVP0.md` - Detailed MVP 0 specification
- `docs/PRD-MVP1-MVP2.md` - Future product roadmap (MVP 1 & 2)
- `docs/GOM OCS Lease Bidding Intelligence Report.md` - Background research

---

## License

See LICENSE file for details.
