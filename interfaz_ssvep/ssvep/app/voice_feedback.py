"""
Retroalimentación auditiva por voz de los estímulos detectados.

Usa la síntesis de voz nativa de Windows (SAPI, vía pywin32) para anunciar
en voz alta, de forma asíncrona (sin bloquear), el estímulo que acaba de
identificar el clasificador.
"""

from typing import Dict, Optional

import win32com.client

# Palabra a anunciar por índice de estímulo, según la convención de índices
# usada en todo el proyecto (0=escape/cuadrado, 1=espacio/círculo,
# 2=derecha, 3=arriba, 4=izquierda, 5=abajo).
STIMULUS_WORDS: Dict[int, str] = {
    0: "Escape",
    1: "Espacio",
    2: "Derecha",
    3: "Arriba",
    4: "Izquierda",
    5: "Abajo",
}

_SVSF_ASYNC = 1  # SpeechVoiceSpeakFlags.SVSFlagsAsync


class VoiceFeedback:
    """Anuncia por voz el estímulo detectado, sin bloquear la interfaz."""

    def __init__(self) -> None:
        self.__voice = win32com.client.Dispatch("SAPI.SpVoice")

    def announce(self, stimulus_index: int) -> None:
        """
        Dice en voz alta la palabra asociada al estímulo detectado.

        Args:
            stimulus_index: Índice del estímulo (0-5). Índices fuera de
                ese rango (códigos especiales de "sin detección") se
                ignoran silenciosamente.
        """
        word: Optional[str] = STIMULUS_WORDS.get(stimulus_index)
        if word is None:
            return
        self.__voice.Speak(word, _SVSF_ASYNC)
