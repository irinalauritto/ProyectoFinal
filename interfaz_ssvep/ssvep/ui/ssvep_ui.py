# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ssvep.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMenuBar,
    QPushButton, QSizePolicy, QSlider, QSpacerItem,
    QStackedWidget, QStatusBar, QTextBrowser, QVBoxLayout,
    QWidget)
from res.images import resources_rc

class Ui_SSVEP(object):
    def setupUi(self, SSVEP):
        if not SSVEP.objectName():
            SSVEP.setObjectName(u"SSVEP")
        SSVEP.resize(1212, 906)
        SSVEP.setStyleSheet(u"")
        self.centralwidget = QWidget(SSVEP)
        self.centralwidget.setObjectName(u"centralwidget")
        self.centralwidget.setStyleSheet(u"QWidget#centralwidget { \n"
"border-image: url(:/images/fondo.svg) 0 0 0 0 stretch stretch; \n"
"background-position: center; \n"
"}")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.stackedWidget = QStackedWidget(self.centralwidget)
        self.stackedWidget.setObjectName(u"stackedWidget")
        self.page_main_menu = QWidget()
        self.page_main_menu.setObjectName(u"page_main_menu")
        self.verticalLayout_2 = QVBoxLayout(self.page_main_menu)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_5 = QLabel(self.page_main_menu)
        self.label_5.setObjectName(u"label_5")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_5.sizePolicy().hasHeightForWidth())
        self.label_5.setSizePolicy(sizePolicy)
        self.label_5.setPixmap(QPixmap(u":/images/logo_gir.png"))
        self.label_5.setScaledContents(False)
        self.label_5.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)

        self.gridLayout.addWidget(self.label_5, 1, 1, 1, 1)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer_4, 4, 4, 1, 1)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer_2, 2, 4, 1, 1)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 2, 1, 1, 1)

        self.btn_start_main = QPushButton(self.page_main_menu)
        self.btn_start_main.setObjectName(u"btn_start_main")
        self.btn_start_main.setStyleSheet(u"QPushButton {\n"
"    border-style: solid;\n"
"    border-width: 1px;\n"
"    border-color: rgba(0, 51, 102, 250);\n"
"    background-color: rgba(0, 51, 102, 160); /* transparencia */\n"
"    color: rgb(255,255,255);\n"
"    border-radius: 10px;\n"
"    font: 25pt \"Cascadia Mono ExtraLight\";\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgba(0,70,140,180);\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: rgba(0,35,70,200);\n"
"    padding-left: 2px;\n"
"    padding-top: 2px;\n"
"}")

        self.gridLayout.addWidget(self.btn_start_main, 2, 3, 1, 1)

        self.verticalSpacer = QSpacerItem(877, 74, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 6, 0, 1, 7)

        self.verticalSpacer_4 = QSpacerItem(17, 75, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer_4, 1, 3, 1, 1)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer_3, 4, 1, 1, 1)

        self.logo_fiuner = QLabel(self.page_main_menu)
        self.logo_fiuner.setObjectName(u"logo_fiuner")
        sizePolicy.setHeightForWidth(self.logo_fiuner.sizePolicy().hasHeightForWidth())
        self.logo_fiuner.setSizePolicy(sizePolicy)
        self.logo_fiuner.setStyleSheet(u"")
        self.logo_fiuner.setPixmap(QPixmap(u":/images/logo_ingenieria.svg"))
        self.logo_fiuner.setScaledContents(False)
        self.logo_fiuner.setAlignment(Qt.AlignRight|Qt.AlignTop|Qt.AlignTrailing)
        self.logo_fiuner.setOpenExternalLinks(True)

        self.gridLayout.addWidget(self.logo_fiuner, 1, 4, 1, 1)

        self.verticalSpacer_5 = QSpacerItem(17, 75, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer_5, 3, 3, 1, 1)

        self.btn_settings_main = QPushButton(self.page_main_menu)
        self.btn_settings_main.setObjectName(u"btn_settings_main")
        self.btn_settings_main.setEnabled(True)
        self.btn_settings_main.setStyleSheet(u"QPushButton {\n"
"    border-style: solid;\n"
"    border-width: 1px;\n"
"    border-color: rgba(0, 51, 102, 250);\n"
"    background-color: rgba(0, 51, 102, 160); /* transparencia */\n"
"    color: rgb(255,255,255);\n"
"    border-radius: 10px;\n"
"    font: 25pt \"Cascadia Mono ExtraLight\";\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgba(0,70,140,180);\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: rgba(0,35,70,200);\n"
"    padding-left: 2px;\n"
"    padding-top: 2px;\n"
"}")

        self.gridLayout.addWidget(self.btn_settings_main, 4, 3, 1, 1)


        self.verticalLayout_2.addLayout(self.gridLayout)

        self.horizontalLayout_9 = QHBoxLayout()
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.horizontalSpacer_19 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_9.addItem(self.horizontalSpacer_19)

        self.btn_info = QPushButton(self.page_main_menu)
        self.btn_info.setObjectName(u"btn_info")
        self.btn_info.setStyleSheet(u"QPushButton {\n"
"    border-style: solid;\n"
"    border-width: 1px;\n"
"    border-color: rgba(0, 51, 102, 250);\n"
"    background-color: rgba(0, 51, 102, 160); /* transparencia */\n"
"    color: rgb(255,255,255);\n"
"    border-radius: 10px;\n"
"    font: 12pt \"Cascadia Mono ExtraLight\";\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgba(0,70,140,180);\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: rgba(0,35,70,200);\n"
"    padding-left: 2px;\n"
"    padding-top: 2px;\n"
"}")

        self.horizontalLayout_9.addWidget(self.btn_info)


        self.verticalLayout_2.addLayout(self.horizontalLayout_9)

        self.stackedWidget.addWidget(self.page_main_menu)
        self.page_info = QWidget()
        self.page_info.setObjectName(u"page_info")
        self.horizontalLayout_12 = QHBoxLayout(self.page_info)
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.horizontalLayout_11 = QHBoxLayout()
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.verticalLayout_17 = QVBoxLayout()
        self.verticalLayout_17.setObjectName(u"verticalLayout_17")
        self.btn_exit_info = QPushButton(self.page_info)
        self.btn_exit_info.setObjectName(u"btn_exit_info")
        self.btn_exit_info.setStyleSheet(u"QPushButton {\n"
"    border-style: solid;\n"
"    border-width: 1px;\n"
"    border-color: rgba(0, 51, 102, 250);\n"
"    background-color: rgba(0, 51, 102, 160); /* transparencia */\n"
"    color: rgb(255,255,255);\n"
"    border-radius: 10px;\n"
"    font: 12pt \"Cascadia Mono ExtraLight\";\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgba(0,70,140,180);\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: rgba(0,35,70,200);\n"
"    padding-left: 2px;\n"
"    padding-top: 2px;\n"
"}")

        self.verticalLayout_17.addWidget(self.btn_exit_info)

        self.verticalSpacer_9 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_17.addItem(self.verticalSpacer_9)


        self.horizontalLayout_11.addLayout(self.verticalLayout_17)

        self.verticalLayout_16 = QVBoxLayout()
        self.verticalLayout_16.setObjectName(u"verticalLayout_16")
        self.html_viewer = QTextBrowser(self.page_info)
        self.html_viewer.setObjectName(u"html_viewer")

        self.verticalLayout_16.addWidget(self.html_viewer)


        self.horizontalLayout_11.addLayout(self.verticalLayout_16)


        self.horizontalLayout_12.addLayout(self.horizontalLayout_11)

        self.stackedWidget.addWidget(self.page_info)
        self.page_user_selection = QWidget()
        self.page_user_selection.setObjectName(u"page_user_selection")
        self.verticalLayout_3 = QVBoxLayout(self.page_user_selection)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.titulo = QLabel(self.page_user_selection)
        self.titulo.setObjectName(u"titulo")
        self.titulo.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 12 22pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"")

        self.horizontalLayout_3.addWidget(self.titulo)

        self.horizontalSpacer_12 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_12)


        self.verticalLayout_3.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalSpacer_14 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer_14)

        self.ql_user_list = QListWidget(self.page_user_selection)
        self.ql_user_list.setObjectName(u"ql_user_list")
        self.ql_user_list.setStyleSheet(u"QListWidget {\n"
"    font-family: \"Cascadia Mono Extralight\";\n"
"    font-size: 18pt;\n"
"    color: white;\n"
"}\n"
"\n"
"QListWidget {\n"
"    background-color: rgba(0, 51, 102, 120);\n"
"    color: white;\n"
"    border-radius: 10px;\n"
"    padding: 5px;\n"
"}\n"
"\n"
"/* Cuando pas\u00e1s el mouse por TODO el cuadro */\n"
"QListWidget:hover {\n"
"    background-color: rgba(0, 51, 102, 160);\n"
"}\n"
"\n"
"/* \u00cdtems normales */\n"
"QListWidget::item {\n"
"    padding: 8px;\n"
"    background-color: transparent;\n"
"}\n"
"\n"
"/* Cuando pas\u00e1s el mouse sobre un \u00edtem */\n"
"QListWidget::item:hover {\n"
"    background-color: rgba(255, 255, 255, 40);\n"
"}\n"
"\n"
"/* \u00cdtem seleccionado */\n"
"QListWidget::item:selected {\n"
"    background-color: rgba(0, 51, 102, 220);\n"
"    color: white;\n"
"}\n"
"\n"
"/* \u00cdtem seleccionado + hover (opcional, queda m\u00e1s fluido) */\n"
"QListWidget::item:selected:hover {\n"
"    background-color: rgba(0, 51, 102, 255);\n"
"}")

        self.horizontalLayout_4.addWidget(self.ql_user_list)

        self.horizontalSpacer_13 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer_13)


        self.verticalLayout_3.addLayout(self.horizontalLayout_4)

        self.verticalSpacer_6 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_3.addItem(self.verticalSpacer_6)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.nuevo_usuario = QLabel(self.page_user_selection)
        self.nuevo_usuario.setObjectName(u"nuevo_usuario")
        self.nuevo_usuario.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 15pt \"Cascadia Mono ExtraLight\";\n"
