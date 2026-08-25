# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'eeg_widget.ui'
##
## Created by: Qt User Interface Compiler version 6.10.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QLabel, QScrollBar, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_EEGWidget(object):
    def setupUi(self, EEGWidget):
        if not EEGWidget.objectName():
            EEGWidget.setObjectName(u"EEGWidget")
        EEGWidget.resize(250, 700)
        EEGWidget.setMinimumSize(QSize(150, 0))
        self.verticalLayout = QVBoxLayout(EEGWidget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.lblCH0 = QLabel(EEGWidget)
        self.lblCH0.setObjectName(u"lblCH0")
        font = QFont()
        font.setFamilies([u"Segoe UI"])
        font.setPointSize(16)
        font.setBold(True)
        font.setItalic(False)
        font.setUnderline(False)
        font.setStrikeOut(False)
        font.setKerning(True)
        font.setStyleStrategy(QFont.PreferDefault)
        self.lblCH0.setFont(font)
        self.lblCH0.setMargin(4)

        self.verticalLayout.addWidget(self.lblCH0)

        self.lblCH1 = QLabel(EEGWidget)
        self.lblCH1.setObjectName(u"lblCH1")
        self.lblCH1.setFont(font)
        self.lblCH1.setMargin(4)

        self.verticalLayout.addWidget(self.lblCH1)

        self.lblCH2 = QLabel(EEGWidget)
        self.lblCH2.setObjectName(u"lblCH2")
        self.lblCH2.setFont(font)
        self.lblCH2.setMargin(4)

        self.verticalLayout.addWidget(self.lblCH2)

        self.lblCH3 = QLabel(EEGWidget)
        self.lblCH3.setObjectName(u"lblCH3")
        self.lblCH3.setFont(font)
        self.lblCH3.setMargin(4)

        self.verticalLayout.addWidget(self.lblCH3)

        self.lblCH4 = QLabel(EEGWidget)
        self.lblCH4.setObjectName(u"lblCH4")
        self.lblCH4.setFont(font)
        self.lblCH4.setMargin(4)

        self.verticalLayout.addWidget(self.lblCH4)

        self.lblCH5 = QLabel(EEGWidget)
        self.lblCH5.setObjectName(u"lblCH5")
        self.lblCH5.setFont(font)
        self.lblCH5.setMargin(4)

        self.verticalLayout.addWidget(self.lblCH5)

        self.lblCH6 = QLabel(EEGWidget)
        self.lblCH6.setObjectName(u"lblCH6")
        self.lblCH6.setFont(font)
        self.lblCH6.setMargin(4)

        self.verticalLayout.addWidget(self.lblCH6)

        self.lblCH7 = QLabel(EEGWidget)
        self.lblCH7.setObjectName(u"lblCH7")
        self.lblCH7.setFont(font)
        self.lblCH7.setMargin(4)

        self.verticalLayout.addWidget(self.lblCH7)

        self.sbEEG = QScrollBar(EEGWidget)
        self.sbEEG.setObjectName(u"sbEEG")
        self.sbEEG.setEnabled(False)
        self.sbEEG.setOrientation(Qt.Horizontal)

        self.verticalLayout.addWidget(self.sbEEG)


        self.retranslateUi(EEGWidget)

        QMetaObject.connectSlotsByName(EEGWidget)
    # setupUi

    def retranslateUi(self, EEGWidget):
        EEGWidget.setWindowTitle(QCoreApplication.translate("EEGWidget", u"Form", None))
        self.lblCH0.setText(QCoreApplication.translate("EEGWidget", u"CH1", None))
        self.lblCH1.setText(QCoreApplication.translate("EEGWidget", u"CH2", None))
        self.lblCH2.setText(QCoreApplication.translate("EEGWidget", u"CH3", None))
        self.lblCH3.setText(QCoreApplication.translate("EEGWidget", u"CH4", None))
        self.lblCH4.setText(QCoreApplication.translate("EEGWidget", u"CH5", None))
        self.lblCH5.setText(QCoreApplication.translate("EEGWidget", u"CH6", None))
        self.lblCH6.setText(QCoreApplication.translate("EEGWidget", u"CH7", None))
        self.lblCH7.setText(QCoreApplication.translate("EEGWidget", u"CH8", None))
    # retranslateUi

