"""RiskLab desktop development build: actual engine outputs, no mock values."""
import json,sys,threading
from pathlib import Path
import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QThread,Signal
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,
 QPushButton,QListWidget,QStackedWidget,QPlainTextEdit,QSpinBox,QFormLayout,QProgressBar,
 QFileDialog,QMessageBox,QTableWidget,QTableWidgetItem,QHeaderView)
from risklab.core.simulation import simulate
from risklab.core.export import save_run,load_run

class Worker(QThread):
    complete=Signal(object,object); failed=Signal(str); progress=Signal(int)
    def __init__(self,inputs):
        super().__init__();self.inputs=inputs;self.cancelled=threading.Event()
    def run(self):
        try:
            r=simulate(**self.inputs,cancel=self.cancelled.is_set,progress=lambda n,total:self.progress.emit(int(n/total*100)))
            if self.cancelled.is_set():raise InterruptedError('Cancelled')
            self.complete.emit(r,self.inputs)
        except Exception as exc:self.failed.emit(str(exc))

class Window(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle('RiskLab - QuantLab | Development');self.resize(1400,950)
        self.result=None;self.inputs=None;self.worker=None
        self.setStyleSheet('QWidget {background:#101722;color:#e1e9f5;font-size:14px;} QListWidget {background:#0a111c;border:0;padding:12px;} QListWidget::item {padding:14px;} QListWidget::item:selected {background:#29384f;color:#64d8dd;} QPushButton {background:#294d8c;border:1px solid #427cf2;border-radius:5px;padding:10px;} QPushButton:disabled {background:#29384f;color:#7e8b9e;} QPlainTextEdit,QSpinBox,QTableWidget {background:#172131;border:1px solid #29384f;padding:8px;} QLabel#title {font-size:27px;font-weight:bold;}')
        container=QWidget();self.setCentralWidget(container);layout=QHBoxLayout(container)
        self.nav=QListWidget();self.nav.setFixedWidth(225);layout.addWidget(self.nav)
        self.pages=QStackedWidget();layout.addWidget(self.pages,1)
        for title in ['Dashboard','Portfolio & Model','New Simulation','Risk Results','Paths & Outcomes','Assumptions & Audit','Run History']:
            self.nav.addItem(title);page=QWidget();box=QVBoxLayout(page);label=QLabel(title);label.setObjectName('title');box.addWidget(label);self.pages.addWidget(page)
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex);self.nav.setCurrentRow(0)
        def box(i):return self.pages.widget(i).layout()
        box(0).addWidget(QLabel('QUANTLAB / RISK\n\nCorrelated Gaussian daily log returns. Fixed shares. USD cash.\nSynthetic demonstration data; model-generated outcomes.'))
        self.overview=QLabel('Load the demo, review the model, then run a simulation.');self.overview.setWordWrap(True);box(0).addWidget(self.overview)
        button=QPushButton('Load synthetic three-asset demo');button.clicked.connect(self.demo);box(0).addWidget(button);box(0).addStretch()
        box(1).addWidget(QLabel('Edit the explicit hypothetical portfolio and daily log parameters.\nZero daily log means do not imply zero expected arithmetic return.'))
        self.editor=QPlainTextEdit();box(1).addWidget(self.editor)
        load=QPushButton('Load scenario JSON');load.clicked.connect(self.load_scenario);box(1).addWidget(load)
        form=QFormLayout();self.paths=QSpinBox();self.paths.setRange(10000,1000000);self.paths.setValue(10000)
        self.steps=QSpinBox();self.steps.setRange(1,252);self.steps.setValue(252)
        self.seed=QSpinBox();self.seed.setRange(0,2147483647);self.seed.setValue(42)
        for label,control in [('Primary paths',self.paths),('Future sessions',self.steps),('Seed',self.seed)]:form.addRow(label,control)
        box(2).addLayout(form);box(2).addWidget(QLabel('95% and 99% tails | batch size 512 | 20 display paths\nMinimum 100 observations in each selected tail.'))
        self.run_button=QPushButton('Run simulation');self.run_button.clicked.connect(self.run_simulation);box(2).addWidget(self.run_button)
        self.cancel_button=QPushButton('Cancel');self.cancel_button.setEnabled(False);self.cancel_button.clicked.connect(self.cancel);box(2).addWidget(self.cancel_button)
        self.progress=QProgressBar();box(2).addWidget(self.progress);box(2).addStretch()
        self.metrics=QLabel('No completed result.');self.metrics.setWordWrap(True);box(3).addWidget(self.metrics)
        self.hist=pg.PlotWidget();self.hist.setLabel('bottom','Terminal dollar loss (gains negative)');self.hist.setLabel('left','Paths');box(3).addWidget(self.hist)
        save=QPushButton('Save completed run');save.clicked.connect(self.save);box(3).addWidget(save)
        self.chart=pg.PlotWidget();self.chart.setLabel('bottom','Future session');self.chart.setLabel('left','Portfolio equity','USD');box(4).addWidget(self.chart)
        box(4).addWidget(QLabel('20 reproducibly selected paths; these are not guaranteed bounds. Risk statistics use ALL paths.'))
        self.table=QTableWidget();self.table.setColumnCount(4);self.table.setHorizontalHeaderLabels(['Path','Terminal equity','Loss','Max drawdown']);self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);box(4).addWidget(self.table)
        self.audit=QPlainTextEdit();self.audit.setReadOnly(True);box(5).addWidget(self.audit)
        box(6).addWidget(QLabel('Open a saved run folder to verify checksums and reconcile its summary without rerunning.'))
        reopen=QPushButton('Open saved run folder');reopen.clicked.connect(self.reopen);box(6).addWidget(reopen);box(6).addStretch()
        self.statusBar().showMessage('Development build | Stability diagnostics and full release validation pending')
        self.demo()
    def demo(self):
        self.editor.setPlainText(json.dumps({'symbols':['SYN-A','SYN-B','SYN-C'],'quantities':[100,150,200],'prices':[100,80,50],'cash':5000,'means':[0,0,0],'covariance':[[.0001,.00003,.00001],[.00003,.000225,.00002],[.00001,.00002,.000064]]},indent=2))
    def load_scenario(self):
        path,_=QFileDialog.getOpenFileName(self,'Scenario JSON','','JSON (*.json)')
        if path:
            try:self.editor.setPlainText(json.dumps(json.loads(Path(path).read_text()),indent=2))
            except Exception as e:self.error(str(e))
    def run_simulation(self):
        if self.worker and self.worker.isRunning():return
        try:
            args=json.loads(self.editor.toPlainText());args.update(n_paths=self.paths.value(),n_steps=self.steps.value(),seed=self.seed.value())
            self.worker=Worker(args);self.worker.complete.connect(self.show_result);self.worker.failed.connect(self.error)
            self.worker.progress.connect(self.progress.setValue);self.worker.finished.connect(self.finished)
            self.run_button.setEnabled(False);self.cancel_button.setEnabled(True);self.progress.setValue(0);self.worker.start()
        except Exception as e:self.error(str(e))
    def cancel(self):
        if self.worker:self.worker.cancelled.set()
    def finished(self):self.run_button.setEnabled(True);self.cancel_button.setEnabled(False)
    def error(self,message):QMessageBox.warning(self,'RiskLab',message)
    def show_result(self,r,args):
        self.result=r;self.inputs=args;s=r['summary'];lines=[f"Initial equity: ${s['initial_equity']:,.2f}   |   Paths: {s['n_paths']:,}",f"Mean terminal equity: ${s['mean_terminal_equity']:,.2f}   |   Loss probability: {100*s['probability_of_loss']:.2f}%"]
        for level,t in s['tails'].items():lines.append(f"{float(level):.0%} VaR: ${t['var']:,.2f}   |   ES: ${t['es']:,.2f}   |   Tail paths: {t['tail_count']}")
        lines.append(f"95th percentile maximum drawdown: {s['drawdown_quantiles']['0.95']:.2%}\nStability: NOT ASSESSED")
        self.metrics.setText('\n'.join(lines));self.overview.setText('\n'.join(lines));self.hist.clear()
        counts,edges=np.histogram(s['initial_equity']-r['terminal_equity'],bins=60)
        self.hist.addItem(pg.BarGraphItem(x=(edges[:-1]+edges[1:])/2,height=counts,width=np.diff(edges)*.9,brush='#427cf2'))
        self.chart.clear()
        for i,path in enumerate(r['preview_equity']):self.chart.plot(path,pen=pg.mkPen(pg.intColor(i,hues=20),width=1))
        n=min(200,len(r['terminal_equity']));self.table.setRowCount(n)
        for i in range(n):
            for j,v in enumerate([str(i),f"{r['terminal_equity'][i]:,.2f}",f"{s['initial_equity']-r['terminal_equity'][i]:,.2f}",f"{r['max_drawdowns'][i]:.2%}"]):self.table.setItem(i,j,QTableWidgetItem(v))
        self.table.setToolTip('First 200 paths shown; saved outcomes include all paths.')
        self.audit.setPlainText(json.dumps({'inputs':args,'summary':s,'covariance':r['covariance_diagnostics'],'limitations':['Independent daily Gaussian log returns','Fixed covariance and holdings','No dividends, splits or cash interest','Stability diagnostics not implemented in this development build']},indent=2))
        self.nav.setCurrentRow(3)
    def save(self):
        if self.result is None:return
        path=QFileDialog.getExistingDirectory(self,'Choose parent folder for completed run')
        if path:
            try:self.statusBar().showMessage('Saved '+str(save_run(self.result,self.inputs,path)))
            except Exception as e:self.error(str(e))
    def reopen(self):
        path=QFileDialog.getExistingDirectory(self,'Open completed run folder')
        if path:
            try:r,args=load_run(path);self.show_result(r,args)
            except Exception as e:self.error(str(e))
    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():
            self.worker.cancelled.set();self.worker.wait()
        event.accept()

def main():
    app=QApplication(sys.argv);window=Window();window.show();sys.exit(app.exec())