"\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.horizontalLayout.addWidget(self.nuevo_usuario)

        self.line = QFrame(self.page_user_selection)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.horizontalLayout.addWidget(self.line)

        self.horizontalSpacer_9 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_9)

        self.le_input_username = QLineEdit(self.page_user_selection)
        self.le_input_username.setObjectName(u"le_input_username")
        self.le_input_username.setMaximumSize(QSize(250, 16777215))

        self.horizontalLayout.addWidget(self.le_input_username)

        self.horizontalSpacer_10 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_10)

        self.btn_user_save = QPushButton(self.page_user_selection)
        self.btn_user_save.setObjectName(u"btn_user_save")
        self.btn_user_save.setStyleSheet(u"QPushButton {\n"
"    border-style: solid;\n"
"    border-width: 1px;\n"
"    border-color: rgba(0, 51, 102, 250);\n"
"    background-color: rgba(0, 51, 102, 160); /* transparencia */\n"
"    color: rgb(255,255,255);\n"
"    border-radius: 10px;\n"
"    font: 25pt \"Cascadia Mono ExtraLight\";\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgba(0,70,140,180);\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: rgba(0,35,70,200);\n"
"    padding-left: 2px;\n"
"    padding-top: 2px;\n"
"}")

        self.horizontalLayout.addWidget(self.btn_user_save)


        self.verticalLayout_3.addLayout(self.horizontalLayout)

        self.verticalSpacer_7 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_3.addItem(self.verticalSpacer_7)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.btn_user_exit = QPushButton(self.page_user_selection)
        self.btn_user_exit.setObjectName(u"btn_user_exit")
        self.btn_user_exit.setStyleSheet(u"QPushButton {\n"
"    border-style: solid;\n"
"    border-width: 1px;\n"
"    border-color: rgba(0, 51, 102, 250);\n"
"    background-color: rgba(0, 51, 102, 160); /* transparencia */\n"
"    color: rgb(255,255,255);\n"
"    border-radius: 10px;\n"
"    font: 25pt \"Cascadia Mono ExtraLight\";\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgba(0,70,140,180);\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: rgba(0,35,70,200);\n"
"    padding-left: 2px;\n"
"    padding-top: 2px;\n"
"}")

        self.horizontalLayout_2.addWidget(self.btn_user_exit)

        self.horizontalSpacer_11 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_11)

        self.btn_user_continue = QPushButton(self.page_user_selection)
        self.btn_user_continue.setObjectName(u"btn_user_continue")
        self.btn_user_continue.setStyleSheet(u"QPushButton {\n"
"    border-style: solid;\n"
"    border-width: 1px;\n"
"    border-color: rgba(0, 51, 102, 250);\n"
"    background-color: rgba(0, 51, 102, 160); /* transparencia */\n"
"    color: rgb(255,255,255);\n"
"    border-radius: 10px;\n"
"    font: 25pt \"Cascadia Mono ExtraLight\";\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgba(0,70,140,180);\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: rgba(0,35,70,200);\n"
"    padding-left: 2px;\n"
"    padding-top: 2px;\n"
"}")

        self.horizontalLayout_2.addWidget(self.btn_user_continue)


        self.verticalLayout_3.addLayout(self.horizontalLayout_2)

        self.stackedWidget.addWidget(self.page_user_selection)
        self.page_user_config = QWidget()
        self.page_user_config.setObjectName(u"page_user_config")
        self.verticalLayout_6 = QVBoxLayout(self.page_user_config)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.horizontalLayout_15 = QHBoxLayout()
        self.horizontalLayout_15.setObjectName(u"horizontalLayout_15")
        self.user_cfg_tile = QLabel(self.page_user_config)
        self.user_cfg_tile.setObjectName(u"user_cfg_tile")
        self.user_cfg_tile.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 12 18pt \"Cascadia Mono ExtraLight\";")

        self.horizontalLayout_15.addWidget(self.user_cfg_tile)

        self.horizontalSpacer_36 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_15.addItem(self.horizontalSpacer_36)

        self.lbl_user_cfg_user_n = QLabel(self.page_user_config)
        self.lbl_user_cfg_user_n.setObjectName(u"lbl_user_cfg_user_n")
        self.lbl_user_cfg_user_n.setStyleSheet(u"    background-color: rgb(210, 177, 252);\n"
"    border: 2px solid rgb(100, 170, 255);\n"
"    border-radius: 12px;\n"
"    padding-left: 10px;\n"
"    color: black;\n"
"    font: 12pt \"Cascadia Mono\";")

        self.horizontalLayout_15.addWidget(self.lbl_user_cfg_user_n)


        self.verticalLayout_6.addLayout(self.horizontalLayout_15)

        self.verticalSpacer_16 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_6.addItem(self.verticalSpacer_16)

        self.horizontalLayout_16 = QHBoxLayout()
        self.horizontalLayout_16.setObjectName(u"horizontalLayout_16")
        self.verticalLayout_8 = QVBoxLayout()
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.horizontalLayout_18 = QHBoxLayout()
        self.horizontalLayout_18.setObjectName(u"horizontalLayout_18")
        self.verticalLayout_9 = QVBoxLayout()
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.label_21 = QLabel(self.page_user_config)
        self.label_21.setObjectName(u"label_21")
        self.label_21.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 18pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.verticalLayout_9.addWidget(self.label_21)

        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.label_27 = QLabel(self.page_user_config)
        self.label_27.setObjectName(u"label_27")
        self.label_27.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 10pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.horizontalLayout_8.addWidget(self.label_27)

        self.verticalLayout_7 = QVBoxLayout()
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.lbl_time_response = QLabel(self.page_user_config)
        self.lbl_time_response.setObjectName(u"lbl_time_response")
        self.lbl_time_response.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 10pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;")
        self.lbl_time_response.setAlignment(Qt.AlignCenter)

        self.verticalLayout_7.addWidget(self.lbl_time_response)

        self.hsld_time_window = QSlider(self.page_user_config)
        self.hsld_time_window.setObjectName(u"hsld_time_window")
        self.hsld_time_window.setFocusPolicy(Qt.ClickFocus)
        self.hsld_time_window.setStyleSheet(u"QSlider::groove:horizontal {\n"
"    height: 6px;\n"
"    background: #BDBDBD;\n"
"    border-radius: 3px;\n"
"}\n"
"\n"
"QSlider::sub-page:horizontal {\n"
"    background: #2D89EF;\n"
"    border-radius: 3px;\n"
"}\n"
"\n"
"QSlider::handle:horizontal {\n"
"    background: white;\n"
"    border: 2px solid #2D89EF;\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    margin: -7px 0;    /* centra el c\u00edrculo sobre la barra */\n"
"    border-radius: 9px; /* hace el handle circular */\n"
"}\n"
"\n"
"QSlider::handle:horizontal:hover {\n"
"    background: #F5F5F5;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:pressed {\n"
"    background: #E0E0E0;\n"
"}")
        self.hsld_time_window.setMinimum(10)
        self.hsld_time_window.setMaximum(40)
        self.hsld_time_window.setSingleStep(5)
        self.hsld_time_window.setSliderPosition(20)
        self.hsld_time_window.setOrientation(Qt.Horizontal)

        self.verticalLayout_7.addWidget(self.hsld_time_window)


        self.horizontalLayout_8.addLayout(self.verticalLayout_7)

        self.label_28 = QLabel(self.page_user_config)
        self.label_28.setObjectName(u"label_28")
        self.label_28.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 10pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.horizontalLayout_8.addWidget(self.label_28)


        self.verticalLayout_9.addLayout(self.horizontalLayout_8)


        self.horizontalLayout_18.addLayout(self.verticalLayout_9)

        self.horizontalSpacer_28 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_18.addItem(self.horizontalSpacer_28)


        self.verticalLayout_8.addLayout(self.horizontalLayout_18)

        self.horizontalLayout_34 = QHBoxLayout()
        self.horizontalLayout_34.setObjectName(u"horizontalLayout_34")
        self.verticalLayout_23 = QVBoxLayout()
        self.verticalLayout_23.setObjectName(u"verticalLayout_23")
        self.label_20 = QLabel(self.page_user_config)
        self.label_20.setObjectName(u"label_20")
        self.label_20.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 13pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.verticalLayout_23.addWidget(self.label_20)

        self.qc_estimulus_method = QComboBox(self.page_user_config)
        self.qc_estimulus_method.addItem("")
        self.qc_estimulus_method.addItem("")
        self.qc_estimulus_method.setObjectName(u"qc_estimulus_method")
        self.qc_estimulus_method.setStyleSheet(u"font: bold 12pt \"Cascadia Mono Extralight\";")

        self.verticalLayout_23.addWidget(self.qc_estimulus_method)


        self.horizontalLayout_34.addLayout(self.verticalLayout_23)

        self.horizontalSpacer_26 = QSpacerItem(40, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_34.addItem(self.horizontalSpacer_26)

        self.verticalLayout_24 = QVBoxLayout()
        self.verticalLayout_24.setObjectName(u"verticalLayout_24")
        self.label_6 = QLabel(self.page_user_config)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 13pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.verticalLayout_24.addWidget(self.label_6)

        self.qc_cass_method = QComboBox(self.page_user_config)
        self.qc_cass_method.addItem("")
        self.qc_cass_method.setObjectName(u"qc_cass_method")
        self.qc_cass_method.setStyleSheet(u"font: bold 12pt \"Cascadia Mono Extralight\";")

        self.verticalLayout_24.addWidget(self.qc_cass_method)


        self.horizontalLayout_34.addLayout(self.verticalLayout_24)

        self.horizontalSpacer_27 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_34.addItem(self.horizontalSpacer_27)


        self.verticalLayout_8.addLayout(self.horizontalLayout_34)

        self.verticalSpacer_18 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_8.addItem(self.verticalSpacer_18)

        self.horizontalLayout_33 = QHBoxLayout()
        self.horizontalLayout_33.setObjectName(u"horizontalLayout_33")
        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.led_user_cfg_esc = QLineEdit(self.page_user_config)
        self.led_user_cfg_esc.setObjectName(u"led_user_cfg_esc")
        self.led_user_cfg_esc.setMinimumSize(QSize(0, 0))
        self.led_user_cfg_esc.setMaximumSize(QSize(100, 16777215))
        self.led_user_cfg_esc.setStyleSheet(u"QLineEdit {\n"
"    background-color: rgb(210, 177, 252);\n"
"    border: 2px solid rgb(100, 170, 255);\n"
"    border-radius: 12px;\n"
"    padding-left: 10px;\n"
"    color: black;\n"
"    font: 12pt \"Cascadia Mono\";\n"
"}")
        self.led_user_cfg_esc.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignVCenter)

        self.gridLayout_2.addWidget(self.led_user_cfg_esc, 1, 2, 1, 1)

        self.label_11 = QLabel(self.page_user_config)
        self.label_11.setObjectName(u"label_11")
        self.label_11.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 15pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.gridLayout_2.addWidget(self.label_11, 0, 2, 1, 1)

        self.led_user_cfg_space = QLineEdit(self.page_user_config)
        self.led_user_cfg_space.setObjectName(u"led_user_cfg_space")
        self.led_user_cfg_space.setMaximumSize(QSize(100, 16777215))
        self.led_user_cfg_space.setStyleSheet(u"QLineEdit {\n"
"    background-color: rgb(210, 177, 252);\n"
"    border: 2px solid rgb(100, 170, 255);\n"
"    border-radius: 12px;\n"
"    padding-left: 10px;\n"
"    color: black;\n"
"    font: 12pt \"Cascadia Mono\";\n"
"}")

        self.gridLayout_2.addWidget(self.led_user_cfg_space, 2, 2, 1, 1)

        self.label_12 = QLabel(self.page_user_config)
        self.label_12.setObjectName(u"label_12")
        self.label_12.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 15pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.gridLayout_2.addWidget(self.label_12, 0, 0, 1, 1)

        self.chk_cfg_show_space = QCheckBox(self.page_user_config)
        self.chk_cfg_show_space.setObjectName(u"chk_cfg_show_space")
        font = QFont()
        font.setFamilies([u"Cascadia Mono Extralight"])
        font.setPointSize(12)
        font.setBold(True)
        font.setItalic(False)
        font.setStrikeOut(False)
        font.setKerning(True)
        self.chk_cfg_show_space.setFont(font)
        self.chk_cfg_show_space.setStyleSheet(u"QCheckBox {\n"
"    color: white;\n"
"    font: bold 12pt \"Cascadia Mono Extralight\";\n"
"}\n"
"\n"
"QCheckBox::indicator {\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    border-radius: 9px; /* c\u00edrculo */\n"
"    border: 2px solid rgb(100, 180, 255);\n"
"    background-color: rgba(255,255,255,80);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    background-color: rgb(0, 170, 255);\n"
"    border: 2px solid white;\n"
"}")

        self.gridLayout_2.addWidget(self.chk_cfg_show_space, 2, 3, 1, 1)

        self.led_user_cfg_down = QLineEdit(self.page_user_config)
        self.led_user_cfg_down.setObjectName(u"led_user_cfg_down")
        self.led_user_cfg_down.setMaximumSize(QSize(100, 16777215))
        self.led_user_cfg_down.setStyleSheet(u"QLineEdit {\n"
"    background-color: rgb(210, 177, 252);\n"
"    border: 2px solid rgb(100, 170, 255);\n"
"    border-radius: 12px;\n"
"    padding-left: 10px;\n"
"    color: black;\n"
"    font: 12pt \"Cascadia Mono\";\n"
"}")

        self.gridLayout_2.addWidget(self.led_user_cfg_down, 6, 2, 1, 1)

        self.led_user_cfg_left = QLineEdit(self.page_user_config)
        self.led_user_cfg_left.setObjectName(u"led_user_cfg_left")
        self.led_user_cfg_left.setMaximumSize(QSize(100, 16777215))
        self.led_user_cfg_left.setStyleSheet(u"QLineEdit {\n"
"    background-color: rgb(210, 177, 252);\n"
"    border: 2px solid rgb(100, 170, 255);\n"
"    border-radius: 12px;\n"
"    padding-left: 10px;\n"
"    color: black;\n"
"    font: 12pt \"Cascadia Mono\";\n"
"}")

        self.gridLayout_2.addWidget(self.led_user_cfg_left, 5, 2, 1, 1)

        self.chk_cfg_show_esc = QCheckBox(self.page_user_config)
        self.chk_cfg_show_esc.setObjectName(u"chk_cfg_show_esc")
        self.chk_cfg_show_esc.setStyleSheet(u"QCheckBox {\n"
"    color: white;\n"
"    font: bold 12pt \"Cascadia Mono Extralight\";\n"
"}\n"
"\n"
"QCheckBox::indicator {\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    border-radius: 9px; /* c\u00edrculo */\n"
"    border: 2px solid rgb(100, 180, 255);\n"
"    background-color: rgba(255,255,255,80);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    background-color: rgb(0, 170, 255);\n"
"    border: 2px solid white;\n"
"}")

        self.gridLayout_2.addWidget(self.chk_cfg_show_esc, 1, 3, 1, 1)

        self.chk_toggle_space = QCheckBox(self.page_user_config)
        self.chk_toggle_space.setObjectName(u"chk_toggle_space")
        self.chk_toggle_space.setStyleSheet(u"QCheckBox {\n"
"    color: white;\n"
"    font: bold 12pt \"Cascadia Mono Extralight\";\n"
"}\n"
"\n"
"QCheckBox::indicator {\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    border-radius: 9px; /* c\u00edrculo */\n"
"    border: 2px solid rgb(100, 180, 255);\n"
"    background-color: rgba(255,255,255,80);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    background-color: rgb(0, 170, 255);\n"
"    border: 2px solid white;\n"
"}")

        self.gridLayout_2.addWidget(self.chk_toggle_space, 2, 4, 1, 1)

        self.label_24 = QLabel(self.page_user_config)
        self.label_24.setObjectName(u"label_24")
        self.label_24.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 15pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.gridLayout_2.addWidget(self.label_24, 0, 4, 1, 1)

        self.label_13 = QLabel(self.page_user_config)
        self.label_13.setObjectName(u"label_13")
        self.label_13.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 13pt \"Cascadia Mono ExtraLight\";\n"
