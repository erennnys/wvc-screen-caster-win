"""
Modern Windows 11 Studio Dark QSS Stylesheet.
"""

DARK_THEME_QSS = """
/* Global Window & Typography */
QWidget {
    background-color: #090D16;
    color: #F8FAFC;
    font-family: "Segoe UI Variable Display", "Segoe UI", -apple-system, sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #090D16;
}

QLabel {
    background: transparent;
}

/* Elevated Surface Cards */
QFrame#heroCard {
    background-color: #111827;
    border: 1px solid #1E293B;
    border-radius: 16px;
}

QFrame#surfaceCard {
    background-color: #111827;
    border: 1px solid #1E293B;
    border-radius: 14px;
}

QFrame#codeBox {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1E1B4B, stop:1 #0F172A);
    border: 1px solid #3B82F6;
    border-radius: 12px;
}

/* Segmented Modern Tab Widget */
QTabWidget::pane {
    border: none;
    background: transparent;
    margin-top: 8px;
}

QTabBar {
    background: transparent;
}

QTabBar::tab {
    background-color: #111827;
    color: #94A3B8;
    padding: 11px 28px;
    margin-right: 8px;
    border: 1px solid #1E293B;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #4F46E5);
    color: #FFFFFF;
    border: 1px solid #60A5FA;
}

QTabBar::tab:hover:!selected {
    background-color: #1E293B;
    color: #E2E8F0;
    border-color: #334155;
}

/* Buttons */
QPushButton {
    background-color: #1E293B;
    color: #F1F5F9;
    border: 1px solid #334155;
    border-radius: 9px;
    padding: 9px 18px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #283548;
    border-color: #475569;
}

QPushButton:pressed {
    background-color: #0F172A;
}

QPushButton:disabled {
    background-color: #0F172A;
    color: #475569;
    border-color: #1E293B;
}

/* Primary Accent Action Button */
QPushButton#primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #4F46E5);
    border: 1px solid #60A5FA;
    color: #FFFFFF;
    font-weight: 700;
}

QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #6366F1);
    border-color: #93C5FD;
}

QPushButton#primaryBtn:pressed {
    background-color: #1D4ED8;
}

/* Danger / Stop Button */
QPushButton#dangerBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #DC2626, stop:1 #B91C1C);
    border: 1px solid #F87171;
    color: #FFFFFF;
    font-weight: 700;
}

QPushButton#dangerBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #EF4444, stop:1 #DC2626);
}

/* Language Toggle Pill Button */
QPushButton#langBtn {
    background-color: #111827;
    color: #CBD5E1;
    border: 1px solid #1E293B;
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 700;
}

QPushButton#langBtn:hover {
    background-color: #1E293B;
    color: #FFFFFF;
    border-color: #38BDF8;
}

/* Inputs & ComboBoxes */
QLineEdit, QComboBox {
    background-color: #0B0F19;
    color: #F8FAFC;
    border: 1px solid #1E293B;
    border-radius: 9px;
    padding: 8px 14px;
    font-size: 13px;
    selection-background-color: #2563EB;
}

QLineEdit:hover, QComboBox:hover {
    border-color: #334155;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid #3B82F6;
    background-color: #0F172A;
}

QComboBox::drop-down {
    border: none;
    width: 28px;
}

QComboBox QAbstractItemView {
    background-color: #111827;
    color: #F8FAFC;
    border: 1px solid #334155;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
    outline: 0;
    padding: 4px;
}

/* CheckBox */
QCheckBox {
    spacing: 10px;
    color: #E2E8F0;
    font-weight: 500;
    background: transparent;
}

QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 6px;
    border: 1px solid #475569;
    background-color: #0B0F19;
}

QCheckBox::indicator:hover {
    border-color: #60A5FA;
}

QCheckBox::indicator:checked {
    background-color: #2563EB;
    border-color: #60A5FA;
}

/* Sliders */
QSlider {
    background: transparent;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #1E293B;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38BDF8, stop:1 #3B82F6);
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #FFFFFF;
    border: 2px solid #3B82F6;
    width: 16px;
    height: 16px;
    margin-top: -6px;
    margin-bottom: -6px;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background: #EFF6FF;
    border-color: #60A5FA;
}

/* Status Bar */
QStatusBar {
    background-color: #090D16;
    border-top: 1px solid #1E293B;
    color: #64748B;
    font-size: 12px;
}
"""
