# Reproducibility and portability

The primary generator is explicit PCG64, consumed batch-major then step-major
using standard normal arrays with shape (batch_paths, assets), multiplied by
the transpose of a recorded eigenfactor. Internal symbols are canonical sorted
identifiers; the original order and mapping are exported. That makes consistent
asset permutations preserve simulated economics.

Record the input/config fingerprints, seed, NumPy build, Python/OS environment,
hardware, factorization, asset order and batch size. Repeatability is limited
to that environment and random-call contract. Different NumPy/LAPACK builds,
hardware or draw shapes may produce different equally valid streams. V1 does
not promise batch-size invariance or cross-platform bitwise random generation.
See NumPy's compatibility policy in the engineering report references.

Preview IDs are evenly spaced path indices, including endpoints when multiple
paths are selected. They consume no randomness. Charts, sorting and user
navigation cannot perturb the numerical stream. The actual primary preview
paths are captured while simulating.

Diagnostics derive SeedSequence children using primary entropy and spawn key
(1701,), then three child streams. Child zero drives bootstrap; children one
and two generate explicit 63-bit seeds for independent repeat simulations.
Those seeds and keys are exported. Paired sensitivity comparisons instead
reuse the primary seed intentionally, and must not be described as independent.

Reopening is different from rerunning. It verifies the manifest/payloads,
uses stored calibrated parameters, recomputes summary statistics from stored
outcomes, and reconciles previews/CSV. It does not refit means/covariance or
sample. A copied folder can be inspected without original input paths. Cross-
hardware summary reconciliation uses declared float tolerance (relative 1e-11,
absolute 1e-9); persisted terminal outcomes remain the original values.

Original design PDF SHA-256:
`fad8e491ef31de48dad100751fe0939d03a1858dc6bfaba86ef4c3277aaf390c`.
The uploaded design was byte-identical; its proposal wording is preserved
unchanged in docs/source, alongside the original implementation prompt.
