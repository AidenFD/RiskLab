# Risk measures and sampling uncertainty

For initial equity V0 and terminal equity VN, dollar loss is L = V0 - VN.
Gains are negative losses. Reported VaR/ES are not floored at zero.

With N ascending sorted losses and confidence alpha:

- k = ceil(alpha*N), one-based; VaR is loss[k-1] in Python indexing.
- q = ceil((1-alpha)*N); ES is the mean of the q largest losses.
- Probability of loss uses the strict condition VN < V0.
- Its plug-in Monte Carlo SE is sqrt(p*(1-p)/N).
- A 95% Wilson interval is also shown, including when p is 0 or 1. A zero
  plug-in SE at those extremes does not establish certainty.

Decimal confidence arithmetic avoids off-by-one tails: N=10000, alpha=.99
has exactly 100 tail paths. Every selected published tail needs at least 100
paths. Tiny fixtures may exercise the low-level summarizer without qualifying
as production estimates. Rank/tie conventions are exported in summary.json.

For V0=1000 and terminal [800,900,1000,1100,1200], sorted losses are
[-200,-100,0,100,200]. At .80 confidence, VaR=100, ES=200 and loss probability=.40.

Maximum drawdown is computed within each path, including V0, from its own
running peak. The path [1000,1200,900,1100] has 25% maximum drawdown while ending
with a 10% gain. Drawdown quantiles across paths use NumPy's declared linear
empirical quantile. Terminal loss and path drawdown are separate statistics.

## Tail diagnostics

Check Stability resamples the entire primary terminal loss sample 300 times
with a separately derived RNG. It reports 95% percentile bootstrap intervals
for VaR/ES, using linear interval quantiles. Resamples are processed one at a
time; only statistics are retained. This is empirical finite-sample sampling
analysis, not a distribution-free guarantee or parameter/model-risk interval.

Two additional independent PCG64 streams simulate the same frozen portfolio,
model, horizon, path count, batching and confidence settings. Their summaries
and stream derivations remain separate; they do not increase primary N or
replace its statistics. If cancelled, diagnostics are incomplete and the old
result revision remains unchanged.

For each VaR/ES, the heuristic flags the range across primary plus two repeats
when it exceeds `max(2*bootstrap_95_interval_width, .01*initial_equity)`.
The dollar floor avoids division by a near-zero or negative VaR. The decision
and thresholds are exported. NO INSTABILITY FLAG means this check found none;
it is not proof of stable real-world risk. NOT ASSESSED is shown until run.
The primary summary retains its original baseline status; current diagnostic
status and all diagnostic evidence live in diagnostics.json.

## Scenario comparison

Four paired runs compare zero log mean, estimated/declared log mean,
zero-mean half-volatility, and zero-mean double-volatility. Volatility scales
by 0.5/2, so covariance scales by 0.25/4. Holdings, initial prices/cash, horizon,
primary counts, definitions and seed remain the same. Mean/covariance changes
are explicit. The common seed aids controlled comparisons; these are not the
independent replicate simulations used for stability assessment.