"\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;\n"
"\n"
"")

        self.gridLayout_2.addWidget(self.label_13, 1, 0, 1, 1)

        self.label_10 = QLabel(self.page_user_config)
        self.label_10.setObjectName(u"label_10")
        self.label_10.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 15pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.gridLayout_2.addWidget(self.label_10, 0, 3, 1, 1)

        self.label_16 = QLabel(self.page_user_config)
        self.label_16.setObjectName(u"label_16")
        self.label_16.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 13pt \"Cascadia Mono ExtraLight\";\n"
"\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.gridLayout_2.addWidget(self.label_16, 4, 0, 1, 1)

        self.label_14 = QLabel(self.page_user_config)
        self.label_14.setObjectName(u"label_14")
        self.label_14.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 13pt \"Cascadia Mono ExtraLight\";\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.gridLayout_2.addWidget(self.label_14, 2, 0, 1, 1)

        self.label_18 = QLabel(self.page_user_config)
        self.label_18.setObjectName(u"label_18")
        self.label_18.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 13pt \"Cascadia Mono ExtraLight\";\n"
"\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.gridLayout_2.addWidget(self.label_18, 6, 0, 1, 1)

        self.label_15 = QLabel(self.page_user_config)
        self.label_15.setObjectName(u"label_15")
        self.label_15.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 13pt \"Cascadia Mono ExtraLight\";\n"
"\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.gridLayout_2.addWidget(self.label_15, 3, 0, 1, 1)

        self.label_17 = QLabel(self.page_user_config)
        self.label_17.setObjectName(u"label_17")
        self.label_17.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 13pt \"Cascadia Mono ExtraLight\";\n"
"\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.gridLayout_2.addWidget(self.label_17, 5, 0, 1, 1)

        self.led_user_cfg_right = QLineEdit(self.page_user_config)
        self.led_user_cfg_right.setObjectName(u"led_user_cfg_right")
        self.led_user_cfg_right.setMaximumSize(QSize(100, 16777215))
        self.led_user_cfg_right.setStyleSheet(u"QLineEdit {\n"
"    background-color: rgb(210, 177, 252);\n"
"    border: 2px solid rgb(100, 170, 255);\n"
"    border-radius: 12px;\n"
"    padding-left: 10px;\n"
"    color: black;\n"
"    font: 12pt \"Cascadia Mono\";\n"
"}")

        self.gridLayout_2.addWidget(self.led_user_cfg_right, 3, 2, 1, 1)

        self.led_user_cfg_up = QLineEdit(self.page_user_config)
        self.led_user_cfg_up.setObjectName(u"led_user_cfg_up")
        self.led_user_cfg_up.setMaximumSize(QSize(100, 16777215))
        self.led_user_cfg_up.setStyleSheet(u"QLineEdit {\n"
"    background-color: rgb(210, 177, 252);\n"
"    border: 2px solid rgb(100, 170, 255);\n"
"    border-radius: 12px;\n"
"    padding-left: 10px;\n"
"    color: black;\n"
"    font: 12pt \"Cascadia Mono\";\n"
"}")

        self.gridLayout_2.addWidget(self.led_user_cfg_up, 4, 2, 1, 1)

        self.chk_cfg_show_up = QCheckBox(self.page_user_config)
        self.chk_cfg_show_up.setObjectName(u"chk_cfg_show_up")
        self.chk_cfg_show_up.setStyleSheet(u"QCheckBox {\n"
"    color: white;\n"
"    font: bold 12pt \"Cascadia Mono Extralight\";\n"
"}\n"
"\n"
"QCheckBox::indicator {\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    border-radius: 9px; /* c\u00edrculo */\n"
"    border: 2px solid rgb(100, 180, 255);\n"
"    background-color: rgba(255,255,255,80);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    background-color: rgb(0, 170, 255);\n"
"    border: 2px solid white;\n"
"}")

        self.gridLayout_2.addWidget(self.chk_cfg_show_up, 4, 3, 1, 1)

        self.chk_cfg_show_right = QCheckBox(self.page_user_config)
        self.chk_cfg_show_right.setObjectName(u"chk_cfg_show_right")
        self.chk_cfg_show_right.setStyleSheet(u"QCheckBox {\n"
"    color: white;\n"
"    font: bold 12pt \"Cascadia Mono Extralight\";\n"
"}\n"
"\n"
"QCheckBox::indicator {\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    border-radius: 9px; /* c\u00edrculo */\n"
"    border: 2px solid rgb(100, 180, 255);\n"
"    background-color: rgba(255,255,255,80);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    background-color: rgb(0, 170, 255);\n"
"    border: 2px solid white;\n"
"}")

        self.gridLayout_2.addWidget(self.chk_cfg_show_right, 3, 3, 1, 1)

        self.chk_cfg_show_left = QCheckBox(self.page_user_config)
        self.chk_cfg_show_left.setObjectName(u"chk_cfg_show_left")
        self.chk_cfg_show_left.setStyleSheet(u"QCheckBox {\n"
"    color: white;\n"
"    font: bold 12pt \"Cascadia Mono Extralight\";\n"
"}\n"
"\n"
"QCheckBox::indicator {\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    border-radius: 9px; /* c\u00edrculo */\n"
"    border: 2px solid rgb(100, 180, 255);\n"
"    background-color: rgba(255,255,255,80);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    background-color: rgb(0, 170, 255);\n"
"    border: 2px solid white;\n"
"}")

        self.gridLayout_2.addWidget(self.chk_cfg_show_left, 5, 3, 1, 1)

        self.chk_cfg_show_down = QCheckBox(self.page_user_config)
        self.chk_cfg_show_down.setObjectName(u"chk_cfg_show_down")
        self.chk_cfg_show_down.setStyleSheet(u"QCheckBox {\n"
"    color: white;\n"
"    font: bold 12pt \"Cascadia Mono Extralight\";\n"
"}\n"
"\n"
"QCheckBox::indicator {\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    border-radius: 9px; /* c\u00edrculo */\n"
"    border: 2px solid rgb(100, 180, 255);\n"
"    background-color: rgba(255,255,255,80);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    background-color: rgb(0, 170, 255);\n"
"    border: 2px solid white;\n"
"}")

        self.gridLayout_2.addWidget(self.chk_cfg_show_down, 6, 3, 1, 1)

        self.label_23 = QLabel(self.page_user_config)
        self.label_23.setObjectName(u"label_23")
        self.label_23.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 13pt \"Cascadia Mono ExtraLight\";\n"
