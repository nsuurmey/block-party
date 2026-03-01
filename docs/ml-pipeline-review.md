# Block-Party MVP 0 — ML Pipeline Review

*Reviewed against code at HEAD (Feb 2026). All findings were verified by executing
the pipeline logic directly against the live data files.*

---

## High-Level Summary

**Strengths**

- Clean, well-documented data-access layer (`boem_loader.py`) with consistent UTM
  reprojection, dual naming-convention support, and sensible type coercions.
- Correct spatial join strategy in Q3 (buffer wells → join centroids) and correct
  adjacency semantics (Rook contiguity with `use_index=False`).
- Thoughtful hypothesis structure: each investigation has an explicit success
  threshold, a contingency plan, and a clear MVP recommendation.
- Cross-validation at the block level confirms Q3's 25 km signal is real
  (Spearman ρ = 0.082, p ≈ 7 × 10⁻¹⁴) and not a statistical artifact.

**Risks**

1. **Silent bug: `TERMED` vs `TERMIN`** — the active-lease filter silently drops
   3,814 terminated leases (about 12 % of the history), causing active lease
   membership to be over-estimated.
2. **Q1 selection bias** — 123 companies that hold adjacent leases but did not bid
   are excluded from the analysis; the reported 11.3× lift is therefore confounded.
3. **Chi-square validity broken** — the (company × block) matrix has 230,162 rows
   but only 28 independent companies; the p-value (1.62 × 10⁻³⁴) is meaningless.
4. **In-sample-only evaluation** — the combined-score notebook fits and evaluates
   on the same 8,294 blocks; no hold-out sale is used (though CV AUC is stable).
5. **Class imbalance unhandled** — 163 positive blocks out of 8,294 (1.97 %);
   the logistic regression has no `class_weight` setting, and Average Precision
   (0.048 in-sample, 0.055 CV) is only 2.5–3× above baseline (0.020).

---

## 1. Data & Preprocessing

### Data sources

| File | Rows | Notes |
|---|---|---|
| `master_lease_sales.csv` | 222 | Only Sale 247 present |
| `cleaned_lease_history.csv` | 31,841 | Parsed `Col_5` → `Lease_Status` + `Status_Date` |
| `lseowndelimit.txt` | 239,901 | 94 % of records are terminated (`Asgn_Status=T`) |
| `blocks.shp` | 29,102 | Full GOM OCS block set, projected to UTM 15N |
| `mv_boreholes_all.txt` | ~all GOM wells | 1,022 missing `Spud_Date`; 1,199 future-dated |

### Bug: `TERMED` vs `TERMIN` (HIGH)

In every notebook the terminal-status set is:

```python
# notebooks 01, 02, 05 — all three instances
terminal_statuses = ["EXPIR", "RELINQ", "TERMED", "CANCEL"]
```

The actual data contains `"TERMIN"`, not `"TERMED"`:

```
Status values in lh:
  EXPIR  12322  ← caught
  RELINQ 11913  ← caught
  TERMIN  3814  ← missed
  REJECT  1501
  CANCEL    26  ← caught
```

Because `"TERMED"` never matches, 3,814 leases that ended after the sale date
(and thus were *active* at sale time) are silently treated as non-active.
The fix is a one-line change in each notebook and in `boem_loader.py` where the
status set is documented:

```python
# Fix
terminal_statuses = ["EXPIR", "RELINQ", "TERMIN", "CANCEL"]
```

### Silent join loss: 31 % of lease-history records have no owner (HIGH)

The `Lease_G` join reconstructs the G-prefix from the 7-digit padded lease number:

```python
active_leases["Lease_G"] = "G" + active_leases["Lease_Number"].str.lstrip("0")
```

Of 31,841 lease-history records, only 69 % match a row in `lseowndelimit.txt`.
Of the 4,706 leases deemed active at sale time, 712 (15 %) cannot be assigned
an owner and are silently dropped from the adjacency analysis.  This is partly
expected (old pre-G-prefix leases), but the drop rate should be logged and
audited, especially because the unmatched leases may be concentrated in specific
planning areas and introduce geographic bias.

