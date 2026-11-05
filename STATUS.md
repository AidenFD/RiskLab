# RiskLab v1.0.0 - source release ready

The implementation follows the original design PDF (SHA-256
fad8e491ef31de48dad100751fe0939d03a1858dc6bfaba86ef4c3277aaf390c) and
full implementation prompt preserved in docs/source.

Implemented and verified: strict portfolio/history input validation, calibrated
and manual models, PSD/singular covariance, canonical asset ordering, batched
Gaussian daily log-return simulation, exact tail conventions, per-path drawdown,
whole-sample bootstrap and independent repeats, paired comparisons, complete
outcome inspection, all nine desktop views, cancellation, corruption-aware
history, portable saved runs, no-refit/no-sampling reopen, ZIP/CSV exports,
Windows scripts, and native Linux packaging.

The final JUnit file docs/test_results.xml records 102 passing tests with no
failures, errors or skips. Evidence includes independent scalar reference and
statistical tests, UI workflow tests and persistence failures. See TESTING.md.
Headless and full-workflow measurements are in benchmark.json and source_smoke/
packaging_smoke reports, with actual screenshots and restart verification.

Exact commands:
- python -m pytest --junitxml=docs/test_results.xml
- python scripts/benchmark.py
- python scripts/verify_release.py --output docs/source_smoke
- python -m PyInstaller --noconfirm --clean RiskLab.spec
- python scripts/verify_release.py --executable dist/RiskLab/RiskLab --output docs/packaging_smoke

Source verification used Python 3.12.14, NumPy 2.5.4, PySide6 6.12.0,
pyqtgraph 0.14.0, pytest 9.2.0, pytest-qt 4.5.0 and PyInstaller 6.22.3 on Linux.
Qt ran with QT_QPA_PLATFORM=offscreen and numerical benchmarks used one
OpenBLAS thread. This is the verification host, not the user's laptop.

UNVERIFIED: native Windows build/runtime/high-DPI and native Linux display
interaction. No Windows executable is included in the source ZIP. Build_Windows.cmd
provides the target-platform build/test workflow. No remote repository was
created or pushed. Next external verification step: run that script on Windows
and perform a normal manual desktop launch.
