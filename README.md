# RiskLab development checkpoint
QuantLab / Risk — Aiden Federico-Dyer

This is a working development foundation, not the completed v1 requested in the master prompt. See STATUS.md for remaining requirements.

Install requirements in a Python 3.12 virtual environment, then run `python -m risklab`. The development GUI loads a synthetic three-asset model; New Simulation runs actual correlated daily log-return paths. Results can be saved and reopened. All outputs are model simulations.

Run foundation tests with `python -m unittest discover -s tests -v`.