**Recommendation:** Log and inspect unmatched leases by planning area; add an
assertion that the match rate for recent leases (Status_Date after 2000) is above
a threshold (e.g., 90 %).

### Missing `Col_1` / `Col_6` column documentation (MEDIUM)

`load_lease_history()` loads two columns whose meaning is explicitly marked TBD:

```python
df["Col_1"] = pd.to_numeric(df["Col_1"], errors="coerce")  # docstring: "meaning TBD"
df["Col_6"] = pd.to_numeric(df["Col_6"], errors="coerce")  # docstring: "meaning TBD"
```

`Col_6` has range 1–3,830 with mean ~1,250, consistent with block acreage or
water depth.  Leaving these unnamed means potentially useful features are ignored.

### Water depth proxy from boreholes (MEDIUM)

`02_relinquishment_signal.ipynb` estimates water depth per block as the median
borehole `Water_Depth` grouped by `(Area_Code, Block_Number)`.  This proxy fails
for the ~59 % of blocks in the OCS that have never been drilled, producing `NaN`
for those rows.  The blocks shapefile (`WATER_DEPT` or equivalent) is the correct
authoritative source and should be preferred.

### Future-dated wells included in lookback windows (MEDIUM)

1,199 borehole records have `Spud_Date` after the sale date (2017-03-22).
Because the well filter uses `wells["Spud_Date"] <= SALE_DATE`, these are excluded
in Q3 — which is correct.  However, the 1,022 records with `Spud_Date = NaT` are
also silently excluded.  If `NaT` is a parsing artifact rather than a true unknown
date, those wells could be legitimate signal.  Add a diagnostic:

```python
print(f"Wells excluded due to NaT Spud_Date: {wells['Spud_Date'].isna().sum()}")
```

---

## 2. Features & Target

### Target definition

`did_bid` is defined at the **block** level (any company bid → True) in Q2/Q3/Q5,
and at the **(company, block)** level in Q1.  Both definitions are intentional and
appropriate for their respective questions.  No leakage is present in the target.

### Active-lease feature reconstruction (Q1, Q5) — conceptually sound but fragile

The logic to infer "was this lease active at sale time?" from the current status
and `Status_Date` is correct in principle: a lease recorded as `RELINQ` with
`Status_Date > SALE_DATE` was indeed active on sale day.  Two failure modes:

1. `Status_Date` is `NaT` for 1,358 rows (4.3 %) — these are dropped as
   *inactive*, possibly incorrectly.
2. The `TERMIN` bug above causes all terminated leases to be misclassified as
   non-active regardless of date (see Section 1).

### 10 km / 6-month well signal is non-monotonic (MEDIUM)

Empirical bin rates for `10km_6mo`:

| Well count bin | Bid rate |
|---|---|
| 0 wells | 1.953 % |
| 1 well  | 2.410 % |
| 2+ wells| 1.887 % |

The "2+ wells" bin is *lower* than "1 well", contradicting the monotonic
hypothesis.  Spearman ρ = 0.004, p = 0.74 — no signal.  The 25 km window is
required for the signal to appear.  The combined-score notebook hard-codes
`WELL_RADIUS_KM = 25` and `WELL_WINDOW_MO = 6` without linking to Q3's best-
combination output; this should be an explicit hand-off.

### Feature correlation and scale

Pearson correlation between `n_adj_companies` and `n_wells_nearby` should be
checked in production (not done in the notebooks).  The standardized logistic
regression coefficient for well activity (0.086) is an order of magnitude smaller
than the adjacency coefficient (0.651), suggesting adjacency dominates almost
entirely and the well signal adds little marginal lift.

---

## 3. Modeling & Evaluation

### Q1: Chi-square test is statistically invalid (HIGH)

The (company × block) analysis matrix has 230,162 rows, but observations are
clustered by company: each of the 28 companies contributes 8,294 rows.  The
chi-square test assumes row independence.  The effective sample size is ~28, not
230,162, and the reported p-value (1.62 × 10⁻³⁴) is wildly over-stated.

Additionally, one expected cell count (adjacent ∩ bid) is **2.26**, below the
minimum of 5 required for chi-square validity:

