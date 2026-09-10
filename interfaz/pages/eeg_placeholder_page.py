"""Pagina EEG/SSVEP: por ahora solo la estetica del mockup (Pantalla3_EEG),
sin logica real. La integracion con AppController/UserUI queda para una
etapa posterior.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from interfaz.shell.app_state import SharedAppState


class EegPlaceholderPage(QWidget):
    def __init__(self, state: SharedAppState, parent=None):
        super().__init__(parent)
        self._state = state

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(14)

        title = QLabel("Control por EEG — SSVEP")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        subtitle = QLabel("Estimulación visual de estado estacionario")
        subtitle.setObjectName("MutedLabel")
        layout.addWidget(subtitle)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        msg = QLabel("Este módulo se integra en una próxima etapa.")
        msg.setObjectName("PlaceholderMessage")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(msg)

        layout.addWidget(card, 1)

    def iniciar_sesion(self) -> None:
        # Sin efecto todavia: la pantalla es solo estetica en esta etapa.
        pass
