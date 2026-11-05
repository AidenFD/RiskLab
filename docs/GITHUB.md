# Restore history and publish when ready

The ZIP deliberately excludes .git and environments; RiskLab_History.bundle
contains the original checkpoint and release implementation history.

From PowerShell in the extracted RiskLab folder:

```powershell
git bundle verify .\RiskLab_History.bundle
git clone .\RiskLab_History.bundle ..\RiskLab_GitHub
cd ..\RiskLab_GitHub
git rev-parse --show-toplevel
git status
```

Confirm the root is RiskLab_GitHub. Create an empty RiskLab repository in the
AidenFD GitHub account, without an added README, license, or .gitignore. Then:

```powershell
git remote add origin https://github.com/AidenFD/RiskLab.git
git push -u origin main
```

These are instructions; no remote was created or pushed by this release task.
Do not initialize or stage a parent home directory. Do not force-push over
existing work. A history bundle itself should not be recursively committed.

Suggested short repository description:

Python/PySide6 Monte Carlo portfolio risk app with correlated log-return
simulation, VaR/expected shortfall, per-path drawdown, sampling diagnostics,
and auditable saved runs.
