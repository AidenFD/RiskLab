# Architecture

RiskLab is independent of BacktestLab and OrderBookLab. It shares their QuantLab
visual palette and product conventions, with a separate fixed-holdings engine.

| Layer | Responsibilities |
| --- | --- |
| core/inputs.py | Strict JSON/numeric/date/portfolio validation; symbol identities |
| core/calibration.py | Declared complete-session history; daily log means and n-1 covariance |
| core/simulation.py | PSD eigenfactor; canonical symbols; bounded batches; cancellation |
| core/valuation.py | Independent fixed-path valuation and per-path drawdown helpers |
| core/risk.py | Explicit signed-loss, VaR/ES, probability and drawdown conventions |
| core/diagnostics.py | Bootstrap uncertainty and independent seed replicates |
| core/export.py | Integrity/reconciliation checks, staging, publication and reopening |
| services/experiments.py | Frozen scenario/config graph, drift modes and paired comparisons |
| services/runs.py, settings.py | Local history inventory and writable workspace selection |
| ui/workers.py | One admitted QThread job, thread-safe cancellation and progress |
| ui/application.py | Nine connected views; widgets only on the GUI thread |
| ui/widgets/tables.py | Numeric model/proxy sorting and complete lightweight outcome tables |

Validated JSON is copied into an owned graph before work starts. Calibration
runs when the scenario is prepared. Simulations use frozen numerical parameters,
fixed quantities and cash. No model is re-estimated inside a path. Reopen,
diagnostics, and comparisons use the persisted calibration; reopening never
samples or recalibrates. Stored history is still structurally validated.

The worker owns private mutable simulation arrays. Finished outcome arrays are
read-only. The GUI receives owned result objects and never mutates the numerical
arrays. Adding diagnostics/comparisons returns a new result revision; a prior
published folder remains unchanged. Only one background operation is admitted.

Rendering, form editing, preview selection and table sorting do not consume
the simulation RNG. Display paths are captured within the actual primary run.
Progress is emitted at most roughly 12.5 Hz, except phase completion. No numerical
work is skipped by rendering throttling. Cancellation is checked every simulated
step, bootstrap iteration, replicate, and before the publication commit point.

Numerical arrays use float64. Display cents are not fed back into valuation.
Canonical symbol ordering makes consistent column/holding permutations leave
outcomes unchanged under the same environment and random-call contract.
