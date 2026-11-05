# Setup, packaging and platform verification

Source setup and Windows commands are in README and START_HERE. Setup installs
requirements.txt, the launcher anchors to its own quoted folder and uses the
local pythonw executable, and the debug command uses python.exe to show errors.
All normal run data lives in a writable user directory, not installed resources.

Build_Windows.cmd installs requirements-dev.txt, runs the complete test suite,
builds RiskLab.spec, and launches scripts/verify_release.py against the produced
Windows executable. It sets Qt offscreen only for verification, then clears
that variable before suggesting a normal launch. The expected artifact is
`dist\RiskLab\RiskLab.exe` plus its companion folder contents.

The spec includes original icon and example resources and excludes unused web,
notebook, plotting and scientific stacks. It produces a one-folder build.
No Linux binary is relabeled as a Windows executable.

Verification on this host used a Linux PyInstaller 6.22.3 build, actual Qt
widgets with QT_QPA_PLATFORM=offscreen, and cold-start/restart subprocesses.
The executable loaded resources, ran the simulation, diagnostic and comparison
workers, published a saved run, closed, restarted and reopened that run without
stochastic execution. Reports/screenshots are in docs/packaging_smoke.

These checks establish that native Linux packaging works in the tested
container. They do NOT establish native X11/Wayland interaction or Windows
build/runtime/high-DPI behavior. Those items remain UNVERIFIED. The supplied
source release does not contain a Windows EXE.

To reproduce a source smoke:
`python scripts/verify_release.py --output docs/source_smoke`.
To verify a built target:
`python scripts/verify_release.py --executable dist/RiskLab/RiskLab --output docs/packaging_smoke`.
On Windows replace the executable path with `dist\RiskLab\RiskLab.exe`.
Run from a project environment; use QT_QPA_PLATFORM=offscreen if no display is
available. A normal manual desktop launch is an additional platform check.