"\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;\n"
"\n"
"")

        self.gridLayout_2.addWidget(self.label_23, 1, 1, 1, 1)

        self.label_29 = QLabel(self.page_user_config)
        self.label_29.setObjectName(u"label_29")
        self.label_29.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 13pt \"Cascadia Mono ExtraLight\";\n"
"\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;\n"
"\n"
"")

        self.gridLayout_2.addWidget(self.label_29, 2, 1, 1, 1)

        self.label_30 = QLabel(self.page_user_config)
        self.label_30.setObjectName(u"label_30")
        self.label_30.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 13pt \"Cascadia Mono ExtraLight\";\n"
"\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;\n"
"\n"
"")

        self.gridLayout_2.addWidget(self.label_30, 3, 1, 1, 1)

        self.label_31 = QLabel(self.page_user_config)
        self.label_31.setObjectName(u"label_31")
        self.label_31.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 13pt \"Cascadia Mono ExtraLight\";\n"
"\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;\n"
"\n"
"")

        self.gridLayout_2.addWidget(self.label_31, 4, 1, 1, 1)

        self.label_32 = QLabel(self.page_user_config)
        self.label_32.setObjectName(u"label_32")
        self.label_32.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 13pt \"Cascadia Mono ExtraLight\";\n"
"\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;\n"
"\n"
"")

        self.gridLayout_2.addWidget(self.label_32, 5, 1, 1, 1)

        self.label_33 = QLabel(self.page_user_config)
        self.label_33.setObjectName(u"label_33")
        self.label_33.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 13pt \"Cascadia Mono ExtraLight\";\n"
