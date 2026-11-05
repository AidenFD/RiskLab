"""Build a standalone engineering report from recorded release evidence.

Optional authoring dependency: reportlab. It is not a runtime or test dependency.
"""
import json,xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape
import reportlab
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak,KeepTogether

ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/'docs'


def evidence():
    suites=ET.parse(DOC/'test_results.xml').getroot().findall('testsuite')
    counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','errors','failures','skipped']}
    return counts,*[json.loads((DOC/p).read_text()) for p in ['benchmark.json','source_smoke/smoke_report.json','packaging_smoke/smoke_report.json']]


def markdown(counts,benchmark,source,packaged):
    s=source['primary_summary'];dpath=Path(source['run_folder'])/'diagnostics.json';d=json.loads(dpath.read_text())
    return f'''# RiskLab v1.0.0 engineering release report

Aiden Federico-Dyer | QuantLab / Risk | November 5, 2026

## Release outcome

RiskLab v1.0.0 is a complete source release of an independent PySide6 desktop
risk research application. The numerical, diagnostics, comparison, saved-run,
export and nine-view desktop workflows are implemented and tested on the
available Linux host. It is no longer the initial development checkpoint.
The source package contains no Windows executable. Native Windows build,
runtime and high-DPI checks remain UNVERIFIED; target build scripts are included.

## Design authority and implementation

The supplied PDF was byte-identical to the original design, SHA-256
fad8e491ef31de48dad100751fe0939d03a1858dc6bfaba86ef4c3277aaf390c.
It and the master prompt are preserved in docs/source. The five engine milestones
are implemented: fixed-path valuation/risk, one-asset increments, correlated
multi-asset generation, historical validation/estimation, and bounded batching.
Desktop and release stages add the nine integrated views, worker ownership,
uncertainty diagnostics, comparisons, persistence, documentation and packaging.
No market model was silently substituted.

The engine samples independent daily Gaussian log-return vectors with within-
vector covariance. Prices update by multiplying exp(log increment); no extra
half-variance term is subtracted. Fixed fractional shares and zero-interest
USD cash are valued without display rounding. PSD eigenfactorization handles
singular and zero covariance, rejecting materially indefinite inputs. Canonical
symbol ordering preserves consistent seeded asset permutations.

Input and calibration boundaries, units, sample denominator, numerical tolerances,
tail definitions, default drift and resource caps are in DECISIONS.md and
DATA_FORMAT.md. Historical calibration requires declared complete sessions;
source kinds remain explicit. BacktestLab/OrderBookLab were product references,
not runtime dependencies. The repository structure is in REPOSITORY_TREE.md.

## Actual test results

- Total: **{counts['tests']} passed**; {counts['failures']} failures,
  {counts['errors']} errors and {counts['skipped']} skips.
- Exact source fixtures: VaR $100, ES $200, loss probability 40% at 80% confidence
  for the five terminal values; 25% maximum drawdown for [1000,1200,900,1100].
- Independent scalar comparison at batch sizes 1, 257 and 512; no production
  valuation/drawdown helpers used to establish reference outcomes.
- Controlled large-sample lognormal moment and cross-asset covariance/mean tests
  use tolerances tied to 5.5 sampling standard errors, rather than exact equality.
- Validation covers duplicates, nonfinite values, units, unsupported instruments,
  complete sessions, tail counts, scalar types, covariance and schema versions.
- Persistence tests include corrupted/rehashed-false summaries, writable fsync
  handles, failures/cancel cleanup, moved folders and immutable result revisions.
- Reopen tests explicitly fail if either simulation or fitting is called.
- Real Qt tests cover input correction, navigation, worker duplication/cancellation,
  event-loop responsiveness, complete outcome models, numeric sort/copy, stability,
  comparisons, history, saving and reopening in a fresh window.

The exact suite output is in test_results.xml. Statistical evidence supports
implementation checks under the chosen model; it does not establish model realism.

## Actual performance and host

| Measurement | Result |
| --- | --- |
| Headless model | 10,000 paths / 252 steps / 10 assets |
| Primary elapsed wall time | {benchmark['wall_seconds']:.6f} seconds |
| Process peak RSS | {benchmark['peak_rss_mib']:.3f} MiB |
| Batch / preview / seed | 512 / 20 / 42 |
| Host | {benchmark['cpu_model']}; {benchmark['cpu_count']} visible CPUs; Linux |
| Python / NumPy | {benchmark['python']} / {benchmark['numpy']} |
| Thread setting | OPENBLAS_NUM_THREADS=1 |
| Source full Qt workflow | {source['elapsed_seconds']:.3f} seconds; {source['peak_rss_mib']:.1f} MiB peak |
| Packaged full Qt workflow | {packaged['elapsed_seconds']:.3f} seconds; {packaged['peak_rss_mib']:.1f} MiB peak |

The headless result includes validation/factorization/simulation/summary but
excludes parsing, diagnostics, publication, GUI and packaging startup. The full
Qt measurements cover the three-asset synthetic demonstration, diagnostics,
comparisons, saving and actual screenshots; they are not the same benchmark.
The design target of 15 seconds / 300 decimal MB for the headless baseline was
met on this host. No result is represented as a measurement of the user's laptop.

## Synthetic demonstration results

The bundled default is synthetic calibration and simulated future paths:
10,000 primary paths, 252 steps, seed 42, batch 512, zero daily log mean.

| Statistic | Actual model output |
| --- | --- |
| Initial equity | ${s['initial_equity']:,.2f} |
| Mean terminal equity | ${s['mean_terminal_equity']:,.2f} |
| 95% loss VaR | ${s['tails']['0.95']['var']:,.2f} |
| 95% expected shortfall | ${s['tails']['0.95']['es']:,.2f} |
| Probability of loss | {s['probability_of_loss']:.2%} |
| Probability plug-in MCSE | {s['probability_se']:.2%} |
| 95th percentile max drawdown | {s['drawdown_quantiles']['0.95']:.2%} |
| Current diagnostic status | {d['status']} |

These are not historical SPY returns, forecasts or trading profits. Risk summaries
use all primary paths; the chart uses a reproducible selected subset. Diagnostics
use 300 full-sample bootstrap resamples and two independently seeded repeat runs;
no replicate is pooled into the primary count. Paired sensitivity comparisons
use common random seeds and are kept distinct from those independent checks.

## Saved results and desktop evidence

Schema-2 folders include the full primary outcomes, preview paths, normalized
scenario/config, stored calibration, metadata, diagnostics/comparisons, manifest,
checksums and COMPLETED. Staging writes are flushed with writable handles,
verified and atomically renamed. Failed/cancelled pre-commit saves do not publish.
Reopening uses persisted parameters and outcomes without refitting/resampling.

Source and native packaged cold-start and restart/reopen checks passed. Actual
Qt screenshots are in docs/screenshots, with packaged evidence separately in
docs/packaging_smoke. The windows, tables, plots and statistics are real app
output captured with Qt's offscreen plugin. Native display interaction is a
separate unverified platform check.

## Start, build and deliverables

On Windows: extract all source files, run Setup_Windows.cmd once, then
Launch_RiskLab.cmd. Debug launch: `.venv\\Scripts\\python.exe -m risklab`.
Build: `Build_Windows.cmd`. Expected target artifact on Windows:
`dist\\RiskLab\\RiskLab.exe`. No Windows executable is included in this source ZIP.

The build script installs verification tools, gates the build on tests, creates
the target package, and runs cold-start/restart smoke checks. A normal manual
Windows launch remains needed to check actual display, dialogs and high DPI.
The verified native Linux executable existed at dist/RiskLab/RiskLab on this host;
it is not distributed as a Windows executable.

Deliverables include source ZIP, this report in Markdown/PDF, actual screenshots,
JUnit/benchmark/smoke evidence, examples including a real completed run, Windows
scripts, pinned requirements, PyInstaller spec and a verified Git history bundle.
Source archives exclude environments, build outputs, caches, ordinary runs and .git.
No remote repository was created or pushed. GITHUB.md supplies restoration steps.

## Limits, deviations and next checks

- Gaussian independent-session returns and constant covariance omit jumps,
  serial dependence and volatility clustering. Monte Carlo precision is not
  parameter-estimation uncertainty or model adequacy.
- No actual corporate-action processing, adjusted/total-return mode, options,
  leverage, shorts, FX, rebalancing, costs, interest, execution or data downloads.
- Source-design open choices were resolved explicitly: zero-log-mean default,
  minimum calibration count, resource caps, scale-relative PSD tolerance,
  Decimal tail indices, independent diagnostic streams and the instability rule.
  These refine operational choices; they do not replace the source model.
- Native Windows build/runtime/high-DPI and native Linux display interaction
  are UNVERIFIED. Next platform step is Build_Windows.cmd and a manual launch.
- V1.1 candidates are model comparisons such as block bootstrap, parameter-risk
  methods, named shocks and properly specified corporate-action/index modes.

## Primary references

- NumPy multivariate sampling: https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.multivariate_normal.html
- NumPy stream compatibility: https://numpy.org/doc/stable/reference/random/compatibility.html
- NumPy covariance: https://numpy.org/doc/stable/reference/generated/numpy.cov.html
- Qt QThread: https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html
- PyInstaller target-platform bundles: https://pyinstaller.org/en/stable/operating-mode.html
'''


