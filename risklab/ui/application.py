"""QuantLab desktop: validated inputs, responsive experiments and auditable results."""
from __future__ import annotations
import copy,json,logging,logging.handlers,os,sys,time
from pathlib import Path
import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt,QTimer,QUrl
from PySide6.QtGui import QIcon,QDesktopServices
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,
 QLabel,QPushButton,QListWidget,QStackedWidget,QFrame,QPlainTextEdit,QSpinBox,QFormLayout,
 QProgressBar,QFileDialog,QTableWidget,QTableWidgetItem,QHeaderView,QLineEdit,QComboBox,
 QTabWidget,QScrollArea,QSplitter)
from risklab import __version__
from risklab.core.inputs import read_json,parse_json,validate_scenario,ValidationError
from risklab.core.calibration import validate_history
from risklab.core.simulation import factor_covariance
from risklab.core.export import save_run,load_run,export_archive
from risklab.services.experiments import default_config,prepare,execute,diagnose,compare
from risklab.services.settings import load_settings,save_settings,app_directory
from risklab.services.runs import list_runs
from .theme import QSS
from .workers import Job
from .widgets.tables import Table,DataModel,OutcomesModel

RESOURCES=Path(__file__).resolve().parents[1]/'resources'
MONEY=lambda v:f'${v:,.2f}'
PERCENT=lambda v:f'{v:.2%}'


def label(text,style=None):
    w=QLabel(text);w.setWordWrap(True)
    if style:w.setObjectName(style)
    return w


def button(text,callback,primary=False):
    b=QPushButton(text);b.clicked.connect(callback)
    if primary:b.setObjectName('Primary')
    return b


def row(*widgets):
    layout=QHBoxLayout()
    for w in widgets:layout.addWidget(w)
    layout.addStretch();return layout


def plot(title,x,y):
    w=pg.PlotWidget(background='#101722');w.setTitle(title,color='#c3d3e8',size='12pt');w.setLabel('bottom',x,color='#a7b9d0');w.setLabel('left',y,color='#a7b9d0')
    w.showGrid(x=False,y=True,alpha=.16);w.setMenuEnabled(False)
    for axis in ('bottom','left'):
        w.getAxis(axis).setTextPen('#a7b9d0');w.getAxis(axis).setPen('#354b69')
    return w


class Metric(QFrame):
    def __init__(self,title):
        super().__init__();self.setObjectName('Card');box=QVBoxLayout(self);box.setContentsMargins(15,12,15,12)
        box.addWidget(label(title,'MetricTitle'));self.value=label('N/A','MetricValue');box.addWidget(self.value)
    def set(self,text):self.value.setText(text)