"\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;\n"
"\n"
"")

        self.gridLayout_2.addWidget(self.label_33, 6, 1, 1, 1)


        self.horizontalLayout_33.addLayout(self.gridLayout_2)


        self.verticalLayout_8.addLayout(self.horizontalLayout_33)

        self.horizontalLayout_press_duration = QHBoxLayout()
        self.horizontalLayout_press_duration.setObjectName(u"horizontalLayout_press_duration")
        self.verticalLayout_press_duration = QVBoxLayout()
        self.verticalLayout_press_duration.setObjectName(u"verticalLayout_press_duration")
        self.label_press_duration_title = QLabel(self.page_user_config)
        self.label_press_duration_title.setObjectName(u"label_press_duration_title")
        self.label_press_duration_title.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 15pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.verticalLayout_press_duration.addWidget(self.label_press_duration_title)

        self.horizontalLayout_press_duration_row = QHBoxLayout()
        self.horizontalLayout_press_duration_row.setObjectName(u"horizontalLayout_press_duration_row")
        self.hsld_press_duration = QSlider(self.page_user_config)
        self.hsld_press_duration.setObjectName(u"hsld_press_duration")
        self.hsld_press_duration.setFocusPolicy(Qt.ClickFocus)
        self.hsld_press_duration.setStyleSheet(u"QSlider::groove:horizontal {\n"
"    height: 6px;\n"
"    background: #BDBDBD;\n"
"    border-radius: 3px;\n"
"}\n"
"\n"
"QSlider::sub-page:horizontal {\n"
"    background: #2D89EF;\n"
"    border-radius: 3px;\n"
"}\n"
"\n"
"QSlider::handle:horizontal {\n"
"    background: white;\n"
"    border: 2px solid #2D89EF;\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    margin: -7px 0;\n"
"    border-radius: 9px;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:hover {\n"
"    background: #F5F5F5;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:pressed {\n"
"    background: #E0E0E0;\n"
"}")
        self.hsld_press_duration.setMinimum(100)
        self.hsld_press_duration.setMaximum(10000)
        self.hsld_press_duration.setSingleStep(100)
        self.hsld_press_duration.setSliderPosition(250)
        self.hsld_press_duration.setOrientation(Qt.Horizontal)

        self.horizontalLayout_press_duration_row.addWidget(self.hsld_press_duration)

        self.lbl_press_duration_value = QLabel(self.page_user_config)
        self.lbl_press_duration_value.setObjectName(u"lbl_press_duration_value")
        self.lbl_press_duration_value.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 10pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.horizontalLayout_press_duration_row.addWidget(self.lbl_press_duration_value)


        self.verticalLayout_press_duration.addLayout(self.horizontalLayout_press_duration_row)


        self.horizontalLayout_press_duration.addLayout(self.verticalLayout_press_duration)

        self.horizontalSpacer_press_duration = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_press_duration.addItem(self.horizontalSpacer_press_duration)


        self.verticalLayout_8.addLayout(self.horizontalLayout_press_duration)


        self.horizontalLayout_16.addLayout(self.verticalLayout_8)

        self.head_widet = QWidget(self.page_user_config)
        self.head_widet.setObjectName(u"head_widet")
        self.head_widet.setMinimumSize(QSize(30, 10))
        self.verticalLayout_22 = QVBoxLayout(self.head_widet)
        self.verticalLayout_22.setObjectName(u"verticalLayout_22")
        self.head_channels_layout = QVBoxLayout()
        self.head_channels_layout.setObjectName(u"head_channels_layout")

        self.verticalLayout_22.addLayout(self.head_channels_layout)


        self.horizontalLayout_16.addWidget(self.head_widet)

        self.horizontalSpacer_38 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_16.addItem(self.horizontalSpacer_38)


        self.verticalLayout_6.addLayout(self.horizontalLayout_16)

        self.verticalSpacer_17 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_6.addItem(self.verticalSpacer_17)

        self.horizontalLayout_17 = QHBoxLayout()
        self.horizontalLayout_17.setObjectName(u"horizontalLayout_17")
        self.btn_user_cfg_exit = QPushButton(self.page_user_config)
        self.btn_user_cfg_exit.setObjectName(u"btn_user_cfg_exit")
        self.btn_user_cfg_exit.setStyleSheet(u"QPushButton {\n"
"    border-style: solid;\n"
"    border-width: 1px;\n"
"    border-color: rgba(0, 51, 102, 250);\n"
"    background-color: rgba(0, 51, 102, 160); /* transparencia */\n"
"    color: rgb(255,255,255);\n"
"    border-radius: 10px;\n"
"    font: 25pt \"Cascadia Mono ExtraLight\";\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgba(0,70,140,180);\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: rgba(0,35,70,200);\n"
"    padding-left: 2px;\n"
"    padding-top: 2px;\n"
"}")

        self.horizontalLayout_17.addWidget(self.btn_user_cfg_exit)

        self.horizontalSpacer_39 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_17.addItem(self.horizontalSpacer_39)

        self.btn_user_cfg_remove = QPushButton(self.page_user_config)
        self.btn_user_cfg_remove.setObjectName(u"btn_user_cfg_remove")
        self.btn_user_cfg_remove.setStyleSheet(u"QPushButton {\n"
"    border-style: solid;\n"
"    border-width: 1px;\n"
"    border-color: rgba(0, 51, 102, 250);\n"
"    background-color: rgba(0, 51, 102, 160); /* transparencia */\n"
"    color: rgb(255,255,255);\n"
"    border-radius: 10px;\n"
"    font: 25pt \"Cascadia Mono ExtraLight\";\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgba(0,70,140,180);\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: rgba(0,35,70,200);\n"
"    padding-left: 2px;\n"
"    padding-top: 2px;\n"
"}")

        self.horizontalLayout_17.addWidget(self.btn_user_cfg_remove)

        self.horizontalSpacer_18 = QSpacerItem(40, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_17.addItem(self.horizontalSpacer_18)

        self.btn_user_cfg_save = QPushButton(self.page_user_config)
        self.btn_user_cfg_save.setObjectName(u"btn_user_cfg_save")
        self.btn_user_cfg_save.setStyleSheet(u"QPushButton {\n"
"    border-style: solid;\n"
"    border-width: 1px;\n"
"    border-color: rgba(0, 51, 102, 250);\n"
"    background-color: rgba(0, 51, 102, 160); /* transparencia */\n"
"    color: rgb(255,255,255);\n"
"    border-radius: 10px;\n"
"    font: 25pt \"Cascadia Mono ExtraLight\";\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgba(0,70,140,180);\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: rgba(0,35,70,200);\n"
"    padding-left: 2px;\n"
"    padding-top: 2px;\n"
"}")

        self.horizontalLayout_17.addWidget(self.btn_user_cfg_save)

        self.horizontalSpacer_6 = QSpacerItem(40, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_17.addItem(self.horizontalSpacer_6)

        self.btn_user_cfg_continue = QPushButton(self.page_user_config)
        self.btn_user_cfg_continue.setObjectName(u"btn_user_cfg_continue")
        self.btn_user_cfg_continue.setStyleSheet(u"QPushButton {\n"
"    border-style: solid;\n"
"    border-width: 1px;\n"
"    border-color: rgba(0, 51, 102, 250);\n"
"    background-color: rgba(0, 51, 102, 160); /* transparencia */\n"
"    color: rgb(255,255,255);\n"
"    border-radius: 10px;\n"
"    font: 25pt \"Cascadia Mono ExtraLight\";\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgba(0,70,140,180);\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: rgba(0,35,70,200);\n"
"    padding-left: 2px;\n"
"    padding-top: 2px;\n"
"}")

        self.horizontalLayout_17.addWidget(self.btn_user_cfg_continue)


        self.verticalLayout_6.addLayout(self.horizontalLayout_17)

        self.stackedWidget.addWidget(self.page_user_config)
        self.page_game_setup = QWidget()
        self.page_game_setup.setObjectName(u"page_game_setup")
        self.verticalLayout_4 = QVBoxLayout(self.page_game_setup)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.label = QLabel(self.page_game_setup)
        self.label.setObjectName(u"label")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy1)
        self.label.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 18pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 120);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.verticalLayout_5.addWidget(self.label)

        self.chk_bandpass = QCheckBox(self.page_game_setup)
        self.chk_bandpass.setObjectName(u"chk_bandpass")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.chk_bandpass.sizePolicy().hasHeightForWidth())
        self.chk_bandpass.setSizePolicy(sizePolicy2)
        self.chk_bandpass.setStyleSheet(u"QCheckBox {\n"
"    color: white;\n"
"    font: bold 12pt \"Cascadia Mono Extralight\";\n"
"}\n"
"\n"
"QCheckBox::indicator {\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    border-radius: 9px; /* c\u00edrculo */\n"
"    border: 2px solid rgb(100, 180, 255);\n"
"    background-color: rgba(255,255,255,80);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    background-color: rgb(0, 170, 255);\n"
"    border: 2px solid white;\n"
"}")

        self.verticalLayout_5.addWidget(self.chk_bandpass)

        self.chk_notch = QCheckBox(self.page_game_setup)
        self.chk_notch.setObjectName(u"chk_notch")
        sizePolicy2.setHeightForWidth(self.chk_notch.sizePolicy().hasHeightForWidth())
        self.chk_notch.setSizePolicy(sizePolicy2)
        self.chk_notch.setStyleSheet(u"QCheckBox {\n"
"    color: white;\n"
"    font: bold 12pt \"Cascadia Mono Extralight\";\n"
"}\n"
"\n"
"QCheckBox::indicator {\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    border-radius: 9px; /* c\u00edrculo */\n"
"    border: 2px solid rgb(100, 180, 255);\n"
"    background-color: rgba(255,255,255,80);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    background-color: rgb(0, 170, 255);\n"
"    border: 2px solid white;\n"
"}")

        self.verticalLayout_5.addWidget(self.chk_notch)

        self.chk_average = QCheckBox(self.page_game_setup)
        self.chk_average.setObjectName(u"chk_average")
        sizePolicy2.setHeightForWidth(self.chk_average.sizePolicy().hasHeightForWidth())
        self.chk_average.setSizePolicy(sizePolicy2)
        self.chk_average.setStyleSheet(u"QCheckBox {\n"
"    color: white;\n"
"    font: bold 12pt \"Cascadia Mono Extralight\";\n"
"}\n"
"\n"
"QCheckBox::indicator {\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    border-radius: 9px; /* c\u00edrculo */\n"
"    border: 2px solid rgb(100, 180, 255);\n"
"    background-color: rgba(255,255,255,80);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    background-color: rgb(0, 170, 255);\n"
"    border: 2px solid white;\n"
"}")

        self.verticalLayout_5.addWidget(self.chk_average)

        self.verticalLayout_21 = QVBoxLayout()
        self.verticalLayout_21.setObjectName(u"verticalLayout_21")
        self.horizontalLayout_19 = QHBoxLayout()
        self.horizontalLayout_19.setObjectName(u"horizontalLayout_19")
        self.label_22 = QLabel(self.page_game_setup)
        self.label_22.setObjectName(u"label_22")
        self.label_22.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 10pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 120);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.horizontalLayout_19.addWidget(self.label_22)

        self.threshold_indicator = QLabel(self.page_game_setup)
        self.threshold_indicator.setObjectName(u"threshold_indicator")
        self.threshold_indicator.setMaximumSize(QSize(100, 16777215))
        self.threshold_indicator.setStyleSheet(u"background-color: rgb(210, 177, 252);\n"
"border: 2px solid rgb(100, 170, 255);\n"
"border-radius: 12px;\n"
"padding-left: 10px;\n"
"color: black;\n"
"font: 10pt \"Cascadia Mono\";\n"
"")

        self.horizontalLayout_19.addWidget(self.threshold_indicator)


        self.verticalLayout_21.addLayout(self.horizontalLayout_19)

        self.horizontalLayout_20 = QHBoxLayout()
        self.horizontalLayout_20.setObjectName(u"horizontalLayout_20")
        self.hsld_threshold = QSlider(self.page_game_setup)
        self.hsld_threshold.setObjectName(u"hsld_threshold")
        sizePolicy2.setHeightForWidth(self.hsld_threshold.sizePolicy().hasHeightForWidth())
        self.hsld_threshold.setSizePolicy(sizePolicy2)
        self.hsld_threshold.setFocusPolicy(Qt.NoFocus)
        self.hsld_threshold.setStyleSheet(u"QSlider::groove:horizontal {\n"
"    height: 6px;\n"
"    background: #BDBDBD;\n"
"    border-radius: 3px;\n"
"}\n"
"\n"
"QSlider::sub-page:horizontal {\n"
"    background: #2D89EF;\n"
"    border-radius: 3px;\n"
"}\n"
"\n"
"QSlider::handle:horizontal {\n"
"    background: white;\n"
"    border: 2px solid #2D89EF;\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    margin: -7px 0;    /* centra el c\u00edrculo sobre la barra */\n"
"    border-radius: 9px; /* hace el handle circular */\n"
"}\n"
"\n"
"QSlider::handle:horizontal:hover {\n"
"    background: #F5F5F5;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:pressed {\n"
"    background: #E0E0E0;\n"
"}")
        self.hsld_threshold.setSingleStep(5)
        self.hsld_threshold.setOrientation(Qt.Horizontal)

        self.horizontalLayout_20.addWidget(self.hsld_threshold)


        self.verticalLayout_21.addLayout(self.horizontalLayout_20)


        self.verticalLayout_5.addLayout(self.verticalLayout_21)

        self.horizontalLayout_30 = QHBoxLayout()
        self.horizontalLayout_30.setObjectName(u"horizontalLayout_30")
        self.label_25 = QLabel(self.page_game_setup)
        self.label_25.setObjectName(u"label_25")
        sizePolicy1.setHeightForWidth(self.label_25.sizePolicy().hasHeightForWidth())
        self.label_25.setSizePolicy(sizePolicy1)
        self.label_25.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 10pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 120);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.horizontalLayout_30.addWidget(self.label_25)

        self.chk_enable_control = QCheckBox(self.page_game_setup)
        self.chk_enable_control.setObjectName(u"chk_enable_control")
        sizePolicy2.setHeightForWidth(self.chk_enable_control.sizePolicy().hasHeightForWidth())
        self.chk_enable_control.setSizePolicy(sizePolicy2)
        self.chk_enable_control.setLayoutDirection(Qt.RightToLeft)
        self.chk_enable_control.setStyleSheet(u"QCheckBox {\n"
"    color: white;\n"
"    font: bold 12pt \"Cascadia Mono Extralight\";\n"
"}\n"
"\n"
"QCheckBox::indicator {\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    border-radius: 9px; /* c\u00edrculo */\n"
"    border: 2px solid rgb(100, 180, 255);\n"
"    background-color: rgba(255,255,255,80);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    background-color: rgb(0, 170, 255);\n"
"    border: 2px solid white;\n"
"}")

        self.horizontalLayout_30.addWidget(self.chk_enable_control)


        self.verticalLayout_5.addLayout(self.horizontalLayout_30)

        self.horizontalLayout_audio_feedback = QHBoxLayout()
        self.horizontalLayout_audio_feedback.setObjectName(u"horizontalLayout_audio_feedback")
        self.label_34 = QLabel(self.page_game_setup)
        self.label_34.setObjectName(u"label_34")
        sizePolicy1.setHeightForWidth(self.label_34.sizePolicy().hasHeightForWidth())
        self.label_34.setSizePolicy(sizePolicy1)
        self.label_34.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 10pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 120);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.horizontalLayout_audio_feedback.addWidget(self.label_34)

        self.chk_enable_audio_feedback = QCheckBox(self.page_game_setup)
        self.chk_enable_audio_feedback.setObjectName(u"chk_enable_audio_feedback")
        sizePolicy2.setHeightForWidth(self.chk_enable_audio_feedback.sizePolicy().hasHeightForWidth())
        self.chk_enable_audio_feedback.setSizePolicy(sizePolicy2)
        self.chk_enable_audio_feedback.setLayoutDirection(Qt.RightToLeft)
        self.chk_enable_audio_feedback.setStyleSheet(u"QCheckBox {\n"
"    color: white;\n"
"    font: bold 12pt \"Cascadia Mono Extralight\";\n"
"}\n"
"\n"
"QCheckBox::indicator {\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    border-radius: 9px; /* c\u00edrculo */\n"
"    border: 2px solid rgb(100, 180, 255);\n"
"    background-color: rgba(255,255,255,80);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    background-color: rgb(0, 170, 255);\n"
"    border: 2px solid white;\n"
"}")

        self.horizontalLayout_audio_feedback.addWidget(self.chk_enable_audio_feedback)


        self.verticalLayout_5.addLayout(self.horizontalLayout_audio_feedback)

        self.verticalSpacer_10 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_5.addItem(self.verticalSpacer_10)

        self.press_duration_widget = QWidget(self.page_game_setup)
        self.press_duration_widget.setObjectName(u"press_duration_widget")
        self.press_duration_widget.setVisible(False)
        self.press_duration_widget_layout = QHBoxLayout(self.press_duration_widget)
        self.press_duration_widget_layout.setObjectName(u"press_duration_widget_layout")
        self.label_press_duration_row2 = QLabel(self.press_duration_widget)
        self.label_press_duration_row2.setObjectName(u"label_press_duration_row2")
        self.label_press_duration_row2.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 10pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.press_duration_widget_layout.addWidget(self.label_press_duration_row2)

        self.hsld_press_duration_2 = QSlider(self.press_duration_widget)
        self.hsld_press_duration_2.setObjectName(u"hsld_press_duration_2")
        self.hsld_press_duration_2.setFocusPolicy(Qt.ClickFocus)
        self.hsld_press_duration_2.setStyleSheet(u"QSlider::groove:horizontal {\n"
"    height: 6px;\n"
"    background: #BDBDBD;\n"
"    border-radius: 3px;\n"
"}\n"
"\n"
"QSlider::sub-page:horizontal {\n"
"    background: #2D89EF;\n"
"    border-radius: 3px;\n"
"}\n"
"\n"
"QSlider::handle:horizontal {\n"
"    background: white;\n"
"    border: 2px solid #2D89EF;\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    margin: -7px 0;\n"
"    border-radius: 9px;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:hover {\n"
"    background: #F5F5F5;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:pressed {\n"
"    background: #E0E0E0;\n"
"}")
        self.hsld_press_duration_2.setMinimum(100)
        self.hsld_press_duration_2.setMaximum(10000)
        self.hsld_press_duration_2.setSingleStep(100)
        self.hsld_press_duration_2.setSliderPosition(250)
        self.hsld_press_duration_2.setOrientation(Qt.Horizontal)

        self.press_duration_widget_layout.addWidget(self.hsld_press_duration_2)

        self.lbl_press_duration_value_2 = QLabel(self.press_duration_widget)
        self.lbl_press_duration_value_2.setObjectName(u"lbl_press_duration_value_2")
        self.lbl_press_duration_value_2.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 10pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 80);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.press_duration_widget_layout.addWidget(self.lbl_press_duration_value_2)


        self.verticalLayout_5.addWidget(self.press_duration_widget)

        self.horizontalLayout_31 = QHBoxLayout()
        self.horizontalLayout_31.setObjectName(u"horizontalLayout_31")
        self.label_26 = QLabel(self.page_game_setup)
        self.label_26.setObjectName(u"label_26")
        self.label_26.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 10pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 120);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.horizontalLayout_31.addWidget(self.label_26)

        self.chk_enable_classify = QCheckBox(self.page_game_setup)
        self.chk_enable_classify.setObjectName(u"chk_enable_classify")
        self.chk_enable_classify.setEnabled(True)
        self.chk_enable_classify.setLayoutDirection(Qt.RightToLeft)
        self.chk_enable_classify.setStyleSheet(u"QCheckBox {\n"
"    color: white;\n"
"    font: bold 12pt \"Cascadia Mono Extralight\";\n"
"}\n"
"\n"
"QCheckBox::indicator {\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    border-radius: 9px; /* c\u00edrculo */\n"
"    border: 2px solid rgb(100, 180, 255);\n"
"    background-color: rgba(255,255,255,80);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    background-color: rgb(0, 170, 255);\n"
"    border: 2px solid white;\n"
"}")

        self.horizontalLayout_31.addWidget(self.chk_enable_classify)


        self.verticalLayout_5.addLayout(self.horizontalLayout_31)

        self.verticalSpacer_8 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_5.addItem(self.verticalSpacer_8)

        self.label_2 = QLabel(self.page_game_setup)
        self.label_2.setObjectName(u"label_2")
        sizePolicy1.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy1)
        self.label_2.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 18pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 120);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.verticalLayout_5.addWidget(self.label_2)

        self.lw_games = QListWidget(self.page_game_setup)
        QListWidgetItem(self.lw_games)
        self.lw_games.setObjectName(u"lw_games")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.lw_games.sizePolicy().hasHeightForWidth())
        self.lw_games.setSizePolicy(sizePolicy3)
        self.lw_games.setMinimumSize(QSize(0, 0))
        self.lw_games.setMaximumSize(QSize(16777215, 16777215))
        self.lw_games.setStyleSheet(u"QListWidget {\n"
"    font-family: \"Cascadia Mono Extralight\";\n"
"    font-size: 12pt;\n"
"    color: white;\n"
"}\n"
"\n"
"QListWidget {\n"
"    background-color: rgba(0, 51, 102, 200);\n"
"    color: white;\n"
"    border-radius: 10px;\n"
"    padding: 5px;\n"
"}\n"
"\n"
"/* Cuando pas\u00e1s el mouse por TODO el cuadro */\n"
"QListWidget:hover {\n"
"    background-color: rgba(0, 51, 102, 160);\n"
"}\n"
"\n"
"/* \u00cdtems normales */\n"
"QListWidget::item {\n"
"    padding: 8px;\n"
"    background-color: transparent;\n"
"}\n"
"\n"
"/* Cuando pas\u00e1s el mouse sobre un \u00edtem */\n"
"QListWidget::item:hover {\n"
"    background-color: rgba(255, 255, 255, 40);\n"
"}\n"
"\n"
"/* \u00cdtem seleccionado */\n"
"QListWidget::item:selected {\n"
"    background-color: rgb(0, 120, 215);\n"
"    color: white;\n"
"    border: 2px solid rgb(120, 200, 255);\n"
"    border-radius: 6px;\n"
"    font-weight: bold;\n"
"}\n"
"/* \u00cdtem seleccionado + hover (opcional, queda m\u00e1s fluido) */\n"
"QListWidget::item:s"
                        "elected:hover {\n"
"    background-color: rgb(0, 140, 255);\n"
"}")

        self.verticalLayout_5.addWidget(self.lw_games)


        self.horizontalLayout_6.addLayout(self.verticalLayout_5)

        self.verticalLayout_10 = QVBoxLayout()
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.horizontalLayout_10 = QHBoxLayout()
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.label_3 = QLabel(self.page_game_setup)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 18pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 120);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.horizontalLayout_10.addWidget(self.label_3)

        self.verticalLayout_13 = QVBoxLayout()
        self.verticalLayout_13.setObjectName(u"verticalLayout_13")
        self.label_9 = QLabel(self.page_game_setup)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 8pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 120);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.verticalLayout_13.addWidget(self.label_9)

        self.cb_eeg_speed = QComboBox(self.page_game_setup)
        self.cb_eeg_speed.addItem("")
        self.cb_eeg_speed.addItem("")
        self.cb_eeg_speed.addItem("")
        self.cb_eeg_speed.setObjectName(u"cb_eeg_speed")

        self.verticalLayout_13.addWidget(self.cb_eeg_speed)


        self.horizontalLayout_10.addLayout(self.verticalLayout_13)

        self.verticalLayout_12 = QVBoxLayout()
        self.verticalLayout_12.setObjectName(u"verticalLayout_12")
        self.label_8 = QLabel(self.page_game_setup)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 8pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 120);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.verticalLayout_12.addWidget(self.label_8)

        self.cb_eeg_scale = QComboBox(self.page_game_setup)
        self.cb_eeg_scale.addItem("")
        self.cb_eeg_scale.addItem("")
        self.cb_eeg_scale.addItem("")
        self.cb_eeg_scale.addItem("")
        self.cb_eeg_scale.addItem("")
        self.cb_eeg_scale.setObjectName(u"cb_eeg_scale")

        self.verticalLayout_12.addWidget(self.cb_eeg_scale)


        self.horizontalLayout_10.addLayout(self.verticalLayout_12)

        self.verticalLayout_11 = QVBoxLayout()
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.label_7 = QLabel(self.page_game_setup)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 8pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 120);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.verticalLayout_11.addWidget(self.label_7)

        self.cb_eeg_amplitude = QComboBox(self.page_game_setup)
        self.cb_eeg_amplitude.addItem("")
        self.cb_eeg_amplitude.addItem("")
        self.cb_eeg_amplitude.addItem("")
        self.cb_eeg_amplitude.setObjectName(u"cb_eeg_amplitude")

        self.verticalLayout_11.addWidget(self.cb_eeg_amplitude)


        self.horizontalLayout_10.addLayout(self.verticalLayout_11)


        self.verticalLayout_10.addLayout(self.horizontalLayout_10)

        self.eeg_container = QWidget(self.page_game_setup)
        self.eeg_container.setObjectName(u"eeg_container")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.eeg_container.sizePolicy().hasHeightForWidth())
        self.eeg_container.setSizePolicy(sizePolicy4)
        self.eeg_container.setStyleSheet(u"")
        self.verticalLayout_19 = QVBoxLayout(self.eeg_container)
        self.verticalLayout_19.setObjectName(u"verticalLayout_19")
        self.eeg_container_layout = QVBoxLayout()
        self.eeg_container_layout.setSpacing(7)
        self.eeg_container_layout.setObjectName(u"eeg_container_layout")

        self.verticalLayout_19.addLayout(self.eeg_container_layout)


        self.verticalLayout_10.addWidget(self.eeg_container)

        self.welch_settings_layout = QHBoxLayout()
        self.welch_settings_layout.setObjectName(u"welch_settings_layout")
        self.horizontalSpacer_23 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.welch_settings_layout.addItem(self.horizontalSpacer_23)

        self.chk_psd = QCheckBox(self.page_game_setup)
        self.chk_psd.setObjectName(u"chk_psd")
        self.chk_psd.setStyleSheet(u"QCheckBox {\n"
"    color: white;\n"
"    font: bold 12pt \"Cascadia Mono Extralight\";\n"
"    background-color: rgba(210, 177, 252, 180);\n"
"    border: 1px solid rgba(255,255,255,40);\n"
"    border-radius: 10px;\n"
"\n"
"    padding: 6px 10px;\n"
"}\n"
"\n"
"\n"
"QCheckBox::indicator {\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    border-radius: 9px; /* c\u00edrculo */\n"
"    border: 2px solid rgb(100, 180, 255);\n"
"    background-color: rgba(255,255,255,80);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    background-color: rgb(0, 170, 255);\n"
"    border: 2px solid white;\n"
"}\n"
"\n"
"")

        self.welch_settings_layout.addWidget(self.chk_psd)

        self.horizontalSpacer_15 = QSpacerItem(40, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        self.welch_settings_layout.addItem(self.horizontalSpacer_15)

        self.welch_settings_widget = QWidget(self.page_game_setup)
        self.welch_settings_widget.setObjectName(u"welch_settings_widget")
        sizePolicy.setHeightForWidth(self.welch_settings_widget.sizePolicy().hasHeightForWidth())
        self.welch_settings_widget.setSizePolicy(sizePolicy)
        self.horizontalLayout_7 = QHBoxLayout(self.welch_settings_widget)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalLayout_32 = QHBoxLayout()
        self.horizontalLayout_32.setObjectName(u"horizontalLayout_32")
        self.verticalLayout_14 = QVBoxLayout()
        self.verticalLayout_14.setObjectName(u"verticalLayout_14")
        self.label_4 = QLabel(self.welch_settings_widget)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 8pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 120);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.verticalLayout_14.addWidget(self.label_4)

        self.cb_psd_channel = QComboBox(self.welch_settings_widget)
        self.cb_psd_channel.setObjectName(u"cb_psd_channel")

        self.verticalLayout_14.addWidget(self.cb_psd_channel)


        self.horizontalLayout_32.addLayout(self.verticalLayout_14)

        self.horizontalSpacer_24 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_32.addItem(self.horizontalSpacer_24)

        self.verticalLayout_15 = QVBoxLayout()
        self.verticalLayout_15.setObjectName(u"verticalLayout_15")
        self.label_19 = QLabel(self.welch_settings_widget)
        self.label_19.setObjectName(u"label_19")
        self.label_19.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"font: 8pt \"Cascadia Mono ExtraLight\";\n"