def build():
    counts,bench,source,packaged=evidence();s=source['primary_summary']
    (DOC/'ENGINEERING_REPORT.md').write_text(markdown(counts,bench,source,packaged),encoding='utf-8')
    output=DOC/'RiskLab_Engineering_Report.pdf'
    fonts=Path(reportlab.__file__).parent/'fonts'
    pdfmetrics.registerFont(TTFont('RiskLabSans',str(fonts/'Vera.ttf')))
    pdfmetrics.registerFont(TTFont('RiskLabSans-Bold',str(fonts/'VeraBd.ttf')))
    pdfmetrics.registerFontFamily('RiskLabSans',normal='RiskLabSans',bold='RiskLabSans-Bold')
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle('BodyRL',fontName='RiskLabSans',fontSize=10,leading=14,textColor=colors.HexColor('#26364b'),spaceAfter=8))
    styles.add(ParagraphStyle('SmallRL',parent=styles['BodyRL'],fontSize=8,leading=11,spaceAfter=5))
    styles.add(ParagraphStyle('TitleRL',fontName='RiskLabSans-Bold',fontSize=36,leading=42,textColor=colors.HexColor('#193d72'),spaceAfter=10))
    styles.add(ParagraphStyle('H1RL',fontName='RiskLabSans-Bold',fontSize=21,leading=26,textColor=colors.HexColor('#193d72'),spaceAfter=14))
    styles.add(ParagraphStyle('H2RL',fontName='RiskLabSans-Bold',fontSize=12,leading=16,textColor=colors.HexColor('#193d72'),spaceBefore=9,spaceAfter=7))
    styles.add(ParagraphStyle('CaptionRL',parent=styles['SmallRL'],textColor=colors.HexColor('#586b84'),alignment=TA_CENTER))
    story=[]
    def p(text,style='BodyRL'):return Paragraph(escape(text),styles[style])
    def add(text,style='BodyRL'):story.append(p(text,style))
    def table(headers,rows,widths):
        data=[[p(x,'SmallRL') for x in headers]]+[[p(str(x),'SmallRL') for x in row] for row in rows]
        t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8eff9')),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#ced8e7')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
        story.append(t);story.append(Spacer(1,10))
    def screenshot(name,width=490):
        image_path=DOC/'screenshots'/name;iw,ih=ImageReader(str(image_path)).getSize()
        image=Image(str(image_path),width=width,height=width*ih/iw);image.hAlign='CENTER';story.append(image)
    def page():story.append(PageBreak())
    add('RiskLab','TitleRL');add('Engineering release report','H1RL')
    add('QuantLab / Risk  |  Aiden Federico-Dyer  |  v1.0.0  |  November 5, 2026','SmallRL')
    add('Complete source release of a local Monte Carlo portfolio risk desktop application. Verified numerical and desktop workflows, reproducible examples, auditable saved results and target-platform build scripts.')
    table(['Passing tests','Headless baseline','Process peak RSS'],[[str(counts['tests']),f"{bench['wall_seconds']:.2f} seconds",f"{bench['peak_rss_mib']:.1f} MiB"]],[163,163,164])
    screenshot('05_risk_results.png')
    add('Actual Qt application output. Synthetic calibration and simulated future outcomes; no historical investment performance is implied.','CaptionRL')
    add('Platform status','H2RL')
    add('Source and native packaged Linux offscreen workflows passed, including restart and saved-run reopening. Windows build/runtime/high-DPI checks remain UNVERIFIED. The source ZIP contains no Windows executable.','SmallRL')
    page()
    add('Model and risk definitions','H1RL')
    add('The source design is unchanged. One to ten USD assets use fixed nonnegative fractional shares and zero-interest cash over at most 252 future sessions.')
    table(['Contract','Implementation'],[
        ['Daily log returns','g ~ Normal(m, Sigma); S_next = S * exp(g). No extra half-variance subtraction.'],
        ['Drift choice','Zero log mean by default, or estimated/declared daily log means. Zero log mean is not zero expected arithmetic return.'],
        ['Calibration','Complete adjacent declared price sessions; sample covariance normalized by n - 1. No gaps or imputation.'],
        ['Covariance','Scale-relative symmetry/PSD checks, recorded tiny corrections, singular PSD eigenfactor.'],
        ['Valuation','Equity = fixed cash + sum(fixed quantity * simulated price), without display rounding.'],
        ['Terminal risk','Loss = V0 - VN. Gains are negative. VaR/ES are not floored at zero.'],
        ['Path risk','Maximum drawdown is measured against each path\'s own running peak, including step zero.']],[108,382])
    add('Exact acceptance fixtures','H2RL')
    add('With V0 = $1,000 and terminal values $800, $900, $1,000, $1,100, $1,200, ascending losses are -$200, -$100, $0, $100, $200. At 80% confidence, VaR is $100, ES is $200 and probability of loss is 40%.')
    add('VaR uses one-based rank ceil(alpha*N); ES averages the largest ceil((1-alpha)*N) losses. Decimal confidence arithmetic gives exactly 100 tail paths at N = 10,000 and alpha = .99. Each selected production tail needs at least 100 paths.')
    add('The equity path 1000, 1200, 900, 1100 has maximum drawdown 25%, despite finishing with a 10% gain. These small fixtures validate definitions, not tail estimation accuracy.')
    add('Sampling uncertainty','H2RL')
    add('Loss probability includes a plug-in Monte Carlo SE and 95% Wilson interval. Tail diagnostics use 300 whole-sample bootstrap resamples plus two independent repeats. The instability rule and independent stream derivations are exported. Paired drift/volatility comparisons are a separate experiment.')
    page()
    add('Verification and performance','H1RL')
    add(f"The final suite has {counts['tests']} passing tests, {counts['failures']} failures, {counts['errors']} errors and {counts['skipped']} skips. JUnit, raw benchmark and smoke reports accompany the release.")
    table(['Requirement','Evidence'],[
        ['R1: valid data/covariance','Strict dates, units, schema, nonfinite-value, PSD and singular fixtures.'],
        ['R2: asset order','Canonical symbol mappings and seeded permutation acceptance test.'],
        ['R3: repeatability','Nonzero-volatility equal-seed array reproduction; preview RNG independence.'],
        ['R4: loss vs drawdown','Hand fixtures and independent scalar reference at batch sizes 1, 257 and 512.'],
        ['R5: assumptions/precision','Exported provenance, seeds, versions, tail counts, bootstrap intervals and repeats.'],
        ['Statistical checks','One-asset lognormal moments and cross-asset means/covariance within declared sampling-SE tolerances.'],
        ['Desktop/persistence','Real workers, event-loop responsiveness, cancel, sort/copy, corruption checks, portable reopen without fitting or sampling.']],[145,345])
    add('Measured host baseline','H2RL')
    add(f"10,000 paths x 252 future steps x 10 assets; batch 512; 20 previews; seed 42. Wall time {bench['wall_seconds']:.6f} seconds; peak RSS {bench['peak_rss_mib']:.3f} MiB. The 15-second / 300-decimal-MB headless design target was met on this host.")
    add(f"{bench['cpu_model']}, {bench['cpu_count']} visible CPUs, Linux; Python {bench['python']}, NumPy {bench['numpy']}, one OpenBLAS thread. Peak memory uses OS process RSS, not Python-only allocation tracing.",'SmallRL')
    table(['Phase','Wall time','Peak RSS'],[
        ['Source full Qt workflow',f"{source['elapsed_seconds']:.3f} s",f"{source['peak_rss_mib']:.1f} MiB"],
        ['Packaged full Qt workflow',f"{packaged['elapsed_seconds']:.3f} s",f"{packaged['peak_rss_mib']:.1f} MiB"]],[290,100,100])
    add('Full Qt checks use the three-asset synthetic demonstration and include diagnostics, comparisons, saving and screenshots. They differ from the ten-asset headless baseline. Native Windows and physical-display behavior remain unverified.','SmallRL')
    page()
    add('Integrated desktop evidence','H1RL')
    screenshot('03_calibration.png',430)
    add('Portfolio validation and daily model diagnostics are visible before sampling. Source kinds and units remain explicit.','CaptionRL')
    story.append(Spacer(1,8))
    screenshot('06_sampling_uncertainty.png',430)
    add('Tail intervals and independent repeat results come from real computations. NO INSTABILITY FLAG is a finite-sample diagnostic outcome, not a guarantee.','CaptionRL')
    page()
    add('Use, audit and limitations','H1RL')
    add('Start on Windows','H2RL')
    for line in ['1. Extract the whole source ZIP and install Python 3.12 if needed.','2. Run Setup_Windows.cmd once, then Launch_RiskLab.cmd.','3. Load the synthetic demo, review its model and run the default simulation.','4. Check Stability, Compare drift / volatility, then Save Run.']:
        add(line)
    add('Build_Windows.cmd runs tests, builds with PyInstaller and performs packaged smoke checks on Windows. Expected output: dist/RiskLab/RiskLab.exe. A normal native desktop/high-DPI check is still required.','SmallRL')
    add('Auditable saved results','H2RL')
    add('Versioned folders store inputs, calibrated parameters, full outcomes, preview paths, summary, diagnostics, comparisons, sampling metadata and checksums. Writable-handle synchronization and verified atomic publication prevent failed/cancelled pre-commit saves becoming completed results.')
    add('Run History opens the included completed example or a relocated saved folder. Reopen uses stored outcomes and calibration, without fitting or stochastic execution. Diagnostics and comparisons create new in-memory revisions; saving creates a new folder, preserving earlier published runs.')
    table(['Default synthetic example','Model output'],[
        ['Initial equity',f"${s['initial_equity']:,.2f}"],['95% loss VaR / ES',f"${s['tails']['0.95']['var']:,.2f} / ${s['tails']['0.95']['es']:,.2f}"],
        ['Loss probability / 95th-percentile max DD',f"{s['probability_of_loss']:.2%} / {s['drawdown_quantiles']['0.95']:.2%}"]],[290,200])
    add('Limits and next platform check','H2RL')
    add('Gaussian independent-session increments and constant covariance omit jumps, volatility clustering and changing dependence. No options, shorts, leverage, FX, rebalancing, execution, costs, dividends, splits, interest or automatic data downloads are modeled.')
    add('The next external verification step is a native Windows build and manual launch. Native Linux offscreen packaging passed. The source release includes test evidence, docs, real screenshots, completed examples, Windows scripts and a Git history bundle; no remote repository was created or pushed.')
    add('Technical sources: NumPy multivariate sampling, covariance and stream-compatibility documentation; Qt QThread documentation; PyInstaller operating-mode documentation. Full links, exact commands and detailed architecture are in the accompanying Markdown report.','SmallRL')
    def footer(canvas,doc):
        canvas.setStrokeColor(colors.HexColor('#d5dfec'));canvas.line(48,39,A4[0]-48,39)
        canvas.setFont('RiskLabSans',8);canvas.setFillColor(colors.HexColor('#586b84'))
        canvas.drawString(48,25,'RiskLab v1.0.0 | Aiden Federico-Dyer | Source release / engineering evidence')
        canvas.drawRightString(A4[0]-48,25,str(doc.page))
    doc=SimpleDocTemplate(str(output),pagesize=A4,rightMargin=48,leftMargin=48,topMargin=40,bottomMargin=48,title='RiskLab v1.0.0 Engineering Release Report',author='Aiden Federico-Dyer')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print(output)

if __name__=='__main__':build()
