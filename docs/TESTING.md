# Verification

Run `python -m pytest` from the project root after installing
requirements-dev.txt. The committed JUnit file records actual counts, failures,
skips and times. UI tests use real PySide6 widgets through pytest-qt.

| Layer | Evidence |
| --- | --- |
| Exact design fixtures | Five-value VaR/ES/probability, 25% drawdown, deterministic paths, singular covariance |
| Validation | Duplicate JSON keys/symbols, nonfinite inputs, dates/gaps, unsupported basis/instruments, tail count, schema and scalar types |
| Independent reference | A scalar path/valuation/drawdown implementation compared with the vectorized engine at batch sizes 1, 257 and 512 |
| Statistical | Lognormal mean/log mean/variance and generated cross-asset covariance/means within 5.5 declared sampling SE tolerances |
| RNG and state | Nonzero-volatility repeatability, asset permutation, preview independence, read-only outcome arrays |
| Diagnostics | Bootstrap/replicates, separate counts/seeds, injected instability warning, cancellation without mutation |
| Persistence | No sampling/refitting on reopen, relocated folders, payload corruption, rehashed false summary, failed sync, cleanup, immutable revisions |
| Desktop | Navigation, input editing, real workers, double-start rejection, cancellation, responsive event loop, numeric sorting/copy, history, comparisons |
| Packaging | Actual cold-start and restart against the native Linux executable, with real Qt screenshots |

Statistical tolerances are not arbitrary equality assertions: tests relate
sample means/covariances to their expected sampling error. Controlled seeds
reduce fragility, but passing one statistical suite does not establish the
model is appropriate for markets. The reference does not call production
valuation or drawdown helpers for its independent scalar calculations.

The Windows synchronization regression emulates the writable-handle rule on
POSIX and exercises actual os.fsync. This is useful evidence, not native Windows
runtime verification. The full suite contains no intentionally skipped release
checks; unavailable platform checks are documented separately, not passed.

The primary engine benchmark excludes parsing, diagnostics, file publication
and Qt. The source/packaged smoke reports measure a broader actual workflow
and process peak memory. Machine and BLAS/thread settings are recorded. RSS
is not confused with Python-only allocation tracing.
