"""Central QuantLab palette and original RiskLab widget styles."""
QSS = '''
QWidget { background:#101722; color:#e6edf7; font-family:"Segoe UI","DejaVu Sans"; font-size:13px; }
QFrame#Sidebar { background:#0a111c; border-right:1px solid #29384f; }
QFrame#Sidebar QLabel { background:transparent; }
QLabel#Brand { font-size:24px; font-weight:700; }
QLabel#Kicker { color:#64d8dd; font-size:10px; letter-spacing:2px; }
QLabel#PageTitle { font-size:27px; font-weight:600; }
QLabel#Muted { color:#9aacc4; }
QLabel#Badge { color:#64d8dd; background:#132c39; padding:7px 12px; border-radius:5px; }
QLabel#Error { color:#ffc0bd; background:#38232c; border:1px solid #77404b; padding:10px; border-radius:6px; }
QFrame#Card { background:#172131; border:1px solid #29384f; border-radius:8px; }
QFrame#Card QLabel { background:transparent; }
QLabel#MetricTitle { color:#9aacc4; font-size:11px; }
QLabel#MetricValue { font-size:24px; font-weight:600; }
QLabel#Section { font-size:15px; font-weight:600; }
QPushButton { background:#1d2b40; border:1px solid #354b69; border-radius:5px; padding:9px 14px; }
QPushButton:hover { background:#2b405d; border-color:#5994ff; }
QPushButton:disabled { color:#70819b; background:#182337; border-color:#26364c; }
QPushButton#Primary { background:#427cf2; border-color:#628ffa; color:white; font-weight:600; }
QPushButton#Primary:hover { background:#528aff; }
QPushButton#Primary:disabled { background:#253b5e; color:#8094b1; }
QListWidget#Navigation { background:#0a111c; border:0; outline:0; }
QListWidget#Navigation::item { padding:12px 10px; color:#a4b5cd; border-radius:5px; }
QListWidget#Navigation::item:selected { background:#1b3150; color:#d4e5ff; border-left:3px solid #5994ff; }
QLineEdit,QSpinBox,QDoubleSpinBox,QComboBox,QDateEdit { background:#0d1726; border:1px solid #354b69; border-radius:4px; padding:7px; min-height:18px; }
QLineEdit:focus,QSpinBox:focus,QComboBox:focus,QPlainTextEdit:focus { border-color:#5994ff; }
QPlainTextEdit { background:#111c2c; border:1px solid #29384f; padding:8px; font-family:"Consolas","DejaVu Sans Mono"; font-size:12px; }
QTableView { background:#111c2c; alternate-background-color:#162336; border:1px solid #29384f; gridline-color:#24354b; selection-background-color:#294b78; }
QTableView::item { padding:5px; }
QHeaderView::section { background:#1b2940; color:#aebfd6; padding:8px; border:0; border-right:1px solid #2b3b53; font-size:11px; }
QTabWidget::pane { border:1px solid #29384f; }
QTabBar::tab { background:#152235; color:#a4b5cd; padding:9px 16px; }
QTabBar::tab:selected { background:#223b5c; color:white; }
QProgressBar { background:#1b2b43; border:0; border-radius:4px; min-height:12px; text-align:center; }
QProgressBar::chunk { background:#427cf2; border-radius:4px; }
QStatusBar { background:#0a111c; color:#9aacc4; border-top:1px solid #29384f; }
QScrollBar:vertical { width:10px; background:#0d1726; }
QScrollBar::handle:vertical { background:#354b69; min-height:25px; border-radius:4px; }
QScrollBar:horizontal { height:10px; background:#0d1726; }
QScrollBar::handle:horizontal { background:#354b69; min-width:25px; border-radius:4px; }
QScrollBar::add-line,QScrollBar::sub-line { height:0;width:0; }
QToolTip { background:#223b5c; color:white; border:1px solid #5994ff; padding:5px; }
'''
