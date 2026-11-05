import copy,json
import numpy as np
import pytest
from PySide6.QtCore import Qt,QTimer
from risklab.ui.application import Window
from risklab.core.export import load_run

@pytest.fixture
def window(qtbot,tmp_path,monkeypatch):
    monkeypatch.setenv('RISKLAB_WORKSPACE',str(tmp_path/'user'))
    w=Window(workspace=tmp_path);qtbot.addWidget(w);w.show()
    yield w
    if w.job:
        w.cancel();qtbot.waitUntil(lambda:w.job is None,timeout=20000)
    w.close()


def ready(w):
    w.load_demo();w.paths.setValue(2000);w.steps.setValue(8);w.confidence.setCurrentIndex(1)
    assert w.validate_current() is not None


def wait(qtbot,w):
    qtbot.waitUntil(lambda:w.job is None,timeout=30000)
    assert not w.last_error,w.last_error


def test_navigation_empty_and_validation(window):
    w=window
    assert w.result is None and w.state=='EMPTY'
    for i in range(9):w.nav.setCurrentRow(i);assert w.pages.currentIndex()==i
    ready(w);assert w.state=='READY';assert w.positions.rowCount()==3
    w.cash.setText('-1');assert w.validate_current() is None;assert w.state=='INVALID';assert w.cash.text()=='-1'
    assert 'Cash' in w.last_error
    w.cash.setText('5000');assert w.validate_current() is not None


def test_worker_result_history_diagnostics_and_comparison(window,qtbot,tmp_path):
    w=window;ready(w);w.run_simulation();identity=w.job_id;w.run_simulation();assert w.job_id==identity
    wait(qtbot,w);assert w.state=='COMPLETED';s=w.result['summary'];original=w.result['terminal_equity'].copy()
    assert w.table.source.rowCount()==2000
    assert f"{s['mean_terminal_equity']:,.2f}" in w.result_metrics[0].value.text()
    w.check_stability();wait(qtbot,w);assert w.result['diagnostics']['status']!='NOT ASSESSED'
    w.compare_scenarios();wait(qtbot,w);assert w.comparison_table.source.rowCount()==4
    np.testing.assert_array_equal(original,w.result['terminal_equity'])
    w.save();wait(qtbot,w);path=w.saved_path;assert path.exists()
    w.refresh_history();wait(qtbot,w);assert w.history_table.source.rowCount()==1
    w.result=None;w.open_run_path(path);wait(qtbot,w)
    np.testing.assert_array_equal(original,w.result['terminal_equity'])
    assert str(path) in w.audit.toPlainText()


def test_cancellation_and_event_loop_responsive(window,qtbot):
    w=window;ready(w);w.paths.setValue(200000);w.steps.setValue(252)
    ticks=[];timer=QTimer(w);timer.timeout.connect(lambda:ticks.append(1));timer.start(1)
    w.run_simulation();qtbot.wait(35);assert ticks
    w.cancel();qtbot.waitUntil(lambda:w.job is None,timeout=10000)
    assert w.state=='CANCELLED';assert w.result is None
    assert not list(__import__('pathlib').Path(w.settings['run_directory']).glob('*/COMPLETED'))


def test_bad_edit_preserves_completed_result(window,qtbot):
    w=window;ready(w);w.run_simulation();wait(qtbot,w);r=w.result
    w.paths.setValue(1);w.run_simulation();assert w.job is None;assert w.result is r
    assert '100 required' in w.last_error


def test_numeric_sort_filter_copy_and_preview(window,qtbot):
    w=window;ready(w);w.run_simulation();wait(qtbot,w)
    w.table.sortByColumn(1,Qt.SortOrder.AscendingOrder);qtbot.wait(10)
    proxy=w.table.proxy
    assert proxy.data(proxy.index(0,1),Qt.ItemDataRole.UserRole)==float(np.min(w.result['terminal_equity']))
    w.path_id.setValue(int(w.result['preview_ids'][0]));w.highlight_path();assert 'equity points' in w.path_details.text()
    w.table.selectRow(0);w.table.copy_selection()
    from PySide6.QtWidgets import QApplication
    assert 'Terminal equity' in QApplication.clipboard().text()


def test_manual_preset_and_history_import(window,tmp_path):
    from risklab.ui.application import RESOURCES
    w=window;w.preset.setCurrentIndex(1);w.load_preset();assert w.model_editor.isReadOnly() is False
    w.load_demo();w.load_history_file(RESOURCES/'examples/SYNTHETIC_3A.csv')
    assert w.model_editor.isReadOnly();assert '756' in w.data_status.text()
    w.detach_history();assert not w.model_editor.isReadOnly();assert w.read_scenario()['model']['kind']=='MANUAL'


def test_compact_layout_and_error_recovery(window):
    w=window;ready(w);w.resize(1040,760)
    for i in range(9):w.nav.setCurrentRow(i)
    w.seed.setText('True');assert w.validate_current() is None
    w.seed.setText('77');assert w.validate_current() is not None
    assert w.error_banner.isHidden()


def test_fresh_window_reopen_labels_saved_result(window,qtbot,tmp_path):
    from risklab.services.experiments import execute,default_config
    from risklab.core.inputs import read_json
    from risklab.core.export import save_run
    from risklab.ui.application import RESOURCES
    s=read_json(RESOURCES/'examples/deterministic.json');cfg=default_config();cfg.update(n_paths=2000,n_steps=3,confidences=['0.95'])
    result,inputs=execute(s,cfg);path=save_run(result,inputs,tmp_path/'saved')
    assert window.scenario is None
    window.open_run_path(path);wait(qtbot,window)
    assert 'Completed result: Deterministic constant equity' in window.context.text()
    assert window.state=='COMPLETED'
