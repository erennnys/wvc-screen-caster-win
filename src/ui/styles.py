"""
Windows 11 Fluent Dark Theme QSS Stylesheet.
"""

DARK_THEME_QSS = """
/* Global Window & Typography */
QWidget {
    background-color: #0b0f19;
    color: #f1f5f9;
    font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #0b0f19;
}

/* Card / Group Container */
QFrame.card, QGroupBox {
    background-color: #141c2e;
    border: 1px solid #1e293b;
    border-radius: 12px;
    margin-top: 10px;
    padding: 16px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #94a3b8;
    font-weight: 600;
}

/* Tabs */
QTabWidget::pane {
    border: none;
    background: transparent;
}

QTabBar::tab {
    background: #141c2e;
    color: #94a3b8;
    padding: 10px 24px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background: #1e293b;
    color: #38bdf8;
    border-bottom: 2px solid #38bdf8;
}

QTabBar::tab:hover:!selected {
    background: #1a233a;
    color: #cbd5e1;
}

/* Buttons */
QPushButton {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 600;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #334155;
    border-color: #475569;
}

QPushButton:pressed {
    background-color: #0f172a;
}

QPushButton.primary-btn {
    background-color: #2563eb;
    border-color: #3b82f6;
    color: #ffffff;
}

QPushButton.primary-btn:hover {
    background-color: #1d4ed8;
    border-color: #60a5fa;
}

QPushButton.danger-btn {
    background-color: #dc2626;
    border-color: #ef4444;
    color: #ffffff;
}

QPushButton.danger-btn:hover {
    background-color: #b91c1c;
}

/* Inputs & Combos */
QLineEdit, QComboBox, QSpinBox {
    background-color: #0f172a;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 12px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border-color: #38bdf8;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

/* Checkbox */
QCheckBox {
    spacing: 8px;
    color: #cbd5e1;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #475569;
    background-color: #0f172a;
}

QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #38bdf8;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 6px;
    background: #334155;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #38bdf8;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #38bdf8;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}

/* Log text area */
QPlainTextEdit {
    background-color: #050811;
    color: #a5b4fc;
    border: 1px solid #1e293b;
    border-radius: 8px;
    font-family: "Cascadia Code", Consolas, monospace;
    font-size: 12px;
    padding: 10px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #0f172a;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}
"""
