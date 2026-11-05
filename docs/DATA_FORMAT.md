# Data and saved-result contracts

## Complete scenario JSON

`schema_version` is integer 1. `name` labels a scenario. `portfolio` contains
`as_of_session` (YYYY-MM-DD), `currency: USD`, nonnegative `cash`, and one to ten
`positions`. Each position declares `symbol`, `instrument_type: EQUITY`,
nonnegative `quantity`, and positive `initial_price`. Fractional shares are valid.
Initial equity must be positive. Duplicate symbols/JSON keys and booleans in
numeric fields are rejected. The versioned JSON examples are the exact schemas.

A MANUAL `model` contains `kind`, ordered `symbols`, `daily_log_mean`, and a
square `daily_log_cov`. Symbols must match positions; arrays are mapped by label.
A HISTORY model contains `kind: HISTORY`; the scenario embeds a `history` record
with `csv_text` and `metadata`. This makes saved runs self-contained.

## History CSV + sidecar

Import `NAME.csv` beside `NAME.meta.json`. CSV has one `Date` column and one
positive raw-price column per symbol; order is mapped by header identifier.
Metadata requires `schema_version: 1`, portfolio-ordered `symbols`, `currency:
USD`, `price_basis: RAW`, `action_free: true`, `source_kind` (SYNTHETIC or
USER_DECLARED), nonempty `calendar_id`, and complete increasing `expected_sessions`.

Every CSV session must equal the declared list, without omissions, duplicates,
extra dates, or reordered rows. A weekend gap is adjacent only when the declared
session list says so; the app does not certify an exchange calendar. Missing
prices are not filled and gaps are not hidden by intersecting files. The
snapshot date/prices must equal the final price session, within tight price
tolerance (relative and absolute 1e-10).

Minimum historical observations are `max(60, 10*asset_count)` adjacent returns.
This is an engineering floor, not a guarantee of estimation accuracy. V1 limits
history to 20,000 price sessions / 8 MB CSV and JSON files to 16 MB. Calibrated
log means and covariance remain daily. Zero-log-mean mode leaves the sample
covariance centered around its estimated sample mean.

Adjusted prices and total-return indices are rejected. Actual dividend/split
processing is excluded. USER_DECLARED action-free data is a user's assertion,
not independently verified provenance. Real dividend-paying SPY is not made
action-free by a synthetic example having no corporate actions.

## Configuration

Fields: `n_paths` (1..200000 subject to tail sufficiency), `n_steps` (1..252),
`seed` (integer 0..2^63-1), `batch_size` (1..4096), `preview_count` (0..100),
`confidences` (1..5 distinct levels in (0,1)), and `drift_mode` (ZERO_LOG_MEAN or
ESTIMATED_LOG_MEAN). For a manual model the second mode uses the declared mean.
At least 100 paths must lie in every selected empirical tail.

## Saved run schema 2

A successful folder contains manifest.json, scenario.json, config.json,
model_parameters.json, summary.json, outcomes.npz, terminal_outcomes.csv,
diagnostics.json, comparisons.json, sampling.json, and COMPLETED. Historical
runs additionally contain history.csv and history.meta.json.

The NPZ contains numeric terminal equity, maximum drawdowns, preview IDs and
preview equity paths. It is loaded with `allow_pickle=False`; unsupported
members, excessive expanded arrays, wrong shapes and invalid domains are rejected.
The CSV contains every path ID, terminal equity, signed dollar loss and maximum
drawdown, at round-trip float precision. It is reconciled with the arrays.

The manifest records input/config fingerprints, SHA-256 payload hashes, UTC
creation time, unique run ID, app/NumPy/Python versions, source kind, asset order,
counts, drift and diagnostic status. COMPLETED binds the manifest checksum.
These are integrity checks, not cryptographic authentication of market data.

Payloads are staged on the same filesystem, flushed/fsynced using writable
handles, read back and reconciled, then renamed into publication. A cancelled
or failed publication removes its staging folder. Rename is the commit point;
cancellation after that point cannot retract a completed save. Every new save
gets a new ID. Saved folders are not modified on reopening.
