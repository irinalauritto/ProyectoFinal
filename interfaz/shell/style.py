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
    border: 1px solid {BORDER};
    border-radius: 8px;
}}

QComboBox, QLineEdit, QPlainTextEdit {{
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    padding: 6px 10px;
    background: {BG_SURFACE};
    color: {TEXT_PRIMARY};
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
    border: 1px solid {BORDER};
    border-radius: 8px;
    text-align: left;
}}

#ModalityCard:checked {{
    border: 2px solid {BLUE};
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
