""""this moduel does this"""
import sys

from PySide2 import QtCore, QtGui, QtWidgets

from Tools import MotorSteuerung, Ui_VisoWidget
from Tools.numpad import Ui_Numpad
from vis_fun import GLWidget


class EmittingStream(QtCore.QObject):
    """simple class to emit the sys.stdout to an other output src"""
    textWritten = QtCore.Signal(str)

    def write(self, text):
        """writes every print() to the QLTextEditor"""
        self.textWritten.emit(str(text))


class MainWindow(QtWidgets.QMainWindow):
    """handles the QT Widgets and all UI relatet operations"""
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui = Ui_VisoWidget()
        self.docked = QtWidgets.QDockWidget("Dock", self)
        self.docked.setWidget(self.ui.setupUi(self.docked))
        self.number: str
        self.num: Ui_Numpad
        self.numdocked: QtWidgets.QDockWidget
        self.visuStattxt: str
        self.oldStatus: str
        self.numb = False
        self.format = QtGui.QTextCharFormat()
        
        self.visuStattxt = ''
        self.oldStatus = 'NOP'
        self.progressBar = QtWidgets.QProgressBar()
        self.lcdX = QtWidgets.QLCDNumber()
        self.lcdY = QtWidgets.QLCDNumber()
        self.lcdZ = QtWidgets.QLCDNumber()
        self.xAktiv = QtWidgets.QLabel()
        self.yAktiv = QtWidgets.QLabel()
        self.zAktiv = QtWidgets.QLabel()
        self.prozessStatus = QtWidgets.QLabel()
        self.xIST = QtWidgets.QLabel()
        self.yIST = QtWidgets.QLabel()
        self.zIST = QtWidgets.QLabel()
        self.start = QtWidgets.QLabel()
        self.stop = QtWidgets.QLabel()

        self.start.setText(" Start: INAKTIV ")
        self.stop.setText(" Stop: INAKTIV ")
        self.xAktiv.setText(" MotorX: INAKTIV ")
        self.yAktiv.setText(" MotorY: INAKTIV ")
        self.zAktiv.setText(" MotorZ: INAKTIV ")
        self.prozessStatus.setText("  NOP  ")
        self.xAktiv.setStyleSheet("background-color: lightgreen")
        self.yAktiv.setStyleSheet("background-color: lightgreen")
        self.zAktiv.setStyleSheet("background-color: lightgreen")
        self.prozessStatus.setStyleSheet("background-color: lightgray")
        self.start.setStyleSheet("background-color: lightgray")
        self.stop.setStyleSheet("background-color: lightgreen")
        self.xIST.setText("X_IST: ")
        self.yIST.setText("  Y_IST: ")
        self.zIST.setText("  Z_IST: ")

        self.abstand = []
        for i in range(5):
            self.abstand.append(QtWidgets.QLabel())
            self.abstand[i].setText("    ")


        self.menu = QtWidgets.QMenu("Konturen", self)
        self.Kontur1 = QtWidgets.QAction("Kontur1", self)
        self.Kontur2 = QtWidgets.QAction("Kontur2", self)
        self.Kontur3 = QtWidgets.QAction("Kontur3", self)
        self.menu.addAction(self.Kontur1)
        self.menu.addAction(self.Kontur2)
        self.menu.addAction(self.Kontur3)


        self.glWidget = GLWidget()
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        self.glWidgetArea = QtWidgets.QScrollArea()
        self.glWidgetArea.setWidget(self.glWidget)
        self.glWidgetArea.setWidgetResizable(True)
        self.glWidgetArea.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff)
        self.glWidgetArea.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff)
        self.glWidgetArea.setSizePolicy(QtWidgets.QSizePolicy.Ignored,
                                        QtWidgets.QSizePolicy.Ignored)
        self.glWidgetArea.setMinimumSize(50, 50)
        sys.stdout = EmittingStream()
        self.connect(sys.stdout, QtCore.SIGNAL(
            'textWritten(QString)'), self.NormalOutputWritten)

        # set the layout
        central_layout = QtWidgets.QVBoxLayout()
        central_layout.addWidget(self.glWidgetArea)
        central_widget.setLayout(central_layout)
        self.setWindowTitle("Visualisierung")
        self.resize(1280, 720)

        self.glWidget.updateProgress.connect(self.UpdateProgressBar)
        self.glWidget.updateLCD.connect(self.UpdateLCD)
        self.glWidget.updateMotorStatus.connect(self.UpdateMotor)
        self.glWidget.updateStatus.connect(self.UpdateStatus)
        self.glWidget.updateStartStop.connect(self.UpdateStartStop)
        self.glWidget.updateSpinnerVal.connect(self.UpdateSpinerVal)

        self.docked.setAllowedAreas(
            QtCore.Qt.BottomDockWidgetArea | QtCore.Qt.TopDockWidgetArea)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.docked)

        self.status = self.statusBar()
        self.status.addPermanentWidget(self.stop)
        self.status.addPermanentWidget(self.abstand[4])
        self.status.addPermanentWidget(self.start)
        self.status.addPermanentWidget(self.abstand[3])
        self.status.addPermanentWidget(self.prozessStatus)
        self.status.addPermanentWidget(self.abstand[2])
        self.status.addPermanentWidget(self.xAktiv)
        self.status.addPermanentWidget(self.yAktiv)
        self.status.addPermanentWidget(self.zAktiv)
        self.status.addPermanentWidget(self.abstand[1])
        self.status.addPermanentWidget(self.xIST)
        self.status.addPermanentWidget(self.lcdX)
        self.status.addPermanentWidget(self.yIST)
        self.status.addPermanentWidget(self.lcdY)
        self.status.addPermanentWidget(self.zIST)
        self.status.addPermanentWidget(self.lcdZ)
        self.status.addPermanentWidget(self.abstand[0])
        self.status.addPermanentWidget(self.progressBar)

        self.ui.xStartSpinBox.valueChanged.connect(self.glWidget.move_to_x)
        self.ui.xStartSpinBox.setRange(
            self.glWidget.min_freq_vec[0], self.glWidget.max_freq_vec[0])
        self.ui.xStartSpinBox.setSingleStep(100)
        self.ui.xStartSpinBox.setValue(MotorSteuerung.GetPosition(0))

        self.ui.yStartSpinBox.valueChanged.connect(self.glWidget.move_to_y)
        self.ui.yStartSpinBox.setRange(
            self.glWidget.min_freq_vec[1], self.glWidget.max_freq_vec[1])
        self.ui.yStartSpinBox.setSingleStep(100)
        self.ui.yStartSpinBox.setValue(MotorSteuerung.GetPosition(1))

        self.ui.zStartSpinBox.valueChanged.connect(self.glWidget.move_to_z)
        self.ui.zStartSpinBox.setRange(
            self.glWidget.min_freq_vec[2], self.glWidget.max_freq_vec[2])
        self.ui.zStartSpinBox.setSingleStep(100)
        self.ui.zStartSpinBox.setValue(MotorSteuerung.GetPosition(2))

        self.lcdX.display(MotorSteuerung.GetPosition(0))
        self.lcdY.display(MotorSteuerung.GetPosition(1))
        self.lcdZ.display(MotorSteuerung.GetPosition(2))

        self.ui.vSpinBox.valueChanged.connect(self.glWidget.set_velocity)
        self.ui.vSpinBox.setValue(0.008)

        self.ui.startButton.clicked.connect(self.glWidget.start_procedure)
        self.ui.stopButton.clicked.connect(self.glWidget.pause_procedure)
        self.ui.hardstopButton.clicked.connect(self.glWidget.stop_procedure)
        self.ui.kalButton.clicked.connect(self.glWidget.calibration_switch)
        self.ui.resetVis.clicked.connect(self.glWidget.reset_view)
        self.ui.onlyVisual.clicked.connect(self.glWidget.visu_only_switch)
        self.ui.clearPos.clicked.connect(self.glWidget.clear_pos)
        self.ui.Bahn.clicked.connect(self.glWidget.conturing_switch)
        self.ui.numBut.clicked.connect(self.InitNum)

        self.ui.toolButton.setMenu(self.menu)
        self.ui.toolButton.clicked.connect(self.ui.toolButton.showMenu)
        self.Kontur1.triggered.connect(self.glWidget.select_contour_1)
        self.Kontur2.triggered.connect(self.glWidget.select_contour_2)
        self.Kontur3.triggered.connect(self.glWidget.select_contour_3)

        

    def InitNum(self):
        self.numb = True
        self.number = ""
        self.num = Ui_Numpad()
        self.numdocked = QtWidgets.QDockWidget("NumDock", self)
        self.numdocked.setWidget(self.num.setupUi(self.numdocked))
        # self.numdocked.maximumSize()
        self.numdocked.setAllowedAreas(
            QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.setCorner(QtCore.Qt.Corner.BottomLeftCorner,
                       QtCore.Qt.BottomDockWidgetArea)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.numdocked)

        self.num.zero.clicked.connect(lambda x: self.EmitNumKey(str(0)))
        self.num.eins.clicked.connect(lambda x: self.EmitNumKey(str(1)))
        self.num.zwei.clicked.connect(lambda x: self.EmitNumKey(str(2)))
        self.num.drei.clicked.connect(lambda x: self.EmitNumKey(str(3)))
        self.num.vier.clicked.connect(lambda x: self.EmitNumKey(str(4)))
        self.num.funf.clicked.connect(lambda x: self.EmitNumKey(str(5)))
        self.num.sechs.clicked.connect(lambda x: self.EmitNumKey(str(6)))
        self.num.sieben.clicked.connect(lambda x: self.EmitNumKey(str(7)))
        self.num.acht.clicked.connect(lambda x: self.EmitNumKey(str(8)))
        self.num.neun.clicked.connect(lambda x: self.EmitNumKey(str(9)))
        self.num.xforSpin.clicked.connect(lambda x: self.EmitNumKey("X"))
        self.num.yforSpin.clicked.connect(lambda x: self.EmitNumKey("Y"))
        self.num.zforSpin.clicked.connect(lambda x: self.EmitNumKey("Z"))
        self.num.delte.clicked.connect(lambda x: self.EmitNumKey("delete"))
        self.num.enter.clicked.connect(lambda x: self.EmitNumKey("enter"))
        self.num.geschw.clicked.connect(lambda x: self.EmitNumKey("v"))

    def __del__(self):
        # Restore sys.stdout
        sys.stdout = sys.__stdout__

    @QtCore.Slot(str)
    def NormalOutputWritten(self, text:str):
        """Append text to the QTextEdit."""
        cursor = self.ui.TextEdit.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        if text.startswith("[bold]"):
            self.format.setFontWeight(QtGui.QFont.Bold)
            text = text[6:]
            cursor.mergeCharFormat(self.format)
        else:
            self.format.setFontWeight(QtGui.QFont.Normal)
            cursor.mergeCharFormat(self.format)

        cursor.insertText(text)
        self.ui.TextEdit.setTextCursor(cursor)
        self.ui.TextEdit.ensureCursorVisible()

    @QtCore.Slot(int)
    def UpdateProgressBar(self, val):
        self.progressBar.setValue(val)

    @QtCore.Slot(list)
    def UpdateLCD(self, positons):
        self.lcdX.display(positons[0])
        self.lcdY.display(positons[1])
        self.lcdZ.display(positons[2])

    @QtCore.Slot(list)
    def UpdateMotor(self, motorStats):
        if not motorStats[0] and motorStats[3]:
            self.xAktiv.setText(" MotorX: AKTIV   ")
            self.xAktiv.setStyleSheet("background-color: red")
        else:
            self.xAktiv.setText(" MotorX: INAKTIV ")
            self.xAktiv.setStyleSheet("background-color: lightgreen")

        if not motorStats[1] and motorStats[3]:
            self.yAktiv.setText(" MotorY: AKTIV   ")
            self.yAktiv.setStyleSheet("background-color: red")
        else:
            self.yAktiv.setText(" MotorY: INAKTIV ")
            self.yAktiv.setStyleSheet("background-color: lightgreen")

        if not motorStats[2] and motorStats[3]:
            self.zAktiv.setText(" MotorZ: AKTIV   ")
            self.zAktiv.setStyleSheet("background-color: red")
        else:
            self.zAktiv.setText(" MotorZ: INAKTIV ")
            self.zAktiv.setStyleSheet("background-color: lightgreen")

    @QtCore.Slot(str)
    def UpdateStatus(self, status):
        if status == "visu_only_activ":
            self.visuStattxt = "onlyVisual"
            status = self.oldStatus
        elif status == "visu_only_inactiv":
            self.visuStattxt = ""
            status = self.oldStatus

        if status == 'NOP':
            self.oldStatus = status
            self.prozessStatus.setText(f" {self.visuStattxt} NOP  ")
            self.prozessStatus.setStyleSheet("background-color: lightgray")
        elif status == "kal":
            self.oldStatus = status
            self.prozessStatus.setText(
                f" {self.visuStattxt} Kalibration AKTIV ")
            self.prozessStatus.setStyleSheet("background-color: yellow")
        elif status == "kon":
            self.oldStatus = status
            self.prozessStatus.setText(f" {self.visuStattxt} Konturing AKTIV ")
            self.prozessStatus.setStyleSheet("background-color: yellow")
        elif status == "Error":
            self.oldStatus = status
            self.prozessStatus.setText(f" {self.visuStattxt} Error ")
            self.prozessStatus.setStyleSheet("background-color: red")

    @QtCore.Slot(list)
    def UpdateStartStop(self, status):
        start, stop = status
        if start:
            self.start.setText(" Start: AKTIV   ")
            self.start.setStyleSheet("background-color: yellow")
        else:
            self.start.setText(" Start: INAKTIV   ")
            self.start.setStyleSheet("background-color: lightgray")

        if stop:
            self.stop.setText(" Stop: AKTIV   ")
            self.stop.setStyleSheet("background-color: red")
        else:
            self.stop.setText(" Stop: INAKTIV   ")
            self.stop.setStyleSheet("background-color: lightgreen")

    @QtCore.Slot()
    def UpdateSpinerVal(self):
        self.ui.xStartSpinBox.setValue(MotorSteuerung.GetPosition(0))
        self.ui.yStartSpinBox.setValue(MotorSteuerung.GetPosition(1))
        self.ui.zStartSpinBox.setValue(MotorSteuerung.GetPosition(2))

    @QtCore.Slot(str)
    def EmitNumKey(self, num):
        if num == "v":
            self.number = num
        elif num == "X":
            self.number = num
        elif num == "Y":
            self.number = num
        elif num == "Z":
            self.number = num

        if num == "enter":
            if self.number[0] == "v":
                self.ui.vSpinBox.setValue(float(self.number[2:]))
            if self.number[0] == "X":
                self.ui.xStartSpinBox.setValue(int(self.number[2:]))
            if self.number[0] == "Y":
                self.ui.yStartSpinBox.setValue(int(self.number[2:]))
            if self.number[0] == "Z":
                self.ui.zStartSpinBox.setValue(int(self.number[2:]))
        else:
            if len(self.number) != 0:
                if self.number[0] == "X" or self.number[0] == "Y" or self.number[0] == "Z" or self.number[0] == "v":
                    if self.number[0:4] != "vv0." and self.number[0] == "v":
                        self.number = "vv0."
                    if num == "delete":
                        self.number = self.number[:-1]
                    elif len(self.number) < 7:
                        self.number += num
                    self.num.lcdNumbpad.display(str(self.number[2:]))
                    print(self.number)

                else:
                    self.num.lcdNumbpad.display("notSeT")
                    print("Bitte eine Achse auswählen")


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.showMaximized()
    res = app.exec_()
    mainWin.glWidget.free_recources()
    sys.exit(res)
