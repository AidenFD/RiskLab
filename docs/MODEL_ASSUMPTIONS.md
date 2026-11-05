# Model assumptions and limitations

RiskLab v1 uses independent daily Gaussian log increments with within-session
asset correlation. S_next = S*exp(g), with g~Normal(m,Sigma). m is mean log
return, so an additional subtraction of half the variance would be wrong.
For one asset, expected future price is S0*exp(T*(m+variance/2)). Thus a zero
log mean does not imply zero expected arithmetic return.

Calibration uses complete adjacent declared price sessions, logarithmic price
changes and sample covariance normalized by n-1. Drift is deliberately a visible
choice. Historical estimates can be noisy and are not forecasts.

Covariance must be finite, square, symmetric within a declared scale-relative
tolerance, and positive semidefinite. Tolerances are max(float64.tiny,
1e-10*matrix/eigenvalue scale), in daily-variance units. Materially indefinite
matrices, even at tiny daily scales, are rejected. Only negative eigenvalues
within tolerance may be clipped. The original/effective covariance,
eigenvalues, tolerance, correction and numerical rank are recorded. No hidden
jitter or shrinkage is applied. Singular PSD models use an eigenfactor; zero
variance gives undefined correlation, displayed as N/A.

Holdings and zero-interest USD cash are fixed. V1 excludes dividends, splits,
options, leverage, shorts, FX, rebalancing, costs and execution. Total-return
indices require a different future valuation contract. Underlying Gaussian
paths omit jumps, fat-tail dynamics, volatility clustering and serial dependence.
Dependence and covariance are constant over the simulation horizon.

Simulated extremes are observations, not guaranteed bounds. Numerical overflow
or nonfinite/nonpositive prices terminate the run rather than clipping or
selectively discarding paths. All primary outcomes enter summaries; the display
subset is never used as a substitute.

Monte Carlo precision, uncertain calibration, and model misspecification are
different limitations. The app measures the first under the declared model.
It does not certify a regulatory model, forecast future losses, or recommend
an investment or trading strategy.