"font-weight: bold;\n"
"\n"
"background-color: rgba(210, 177, 252, 120);\n"
"border-radius: 10px;\n"
"padding: 5px;")

        self.verticalLayout_15.addWidget(self.label_19)

        self.cb_psd_mode = QComboBox(self.welch_settings_widget)
        self.cb_psd_mode.addItem("")
        self.cb_psd_mode.addItem("")
        self.cb_psd_mode.addItem("")
        self.cb_psd_mode.setObjectName(u"cb_psd_mode")

        self.verticalLayout_15.addWidget(self.cb_psd_mode)


        self.horizontalLayout_32.addLayout(self.verticalLayout_15)

        self.horizontalSpacer_25 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_32.addItem(self.horizontalSpacer_25)

        self.verticalLayout_18 = QVBoxLayout()
        self.verticalLayout_18.setObjectName(u"verticalLayout_18")
        self.lbl_windows_welch = QLabel(self.welch_settings_widget)
        self.lbl_windows_welch.setObjectName(u"lbl_windows_welch")
        self.lbl_windows_welch.setStyleSheet(u"background-color: rgb(210, 177, 252);\n"
"border: 2px solid rgb(100, 170, 255);\n"
"border-radius: 8px;\n"
"padding-left: 10px;\n"
"color: black;\n"
"font: 10pt \"Cascadia Mono\";\n"
"")

        self.verticalLayout_18.addWidget(self.lbl_windows_welch)

        self.hsld_windows_welch = QSlider(self.welch_settings_widget)
        self.hsld_windows_welch.setObjectName(u"hsld_windows_welch")
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy5.setHorizontalStretch(0)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.hsld_windows_welch.sizePolicy().hasHeightForWidth())
        self.hsld_windows_welch.setSizePolicy(sizePolicy5)
        self.hsld_windows_welch.setFocusPolicy(Qt.NoFocus)
        self.hsld_windows_welch.setStyleSheet(u"QSlider::groove:horizontal {\n"
"    height: 6px;\n"
"    background: #BDBDBD;\n"
"    border-radius: 3px;\n"
"}\n"
"\n"
"QSlider::sub-page:horizontal {\n"
"    background: #2D89EF;\n"
"    border-radius: 3px;\n"
"}\n"
"\n"
"QSlider::handle:horizontal {\n"
"    background: white;\n"
"    border: 2px solid #2D89EF;\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    margin: -7px 0;    /* centra el c\u00edrculo sobre la barra */\n"
"    border-radius: 9px; /* hace el handle circular */\n"
"}\n"
"\n"
"QSlider::handle:horizontal:hover {\n"
"    background: #F5F5F5;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:pressed {\n"
"    background: #E0E0E0;\n"
"}")
        self.hsld_windows_welch.setMinimum(1)
        self.hsld_windows_welch.setMaximum(4)
        self.hsld_windows_welch.setSingleStep(1)
        self.hsld_windows_welch.setPageStep(1)
        self.hsld_windows_welch.setValue(1)
        self.hsld_windows_welch.setOrientation(Qt.Horizontal)

        self.verticalLayout_18.addWidget(self.hsld_windows_welch)


        self.horizontalLayout_32.addLayout(self.verticalLayout_18)

        self.verticalLayout_20 = QVBoxLayout()
        self.verticalLayout_20.setObjectName(u"verticalLayout_20")
        self.lbl_overlap_percentage = QLabel(self.welch_settings_widget)
        self.lbl_overlap_percentage.setObjectName(u"lbl_overlap_percentage")
        self.lbl_overlap_percentage.setStyleSheet(u"background-color: rgb(210, 177, 252);\n"
"border: 2px solid rgb(100, 170, 255);\n"
"border-radius: 8px;\n"
"padding-left: 10px;\n"
"color: black;\n"
"font: 10pt \"Cascadia Mono\";\n"
"")

        self.verticalLayout_20.addWidget(self.lbl_overlap_percentage)

        self.hsld_overlap = QSlider(self.welch_settings_widget)
        self.hsld_overlap.setObjectName(u"hsld_overlap")
        sizePolicy6 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy6.setHorizontalStretch(0)
        sizePolicy6.setVerticalStretch(0)
        sizePolicy6.setHeightForWidth(self.hsld_overlap.sizePolicy().hasHeightForWidth())
        self.hsld_overlap.setSizePolicy(sizePolicy6)
        self.hsld_overlap.setFocusPolicy(Qt.NoFocus)
        self.hsld_overlap.setStyleSheet(u"QSlider::groove:horizontal {\n"
"    height: 6px;\n"
"    background: #BDBDBD;\n"
"    border-radius: 3px;\n"
"}\n"
"\n"
"QSlider::sub-page:horizontal {\n"
"    background: #2D89EF;\n"
"    border-radius: 3px;\n"
"}\n"
"\n"
"QSlider::handle:horizontal {\n"
"    background: white;\n"
"    border: 2px solid #2D89EF;\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    margin: -7px 0;    /* centra el c\u00edrculo sobre la barra */\n"
"    border-radius: 9px; /* hace el handle circular */\n"
"}\n"
"\n"
"QSlider::handle:horizontal:hover {\n"
"    background: #F5F5F5;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:pressed {\n"
"    background: #E0E0E0;\n"
"}")
        self.hsld_overlap.setOrientation(Qt.Horizontal)

        self.verticalLayout_20.addWidget(self.hsld_overlap)


        self.horizontalLayout_32.addLayout(self.verticalLayout_20)


        self.horizontalLayout_7.addLayout(self.horizontalLayout_32)


        self.welch_settings_layout.addWidget(self.welch_settings_widget)

        self.horizontalSpacer_16 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.welch_settings_layout.addItem(self.horizontalSpacer_16)


        self.verticalLayout_10.addLayout(self.welch_settings_layout)

        self.horizontalLayout_14 = QHBoxLayout()
        self.horizontalLayout_14.setObjectName(u"horizontalLayout_14")
        self.horizontalSpacer_22 = QSpacerItem(40, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_14.addItem(self.horizontalSpacer_22)

        self.psd_container = QWidget(self.page_game_setup)
        self.psd_container.setObjectName(u"psd_container")
        sizePolicy4.setHeightForWidth(self.psd_container.sizePolicy().hasHeightForWidth())
        self.psd_container.setSizePolicy(sizePolicy4)
        self.psd_container.setMaximumSize(QSize(16777215, 200))
        self.psd_container.setStyleSheet(u"background-color: white;")
        self.horizontalLayout_21 = QHBoxLayout(self.psd_container)
        self.horizontalLayout_21.setObjectName(u"horizontalLayout_21")
        self.psd_container_layout = QHBoxLayout()
        self.psd_container_layout.setObjectName(u"psd_container_layout")

        self.horizontalLayout_21.addLayout(self.psd_container_layout)


        self.horizontalLayout_14.addWidget(self.psd_container)

        self.horizontalSpacer_21 = QSpacerItem(40, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_14.addItem(self.horizontalSpacer_21)


        self.verticalLayout_10.addLayout(self.horizontalLayout_14)


        self.horizontalLayout_6.addLayout(self.verticalLayout_10)


        self.verticalLayout_4.addLayout(self.horizontalLayout_6)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.btn_exit_game_setup = QPushButton(self.page_game_setup)
        self.btn_exit_game_setup.setObjectName(u"btn_exit_game_setup")
        self.btn_exit_game_setup.setStyleSheet(u"QPushButton {\n"
"    border-style: solid;\n"
"    border-width: 1px;\n"
"    border-color: rgba(0, 51, 102, 250);\n"
"    background-color: rgba(0, 51, 102, 160); /* transparencia */\n"
"    color: rgb(255,255,255);\n"
"    border-radius: 10px;\n"
"    font: 18pt \"Cascadia Mono ExtraLight\";\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgba(0,70,140,180);\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: rgba(0,35,70,200);\n"
"    padding-left: 2px;\n"
"    padding-top: 2px;\n"
"}")

        self.horizontalLayout_5.addWidget(self.btn_exit_game_setup)

        self.horizontalSpacer_7 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_7)

        self.btn_start_train = QPushButton(self.page_game_setup)
        self.btn_start_train.setObjectName(u"btn_start_train")
        self.btn_start_train.setStyleSheet(u"QPushButton {\n"
"    border-style: solid;\n"
"    border-width: 1px;\n"
"    border-color: rgba(0, 51, 102, 250);\n"
"    background-color: rgba(0, 51, 102, 160); /* transparencia */\n"
"    color: rgb(255,255,255);\n"
"    border-radius: 10px;\n"
"    font: 18pt \"Cascadia Mono ExtraLight\";\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgba(0,70,140,180);\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: rgba(0,35,70,200);\n"
"    padding-left: 2px;\n"
"    padding-top: 2px;\n"
"}")

        self.horizontalLayout_5.addWidget(self.btn_start_train)

        self.horizontalSpacer_8 = QSpacerItem(40, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_8)

        self.btn_start_game = QPushButton(self.page_game_setup)
        self.btn_start_game.setObjectName(u"btn_start_game")
        self.btn_start_game.setStyleSheet(u"QPushButton {\n"
"    border-style: solid;\n"
"    border-width: 1px;\n"
"    border-color: rgba(0, 51, 102, 250);\n"
"    background-color: rgba(0, 51, 102, 160); /* transparencia */\n"
"    color: rgb(255,255,255);\n"
"    border-radius: 10px;\n"
"    font: 18pt \"Cascadia Mono ExtraLight\";\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgba(0,70,140,180);\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: rgba(0,35,70,200);\n"
"    padding-left: 2px;\n"
"    padding-top: 2px;\n"
"}")

        self.horizontalLayout_5.addWidget(self.btn_start_game)

        self.horizontalSpacer_5 = QSpacerItem(40, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_5)

        self.btn_start_test = QPushButton(self.page_game_setup)
        self.btn_start_test.setObjectName(u"btn_start_test")
        self.btn_start_test.setStyleSheet(u"QPushButton {\n"
"    border-style: solid;\n"
"    border-width: 1px;\n"
"    border-color: rgba(0, 51, 102, 250);\n"
"    background-color: rgba(0, 51, 102, 160); /* transparencia */\n"
"    color: rgb(255,255,255);\n"
"    border-radius: 10px;\n"
"    font: 18pt \"Cascadia Mono ExtraLight\";\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgba(0,70,140,180);\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: rgba(0,35,70,200);\n"
"    padding-left: 2px;\n"
"    padding-top: 2px;\n"
"}")

        self.horizontalLayout_5.addWidget(self.btn_start_test)


        self.verticalLayout_4.addLayout(self.horizontalLayout_5)

        self.stackedWidget.addWidget(self.page_game_setup)

        self.verticalLayout.addWidget(self.stackedWidget)

        SSVEP.setCentralWidget(self.centralwidget)
        self.statusBar = QStatusBar(SSVEP)
        self.statusBar.setObjectName(u"statusBar")
        SSVEP.setStatusBar(self.statusBar)
        self.menuBar = QMenuBar(SSVEP)
        self.menuBar.setObjectName(u"menuBar")
        self.menuBar.setGeometry(QRect(0, 0, 1212, 26))
        SSVEP.setMenuBar(self.menuBar)

        self.retranslateUi(SSVEP)

        self.stackedWidget.setCurrentIndex(4)


        QMetaObject.connectSlotsByName(SSVEP)
    # setupUi

    def retranslateUi(self, SSVEP):
        SSVEP.setWindowTitle(QCoreApplication.translate("SSVEP", u"MainWindow", None))
        self.label_5.setText("")
        self.btn_start_main.setText(QCoreApplication.translate("SSVEP", u"Inicio", None))
        self.logo_fiuner.setText("")
        self.btn_settings_main.setText(QCoreApplication.translate("SSVEP", u"Configuraci\u00f3n", None))
        self.btn_info.setText(QCoreApplication.translate("SSVEP", u"Informaci\u00f3n", None))
        self.btn_exit_info.setText(QCoreApplication.translate("SSVEP", u"Salir", None))
        self.titulo.setText(QCoreApplication.translate("SSVEP", u"Seleccionar Usuario", None))
        self.nuevo_usuario.setText(QCoreApplication.translate("SSVEP", u"Nuevo usuario", None))
        self.btn_user_save.setText(QCoreApplication.translate("SSVEP", u"Guardar", None))
        self.btn_user_exit.setText(QCoreApplication.translate("SSVEP", u"Salir", None))
        self.btn_user_continue.setText(QCoreApplication.translate("SSVEP", u"Continuar", None))
        self.user_cfg_tile.setText(QCoreApplication.translate("SSVEP", u"Configuraciones de usuario", None))
        self.lbl_user_cfg_user_n.setText(QCoreApplication.translate("SSVEP", u"TextLabel", None))
        self.label_21.setText(QCoreApplication.translate("SSVEP", u"Tiempo de respuesta", None))
        self.label_27.setText(QCoreApplication.translate("SSVEP", u"Velocidad", None))
        self.lbl_time_response.setText("")
        self.label_28.setText(QCoreApplication.translate("SSVEP", u"Exactitud", None))
        self.label_20.setText(QCoreApplication.translate("SSVEP", u"Estilo de\n"
"est\u00edmulos", None))
        self.qc_estimulus_method.setItemText(0, QCoreApplication.translate("SSVEP", u"Lleno", None))
        self.qc_estimulus_method.setItemText(1, QCoreApplication.translate("SSVEP", u"Cuadriculado", None))

        self.label_6.setText(QCoreApplication.translate("SSVEP", u"M\u00e9todo de\n"
"clasificaci\u00f3n", None))
        self.qc_cass_method.setItemText(0, QCoreApplication.translate("SSVEP", u"Sin calibraci\u00f3n", None))

        self.label_11.setText(QCoreApplication.translate("SSVEP", u"Frec. [Hz]", None))
        self.label_12.setText(QCoreApplication.translate("SSVEP", u"Acciones", None))
        self.chk_cfg_show_space.setText("")
        self.chk_cfg_show_esc.setText("")
        self.chk_toggle_space.setText("")
        self.label_24.setText(QCoreApplication.translate("SSVEP", u"Sostener", None))
        self.label_13.setText(QCoreApplication.translate("SSVEP", u"Escape", None))
        self.label_10.setText(QCoreApplication.translate("SSVEP", u"\u2715\u2014\u2713", None))
        self.label_16.setText(QCoreApplication.translate("SSVEP", u"Arriba", None))
        self.label_14.setText(QCoreApplication.translate("SSVEP", u"Espacio", None))
        self.label_18.setText(QCoreApplication.translate("SSVEP", u"Abajo", None))
        self.label_15.setText(QCoreApplication.translate("SSVEP", u"Derecha", None))
        self.label_17.setText(QCoreApplication.translate("SSVEP", u"Izquierda", None))
        self.chk_cfg_show_up.setText("")
        self.chk_cfg_show_right.setText("")
        self.chk_cfg_show_left.setText("")
        self.chk_cfg_show_down.setText("")
        self.label_23.setText(QCoreApplication.translate("SSVEP", u"\u25a0", None))
        self.label_29.setText(QCoreApplication.translate("SSVEP", u"\u25cf", None))
        self.label_30.setText(QCoreApplication.translate("SSVEP", u"\u2192", None))
        self.label_31.setText(QCoreApplication.translate("SSVEP", u"\u2191", None))
        self.label_32.setText(QCoreApplication.translate("SSVEP", u"\u2190", None))
        self.label_33.setText(QCoreApplication.translate("SSVEP", u"\u2193", None))
        self.label_press_duration_title.setText(QCoreApplication.translate("SSVEP", u"Duraci\u00f3n de pulsaci\u00f3n (ms)", None))
        self.lbl_press_duration_value.setText(QCoreApplication.translate("SSVEP", u"250 ms", None))
        self.btn_user_cfg_exit.setText(QCoreApplication.translate("SSVEP", u"Salir", None))
        self.btn_user_cfg_remove.setText(QCoreApplication.translate("SSVEP", u"Eliminar", None))
        self.btn_user_cfg_save.setText(QCoreApplication.translate("SSVEP", u"Guardar", None))
        self.btn_user_cfg_continue.setText(QCoreApplication.translate("SSVEP", u"Continuar", None))
        self.label.setText(QCoreApplication.translate("SSVEP", u"Filtros", None))
        self.chk_bandpass.setText(QCoreApplication.translate("SSVEP", u"Pasa banda", None))
        self.chk_notch.setText(QCoreApplication.translate("SSVEP", u"Notch", None))
        self.chk_average.setText(QCoreApplication.translate("SSVEP", u"Media", None))
        self.label_22.setText(QCoreApplication.translate("SSVEP", u"Umbral de\n"
"detecci\u00f3n", None))
        self.threshold_indicator.setText(QCoreApplication.translate("SSVEP", u"TextLabel", None))
        self.label_25.setText(QCoreApplication.translate("SSVEP", u"Enviar teclas", None))
        self.chk_enable_control.setText("")
        self.label_34.setText(QCoreApplication.translate("SSVEP", u"Retroalimentaci\u00f3n auditiva", None))
        self.chk_enable_audio_feedback.setText("")
        self.label_press_duration_row2.setText(QCoreApplication.translate("SSVEP", u"Duraci\u00f3n (ms)", None))
        self.lbl_press_duration_value_2.setText(QCoreApplication.translate("SSVEP", u"250 ms", None))
        self.label_26.setText(QCoreApplication.translate("SSVEP", u"Clasificar", None))
        self.chk_enable_classify.setText("")
        self.label_2.setText(QCoreApplication.translate("SSVEP", u"Aplicaciones", None))

        __sortingEnabled = self.lw_games.isSortingEnabled()
        self.lw_games.setSortingEnabled(False)
        ___qlistwidgetitem = self.lw_games.item(0)
        ___qlistwidgetitem.setText(QCoreApplication.translate("SSVEP", u"Solo est\u00edmulos", None));
        self.lw_games.setSortingEnabled(__sortingEnabled)

        self.label_3.setText(QCoreApplication.translate("SSVEP", u"EEG en tiempor real", None))
        self.label_9.setText(QCoreApplication.translate("SSVEP", u"Velocidad", None))
        self.cb_eeg_speed.setItemText(0, QCoreApplication.translate("SSVEP", u"x1.0", None))
        self.cb_eeg_speed.setItemText(1, QCoreApplication.translate("SSVEP", u"x0.5", None))
        self.cb_eeg_speed.setItemText(2, QCoreApplication.translate("SSVEP", u"x2.0", None))

        self.label_8.setText(QCoreApplication.translate("SSVEP", u"Escala", None))
        self.cb_eeg_scale.setItemText(0, QCoreApplication.translate("SSVEP", u"x100", None))
        self.cb_eeg_scale.setItemText(1, QCoreApplication.translate("SSVEP", u"x1", None))
        self.cb_eeg_scale.setItemText(2, QCoreApplication.translate("SSVEP", u"x10", None))
        self.cb_eeg_scale.setItemText(3, QCoreApplication.translate("SSVEP", u"x1000", None))
        self.cb_eeg_scale.setItemText(4, "")

        self.label_7.setText(QCoreApplication.translate("SSVEP", u"Amplitud", None))
        self.cb_eeg_amplitude.setItemText(0, QCoreApplication.translate("SSVEP", u"mV", None))
        self.cb_eeg_amplitude.setItemText(1, QCoreApplication.translate("SSVEP", u"uV", None))
        self.cb_eeg_amplitude.setItemText(2, QCoreApplication.translate("SSVEP", u"nV", None))

        self.chk_psd.setText(QCoreApplication.translate("SSVEP", u"Graficar PSD", None))
        self.label_4.setText(QCoreApplication.translate("SSVEP", u"Canales", None))
        self.label_19.setText(QCoreApplication.translate("SSVEP", u"Visualizaci\u00f3n", None))
        self.cb_psd_mode.setItemText(0, QCoreApplication.translate("SSVEP", u"Valor absoluto", None))
        self.cb_psd_mode.setItemText(1, QCoreApplication.translate("SSVEP", u"Decibeles (dB)", None))
        self.cb_psd_mode.setItemText(2, QCoreApplication.translate("SSVEP", u"Normalizada", None))

        self.lbl_windows_welch.setText(QCoreApplication.translate("SSVEP", u"TextLabel", None))
        self.lbl_overlap_percentage.setText(QCoreApplication.translate("SSVEP", u"TextLabel", None))
        self.btn_exit_game_setup.setText(QCoreApplication.translate("SSVEP", u"Salir", None))
        self.btn_start_train.setText(QCoreApplication.translate("SSVEP", u"Iniciar\n"
" calibraci\u00f3n ", None))
        self.btn_start_game.setText(QCoreApplication.translate("SSVEP", u"Iniciar\n"
"juego", None))
        self.btn_start_test.setText(QCoreApplication.translate("SSVEP", u"Prueba de\n"
" desempe\u00f1o", None))
    # retranslateUi