class Window(QMainWindow):
    def __init__(self,*,workspace=None):
        super().__init__()
        self.setWindowTitle('RiskLab - QuantLab');self.setWindowIcon(QIcon(str(RESOURCES/'icon.svg')))
        self.resize(1400,980);self.setMinimumSize(1040,760);self.setStyleSheet(QSS)
        self.settings=load_settings()
        if workspace:self.settings['run_directory']=str(Path(workspace)/'runs')
        self.result=None;self.inputs=None;self.saved_path=None;self.job=None;self.job_id=0
        self.state='EMPTY';self.scenario=None;self.history=None;self.updating=False;self.history_records=[]
        self.elapsed_start=0.;self.current_action='';self.last_error='';self.last_completed_action=''
        container=QWidget();self.setCentralWidget(container);outer=QHBoxLayout(container);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0)
        sidebar=QFrame();sidebar.setObjectName('Sidebar');sidebar.setFixedWidth(222);left=QVBoxLayout(sidebar);left.setContentsMargins(15,24,15,18)
        left.addWidget(label('RiskLab','Brand'));left.addWidget(label('QUANTLAB  /  RISK','Kicker'));left.addSpacing(24)
        self.nav=QListWidget();self.nav.setObjectName('Navigation');self.nav.setSpacing(4)
        for name in ['Dashboard','Portfolio & Data','Model & Calibration','New Simulation','Risk Results','Paths & Outcomes','Assumptions & Audit','Run History','Settings / About']:self.nav.addItem(name)
        left.addWidget(self.nav,1);left.addWidget(label('LOCAL ENGINE\nv'+__version__+'  /  Gaussian log returns\nSimulated outcomes','Muted'));outer.addWidget(sidebar)
        body=QWidget();bodybox=QVBoxLayout(body);bodybox.setContentsMargins(24,20,24,12);bodybox.setSpacing(12);outer.addWidget(body,1)
        head=QHBoxLayout();self.page_title=label('Dashboard','PageTitle');head.addWidget(self.page_title,1);self.badge=label('EMPTY','Badge');head.addWidget(self.badge);bodybox.addLayout(head)
        self.context=label('Choose a synthetic example or import a declared portfolio.','Muted');bodybox.addWidget(self.context)
        self.error_banner=label('','Error');self.error_banner.hide();bodybox.addWidget(self.error_banner)
        self.pages=QStackedWidget();bodybox.addWidget(self.pages,1)
        self.boxes=[]
        for _ in range(9):
            scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.Shape.NoFrame)
            content=QWidget();box=QVBoxLayout(content);box.setContentsMargins(0,0,8,4);box.setSpacing(12)
            scroll.setWidget(content);self.pages.addWidget(scroll);self.boxes.append(box)
        self.nav.currentRowChanged.connect(self.navigate)
        self._dashboard();self._portfolio();self._model();self._configuration();self._results();self._paths();self._audit();self._history();self._settings()
        self.nav.setCurrentRow(0)
        self.clock=QTimer(self);self.clock.setInterval(200);self.clock.timeout.connect(self._tick)
        self.statusBar().showMessage('Ready | All future paths are simulated. No live trading.')
        self.refresh_recent()

    def navigate(self,index):
        self.pages.setCurrentIndex(index);self.page_title.setText(self.nav.item(index).text())

    def set_state(self,state):self.state=state;self.badge.setText(state)

    def _dashboard(self):
        b=self.boxes[0];b.addWidget(label('Explore portfolio uncertainty','Section'))
        b.addWidget(label('Fixed holdings, correlated daily log returns, and explicit assumptions. Start with a complete synthetic example.','Muted'))
        b.addLayout(row(button('Load synthetic demo',self.load_demo,True),button('Configure simulation',lambda:self.nav.setCurrentRow(3))))
        self.dashboard_metrics=[];grid=QGridLayout()
        for i,title in enumerate(['Initial equity','95% loss VaR','95% expected shortfall','Probability of loss']):
            m=Metric(title);grid.addWidget(m,i//2,i%2);self.dashboard_metrics.append(m)
        b.addLayout(grid)
        self.dashboard_chart=plot('Selected equity paths / last completed run','Future session step','Equity / USD');self.dashboard_chart.setMinimumHeight(230);b.addWidget(self.dashboard_chart,1)
        self.dashboard_detail=label('No completed result. Risk estimates will use every primary path, not only the chart subset.','Muted');b.addWidget(self.dashboard_detail)
        self.recent_label=label('Recent runs: none','Muted');b.addWidget(self.recent_label)

    def _portfolio(self):
        b=self.boxes[1]
        self.preset=QComboBox()
        for title,key in [('Correlated synthetic history','correlated_history'),('Deterministic constant','deterministic'),('Deterministic growth','deterministic_growth'),('Low volatility','low_volatility'),('High volatility','high_volatility'),('Perfect positive correlation','singular'),('All cash','all_cash')]:self.preset.addItem(title,key)
        b.addLayout(row(self.preset,button('Load example',self.load_preset),button('Load scenario JSON',self.open_scenario),button('Export scenario JSON',self.export_scenario)))
        form=QFormLayout();self.name=QLineEdit('Untitled portfolio');self.asof=QLineEdit('2023-11-27');self.cash=QLineEdit('5000')
        form.addRow('Scenario name',self.name);form.addRow('As-of session / YYYY-MM-DD',self.asof);form.addRow('Cash / USD, no interest',self.cash);b.addLayout(form)
        self.positions=QTableWidget(0,4);self.positions.setHorizontalHeaderLabels(['Symbol','Quantity / shares','Initial price / USD','Instrument type']);self.positions.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.positions.setMinimumHeight(220);b.addWidget(self.positions)
        b.addLayout(row(button('Add asset',self.add_asset),button('Remove selected asset',self.remove_asset),button('Load history CSV + metadata',self.open_history)))
        self.data_status=label('No data loaded.','Muted');b.addWidget(self.data_status)
        self.portfolio_totals=label('Initial equity: N/A','Section');b.addWidget(self.portfolio_totals)
        b.addLayout(row(button('Validate portfolio and model',self.validate_current,True),button('Model & Calibration',lambda:self.nav.setCurrentRow(2))))
        b.addWidget(label('RAW action-free inputs only. No forward filling. USER_DECLARED history is not independently verified. All bundled examples are synthetic.','Muted'));b.addStretch()
        self.positions.itemChanged.connect(self.dirty)
        for edit in (self.name,self.asof,self.cash):edit.textChanged.connect(self.dirty)

    def _model(self):
        b=self.boxes[2]
        self.model_status=label('Load and validate a scenario to inspect its model.','Muted');b.addWidget(self.model_status)
        b.addLayout(row(button('Validate / calibrate',self.validate_current,True),button('Convert to manual model',self.detach_history)))
        self.model_table=Table();self.model_table.setMinimumHeight(180);b.addWidget(self.model_table)
        tabs=QTabWidget();b.addWidget(tabs,1)
        self.covariance_table=Table();self.correlation_table=Table();self.eigen_text=QPlainTextEdit();self.eigen_text.setReadOnly(True)
        tabs.addTab(self.covariance_table,'Daily covariance');tabs.addTab(self.correlation_table,'Correlation');tabs.addTab(self.eigen_text,'Validation diagnostics')
        b.addWidget(label('Advanced manual model / daily log units','Section'))
        self.model_editor=QPlainTextEdit();self.model_editor.setMaximumHeight(180);self.model_editor.setPlaceholderText('Load a preset or paste a versioned manual model.');self.model_editor.textChanged.connect(self.dirty);b.addWidget(self.model_editor)
        b.addWidget(label('Zero log mean sets the applied mean vector to zero. It does not imply zero expected arithmetic return. Annualization is not used by the sampler.','Muted'))

    def _configuration(self):
        b=self.boxes[3];form=QFormLayout()
        self.paths=QSpinBox();self.paths.setRange(1,200000);self.paths.setSingleStep(1000);self.paths.setValue(10000)
        self.steps=QSpinBox();self.steps.setRange(1,252);self.steps.setValue(252)
        self.seed=QLineEdit('42');self.batch=QSpinBox();self.batch.setRange(1,4096);self.batch.setValue(512)
        self.preview=QSpinBox();self.preview.setRange(0,100);self.preview.setValue(20)
        self.confidence=QComboBox();self.confidence.addItem('95% and 99% (at least 10,000 paths)',['0.95','0.99']);self.confidence.addItem('95% (at least 2,000 paths)',['0.95']);self.confidence.addItem('99% (at least 10,000 paths)',['0.99'])
        self.drift=QComboBox();self.drift.addItem('Zero daily log mean','ZERO_LOG_MEAN');self.drift.addItem('Estimated / declared daily log mean','ESTIMATED_LOG_MEAN')
        for title,w in [('Primary paths',self.paths),('Future session steps',self.steps),('Seed / nonnegative integer',self.seed),('Batch size / reproducibility input',self.batch),('Selected display paths',self.preview),('Loss confidence',self.confidence),('Applied daily log drift',self.drift)]:form.addRow(title,w)
        b.addLayout(form)
        self.config_review=label('Validate your scenario before running.','Muted');b.addWidget(self.config_review)
        self.run_button=button('Run simulation',self.run_simulation,True);self.cancel_button=button('Cancel current operation',self.cancel);self.cancel_button.setEnabled(False)
        b.addLayout(row(self.run_button,self.cancel_button));self.progress=QProgressBar();self.progress.setRange(0,100);self.progress.setValue(0);b.addWidget(self.progress)
        self.progress_label=label('No operation running.','Muted');b.addWidget(self.progress_label)
        b.addWidget(label('A step is a future trading session, not a calendar day. Every selected tail must contain at least 100 paths. Changing batching may change the random stream.','Muted'));b.addStretch()
        for c in (self.paths,self.steps,self.batch,self.preview):c.valueChanged.connect(self.dirty)
        for c in (self.confidence,self.drift):c.currentIndexChanged.connect(self.dirty)
        self.seed.textChanged.connect(self.dirty)

    def _results(self):
        b=self.boxes[4]
        self.result_context=label('No completed run.','Muted');b.addWidget(self.result_context)
        self.result_metrics=[];grid=QGridLayout()
        for i,title in enumerate(['Mean terminal equity','95% loss VaR','95% expected shortfall','Probability of loss','95th percentile max drawdown','Primary paths']):
            m=Metric(title);grid.addWidget(m,i//3,i%3);self.result_metrics.append(m)
        b.addLayout(grid)
        self.save_button=button('Save run',self.save);self.stability_button=button('Check stability',self.check_stability);self.compare_button=button('Compare drift / volatility',self.compare_scenarios)
        b.addLayout(row(self.save_button,self.stability_button,self.compare_button))
        self.result_tabs=QTabWidget();b.addWidget(self.result_tabs,1)
        plots=QWidget();pb=QVBoxLayout(plots);graphs=QHBoxLayout();pb.addLayout(graphs,1)
        self.hist=plot('Terminal loss / all paths','Dollar loss (gains negative)','Path count');self.hist.setMinimumHeight(260);self.hist.setMaximumHeight(320);graphs.addWidget(self.hist,1)
        self.drawdown_hist=plot('Full-path maximum drawdown','Drawdown / %','Path count');self.drawdown_hist.setMinimumHeight(260);self.drawdown_hist.setMaximumHeight(320);graphs.addWidget(self.drawdown_hist,1)
        self.tails_table=Table();self.tails_table.setMinimumHeight(110);self.tails_table.setMaximumHeight(140);pb.addWidget(self.tails_table);self.result_tabs.addTab(plots,'Loss && drawdown')
        diagnostic=QWidget();db=QVBoxLayout(diagnostic);self.diagnostic_status=label('NOT ASSESSED','Section');db.addWidget(self.diagnostic_status)
        self.diagnostic_table=Table();db.addWidget(self.diagnostic_table)
        self.diagnostic_detail=QPlainTextEdit();self.diagnostic_detail.setReadOnly(True);db.addWidget(self.diagnostic_detail);self.result_tabs.addTab(diagnostic,'Sampling uncertainty')
        comparisons=QWidget();cb=QVBoxLayout(comparisons);cb.addWidget(label('Same portfolio, horizon, counts, tail conventions and common random seed. These paired scenarios are not independent stability replicates.','Muted'))
        self.comparison_table=Table();cb.addWidget(self.comparison_table);self.result_tabs.addTab(comparisons,'Scenario comparison')
        for w in (self.save_button,self.stability_button,self.compare_button):w.setEnabled(False)

    def _paths(self):
        b=self.boxes[5];self.chart=plot('Selected equity paths','Future session step','Portfolio equity / USD');self.chart.setMinimumHeight(260);b.addWidget(self.chart)
        self.preview_note=label('No paths yet.','Muted');b.addWidget(self.preview_note)
        b.addLayout(row(label('Inspect path ID'),self._path_spin(),button('Highlight path',self.highlight_path)))
        self.path_details=label('Select a stored preview path to inspect its full equity and drawdown.','Muted');b.addWidget(self.path_details)
        filterrow=QHBoxLayout();self.outcome_filter=QLineEdit();self.outcome_filter.setPlaceholderText('Filter outcomes / copy selected rows with Ctrl+C');filterrow.addWidget(self.outcome_filter,1);filterrow.addWidget(button('Export all outcomes CSV',self.export_outcomes));b.addLayout(filterrow)
        self.table=Table();self.table.setMinimumHeight(230);b.addWidget(self.table,1);self.outcome_filter.textChanged.connect(self.table.filter)

    def _path_spin(self):
        self.path_id=QSpinBox();self.path_id.setRange(0,199999);return self.path_id

    def _audit(self):
        b=self.boxes[6];b.addWidget(label('Input fingerprints, units, model diagnostics, sampling contract and saved payload status.','Muted'))
        self.audit=QPlainTextEdit();self.audit.setReadOnly(True);b.addWidget(self.audit,1)

    def _history(self):
        b=self.boxes[7];b.addLayout(row(button('Refresh',self.refresh_history),button('Open selected run',self.open_selected),button('Open run folder...',self.reopen),button('Export selected run ZIP',self.export_selected),button('Show folder',self.show_selected_folder)))
        self.history_table=Table();b.addWidget(self.history_table,1);self.history_table.doubleClicked.connect(lambda _:self.open_selected())
        self.history_note=label('Completed folders are verified before opening. Incomplete staging folders are excluded.','Muted');b.addWidget(self.history_note)

    def _settings(self):
        b=self.boxes[8];b.addWidget(label('RiskLab  '+__version__+'  /  QuantLab','Section'))
        b.addWidget(label('Local Monte Carlo portfolio risk research. Correlated Gaussian daily log returns; fixed nonnegative equity holdings and cash. No live orders or broker connections.','Muted'))
        self.run_directory=QLineEdit(self.settings['run_directory']);form=QFormLayout();form.addRow('Run directory / writable workspace',self.run_directory);b.addLayout(form)
        b.addLayout(row(button('Choose directory',self.choose_directory),button('Save setting',self.apply_settings)))
        b.addWidget(label('Model boundaries','Section'))
        b.addWidget(label('Independent daily increments and constant covariance can miss jumps, volatility clustering and changing dependence. Synthetic examples are fictional. Imported RAW history requires an action-free declaration. Options, dividends, splits, FX, leverage and rebalancing are outside v1.'))
        b.addWidget(label('Monte Carlo precision is not model certainty. A narrow bootstrap interval does not establish that future market losses follow this model. VaR is a loss threshold, not the worst possible loss.'))
        b.addWidget(label('Reproducibility','Section'));b.addWidget(label('Record seed, batch size, NumPy build, factorization, inputs and hardware environment. Saved runs reopen from persisted outcomes without sampling again.','Muted'))
        b.addWidget(label('Schema 2 / PCG64 / eigh factorization\nNative Windows build, executable runtime and high-DPI behavior require Windows verification.','Muted'));b.addStretch()

    def dirty(self,*_):
        if self.updating:return
        if not self.busy():self.set_state('INVALID')
        self.data_status.setText('Inputs edited. Validate to refresh portfolio and model diagnostics. Last completed results remain available.')

    def busy(self):return self.job is not None

    def load_demo(self):
        self.load_scenario(read_json(RESOURCES/'examples'/'correlated_history.json'));self.nav.setCurrentRow(1)

    def load_preset(self):
        self.load_scenario(read_json(RESOURCES/'examples'/f'{self.preset.currentData()}.json'))
        if self.preset.currentData()=='deterministic_growth':
            self.drift.setCurrentIndex(1);self.validate_current()

    def load_scenario(self,scenario):
        if self.busy():return
        validate_scenario(scenario)
        self.updating=True
        self.scenario=copy.deepcopy(scenario);self.history=copy.deepcopy(scenario.get('history'))
        self.name.setText(str(scenario.get('name','Untitled')));p=scenario['portfolio'];self.cash.setText(str(p['cash']));self.asof.setText(p['as_of_session'])
        self.positions.setRowCount(len(p['positions']))
        for i,pos in enumerate(p['positions']):
            for j,key in enumerate(('symbol','quantity','initial_price','instrument_type')):self.positions.setItem(i,j,QTableWidgetItem(str(pos[key])))
        self.model_editor.setPlainText(json.dumps(scenario['model'],indent=2))
        self.model_editor.setReadOnly(scenario['model']['kind']=='HISTORY')
        self.updating=False;self.validate_current()

    def read_scenario(self):
        positions=[]
        for i in range(self.positions.rowCount()):
            values=[self.positions.item(i,j).text() if self.positions.item(i,j) else '' for j in range(4)]
            positions.append(dict(zip(('symbol','quantity','initial_price','instrument_type'),values)))
        s={'schema_version':1,'name':self.name.text(),'portfolio':{'currency':'USD','as_of_session':self.asof.text(),'cash':self.cash.text(),'positions':positions},'model':parse_json(self.model_editor.toPlainText())}
        if s['model'].get('kind')=='HISTORY':s['history']=copy.deepcopy(self.history)
        return s

    def configuration(self):
        text=self.seed.text()
        if not text.isascii() or not text.isdigit():raise ValidationError('Seed must be a nonnegative integer')
        return {'n_paths':self.paths.value(),'n_steps':self.steps.value(),'seed':int(text),'batch_size':self.batch.value(),'preview_count':self.preview.value(),'confidences':list(self.confidence.currentData()),'drift_mode':self.drift.currentData()}

    def validate_current(self):
        try:
            scenario=self.read_scenario();config=self.configuration();args,inputs=prepare(scenario,config);v=validate_scenario(scenario)
            self.scenario=scenario;self.error_banner.hide();self.last_error='';self.set_state('READY');self.statusBar().showMessage('Inputs validated. Ready to run; prior completed results remain available.')
            p=scenario['portfolio'];n=v['n_observations'];source=v['provenance']
            self.context.setText(f"{scenario.get('name','Portfolio')}  |  {source}  |  USD  |  as of {p['as_of_session']}")
            self.data_status.setText(f"Validated {len(v['symbols'])} assets. {source}. "+(f"{n} complete adjacent log-return observations; no gaps or imputation." if n else 'Explicit hypothetical manual parameters.'))
            total=v['initial_equity'];weights=[q*price/total for q,price in zip(v['quantities'],v['prices'])]
            self.portfolio_totals.setText('Initial equity '+MONEY(total)+'  |  cash '+MONEY(v['cash'])+'  |  asset weights '+', '.join(f'{s} {w:.1%}' for s,w in zip(v['symbols'],weights)))
            self.config_review.setText(f"Ready: {config['n_paths']:,} primary paths × {config['n_steps']} future sessions. {config['drift_mode']}. Initial equity {MONEY(total)}.")
            self.model_status.setText(f"{source} / {scenario['model']['kind']} | Observations: {n or 'manual'} | Daily log units | Applied drift: {config['drift_mode']}")
            diag=v['covariance_diagnostics'];cov=v['covariance'];std=np.sqrt(np.maximum(np.diag(cov),0))
            rows=[[s,float(m),float(a),float(sd)] for s,m,a,sd in zip(v['symbols'],v['estimated_mean'],args['means'],std)]
            self.model_table.use(DataModel(['Symbol','Estimated daily log mean' if scenario['model']['kind']=='HISTORY' else 'Declared daily log mean','Applied daily log mean','Daily log stdev'],rows,{1:lambda x:f'{x:.6f}',2:lambda x:f'{x:.6f}',3:lambda x:f'{x:.6f}'}))
            self.covariance_table.use(DataModel(['Asset']+v['symbols'],[[s]+list(map(float,cov[i])) for i,s in enumerate(v['symbols'])],{i:lambda x:f'{x:.7f}' for i in range(1,len(std)+1)}))
            corr=[]
            for i,s in enumerate(v['symbols']):corr.append([s]+[float(cov[i,j]/(std[i]*std[j])) if std[i]>0 and std[j]>0 else None for j in range(len(std))])
            self.correlation_table.use(DataModel(['Asset']+v['symbols'],corr,{i:lambda x:f'{x:.4f}' for i in range(1,len(std)+1)}))
            self.eigen_text.setPlainText(json.dumps(diag,indent=2)+'\nZero-variance correlation: N/A, undefined.')
            return scenario,config
        except Exception as exc:self.error(str(exc),state='INVALID');return None

    def add_asset(self):
        if self.positions.rowCount()>=10:return self.error('V1 supports at most ten assets.',state='INVALID')
        i=self.positions.rowCount();self.positions.insertRow(i)
        for j,v in enumerate([f'ASSET-{i+1}','0','100','EQUITY']):self.positions.setItem(i,j,QTableWidgetItem(v))

    def remove_asset(self):
        i=self.positions.currentRow()
        if i>=0:self.positions.removeRow(i);self.dirty()

    def open_scenario(self):
        path,_=QFileDialog.getOpenFileName(self,'Load complete RiskLab scenario','','JSON (*.json)')
        if path:
            try:self.load_scenario(read_json(path))
            except Exception as exc:self.error(str(exc),state='INVALID')

    def export_scenario(self):
        validated=self.validate_current()
        if not validated:return
        path,_=QFileDialog.getSaveFileName(self,'Export scenario','RiskLab_Scenario.json','JSON (*.json)')
        if path:
            from risklab.core.export import write_json
            self.start_job('Export scenario',lambda cancel,progress:write_json(path,validated[0]),lambda _:self.statusBar().showMessage('Scenario exported.'))

    def open_history(self):
        path,_=QFileDialog.getOpenFileName(self,'Load RAW history CSV (matching .meta.json required)','','CSV (*.csv)')
        if path:
            try:self.load_history_file(path)
            except Exception as exc:self.error(str(exc),state='INVALID')

    def load_history_file(self,path):
        symbols=[self.positions.item(i,0).text() for i in range(self.positions.rowCount())]
        text=Path(path).read_text(encoding='utf-8-sig');meta=read_json(Path(path).with_suffix('.meta.json'))
        v=validate_history(text,meta,symbols)
        self.history={'csv_text':text,'metadata':meta};self.updating=True;self.asof.setText(v['dates'][-1])
        for i,p in enumerate(v['prices'][-1]):self.positions.setItem(i,2,QTableWidgetItem(repr(float(p))))
        self.model_editor.setPlainText('{"kind":"HISTORY"}');self.model_editor.setReadOnly(True);self.updating=False
        self.validate_current()

    def detach_history(self):
        validated=self.validate_current()
        if not validated:return
        s,_=validated;v=validate_scenario(s);s.pop('history',None)
        s['model']={'kind':'MANUAL','symbols':v['symbols'],'daily_log_mean':v['estimated_mean'].tolist(),'daily_log_cov':v['covariance'].tolist()}
        self.load_scenario(s)

    def start_job(self,action,function,handler):
        if self.busy():return False
        self.job_id+=1;identity=self.job_id;self.current_action=action;self.elapsed_start=time.monotonic();self.last_error='';self.error_banner.hide();self.set_state('RUNNING')
        self.job=Job(identity,function,self);self.job.completed.connect(lambda ident,value:self._completed(ident,value,handler));self.job.failed.connect(self._failed)
        self.job.advanced.connect(self._progress);self.job.finished.connect(self._finished)
        self._lock(True);self.cancel_button.setEnabled(True);self.progress.setValue(0);self.progress_label.setText(action+'...');self.clock.start();self.job.start()
        logging.getLogger('risklab').info('Started %s / job %s',action,identity);return True

    def _lock(self,locked):
        for w in (self.positions,self.name,self.cash,self.asof,self.model_editor,self.preset,self.paths,self.steps,self.seed,self.batch,self.preview,self.confidence,self.drift):w.setEnabled(not locked)
        self.run_button.setEnabled(not locked)
        # Disable every action that can edit inputs, open dialogs or enqueue another job.
        for page in (1,2,4,5,7,8):
            for w in self.pages.widget(page).findChildren(QPushButton):w.setEnabled(not locked)
        if not locked:
            for w in (self.save_button,self.stability_button,self.compare_button):w.setEnabled(self.result is not None)

    def _completed(self,identity,value,handler):
        if identity!=self.job_id:return
        try:
            handler(value);self.last_completed_action=self.current_action
            self.set_state('COMPLETED');self.progress.setValue(100);self.statusBar().showMessage(self.current_action+' completed')
        except Exception as exc:self.error(str(exc),state='FAILED')

    def _failed(self,identity,message,cancelled):
        if identity!=self.job_id:return
        self.error(message,state='CANCELLED' if cancelled else 'FAILED')
        if self.current_action=='Stability diagnostics' and self.result is not None:
            self.diagnostic_status.setText('INCOMPLETE: diagnostic operation did not replace the prior completed result.')

    def _finished(self):
        finished=self.job;self.job=None;self.clock.stop();self._lock(False);self.cancel_button.setEnabled(False)
        if finished:finished.deleteLater()
        self._tick()

    def _progress(self,identity,snapshot):
        if identity!=self.job_id:return
        self.progress.setValue(round(100*snapshot.completed/max(1,snapshot.total)))
        self.progress_label.setText(f'{snapshot.phase}: {snapshot.completed:,} / {snapshot.total:,}')

    def _tick(self):
        if self.elapsed_start:self.statusBar().showMessage(f'{self.current_action} | {self.state} | {time.monotonic()-self.elapsed_start:.1f} seconds')

    def cancel(self):
        if self.job:self.job.token.set();self.set_state('CANCELLING')

    def error(self,message,state='FAILED'):
        self.last_error=message;self.error_banner.setText(message);self.error_banner.show();self.set_state(state);self.statusBar().showMessage(message)

    def run_simulation(self):
        if self.busy():return
        validated=self.validate_current()
        if not validated:return
        scenario,config=validated
        self.start_job('Primary simulation',lambda cancel,progress:execute(scenario,config,cancel=cancel,progress=progress),self.accept_result)

    def accept_result(self,value):
        r,inputs=value;self.result=r;self.inputs=inputs;self.saved_path=None;self.render_result();self.nav.setCurrentRow(4)

    def check_stability(self):
        if self.result is None or self.busy():return
        r,inputs=self.result,self.inputs
        self.start_job('Stability diagnostics',lambda cancel,progress:diagnose(r,inputs,cancel=cancel,progress=progress),self.accept_diagnostics)

    def accept_diagnostics(self,value):
        self.accept_result(value);self.result_tabs.setCurrentIndex(1)

    def compare_scenarios(self):
        if self.result is None or self.busy():return
        r,inputs=self.result,self.inputs
        self.start_job('Scenario comparison',lambda cancel,progress:compare(r,inputs,cancel=cancel,progress=progress),self.accept_comparison)

    def accept_comparison(self,value):
        self.accept_result(value);self.result_tabs.setCurrentIndex(2)

    def histogram(self,chart,values,color):
        chart.clear();counts,edges=np.histogram(values,bins=50)
        chart.addItem(pg.BarGraphItem(x=(edges[:-1]+edges[1:])/2,height=counts,width=np.diff(edges)*.92,brush=color,pen=None))

    def render_result(self):
        r=self.result;s=r['summary'];cfg=self.inputs['config'];tails=s['tails'];level='0.95' if '0.95' in tails else next(iter(tails));tail=tails[level]
        self.result_metrics[1].layout().itemAt(0).widget().setText(f'{float(level):.0%} loss VaR')
        self.result_metrics[2].layout().itemAt(0).widget().setText(f'{float(level):.0%} expected shortfall')
        values=[MONEY(s['mean_terminal_equity']),MONEY(tail['var']),MONEY(tail['es']),PERCENT(s['probability_of_loss']),PERCENT(s['drawdown_quantiles']['0.95']),f"{s['n_paths']:,}"]
        for card,value in zip(self.result_metrics,values):card.set(value)
        for card,value in zip(self.dashboard_metrics,[MONEY(s['initial_equity']),values[1],values[2],values[3]]):card.set(value)
        for card,title in [(self.dashboard_metrics[1],f'{float(level):.0%} loss VaR'),(self.dashboard_metrics[2],f'{float(level):.0%} expected shortfall')]:card.layout().itemAt(0).widget().setText(title)
        source=self.inputs['resolved_model']['source_kind'];name=self.inputs['scenario'].get('name','Portfolio')
        self.context.setText(f'Completed result: {name} | {source} inputs | USD')
        self.result_context.setText(f"{name} | {source} inputs / simulated future paths | {cfg['n_steps']} future sessions | seed {cfg['seed']} | {cfg['drift_mode']}\nLoss probability MCSE {s['probability_se']:.2%}; 95% Wilson interval [{s['probability_wilson_95'][0]:.2%}, {s['probability_wilson_95'][1]:.2%}].")
        lo,hi=s['probability_wilson_95']
        self.dashboard_detail.setText(f"{s['n_paths']:,} primary paths. Loss probability SE {s['probability_se']:.2%}; 95% Wilson interval [{lo:.2%}, {hi:.2%}].\nStability: {r.get('diagnostics',{}).get('status','NOT ASSESSED')}. Terminal loss and full-path drawdown are separate measures.")
        self.histogram(self.hist,s['initial_equity']-r['terminal_equity'],'#427cf2');self.histogram(self.drawdown_hist,100*r['max_drawdowns'],'#64d8dd')
        for index,(c,t) in enumerate(tails.items()):self.hist.addItem(pg.InfiniteLine(pos=t['var'],pen=pg.mkPen('#f6be73',width=1),label=f'{float(c):.0%} VaR',labelOpts={'position':.88-.18*index,'color':'#f6be73'}))
        self.tails_table.use(DataModel(['Confidence','VaR / USD','ES / USD','Tail paths','VaR rank'],[[float(c),t['var'],t['es'],t['tail_count'],t['rank']] for c,t in tails.items()],{0:PERCENT,1:MONEY,2:MONEY}))
        self.chart.clear();self.dashboard_chart.clear()
        for i,path in enumerate(r['preview_equity']):
            pen=pg.mkPen(pg.intColor(i,hues=max(1,len(r['preview_ids'])),sat=150,alpha=165),width=1)
            self.chart.plot(path,pen=pen);self.dashboard_chart.plot(path,pen=pen)
        self.preview_note.setText(f"{len(r['preview_ids'])} evenly spaced display paths from {s['n_paths']:,} primary paths. All-path metrics use every outcome. These paths are not probability bounds.")
        self.path_id.setMaximum(s['n_paths']-1);self.table.use(OutcomesModel(r));self.table.sortByColumn(0,Qt.SortOrder.AscendingOrder)
        d=r.get('diagnostics',{'status':'NOT ASSESSED'});self.diagnostic_status.setText(d['status'])
        rows=[]
        for c,metrics in d.get('intervals',{}).items():
            for metric,interval in metrics.items():rows.append([float(c),metric.upper(),tails[c][metric],interval[0],interval[1]])
        self.diagnostic_table.use(DataModel(['Confidence','Metric','Primary / USD','95% lower / USD','95% upper / USD'],rows,{0:PERCENT,2:MONEY,3:MONEY,4:MONEY}))
        detail=['Sampling precision under the declared model; this does not establish model realism.']
        if d.get('replicates'):
            detail += ['', f"Bootstrap: {d['bootstrap_resamples']} full-sample resamples; 95% percentile intervals.", 'Independent repeats (not pooled into the primary path count):']
            for index,rep in enumerate(d['replicates'],1):
                rs=rep['summary'];detail.append(f"\nRepeat {index} | seed {rep['seed']} | {rs['n_paths']:,} paths | loss probability {rs['probability_of_loss']:.2%}")
                for c,t in rs['tails'].items():detail.append(f"  {float(c):.0%} VaR {MONEY(t['var'])}; ES {MONEY(t['es'])}; {t['tail_count']} tail paths")
            detail += ['','Warning rule: '+d['rule'],'','Warnings: '+('; '.join(d['flags']) or 'No instability flag under this finite-sample check.'),'',d['limitations']]
        else:detail += ['','Run Check stability to compute bootstrap intervals and two independent repeats.']
        self.diagnostic_detail.setPlainText('\n'.join(detail))
        comparison_rows=[]
        for item in r.get('comparisons',[]):
            t=item['summary']['tails'][level]
            comparison_rows.append([item['label'],item['summary']['initial_equity'],t['var'],t['es'],item['summary']['probability_of_loss'],item['summary']['drawdown_quantiles']['0.95']])
        self.comparison_table.use(DataModel(['Scenario','Initial / USD','VaR / USD','ES / USD','Loss probability','95% max DD'],comparison_rows,{1:MONEY,2:MONEY,3:MONEY,4:PERCENT,5:PERCENT}))
        self.update_audit()
        for w in (self.save_button,self.stability_button,self.compare_button):w.setEnabled(not self.busy())

    def highlight_path(self):
        if self.result is None:return
        r=self.result;i=self.path_id.value();matches=np.flatnonzero(r['preview_ids']==i)
        if not len(matches):
            self.path_details.setText(f'Path {i}: terminal {MONEY(r["terminal_equity"][i])}, maximum drawdown {r["max_drawdowns"][i]:.2%}. Full trajectory not retained; choose a preview ID: '+', '.join(map(str,r['preview_ids'])))
            return
        path=r['preview_equity'][matches[0]];self.chart.clear();self.chart.plot(path,pen=pg.mkPen('#64d8dd',width=2))
        self.path_details.setText(f'Path {i}: {len(path)} equity points including step zero. Terminal {MONEY(path[-1])}. Maximum drawdown {r["max_drawdowns"][i]:.2%}.')

    def update_audit(self):
        if self.result is None:return
        from risklab.core.export import object_hash
        r=self.result
        audit={'scenario_fingerprint':object_hash(self.inputs['scenario']),'config_fingerprint':object_hash(self.inputs['config']),
               'inputs':self.inputs,'sampling':r['sampling'],'covariance_diagnostics':r['covariance_diagnostics'],
               'canonical_symbols':r['canonical_symbols'],'canonical_to_declared':r['canonical_to_declared'],
               'summary':r['summary'],'diagnostics':r.get('diagnostics'), 'comparisons':r.get('comparisons'),
               'saved_run':str(self.saved_path) if self.saved_path else 'Not yet saved / this result revision has no published folder',
               'limitations':['Independent Gaussian daily log returns','Constant covariance and fixed holdings','No dividends, splits or interest','Sampling precision does not measure model realism']}
        self.audit.setPlainText(json.dumps(audit,indent=2))

    def save(self):
        if self.result is None or self.busy():return
        r,inputs=self.result,self.inputs;root=self.settings['run_directory']
        self.start_job('Save run',lambda cancel,progress:save_run(r,inputs,root,cancel=cancel),self.saved)

    def saved(self,path):
        self.saved_path=Path(path);self.update_audit();self.refresh_recent();self.history_note.setText('Saved verified run: '+str(path))

    def export_outcomes(self):
        if self.result is None or self.busy():return
        path,_=QFileDialog.getSaveFileName(self,'Export all outcomes','RiskLab_Outcomes.csv','CSV (*.csv)')
        if not path:return
        r=self.result
        def write(cancel,progress):
            import csv
            with Path(path).open('w',newline='',encoding='utf-8') as f:
                writer=csv.writer(f);writer.writerow(['path_id','terminal_equity','loss','max_drawdown'])
                for i,(v,dd) in enumerate(zip(r['terminal_equity'],r['max_drawdowns'])):
                    if i%1024==0 and cancel():raise InterruptedError('CSV export cancelled; destination may be partial')
                    writer.writerow([i,repr(float(v)),repr(float(r['summary']['initial_equity']-v)),repr(float(dd))])
            return path
        self.start_job('Export outcomes',write,lambda _:None)

    def refresh_recent(self):
        try:
            records=list_runs(self.settings['run_directory'])
            self.recent_label.setText('Recent runs: '+(' / '.join(x['manifest'].get('scenario_name',x['manifest'].get('run_id','Unknown')) for x in records[:3]) or 'none'))
        except OSError as exc:self.recent_label.setText('Run directory unavailable: '+str(exc))

    def refresh_history(self):
        if self.busy():return
        root=self.settings['run_directory']
        def inventory(cancel,progress):
            records=list_runs(root)
            for i,rec in enumerate(records):
                if cancel():raise InterruptedError('History refresh cancelled')
                try:load_run(rec['path']);rec['manifest']['status']='VERIFIED'
                except Exception as exc:rec['error']=str(exc);rec['manifest']['status']='CORRUPT'
                progress('Verify saved runs',i+1,len(records))
            return records
        self.start_job('Refresh run history',inventory,self.show_history)

    def show_history(self,records):
        self.history_records=records
        rows=[]
        for rec in records:
            m=rec['manifest'];rows.append([m.get('created_utc',''),m.get('scenario_name','Unknown'),m.get('n_paths'),m.get('n_steps'),m.get('drift_mode',''),m.get('diagnostics_status',''),m.get('status','UNVERIFIED'),rec['path']])
        self.history_table.use(DataModel(['Created UTC','Scenario','Paths','Steps','Drift','Diagnostics','Status','Folder'],rows))
        self.history_note.setText(f'{len(records)} saved folder(s). Corrupt entries are not opened as completed results.')

    def selected_run(self):
        idx=self.history_table.currentIndex()
        if not idx.isValid():return None
        source=self.history_table.proxy.mapToSource(idx)
        return self.history_records[source.row()]['path']

    def open_selected(self):
        path=self.selected_run()
        if path:self.open_run_path(path)

    def reopen(self):
        if self.busy():return
        path=QFileDialog.getExistingDirectory(self,'Open completed run folder')
        if path:self.open_run_path(path)

    def open_run_path(self,path):
        if self.busy():return
        def opened(value):
            self.accept_result(value);self.saved_path=Path(path);self.update_audit()
        self.start_job('Open saved run',lambda cancel,progress:load_run(path),opened)

    def export_selected(self):
        path=self.selected_run()
        if not path:return
        dest,_=QFileDialog.getSaveFileName(self,'Export portable run ZIP','RiskLab_Run.zip','ZIP (*.zip)')
        if dest:self.start_job('Export run ZIP',lambda cancel,progress:export_archive(path,dest),lambda _:None)

    def show_selected_folder(self):
        path=self.selected_run()
        if path:QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).resolve())))

    def choose_directory(self):
        path=QFileDialog.getExistingDirectory(self,'Select writable run directory')
        if path:self.run_directory.setText(path)

    def apply_settings(self):
        try:
            path=Path(self.run_directory.text()).expanduser().resolve();path.mkdir(parents=True,exist_ok=True)
            import tempfile
            with tempfile.TemporaryFile(dir=path):pass
            self.settings['run_directory']=str(path);save_settings(self.settings);self.refresh_recent();self.error_banner.hide();self.statusBar().showMessage('Run directory saved.')
        except Exception as exc:self.error(str(exc))

    def closeEvent(self,event):
        if self.job:
            self.job.token.set()
            if not self.job.wait(3000):
                self.statusBar().showMessage('Cancelling current operation before closing...');event.ignore();return
        event.accept()


def setup_logging():
    folder=app_directory();folder.mkdir(parents=True,exist_ok=True)
    logger=logging.getLogger('risklab');logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler=logging.handlers.RotatingFileHandler(folder/'risklab.log',maxBytes=1000000,backupCount=3,encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'));logger.addHandler(handler)
    logger.info('RiskLab %s starting',__version__)


def main():
    setup_logging();app=QApplication(sys.argv);app.setApplicationName('RiskLab');app.setOrganizationName('QuantLab')
    window=Window();window.show()
    if '--smoke-test' in sys.argv:
        from risklab.ui.smoke import automate
        automate(app,window)
    sys.exit(app.exec())
