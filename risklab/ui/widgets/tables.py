"""Lightweight numeric models; outcomes always expose every simulated path."""
import csv,io
from PySide6.QtCore import QAbstractTableModel,Qt,QSortFilterProxyModel
from PySide6.QtGui import QKeySequence,QShortcut
from PySide6.QtWidgets import QTableView,QHeaderView,QAbstractItemView,QApplication

class DataModel(QAbstractTableModel):
    def __init__(self,headers,rows=(),formats=None,parent=None):
        super().__init__(parent);self.headers=list(headers);self.rows=list(rows);self.formats=formats or {}
    def rowCount(self,parent=None):return len(self.rows)
    def columnCount(self,parent=None):return len(self.headers)
    def data(self,index,role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():return None
        value=self.rows[index.row()][index.column()]
        if role==Qt.ItemDataRole.UserRole:
            if hasattr(value,'item'):value=value.item()
            return value
        if role==Qt.ItemDataRole.TextAlignmentRole:return int(Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignLeft)
        if role in (Qt.ItemDataRole.DisplayRole,Qt.ItemDataRole.ToolTipRole):
            if value is None:return 'N/A'
            formatter=self.formats.get(index.column())
            return formatter(value) if formatter else str(value)
        return None
    def headerData(self,section,orientation,role=Qt.ItemDataRole.DisplayRole):
        if role==Qt.ItemDataRole.DisplayRole:
            return self.headers[section] if orientation==Qt.Orientation.Horizontal else str(section+1)
    def replace(self,rows):
        self.beginResetModel();self.rows=list(rows);self.endResetModel()

class OutcomesModel(DataModel):
    def __init__(self,result,parent=None):
        super().__init__(['Path ID','Terminal equity / USD','Loss / USD','Loss / %','Max drawdown / %'],parent=parent)
        self.result=result
    def rowCount(self,parent=None):return len(self.result['terminal_equity'])
    def data(self,index,role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():return None
        i,j=index.row(),index.column();r=self.result;initial=r['summary']['initial_equity'];v=float(r['terminal_equity'][i]);loss=initial-v
        value=[i,v,loss,loss/initial,float(r['max_drawdowns'][i])][j]
        if role==Qt.ItemDataRole.UserRole:return value
        if role==Qt.ItemDataRole.DisplayRole:return str(i) if j==0 else (f'{value:.2%}' if j>=3 else f'{value:,.2f}')
        return None

class Table(QTableView):
    def __init__(self,parent=None):
        super().__init__(parent);self.setAlternatingRowColors(True);self.setSortingEnabled(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.verticalHeader().setVisible(False);self.verticalHeader().setDefaultSectionSize(32)
        self.proxy=QSortFilterProxyModel(self);self.proxy.setSortRole(Qt.ItemDataRole.UserRole);self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive);self.proxy.setFilterKeyColumn(-1)
        self.setModel(self.proxy)
        QShortcut(QKeySequence.StandardKey.Copy,self,activated=self.copy_selection)
    def use(self,model):
        self.source=model;self.proxy.setSourceModel(model)
    def filter(self,text):self.proxy.setFilterFixedString(text)
    def copy_selection(self):
        rows=sorted({i.row() for i in self.selectionModel().selectedRows()})
        if not rows:return
        out=io.StringIO();writer=csv.writer(out,delimiter='\t')
        writer.writerow([self.proxy.headerData(j,Qt.Orientation.Horizontal) for j in range(self.proxy.columnCount())])
        for i in rows:writer.writerow([self.proxy.data(self.proxy.index(i,j)) for j in range(self.proxy.columnCount())])
        QApplication.clipboard().setText(out.getvalue())
