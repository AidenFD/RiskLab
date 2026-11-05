# First demonstration

This is a synthetic educational demonstration, not a historical investment test.
The fixture generator uses PCG64 seed 20260924, a declared fictional weekday
calendar, and 757 price rows / 756 adjacent daily log returns for SYN-A/B/C.
It makes no claim that those dates/returns came from an exchange or vendor.

## 60-90 second overview

1. Launch RiskLab and click Load synthetic demo on Dashboard.
2. Portfolio & Data shows USD cash, fixed shares and the exact final history
   prices. Model & Calibration shows estimated means, covariance, correlation,
   numerical rank, and the absence/presence of tiny numerical corrections.
3. New Simulation: 10,000 paths, 252 future sessions, seed 42, batch 512,
   preview 20, 95% and 99% confidence, zero daily log mean. Run.
4. Risk Results distinguishes terminal loss from maximum drawdown. Explain
   that VaR is a loss threshold and ES averages the declared worst tail.
5. Check Stability. Inspect bootstrap intervals and two separate seeded repeats.
6. Compare drift / volatility. Only the declared mean/covariance changes.
7. Paths & Outcomes shows selected paths and the complete numeric outcome table.
8. Save Run; use Run History to reopen its verified folder after a restart.

On the verified NumPy 2.5.4 Linux environment, the default primary run has
initial equity $41,987.621577104816, mean terminal equity $42,627.320655900134,
95% loss VaR $6,629.99, 95% ES $7,976.79, loss probability 47.76%, and 95th
percentile per-path maximum drawdown about 20.59%. These are **simulated model
results**, not actual SPY returns or forecasts. The exact persisted primary
summary, uncertainty diagnostics and comparison summaries are included in the
completed example. Other compatible environments can generate different draws.

## Other presets

Deterministic constant, deterministic growth, low volatility, high volatility,
perfect positive correlation and all-cash examples are available on Portfolio
& Data. The growth preset selects the estimated/declared mean mode so its
nonzero manual log mean is actually applied. Zero-log-mean mode overrides it
back to zero explicitly. Low/high volatility presets use identical holdings.

The embedded source also includes invalid fixtures. To test them, use Load
scenario JSON, observe a readable error, then reload a valid preset. Never
present a rejected or cancelled operation as a completed simulated result.

## Open an included completed run

Use Run History > Open run folder... and select the hashed child directory of
examples/completed_runs containing COMPLETED and manifest.json. No simulation
is required. Save a new folder after adding diagnostics or comparisons; opening
and inspecting never overwrites the original.
