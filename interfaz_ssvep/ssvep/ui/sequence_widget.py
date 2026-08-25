# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'sequence_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QLabel, QScrollArea,
    QSizePolicy, QSpacerItem, QVBoxLayout, QWidget)
from res.images import resources_rc

class Ui_sequenceWidget(object):
    def setupUi(self, sequenceWidget):
        if not sequenceWidget.objectName():
            sequenceWidget.setObjectName(u"sequenceWidget")
        sequenceWidget.resize(772, 590)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(sequenceWidget.sizePolicy().hasHeightForWidth())
        sequenceWidget.setSizePolicy(sizePolicy)
        self.verticalLayout_2 = QVBoxLayout(sequenceWidget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.lblExpectedSequence = QLabel(sequenceWidget)
        self.lblExpectedSequence.setObjectName(u"lblExpectedSequence")
        self.lblExpectedSequence.setEnabled(True)
        self.lblExpectedSequence.setMinimumSize(QSize(0, 0))
        self.lblExpectedSequence.setMaximumSize(QSize(16777215, 60))
        self.lblExpectedSequence.setStyleSheet(u"color: rgb(25, 25, 25);\n"
"font: 18pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(255, 255, 255, 215);\n"
"border: 2px solid rgba(0, 0, 0, 60);\n"
"border-radius: 10px;\n"
"padding: 6px;")

        self.verticalLayout.addWidget(self.lblExpectedSequence)

        self.expecteSequenceWidget = QWidget(sequenceWidget)
        self.expecteSequenceWidget.setObjectName(u"expecteSequenceWidget")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(10)
        sizePolicy1.setHeightForWidth(self.expecteSequenceWidget.sizePolicy().hasHeightForWidth())
        self.expecteSequenceWidget.setSizePolicy(sizePolicy1)
        self.gridLayout = QGridLayout(self.expecteSequenceWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.expectedSequenceLayout = QGridLayout()
        self.expectedSequenceLayout.setObjectName(u"expectedSequenceLayout")

        self.gridLayout.addLayout(self.expectedSequenceLayout, 0, 0, 1, 1)


        self.verticalLayout.addWidget(self.expecteSequenceWidget)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout.addItem(self.verticalSpacer_2)

        self.lblDetectedSequence = QLabel(sequenceWidget)
        self.lblDetectedSequence.setObjectName(u"lblDetectedSequence")
        self.lblDetectedSequence.setEnabled(True)
        self.lblDetectedSequence.setStyleSheet(u"color: rgb(25, 25, 25);\n"
"font: 18pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(255, 255, 255, 215);\n"
"border: 2px solid rgba(0, 0, 0, 60);\n"
"border-radius: 10px;\n"
"padding: 6px;")

        self.verticalLayout.addWidget(self.lblDetectedSequence)

        self.scrollArea = QScrollArea(sequenceWidget)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setEnabled(True)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea.setWidgetResizable(True)
        self.detectedSequenceWidget = QWidget()
        self.detectedSequenceWidget.setObjectName(u"detectedSequenceWidget")
        self.detectedSequenceWidget.setGeometry(QRect(0, 0, 746, 360))
        self.gridLayout_4 = QGridLayout(self.detectedSequenceWidget)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.detectedSequenceLayout = QGridLayout()
        self.detectedSequenceLayout.setObjectName(u"detectedSequenceLayout")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.detectedSequenceLayout.addItem(self.verticalSpacer, 0, 0, 1, 1)


        self.gridLayout_4.addLayout(self.detectedSequenceLayout, 0, 0, 1, 1)

        self.scrollArea.setWidget(self.detectedSequenceWidget)

        self.verticalLayout.addWidget(self.scrollArea)


        self.verticalLayout_2.addLayout(self.verticalLayout)


        self.retranslateUi(sequenceWidget)

        QMetaObject.connectSlotsByName(sequenceWidget)
    # setupUi

    def retranslateUi(self, sequenceWidget):
        sequenceWidget.setWindowTitle(QCoreApplication.translate("sequenceWidget", u"Form", None))
        self.lblExpectedSequence.setText(QCoreApplication.translate("sequenceWidget", u"Secuencia esperada", None))
        self.lblDetectedSequence.setText(QCoreApplication.translate("sequenceWidget", u"Secuencia detectada", None))
    # retranslateUi