```
Expected counts:
[[225,276   107]
 [  4,777     2]]   ← bottom-right = 2.26 (invalid)
```

**Fix:** Replace with a **permutation test** that shuffles the `adjacent` label
within each company, preserving the within-company structure:

```python
import numpy as np

rng = np.random.default_rng(42)
observed_lift = rate_adj / rate_non
perm_lifts = []
for _ in range(10_000):
    shuffled = matrix.copy()
    shuffled["adjacent"] = rng.permutation(shuffled["adjacent"].values)
    r_adj = shuffled.loc[shuffled["adjacent"], "did_bid"].mean()
    r_non = shuffled.loc[~shuffled["adjacent"], "did_bid"].mean()
    perm_lifts.append(r_adj / r_non if r_non > 0 else np.nan)
p_perm = np.nanmean(np.array(perm_lifts) >= observed_lift)
print(f"Permutation p-value: {p_perm:.4f}")
```

### Q1: Selection bias — only bidding companies included (HIGH)

```python
bid_companies = sales["Company_Number"].unique()   # 28 companies
```

Of the 150 companies with active leases in the sale's protraction areas, **123
did not place any bid**.  Because the analysis universe is restricted to
`bid_companies`, the denominator for "adjacent companies that didn't bid on a
given block" only counts bidding companies.  Companies that held adjacent leases
and chose to abstain entirely are excluded, which inflates the apparent lift.

The reported 11.3× lift should be treated as an *upper bound*, not a true signal
estimate.  The correct analysis is one of:

- Include all companies with an active GOM lease (wider universe).
- Frame as a conditional question: "given a company bids somewhere in the sale,
  does adjacency predict *which* blocks they choose?"  This is still useful but
  must be stated explicitly.

### Q5: In-sample evaluation (HIGH)

```python
model.fit(X_scaled, y)
universe["score"] = model.predict_proba(X_scaled)[:, 1]   # training data re-used
auc = roc_auc_score(y, universe["score"])                  # in-sample AUC
```

Running 5-fold stratified CV against the actual data confirms that in this case
the in-sample and CV metrics are nearly identical (AUC 0.765 vs 0.765 ± 0.053),
but this must be shown explicitly, and Average Precision diverges (in-sample
0.048 vs CV 0.055) due to class imbalance.  Add CV to the notebook:

```python
from sklearn.model_selection import cross_val_score, StratifiedKFold

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_aucs = cross_val_score(model, X_scaled, y, cv=cv, scoring="roc_auc")
cv_aps  = cross_val_score(model, X_scaled, y, cv=cv, scoring="average_precision")
print(f"CV AUC: {cv_aucs.mean():.3f} ± {cv_aucs.std():.3f}")
print(f"CV AP:  {cv_aps.mean():.3f} ± {cv_aps.std():.3f}")
```

**The real held-out test must be a separate sale** (Sales 257, 261, or Dec 2025),
not a CV fold within Sale 247.

### Class imbalance unhandled (MEDIUM)

163 positives out of 8,294 blocks (1.97 %).  Logistic regression without
`class_weight='balanced'` will under-predict the minority class.  Observed
precision at top-N from the live run:

| Top-N | Precision | Recall |
|---|---|---|
| 50  | 4.0 % | 1.2 % |
| 100 | 8.0 % | 4.9 % |
| 200 | 7.5 % | 9.2 % |

Baseline precision is 1.97 %.  The model achieves 3–4× lift at top-100/200,
which is useful for a UI rank-list but falls well short of the implied promise
of the 11× adjacency signal.  Add `class_weight='balanced'` and compare:

```python
model = LogisticRegression(random_state=42, max_iter=1000, class_weight="balanced")
```

### Split strategy (MEDIUM)

All four investigations use a single sale (Sale 247, March 2017) both to derive
signals and to evaluate them.  There is no temporal hold-out.  The PRD identifies
Sales 257 and 261 as the intended training set and Dec 2025 as validation; the
notebooks should be updated to:

1. Derive features from Sale 247 (or 257/261).
2. Evaluate on a strictly later sale.

