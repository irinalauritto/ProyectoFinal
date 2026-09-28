"""Hoja de estilos (QSS) con la paleta del artefacto "Comando AAC".

Colores tomados de los mockups Main/Pantalla2_EMG/Pantalla3_EEG (paleta
azul sobre grises, ya confirmada). Se aplica a nivel de QApplication para
que tambien alcance a los QMessageBox que abre interfazEmg.py sin tener que
tocar ese archivo.
"""

BLUE = "#2f6690"
BLUE_HOVER = "#204a68"
BG_APP = "#f2f4f6"
BG_SURFACE = "#ffffff"
BORDER = "#dfe3e8"
BORDER_STRONG = "#c7cdd6"
TEXT_PRIMARY = "#262c34"
TEXT_MUTED = "#69707b"
NAV_ACTIVE_BG = "#e7eff4"
DISABLED_BG = "#eef0f3"
DISABLED_TEXT = "#a7acb4"

STYLESHEET = f"""
QMainWindow {{
    background: {BG_APP};
}}

QWidget {{
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}}

/* Transparencia de QScrollArea resuelta aca (no con setStyleSheet directo
   sobre el widget -- eso corta la cascada para sus hijos). El viewport de
   un QScrollArea son dos QWidget anidados entre el area y el contenido. */
QScrollArea {{
    background: transparent;
    border: none;
}}

QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

#Sidebar {{
    background: {BG_SURFACE};
    border-right: 1px solid {BORDER};
}}

#SidebarLogo {{
    background: {NAV_ACTIVE_BG};
    border-radius: 6px;
}}

#SidebarTitle {{
    font-size: 14px;
    font-weight: 700;
    color: {TEXT_PRIMARY};
}}

#SidebarNavButton {{
    text-align: left;
    padding: 10px 12px;
    border: none;
    border-radius: 6px;
    color: {TEXT_MUTED};
    font-size: 13px;
    font-weight: 600;
    background: transparent;
}}

#SidebarNavButton:hover {{
    background: {BG_APP};
}}

#SidebarNavButton:checked {{
    background: {NAV_ACTIVE_BG};
    color: {BLUE_HOVER};
}}

#SidebarCollapseButton, #SidebarExpandButton {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    background: {BG_SURFACE};
    color: {TEXT_MUTED};
    font-weight: 700;
}}

#SidebarCollapseButton:hover, #SidebarExpandButton:hover {{
    background: {NAV_ACTIVE_BG};
    color: {BLUE_HOVER};
}}

#SidebarFooter {{
    border-top: 1px solid {BORDER};
}}

#SidebarPatientLabel, #SidebarDeviceLabel {{
    font-size: 11px;
    color: {TEXT_MUTED};
}}

#PageTitle {{
    font-size: 20px;
    font-weight: 600;
    color: {TEXT_PRIMARY};
}}

#SectionLabel {{
    font-size: 11px;
    font-weight: 700;
    color: {TEXT_MUTED};
    letter-spacing: 0.5px;
}}

#SectionTitle {{
    font-size: 13px;
    font-weight: 700;
    color: {TEXT_PRIMARY};
}}

#MutedLabel {{
    font-size: 12px;
    color: {TEXT_MUTED};
}}

#MutedCenteredLabel {{
    font-size: 12px;
    color: {TEXT_MUTED};
}}

#PlaceholderMessage {{
    font-size: 13px;
    color: {TEXT_MUTED};
}}

#Card {{
    background: {BG_SURFACE};
    border: 1px solid {BORDER_STRONG};
    border-radius: 8px;
}}

QComboBox, QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox {{
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    padding: 6px 10px;
    background: {BG_SURFACE};
    color: {TEXT_PRIMARY};
}}

/* Base generica para todo boton/lista/checkbox/slider/groupbox que no
   tenga su propio object-name (p. ej. los controles propios de SSVEP y de
   EMG embebidos, que no se tocan pero heredan la paleta igual). Los
   selectores por #ObjectName de arriba/abajo (ID) ganan siempre sobre
   estos por especificidad, asi que no rompen nada de lo ya estilizado. */
QPushButton {{
    padding: 8px 14px;
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    background: {BG_SURFACE};
    color: {TEXT_PRIMARY};
}}

QPushButton:hover {{
    background: {NAV_ACTIVE_BG};
    border-color: {BLUE};
}}

QPushButton:pressed {{
    background: {NAV_ACTIVE_BG};
}}

QPushButton:disabled {{
    background: {DISABLED_BG};
    color: {DISABLED_TEXT};
    border-color: {BORDER};
}}

QListWidget, QListView {{
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    background: {BG_SURFACE};
    color: {TEXT_PRIMARY};
    outline: none;
}}

QListWidget::item:selected, QListView::item:selected {{
    background: {NAV_ACTIVE_BG};
    color: {BLUE_HOVER};
}}

QCheckBox, QRadioButton {{
    color: {TEXT_PRIMARY};
    spacing: 8px;
}}

QSlider::groove:horizontal {{
    height: 4px;
    background: {BORDER};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 7px;
    background: {BLUE};
}}

QSlider::sub-page:horizontal {{
    background: {BLUE};
    border-radius: 2px;
}}

QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 12px;
    font-weight: 600;
    color: {TEXT_PRIMARY};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}}

QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 8px;
}}

QTabBar::tab {{
    padding: 8px 14px;
    background: {BG_SURFACE};
    border: 1px solid {BORDER_STRONG};
    color: {TEXT_MUTED};
}}

QTabBar::tab:selected {{
    background: {BLUE};
    color: white;
}}

#SegmentButton {{
    padding: 9px 12px;
    font-size: 12px;
    font-weight: 600;
    border: 1px solid {BORDER_STRONG};
    background: {BG_SURFACE};
    color: {TEXT_MUTED};
}}

#SegmentButton:checked {{
    background: {BLUE};
    color: white;
    border-color: {BLUE};
}}

#ModalityCard {{
    background: {BG_SURFACE};
    border: 2px solid {BORDER_STRONG};
    border-radius: 8px;
    text-align: left;
}}

#ModalityCard:hover {{
    border-color: {BLUE};
}}

#ModalityCard:checked {{
    border-color: {BLUE};
    background: {NAV_ACTIVE_BG};
}}

#ModalityCardTitle {{
    font-size: 14px;
    font-weight: 600;
    color: {TEXT_PRIMARY};
}}

#ModalityCardDesc {{
    font-size: 12px;
    color: {TEXT_MUTED};
}}

#PrimaryButton {{
    padding: 10px 22px;
    font-size: 13px;
    font-weight: 600;
    color: white;
    background: {BLUE};
    border: 1px solid {BLUE};
    border-radius: 6px;
}}

#PrimaryButton:hover {{
    background: {BLUE_HOVER};
    border-color: {BLUE_HOVER};
}}

#PrimaryButton:disabled {{
    background: {DISABLED_BG};
    color: {DISABLED_TEXT};
    border-color: {BORDER};
}}

#SecondaryButton {{
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 600;
    color: {BLUE};
    background: {BG_SURFACE};
    border: 1px solid {BLUE};
    border-radius: 6px;
}}

#SecondaryButton:hover {{
    background: {NAV_ACTIVE_BG};
}}

#SecondaryButton:disabled {{
    color: {DISABLED_TEXT};
    border-color: {BORDER};
}}

#BadgeFixed {{
    padding: 5px 10px;
    border-radius: 999px;
    background: {DISABLED_BG};
    color: {TEXT_MUTED};
    font-size: 11px;
    font-weight: 600;
}}

#BadgeActive {{
    padding: 5px 11px;
    border-radius: 999px;
    background: {BLUE};
    color: white;
    font-size: 11px;
    font-weight: 600;
}}

#BadgeInactive {{
    padding: 5px 11px;
    border-radius: 999px;
    background: {BG_SURFACE};
    border: 1px solid {BORDER_STRONG};
    color: {TEXT_MUTED};
    font-size: 11px;
    font-weight: 600;
}}

#ChannelChip {{
    padding: 5px 11px;
    border-radius: 999px;
    background: {BG_SURFACE};
    border: 1px solid {BORDER_STRONG};
    color: {TEXT_MUTED};
    font-size: 11px;
    font-weight: 600;
}}

#ChannelChip:hover {{
    border-color: {BLUE};
}}

#ChannelChip:checked {{
    background: {BLUE};
    border-color: {BLUE};
    color: white;
}}

#ChannelChip:disabled {{
    color: {BORDER_STRONG};
    background: {DISABLED_BG};
}}

#HelpButton {{
    min-width: 18px;
    max-width: 18px;
    min-height: 18px;
    max-height: 18px;
    border-radius: 9px;
    border: 1px solid {BORDER_STRONG};
    background: transparent;
    color: {TEXT_MUTED};
    font-size: 11px;
    padding: 0;
}}

#HelpButton:hover {{
    border-color: {BLUE};
    color: {BLUE};
}}

#FreqTile {{
    background: {DISABLED_BG};
    border-radius: 6px;
}}

#FreqTileLabel {{
    font-size: 10px;
    color: {TEXT_MUTED};
    font-weight: 600;
}}

#FreqTileValue {{
    font-size: 11px;
    color: {TEXT_PRIMARY};
    font-weight: 700;
}}

#GhostButton {{
    padding: 8px 10px;
    font-size: 12px;
    font-weight: 600;
    color: {TEXT_MUTED};
    background: {BG_SURFACE};
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
}}

#GhostButton:hover {{
    background: {DISABLED_BG};
}}

#GhostButton:disabled {{
    color: {DISABLED_TEXT};
    background: {DISABLED_BG};
    border-color: {BORDER};
}}

QProgressBar#CalibrationBar {{
    border: none;
    border-radius: 4px;
    background: {DISABLED_BG};
    height: 8px;
    max-height: 8px;
    text-align: center;
}}

QProgressBar#CalibrationBar::chunk {{
    background: {BLUE};
    border-radius: 4px;
}}

#WarningLabel {{
    font-size: 11px;
    font-weight: 600;
    color: #9a8130;
}}

QMessageBox {{
    background: {BG_SURFACE};
}}

QMessageBox QLabel {{
    color: {TEXT_PRIMARY};
    font-size: 13px;
}}

QMessageBox QPushButton {{
    padding: 6px 16px;
    border-radius: 6px;
    border: 1px solid {BLUE};
    background: {BLUE};
    color: white;
    font-weight: 600;
    min-width: 70px;
}}

QMessageBox QPushButton:hover {{
    background: {BLUE_HOVER};
    border-color: {BLUE_HOVER};
}}
"""
