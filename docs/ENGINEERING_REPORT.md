# RiskLab v1.0.0 engineering release report

Aiden Federico-Dyer | QuantLab / Risk | November 5, 2026

## Release outcome

RiskLab v1.0.0 is a complete source release of an independent PySide6 desktop
risk research application. The numerical, diagnostics, comparison, saved-run,
export and nine-view desktop workflows are implemented and tested on the
available Linux host. It is no longer the initial development checkpoint.
The source package contains no Windows executable. Native Windows build,
runtime and high-DPI checks remain UNVERIFIED; target build scripts are included.

## Design authority and implementation

The supplied PDF was byte-identical to the original design, SHA-256
fad8e491ef31de48dad100751fe0939d03a1858dc6bfaba86ef4c3277aaf390c.
It and the master prompt are preserved in docs/source. The five engine milestones
are implemented: fixed-path valuation/risk, one-asset increments, correlated
multi-asset generation, historical validation/estimation, and bounded batching.
Desktop and release stages add the nine integrated views, worker ownership,
uncertainty diagnostics, comparisons, persistence, documentation and packaging.
No market model was silently substituted.

The engine samples independent daily Gaussian log-return vectors with within-
vector covariance. Prices update by multiplying exp(log increment); no extra
half-variance term is subtracted. Fixed fractional shares and zero-interest
USD cash are valued without display rounding. PSD eigenfactorization handles
singular and zero covariance, rejecting materially indefinite inputs. Canonical
symbol ordering preserves consistent seeded asset permutations.

Input and calibration boundaries, units, sample denominator, numerical tolerances,
tail definitions, default drift and resource caps are in DECISIONS.md and
DATA_FORMAT.md. Historical calibration requires declared complete sessions;
source kinds remain explicit. BacktestLab/OrderBookLab were product references,
not runtime dependencies. The repository structure is in REPOSITORY_TREE.md.

## Actual test results

- Total: **102 passed**; 0 failures,
  0 errors and 0 skips.
- Exact source fixtures: VaR $100, ES $200, loss probability 40% at 80% confidence
  for the five terminal values; 25% maximum drawdown for [1000,1200,900,1100].
- Independent scalar comparison at batch sizes 1, 257 and 512; no production
  valuation/drawdown helpers used to establish reference outcomes.
- Controlled large-sample lognormal moment and cross-asset covariance/mean tests
  use tolerances tied to 5.5 sampling standard errors, rather than exact equality.
- Validation covers duplicates, nonfinite values, units, unsupported instruments,
  complete sessions, tail counts, scalar types, covariance and schema versions.
- Persistence tests include corrupted/rehashed-false summaries, writable fsync
  handles, failures/cancel cleanup, moved folders and immutable result revisions.
- Reopen tests explicitly fail if either simulation or fitting is called.
- Real Qt tests cover input correction, navigation, worker duplication/cancellation,
  event-loop responsiveness, complete outcome models, numeric sort/copy, stability,
  comparisons, history, saving and reopening in a fresh window.

The exact suite output is in test_results.xml. Statistical evidence supports
implementation checks under the chosen model; it does not establish model realism.

## Actual performance and host

| Measurement | Result |
| --- | --- |
| Headless model | 10,000 paths / 252 steps / 10 assets |
| Primary elapsed wall time | 0.589636 seconds |
| Process peak RSS | 32.031 MiB |
| Batch / preview / seed | 512 / 20 / 42 |
| Host | AMD EPYC 9V74 80-Core Processor; 9 visible CPUs; Linux |
| Python / NumPy | 3.12.14 / 2.5.4 |
| Thread setting | OPENBLAS_NUM_THREADS=1 |
| Source full Qt workflow | 5.198 seconds; 140.4 MiB peak |
| Packaged full Qt workflow | 4.694 seconds; 143.7 MiB peak |

The headless result includes validation/factorization/simulation/summary but
excludes parsing, diagnostics, publication, GUI and packaging startup. The full
Qt measurements cover the three-asset synthetic demonstration, diagnostics,
comparisons, saving and actual screenshots; they are not the same benchmark.
The design target of 15 seconds / 300 decimal MB for the headless baseline was
met on this host. No result is represented as a measurement of the user's laptop.