For Q4 (archetype stability), the comparison between Sales 257 and 261 is the
right approach — but that notebook is absent from the repo (only notebooks 00–03
and 05 exist; notebook 04 is missing).

### Metrics

ROC-AUC is appropriate for ranking but misleading given the severe imbalance.
**Average Precision (area under precision-recall curve)** is already computed and
is the better primary metric.  Add a calibration plot (reliability diagram) to
verify that predicted scores correspond to actual bid probabilities.

---

## 4. Reproducibility & Robustness

### Missing random seeds for NumPy (MEDIUM)

Scikit-learn operations use `random_state=42`, but there is no global NumPy seed
(`np.random.seed` or `np.random.default_rng`).  Any stochastic operation
outside sklearn (e.g., a future permutation test) will be non-reproducible.

```python
# Add at the top of each notebook, after imports
rng = np.random.default_rng(42)
```

### No dependency locking (MEDIUM)

`requirements.txt` specifies only lower bounds (`pandas>=2.0`, etc.).  A
`pip freeze > requirements-lock.txt` or a `conda` environment file should be
committed so the environment can be reproduced exactly.

### No data validation or schema checks (MEDIUM)

None of the notebooks verify that the loaded DataFrames have the expected shape,
column names, or value ranges.  A silent schema change in a BOEM data update
would produce wrong results without any error.  Minimal checks to add:

```python
assert set(["Lease_Number","Lease_Status","Status_Date"]).issubset(lh.columns), \
    "lease_history schema mismatch"
assert lh["Lease_Status"].notna().mean() > 0.95, \
    f"Too many null lease statuses: {lh['Lease_Status'].isna().mean():.1%}"
assert universe["did_bid"].sum() > 0, "No bids found — check Protraction_ID join"
```

### Notebook 04 (company archetypes) is absent (LOW)

The PRD lists four investigation notebooks (01–04) plus the combined score (05).
Notebook 04 — the company archetype stability analysis — does not exist in the
repo.  This means Q4 of the MVP 0 validation is unaddressed.

### Disconnected adjacency graph (LOW)

`libpysal` emits a warning during `Rook.from_dataframe`:

```
UserWarning: The weights matrix is not fully connected:
 There are 2 disconnected components.
```

This is expected for a universe that spans multiple non-contiguous planning
areas (e.g., a block in the eastern GOM isolated from the western cluster).
The warning should be suppressed after confirmation and documented, or the
universe should be filtered to a single connected planning area when running Q1.

---

## 5. Code Quality

### Duplicated active-lease logic (MEDIUM)

The same ~15-line block for reconstructing active leases at sale time appears
verbatim in three places: `01_adjacency_signal.ipynb`, `05_combined_score.ipynb`,
and in the description of `02_relinquishment_signal.ipynb`.  It should be
extracted into `boem_loader.py`:

```python
def active_leases_at(
    lh: pd.DataFrame,
    lo: pd.DataFrame,
    as_of: pd.Timestamp,
    aliquot: str = "1",
) -> pd.DataFrame:
    """Return active (Lease_Number, Company_Number) pairs as of *as_of* date."""
    active_statuses = ["PRIMRY", "PROD", "SOO", "SOP", "UNIT", "DSO", "OPERNS"]
    terminal_statuses = ["EXPIR", "RELINQ", "TERMIN", "CANCEL"]   # note: TERMIN not TERMED
    mask = (
        lh["Lease_Status"].isin(active_statuses)
        | (lh["Lease_Status"].isin(terminal_statuses) & (lh["Status_Date"] > as_of))
    )
    active = lh[mask].copy()
    active["Lease_G"] = "G" + active["Lease_Number"].str.lstrip("0")
    owners = (
        lo[lo["Asgn_Eff_Date"] <= as_of]
        .query(f"Owner_Aliquot == '{aliquot}'")
        .sort_values("Asgn_Eff_Date")
        .drop_duplicates("Lease_Number", keep="last")
    )
    return active.merge(
        owners[["Lease_Number", "Company_Number"]],
        left_on="Lease_G", right_on="Lease_Number",
        how="inner", suffixes=("_lh", "_lo"),
    )
```

