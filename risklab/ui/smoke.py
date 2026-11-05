"""Real source/packaged desktop verification; no dialogs or fake screenshots."""
import json,os,time
from pathlib import Path
from PySide6.QtCore import QTimer


def automate(app,window):
    root=Path(os.environ.get('RISKLAB_SMOKE_DIR','smoke_evidence')).resolve();root.mkdir(parents=True,exist_ok=True)
    window.settings['run_directory']=str(root/'runs')
    report={'mode':'reopen' if os.environ.get('RISKLAB_OPEN_RUN') else 'full','screenshots':[],
            'platform':os.sys.platform,'capture':'actual Qt widgets; platform plugin '+os.environ.get('QT_QPA_PLATFORM','native')}
    started=time.monotonic();stage=0;timer=QTimer(window);timer.setInterval(40)
    def capture(name,page=None):
        if page is not None:window.nav.setCurrentRow(page)
        app.processEvents();path=root/name
        if not window.grab().save(str(path)):raise RuntimeError('Screenshot save failed')
        report['screenshots'].append(name)
    def finish(code,error=None):
        timer.stop();report.update(elapsed_seconds=time.monotonic()-started,success=code==0)
        if error:report['error']=str(error)
        try:
            import resource
            report['peak_rss_mib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
        except ImportError:pass
        (root/'smoke_report.json').write_text(json.dumps(report,indent=2))
        app.exit(code)
    def step():
        nonlocal stage
        try:
            if time.monotonic()-started>180:raise TimeoutError('Desktop smoke timed out')
            if window.busy():return
            if window.last_error:raise RuntimeError(window.last_error)
            if os.environ.get('RISKLAB_OPEN_RUN'):
                if stage==0:window.open_run_path(os.environ['RISKLAB_OPEN_RUN']);stage=1;return
                report['run_folder']=str(window.saved_path);report['reopened_summary']=window.result['summary']
                capture('reopened_results.png',4);finish(0);return
            if stage==0:
                capture('01_dashboard_empty.png',0);window.load_demo();capture('02_portfolio.png',1);capture('03_calibration.png',2);capture('04_configuration.png',3)
                window.run_simulation();stage=1;return
            if stage==1:
                capture('05_risk_results.png',4);window.check_stability();stage=2;return
            if stage==2:
                capture('06_sampling_uncertainty.png',4);window.compare_scenarios();stage=3;return
            if stage==3:
                capture('07_comparison.png',4);capture('08_paths_outcomes.png',5);window.save();stage=4;return
            if stage==4:
                report['run_folder']=str(window.saved_path);report['primary_summary']=window.result['summary'];report['diagnostics_status']=window.result['diagnostics']['status']
                capture('09_audit.png',6);window.refresh_history();stage=5;return
            if stage==5:
                capture('10_run_history.png',7);capture('11_settings.png',8)
                window.cash.setText('-1');window.validate_current();capture('12_validation_error.png',1)
                window.cash.setText('5000');window.validate_current();window.resize(1040,760);window.result_tabs.setCurrentIndex(0);capture('13_compact_results.png',4)
                finish(0)
        except Exception as exc:finish(1,exc)
    timer.timeout.connect(step);timer.start()
