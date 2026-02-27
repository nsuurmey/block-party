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

## Running in Google Colab

You can run the Block-Party notebooks in Google Colab without any local setup. Colab provides free GPU/CPU compute and a pre-installed Python environment.

### Quick Start

Open any notebook directly in Colab using these links:

| Notebook | Open in Colab |
|----------|--------------|
| `00_data_loading.ipynb` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/nsuurmey/block-party/blob/main/mvp0/notebooks/00_data_loading.ipynb) |
| `01_adjacency_signal.ipynb` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/nsuurmey/block-party/blob/main/mvp0/notebooks/01_adjacency_signal.ipynb) |
| `02_relinquishment_signal.ipynb` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/nsuurmey/block-party/blob/main/mvp0/notebooks/02_relinquishment_signal.ipynb) |
| `03_well_activity_signal.ipynb` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/nsuurmey/block-party/blob/main/mvp0/notebooks/03_well_activity_signal.ipynb) |
| `05_combined_score.ipynb` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/nsuurmey/block-party/blob/main/mvp0/notebooks/05_combined_score.ipynb) |

### Step-by-Step Setup

Once a notebook is open in Colab, add a setup cell at the top and run it before anything else:

**Step 1 — Clone the repo and install dependencies:**
```python
# Clone the repository
!git clone https://github.com/nsuurmey/block-party.git

# Install dependencies
!pip install -r block-party/mvp0/requirements.txt

# Add the repo to the Python path so boem_loader.py can be imported
import sys
sys.path.insert(0, 'block-party/mvp0')
sys.path.insert(0, 'block-party')
```

**Step 2 — Make the `data/` directory available:**

Colab sessions are ephemeral, so you need to bring your BOEM data files into the session each time. Choose one of these approaches:

**Option A: Upload from your computer (simplest, small files)**
```python
from google.colab import files

# Upload one or more files — a file picker dialog will appear
uploaded = files.upload()

# Move uploaded files to the correct data subdirectory, e.g.:
import shutil, os
os.makedirs('block-party/data/lease-sales', exist_ok=True)
for fname in uploaded:
    shutil.move(fname, f'block-party/data/lease-sales/{fname}')
```

**Option B: Mount Google Drive (recommended for repeated use)**
```python
from google.colab import drive
drive.mount('/content/drive')

# Symlink your Drive data folder into the repo's data directory
import os
os.symlink(
    '/content/drive/MyDrive/block-party-data',  # adjust to your Drive path
    'block-party/data'
)
```
> Store your BOEM files in a `block-party-data/` folder in Google Drive, organized as `lease-sales/`, `shapefiles/`, and `wells/` subdirectories. The symlink makes them appear at the path the notebooks expect.

**Option C: Download BOEM files directly (no local files needed)**
```python
import os

# Example: download a specific sale's bid file directly from BOEM
os.makedirs('block-party/data/lease-sales/sale_257', exist_ok=True)
!wget -P block-party/data/lease-sales/sale_257 \
    "https://www.data.boem.gov/Leasing/Files/LeaseAucResults/Sale257Bids.zip"

# Unzip after downloading
!unzip -o block-party/data/lease-sales/sale_257/Sale257Bids.zip \
    -d block-party/data/lease-sales/sale_257/
```
> Check [data.boem.gov](https://www.data.boem.gov/Main/Leasing.aspx) for current download URLs.

**Step 3 — Update notebook paths (if needed):**

The notebooks reference data with relative paths from the repo root. If Colab's working directory is `/content`, update any path variables in the notebook to include the `block-party/` prefix:

```python
import os
os.chdir('block-party')  # run this once to make all relative paths work
```

### Notes

- **Runtime resets:** Colab runtimes disconnect after ~90 minutes of inactivity. Re-run the setup cell after reconnecting. If using Google Drive (Option B), your data persists automatically.
- **Memory:** The default Colab CPU runtime (~12 GB RAM) is sufficient for MVP 0 notebooks. Upgrade to a High-RAM runtime under *Runtime → Change runtime type* if you encounter memory errors on large shapefiles.
- **Folium maps:** Interactive Folium maps render inline in Colab without any extra configuration.

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
