# Implementation decisions - v1.0.0

The original RiskLab design governs model semantics. BacktestLab/OrderBookLab
were inspected as QuantLab product references and are not runtime dependencies.
The original design PDF was byte-identical to the earlier upload and is preserved.

1. Daily Gaussian LOG returns; no additional half-variance subtraction. Zero log
   mean is the initial UI default; estimated/declared mean is an explicit alternative.
2. Fixed nonnegative fractional shares and zero-interest USD cash; one to ten assets.
   Options, execution, costs, dividends, splits, FX and rebalancing are outside v1.
3. Historical inputs are declared action-free RAW prices with full expected sessions.
   No calendar inference or imputation. Minimum adjacent returns: max(60,10*A).
4. Sample covariance is centered around the sample mean and normalized by n-1,
   even when zero log mean is applied to future increments.
5. PSD/symmetry tolerances are scale-relative: max(float64.tiny, 1e-10*scale).
   Tiny negative eigenvalues may be clipped and recorded; materially invalid
   matrices, including at tiny daily scales, are rejected. Singular PSD uses eigh.
6. Canonical internal symbol order preserves same-environment seeded permutation
   invariance. Original order/mapping and effective covariance are exported.
7. PCG64 uses batch-major/step-major normal draws. Seed AND batch size belong to
   the reproducibility contract. No cross-platform bitwise sampling promise.
8. Defaults: 10,000 paths, 252 steps, seed 42, batch 512, 20 preview paths and
   95%/99% confidence. Caps: 200,000 paths, 252 steps, 10 assets, 4096 batch,
   100 previews, 20,000 price sessions / 8 MB CSV, 16 MB JSON.
9. Preview path IDs are evenly spaced and consume no RNG. Full-path risk uses
   every primary path. Terminal outcomes and maximum drawdowns are retained for all.
10. Decimal tail ranks preserve the design's finite-sample VaR/ES definitions.
    Negative VaR/ES are valid. Normal risk publication requires 100 paths per tail.
11. Probability uncertainty uses plug-in SE and a 95% Wilson interval. Tail
    diagnostics use 300 whole-sample bootstrap resamples plus two separate seeded
    repeats. Heuristic instability rule: range > max(2*bootstrap CI width,1% V0).
12. Sensitivity runs use a common seed, fixed snapshot/horizon and explicit mean/
    covariance scales. They are not independent stability replicates.
13. Stored calibrated parameters are reused by diagnostics, comparison, validation
    and reopening. Reopen does not refit or resimulate. Integrity and reconciliation
    are checked against complete stored outcomes, input shapes/units and CSV/previews.
14. Staging, writable-handle fsync and verified atomic rename publish immutable
    schema-2 folders. Rename is the commit point; failures/cancels before it clean up.
15. One admitted QThread job owns work. Main thread owns widgets. Arrays become
    read-only on completion. Numerical jobs, persistence and history verification
    remain off the GUI thread; lightweight rendering stays on it.
16. Central QSS, readable metric cards, model-based complete outcome tables and
    real offscreen Qt screenshot review provide the QuantLab presentation.
17. Source ZIP and Git bundle are the portable release artifacts. Native Linux
    packaging was verified. Native Windows build/runtime and display/high-DPI
    checks remain unverified; scripts provide the target build and smoke workflow.
