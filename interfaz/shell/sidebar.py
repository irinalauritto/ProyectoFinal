"""Barra lateral del shell: logo, navegacion y estado (paciente/dispositivo)."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

NAV_ITEMS = [
    ("inicio", "Inicio"),
    ("emg", "EMG"),
    ("eeg", "EEG / SSVEP"),
]


class Sidebar(QWidget):
    navigate_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(224)
        self._nav_buttons: dict[str, QPushButton] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(20, 22, 20, 18)
        header.setSpacing(10)
        logo = QLabel()
        logo.setObjectName("SidebarLogo")
        logo.setFixedSize(30, 30)
        header.addWidget(logo)
        title = QLabel("Control AAC")
        title.setObjectName("SidebarTitle")
        header.addWidget(title)
        header.addStretch(1)
        layout.addLayout(header)

        nav_layout = QVBoxLayout()
        nav_layout.setContentsMargins(12, 6, 12, 6)
        nav_layout.setSpacing(2)
        for key, label in NAV_ITEMS:
            btn = QPushButton(label)
            btn.setObjectName("SidebarNavButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _checked=False, k=key: self.navigate_requested.emit(k))
            nav_layout.addWidget(btn)
            self._nav_buttons[key] = btn
        layout.addLayout(nav_layout)

        layout.addStretch(1)

        footer = QFrame()
        footer.setObjectName("SidebarFooter")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(20, 14, 20, 14)
        footer_layout.setSpacing(6)
        self.lbl_patient = QLabel("Paciente: (sin definir)")
        self.lbl_patient.setObjectName("SidebarPatientLabel")
        self.lbl_patient.setWordWrap(True)
        footer_layout.addWidget(self.lbl_patient)
        self.lbl_device = QLabel("● Sin dispositivo")
        self.lbl_device.setObjectName("SidebarDeviceLabel")
        footer_layout.addWidget(self.lbl_device)
        layout.addWidget(footer)

        self.set_active("inicio")

    def set_active(self, key: str) -> None:
        for item_key, btn in self._nav_buttons.items():
            btn.setChecked(item_key == key)

    def set_patient_label(self, text: str) -> None:
        self.lbl_patient.setText(f"Paciente: {text}")

    def set_device_label(self, text: str) -> None:
        self.lbl_device.setText(f"● {text}")
