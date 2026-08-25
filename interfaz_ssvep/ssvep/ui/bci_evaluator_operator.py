# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'bci_evaluator_operator.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QSpacerItem, QVBoxLayout, QWidget)

class Ui_BCIEvaluatorOperator(object):
    def setupUi(self, BCIEvaluatorOperator):
        if not BCIEvaluatorOperator.objectName():
            BCIEvaluatorOperator.setObjectName(u"BCIEvaluatorOperator")
        BCIEvaluatorOperator.resize(972, 693)
        palette = QPalette()
        brush = QBrush(QColor(255, 255, 255, 255))
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        palette.setBrush(QPalette.ColorGroup.Active, QPalette.ColorRole.Button, brush)
        palette.setBrush(QPalette.ColorGroup.Active, QPalette.ColorRole.Base, brush)
        palette.setBrush(QPalette.ColorGroup.Active, QPalette.ColorRole.Window, brush)
        palette.setBrush(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Button, brush)
        palette.setBrush(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Base, brush)
        palette.setBrush(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Window, brush)
        palette.setBrush(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Button, brush)
        palette.setBrush(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base, brush)
        palette.setBrush(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Window, brush)
        BCIEvaluatorOperator.setPalette(palette)
        font = QFont()
        font.setFamilies([u"SansSerif"])
        BCIEvaluatorOperator.setFont(font)
        BCIEvaluatorOperator.setAutoFillBackground(True)
        BCIEvaluatorOperator.setStyleSheet(u"background-color: rgb(255, 255, 255);")
        self.verticalLayout_2 = QVBoxLayout(BCIEvaluatorOperator)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.widget = QWidget(BCIEvaluatorOperator)
        self.widget.setObjectName(u"widget")
        self.verticalLayout_5 = QVBoxLayout(self.widget)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.btn_start = QPushButton(self.widget)
        self.btn_start.setObjectName(u"btn_start")
        self.btn_start.setStyleSheet(u"QPushButton {\n"
"    color: rgb(20, 20, 20);\n"
"\n"
"    background-color: rgba(255, 255, 255, 220);\n"
"    border: 2px solid rgb(35, 35, 35);\n"
"    border-radius: 10px;\n"
"\n"
"    font: 12pt \"Cascadia Mono ExtraLight\";\n"
"    font-weight: bold;\n"
"\n"
"    padding: 8px 16px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgba(240, 240, 240, 235);\n"
"    border: 2px solid rgb(0, 0, 0);\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: rgba(225, 225, 225, 240);\n"
"    padding-left: 2px;\n"
"    padding-top: 2px;\n"
"}")

        self.horizontalLayout_2.addWidget(self.btn_start)

        self.btn_stop = QPushButton(self.widget)
        self.btn_stop.setObjectName(u"btn_stop")
        self.btn_stop.setStyleSheet(u"QPushButton {\n"
"    color: rgb(20, 20, 20);\n"
"\n"
"    background-color: rgba(255, 255, 255, 220);\n"
"    border: 2px solid rgb(35, 35, 35);\n"
"    border-radius: 10px;\n"
"\n"
"    font: 12pt \"Cascadia Mono ExtraLight\";\n"
"    font-weight: bold;\n"
"\n"
"    padding: 8px 16px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgba(240, 240, 240, 235);\n"
"    border: 2px solid rgb(0, 0, 0);\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: rgba(225, 225, 225, 240);\n"
"    padding-left: 2px;\n"
"    padding-top: 2px;\n"
"}")

        self.horizontalLayout_2.addWidget(self.btn_stop)

        self.lbl_time = QLabel(self.widget)
        self.lbl_time.setObjectName(u"lbl_time")
        self.lbl_time.setStyleSheet(u"color: rgb(15, 15, 15);\n"
"font: 12pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(245, 245, 245, 220);\n"
"border: 1px solid rgba(0, 0, 0, 35);\n"
"border-radius: 8px;\n"
"padding: 5px;")

        self.horizontalLayout_2.addWidget(self.lbl_time)


        self.horizontalLayout.addLayout(self.horizontalLayout_2)


        self.verticalLayout_5.addLayout(self.horizontalLayout)

        self.sequence_layout = QVBoxLayout()
        self.sequence_layout.setObjectName(u"sequence_layout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.sequence_layout.addItem(self.horizontalSpacer)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.sequence_layout.addItem(self.horizontalSpacer_2)


        self.verticalLayout_5.addLayout(self.sequence_layout)


        self.verticalLayout.addWidget(self.widget)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.lbl_hits = QLabel(BCIEvaluatorOperator)
        self.lbl_hits.setObjectName(u"lbl_hits")
        self.lbl_hits.setStyleSheet(u"color: rgb(15, 15, 15);\n"
"font: 12pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(245, 245, 245, 220);\n"
"border: 1px solid rgba(0, 0, 0, 35);\n"
"border-radius: 8px;\n"
"padding: 5px;")

        self.verticalLayout_3.addWidget(self.lbl_hits)

        self.lbl_miss = QLabel(BCIEvaluatorOperator)
        self.lbl_miss.setObjectName(u"lbl_miss")
        self.lbl_miss.setStyleSheet(u"color: rgb(15, 15, 15);\n"
"font: 12pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(245, 245, 245, 220);\n"
"border: 1px solid rgba(0, 0, 0, 35);\n"
"border-radius: 8px;\n"
"padding: 5px;")

        self.verticalLayout_3.addWidget(self.lbl_miss)


        self.horizontalLayout_3.addLayout(self.verticalLayout_3)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_3)


        self.verticalLayout.addLayout(self.horizontalLayout_3)


        self.verticalLayout_2.addLayout(self.verticalLayout)


        self.retranslateUi(BCIEvaluatorOperator)

        QMetaObject.connectSlotsByName(BCIEvaluatorOperator)
    # setupUi

    def retranslateUi(self, BCIEvaluatorOperator):
        BCIEvaluatorOperator.setWindowTitle(QCoreApplication.translate("BCIEvaluatorOperator", u"Form", None))
        self.btn_start.setText(QCoreApplication.translate("BCIEvaluatorOperator", u"Iniciar", None))
        self.btn_stop.setText(QCoreApplication.translate("BCIEvaluatorOperator", u"Detener", None))
        self.lbl_time.setText(QCoreApplication.translate("BCIEvaluatorOperator", u"Tiempo:", None))
        self.lbl_hits.setText(QCoreApplication.translate("BCIEvaluatorOperator", u"Aciertos", None))
        self.lbl_miss.setText(QCoreApplication.translate("BCIEvaluatorOperator", u"Errores", None))
    # retranslateUi

