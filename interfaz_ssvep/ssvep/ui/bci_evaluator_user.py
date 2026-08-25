# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'bci_evaluator_user.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QSizePolicy, QWidget)

class Ui_BCIEvaluatorUser(object):
    def setupUi(self, BCIEvaluatorUser):
        if not BCIEvaluatorUser.objectName():
            BCIEvaluatorUser.setObjectName(u"BCIEvaluatorUser")
        BCIEvaluatorUser.resize(834, 556)
        BCIEvaluatorUser.setStyleSheet(u"\n"
"background-color: rgb(255, 255, 255);")
        self.horizontalLayout_2 = QHBoxLayout(BCIEvaluatorUser)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.sequence_layout = QHBoxLayout()
        self.sequence_layout.setObjectName(u"sequence_layout")

        self.horizontalLayout_2.addLayout(self.sequence_layout)


        self.retranslateUi(BCIEvaluatorUser)

        QMetaObject.connectSlotsByName(BCIEvaluatorUser)
    # setupUi

    def retranslateUi(self, BCIEvaluatorUser):
        BCIEvaluatorUser.setWindowTitle(QCoreApplication.translate("BCIEvaluatorUser", u"Form", None))
    # retranslateUi