## Synthetic demonstration results

The bundled default is synthetic calibration and simulated future paths:
10,000 primary paths, 252 steps, seed 42, batch 512, zero daily log mean.

| Statistic | Actual model output |
| --- | --- |
| Initial equity | $41,987.62 |
| Mean terminal equity | $42,627.32 |
| 95% loss VaR | $6,629.99 |
| 95% expected shortfall | $7,976.79 |
| Probability of loss | 47.76% |
| Probability plug-in MCSE | 0.50% |
| 95th percentile max drawdown | 20.59% |
| Current diagnostic status | NO INSTABILITY FLAG |

These are not historical SPY returns, forecasts or trading profits. Risk summaries
use all primary paths; the chart uses a reproducible selected subset. Diagnostics
use 300 full-sample bootstrap resamples and two independently seeded repeat runs;
no replicate is pooled into the primary count. Paired sensitivity comparisons
use common random seeds and are kept distinct from those independent checks.

## Saved results and desktop evidence

Schema-2 folders include the full primary outcomes, preview paths, normalized
scenario/config, stored calibration, metadata, diagnostics/comparisons, manifest,
checksums and COMPLETED. Staging writes are flushed with writable handles,
verified and atomically renamed. Failed/cancelled pre-commit saves do not publish.
Reopening uses persisted parameters and outcomes without refitting/resampling.

Source and native packaged cold-start and restart/reopen checks passed. Actual
Qt screenshots are in docs/screenshots, with packaged evidence separately in
docs/packaging_smoke. The windows, tables, plots and statistics are real app
output captured with Qt's offscreen plugin. Native display interaction is a
separate unverified platform check.

## Start, build and deliverables

On Windows: extract all source files, run Setup_Windows.cmd once, then
Launch_RiskLab.cmd. Debug launch: `.venv\Scripts\python.exe -m risklab`.
Build: `Build_Windows.cmd`. Expected target artifact on Windows:
`dist\RiskLab\RiskLab.exe`. No Windows executable is included in this source ZIP.

The build script installs verification tools, gates the build on tests, creates
the target package, and runs cold-start/restart smoke checks. A normal manual
Windows launch remains needed to check actual display, dialogs and high DPI.
The verified native Linux executable existed at dist/RiskLab/RiskLab on this host;
it is not distributed as a Windows executable.

Deliverables include source ZIP, this report in Markdown/PDF, actual screenshots,
JUnit/benchmark/smoke evidence, examples including a real completed run, Windows
scripts, pinned requirements, PyInstaller spec and a verified Git history bundle.
Source archives exclude environments, build outputs, caches, ordinary runs and .git.
No remote repository was created or pushed. GITHUB.md supplies restoration steps.

## Limits, deviations and next checks

- Gaussian independent-session returns and constant covariance omit jumps,
  serial dependence and volatility clustering. Monte Carlo precision is not
  parameter-estimation uncertainty or model adequacy.
- No actual corporate-action processing, adjusted/total-return mode, options,
  leverage, shorts, FX, rebalancing, costs, interest, execution or data downloads.
- Source-design open choices were resolved explicitly: zero-log-mean default,
  minimum calibration count, resource caps, scale-relative PSD tolerance,
  Decimal tail indices, independent diagnostic streams and the instability rule.
  These refine operational choices; they do not replace the source model.
- Native Windows build/runtime/high-DPI and native Linux display interaction
  are UNVERIFIED. Next platform step is Build_Windows.cmd and a manual launch.
- V1.1 candidates are model comparisons such as block bootstrap, parameter-risk
  methods, named shocks and properly specified corporate-action/index modes.

## Primary references

- NumPy multivariate sampling: https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.multivariate_normal.html
- NumPy stream compatibility: https://numpy.org/doc/stable/reference/random/compatibility.html
- NumPy covariance: https://numpy.org/doc/stable/reference/generated/numpy.cov.html
- Qt QThread: https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html
- PyInstaller target-platform bundles: https://pyinstaller.org/en/stable/operating-mode.html