### `iterrows()` in hot path (LOW)

Several notebooks build the `did_bid` flag with an `iterrows()` loop over the
entire universe (8,294 iterations per notebook).  Replace with a vectorized merge:

```python
# Before (slow)
universe["did_bid"] = [
    (r["Protraction_ID"], r["Block_Number"]) in bid_pairs
    for _, r in universe.iterrows()
]

# After (fast)
sales_flag = sales[["Protraction_ID", "Block_Number"]].drop_duplicates()
sales_flag["did_bid"] = True
universe = universe.merge(sales_flag, on=["Protraction_ID", "Block_Number"], how="left")
universe["did_bid"] = universe["did_bid"].fillna(False)
```

### Rook adjacency recomputed in every notebook (LOW)

The 8,294-block Rook weight matrix takes measurable time (noted with `%%time` in
the notebooks) and is rebuilt from scratch in notebooks 01, 02, and 05.  Cache
it as a serialized file (e.g., `weights_sale247.gal`) and load it in subsequent
notebooks:

```python
from libpysal.weights import Rook
import libpysal

cache = "weights_sale247.gal"
if os.path.exists(cache):
    w = libpysal.io.open(cache).read()
else:
    w = Rook.from_dataframe(universe, use_index=False)
    libpysal.io.open(cache, "w").write(w)
```

### Magic numbers (LOW)

Several hard-coded values lack explanation:

| Location | Value | Issue |
|---|---|---|
| `03_well_activity_signal.ipynb` cell 11 | `bins=[-1, 0, 1, 999]` | Use `np.inf` not 999 |
| `05_combined_score.ipynb` cell 24 | `TOP_N = 200` | Unexplained; should be a config param |
| `05_combined_score.ipynb` cell 10 | `WELL_RADIUS_KM = 25` | Should be drawn from Q3 result |
| `02_relinquishment_signal.ipynb` cell 15 | `99999` in depth bins | Use `np.inf` |

---

## Prioritized Actions

### High priority (correctness / methodology)

1. **Fix `TERMED` → `TERMIN`** in every notebook and in `boem_loader.py`
   documentation.  3,814 incorrectly classified leases affect all signal
   estimates.

2. **Replace chi-square with a permutation test in Q1** that respects the
   company-clustering structure.  The current p-value is statistically meaningless.

3. **Acknowledge and scope Q1 selection bias** — explicitly state that the
   analysis is conditional on bidding, or expand the company universe to all
   GOM-active operators.

4. **Add explicit cross-validation to notebook 05** and hold out at least one
   full sale (Sale 257 or 261) as an out-of-sample test.

5. **Add `class_weight='balanced'` to the logistic regression** and report
   calibrated probabilities alongside AUC/AP.

### Medium priority (robustness / reproducibility)

6. **Log unmatched leases** in the `Lease_G` → `lo["Lease_Number"]` join and
   assert that the match rate for recent leases (post-2000) exceeds 90 %.

7. **Add schema assertions** at the top of each notebook (column presence, row
   counts, null rates, bid count > 0).

8. **Lock dependency versions** with `pip freeze > requirements-lock.txt` or a
   `conda` environment file.

9. **Use the blocks shapefile's native water-depth attribute** in Q2 instead of
   deriving it from borehole medians (which covers only ~41 % of blocks).

10. **Create notebook 04** for company archetype stability (Q4), which is
    specified in the PRD and MVP 0 spec but absent from the repo.

### Low priority (ergonomics / maintainability)

11. **Extract `active_leases_at(lh, lo, as_of)`** into `boem_loader.py` to
    eliminate the three duplicated reconstruction blocks (and the `TERMIN` bug
    in one place instead of three).

12. **Replace `iterrows()` membership tests** with vectorized merge + `fillna`.

13. **Cache the Rook weight matrix** across notebooks.

14. **Replace magic numbers** `999` and `99999` in `pd.cut` bins with `np.inf`
    and document `TOP_N` and `WELL_RADIUS_KM` as explicit config variables.

15. **Suppress the expected libpysal disconnected-graph warning** after
    confirming it is benign, and add a comment explaining why.
