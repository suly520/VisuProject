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
    #TODO:BEAUTY splitt class
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_labels()
        self.visu_ui = Ui_VisoWidget()
        self.docker_widget = QtWidgets.QDockWidget("Dock", self)
        self.docker_widget.setWidget(self.visu_ui.setupUi(self.docker_widget))
        self.num_buffer: str
        self.numpad_ui: Ui_Numpad
        self.num_dock_widget: QtWidgets.QDockWidget
        self.process_status_txt: str
        self.process_status_txt_old: str
        self.format = QtGui.QTextCharFormat()
        self.process_status_txt = ''
        self.process_status_txt_old = 'NOP'
        self.progress_bar = QtWidgets.QProgressBar()

        self.conturing_menu = QtWidgets.QMenu("Konturen", self)
        self.shape_1 = QtWidgets.QAction("Kontur1", self)
        self.shape_2 = QtWidgets.QAction("Kontur2", self)
        self.shape_3 = QtWidgets.QAction("Kontur3", self)
        self.conturing_menu.addAction(self.shape_1)
        self.conturing_menu.addAction(self.shape_2)
        self.conturing_menu.addAction(self.shape_3)

        self.gl_widget = GLWidget()
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        self.gl_widget_area = QtWidgets.QScrollArea()
        self.gl_widget_area.setWidget(self.gl_widget)
        self.gl_widget_area.setWidgetResizable(True)
        self.gl_widget_area.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff)
        self.gl_widget_area.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff)
        self.gl_widget_area.setSizePolicy(QtWidgets.QSizePolicy.Ignored,
                                          QtWidgets.QSizePolicy.Ignored)
        self.gl_widget_area.setMinimumSize(50, 50)
        sys.stdout = EmittingStream()
        self.connect(sys.stdout, QtCore.SIGNAL(
            'textWritten(QString)'), self.write_to_textedit)

        # set the layout
        central_layout = QtWidgets.QVBoxLayout()
        central_layout.addWidget(self.gl_widget_area)
        central_widget.setLayout(central_layout)
        self.setWindowTitle("Visualisierung")
        self.resize(1280, 720)

        self.gl_widget.updateProgress.connect(self.update_progressbar)
        self.gl_widget.updateLCD.connect(self.update_numpad_txt)
        self.gl_widget.updateMotorStatus.connect(self.update_motor_status_txt)
        self.gl_widget.updateStatus.connect(self.update_process_status_txt)
        self.gl_widget.updateStartStop.connect(self.update_start_stop_txt)
        self.gl_widget.updateSpinnerVal.connect(self.update_distance_input)

        self.docker_widget.setAllowedAreas(
            QtCore.Qt.BottomDockWidgetArea | QtCore.Qt.TopDockWidgetArea)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.docker_widget)

        self._init_statusbar()

        self._setup_visu_ui()

    def __del__(self):
        # Restore sys.stdout
        sys.stdout = sys.__stdout__

    def _init_labels(self):
        """inits all labels assosiated with the user interface"""
        self.process_status_label = QtWidgets.QLabel()
        self.process_status_label.setText("  NOP  ")
        self.process_status_label.setStyleSheet("background-color: lightgray")

        self.start_label = QtWidgets.QLabel()
        self.start_label.setText(" Start: INAKTIV ")
        self.start_label.setStyleSheet("background-color: lightgray")

        self.stop_label = QtWidgets.QLabel()
        self.stop_label.setText(" Stop: INAKTIV ")
        self.stop_label.setStyleSheet("background-color: lightgreen")

        self.num_input_x = QtWidgets.QLCDNumber()
        self.num_input_y = QtWidgets.QLCDNumber()
        self.num_input_z = QtWidgets.QLCDNumber()

        self.x_activ = QtWidgets.QLabel()
        self.x_activ.setText(" MotorX: INAKTIV ")
        self.x_activ.setStyleSheet("background-color: lightgreen")
        self.y_activ = QtWidgets.QLabel()
        self.y_activ.setText(" MotorY: INAKTIV ")
        self.y_activ.setStyleSheet("background-color: lightgreen")
        self.z_activ = QtWidgets.QLabel()
        self.z_activ.setText(" MotorZ: INAKTIV ")
        self.z_activ.setStyleSheet("background-color: lightgreen")

        self.actual_pos_x_label = QtWidgets.QLabel()
        self.actual_pos_x_label.setText("X_IST: ")

        self.actual_pos_y_label = QtWidgets.QLabel()
        self.actual_pos_y_label.setText("  Y_IST: ")

        self.actual_pos_z_label = QtWidgets.QLabel()
        self.actual_pos_z_label.setText("  Z_IST: ")

        self.distance_labels = []
        for i in range(5):
            self.distance_labels.append(QtWidgets.QLabel())
            self.distance_labels[i].setText("    ")

    def _init_statusbar(self):
        """assigns all widgets to the statusbar"""
        self.status = self.statusBar()
        self.status.addPermanentWidget(self.stop_label)
        self.status.addPermanentWidget(self.distance_labels[4])
        self.status.addPermanentWidget(self.start_label)
        self.status.addPermanentWidget(self.distance_labels[3])
        self.status.addPermanentWidget(self.process_status_label)
        self.status.addPermanentWidget(self.distance_labels[2])
        self.status.addPermanentWidget(self.x_activ)
        self.status.addPermanentWidget(self.y_activ)
        self.status.addPermanentWidget(self.z_activ)
        self.status.addPermanentWidget(self.distance_labels[1])
        self.status.addPermanentWidget(self.actual_pos_x_label)
        self.status.addPermanentWidget(self.num_input_x)
        self.status.addPermanentWidget(self.actual_pos_y_label)
        self.status.addPermanentWidget(self.num_input_y)
        self.status.addPermanentWidget(self.actual_pos_z_label)
        self.status.addPermanentWidget(self.num_input_z)
        self.status.addPermanentWidget(self.distance_labels[0])
        self.status.addPermanentWidget(self.progress_bar)

    def _init_numpad_widget(self):
        """inits all numpad related variables """
        self.num_buffer = ""
        self.numpad_ui = Ui_Numpad()
        self.num_dock_widget = QtWidgets.QDockWidget("NumDock", self)
        self.num_dock_widget.setWidget(
            self.numpad_ui.setupUi(self.num_dock_widget))
        # self.num_dock_widget.maximumSize()
        self.num_dock_widget.setAllowedAreas(
            QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.setCorner(QtCore.Qt.Corner.BottomLeftCorner,
                       QtCore.Qt.BottomDockWidgetArea)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.num_dock_widget)

        self.numpad_ui.zero.clicked.connect(lambda x: self.emit_num(str(0)))
        self.numpad_ui.eins.clicked.connect(lambda x: self.emit_num(str(1)))
        self.numpad_ui.zwei.clicked.connect(lambda x: self.emit_num(str(2)))
        self.numpad_ui.drei.clicked.connect(lambda x: self.emit_num(str(3)))
        self.numpad_ui.vier.clicked.connect(lambda x: self.emit_num(str(4)))
        self.numpad_ui.funf.clicked.connect(lambda x: self.emit_num(str(5)))
        self.numpad_ui.sechs.clicked.connect(lambda x: self.emit_num(str(6)))
        self.numpad_ui.sieben.clicked.connect(
            lambda x: self.emit_num(str(7)))
        self.numpad_ui.acht.clicked.connect(lambda x: self.emit_num(str(8)))
        self.numpad_ui.neun.clicked.connect(lambda x: self.emit_num(str(9)))
        self.numpad_ui.xforSpin.clicked.connect(lambda x: self.emit_num("X"))
        self.numpad_ui.yforSpin.clicked.connect(lambda x: self.emit_num("Y"))
        self.numpad_ui.zforSpin.clicked.connect(lambda x: self.emit_num("Z"))
        self.numpad_ui.delte.clicked.connect(
            lambda x: self.emit_num("delete"))
        self.numpad_ui.enter.clicked.connect(
            lambda x: self.emit_num("enter"))
        self.numpad_ui.geschw.clicked.connect(lambda x: self.emit_num("v"))
        print(self.num_buffer)

    def _setup_visu_ui(self):
        self.visu_ui.xStartSpinBox.valueChanged.connect(
            self.gl_widget.move_to_x)
        self.visu_ui.xStartSpinBox.setRange(
            self.gl_widget.min_freq_vec[0], self.gl_widget.max_freq_vec[0])
        self.visu_ui.xStartSpinBox.setSingleStep(100)
        self.visu_ui.xStartSpinBox.setValue(MotorSteuerung.GetPosition(0))

        self.visu_ui.yStartSpinBox.valueChanged.connect(
            self.gl_widget.move_to_y)
        self.visu_ui.yStartSpinBox.setRange(
            self.gl_widget.min_freq_vec[1], self.gl_widget.max_freq_vec[1])
        self.visu_ui.yStartSpinBox.setSingleStep(100)
        self.visu_ui.yStartSpinBox.setValue(MotorSteuerung.GetPosition(1))

        self.visu_ui.zStartSpinBox.valueChanged.connect(
            self.gl_widget.move_to_z)
        self.visu_ui.zStartSpinBox.setRange(
            self.gl_widget.min_freq_vec[2], self.gl_widget.max_freq_vec[2])
        self.visu_ui.zStartSpinBox.setSingleStep(100)
        self.visu_ui.zStartSpinBox.setValue(MotorSteuerung.GetPosition(2))

        self.num_input_x.display(MotorSteuerung.GetPosition(0))
        self.num_input_y.display(MotorSteuerung.GetPosition(1))
        self.num_input_z.display(MotorSteuerung.GetPosition(2))

        self.visu_ui.vSpinBox.valueChanged.connect(self.gl_widget.set_velocity)
        self.visu_ui.vSpinBox.setValue(0.008)

        self.visu_ui.startButton.clicked.connect(
            self.gl_widget.start_procedure)
        self.visu_ui.stopButton.clicked.connect(self.gl_widget.pause_procedure)
        self.visu_ui.hardstopButton.clicked.connect(
            self.gl_widget.stop_procedure)
        self.visu_ui.kalButton.clicked.connect(
            self.gl_widget.calibration_switch)
        self.visu_ui.resetVis.clicked.connect(self.gl_widget.reset_view)
        self.visu_ui.onlyVisual.clicked.connect(
            self.gl_widget.visu_only_switch)
        self.visu_ui.clearPos.clicked.connect(self.gl_widget.clear_pos)
        self.visu_ui.Bahn.clicked.connect(self.gl_widget.conturing_switch)
        self.visu_ui.numBut.clicked.connect(self._init_numpad_widget)

        self.visu_ui.toolButton.setMenu(self.conturing_menu)
        self.visu_ui.toolButton.clicked.connect(
            self.visu_ui.toolButton.showMenu)
        self.shape_1.triggered.connect(self.gl_widget.select_contour_1)
        self.shape_2.triggered.connect(self.gl_widget.select_contour_2)
        self.shape_3.triggered.connect(self.gl_widget.select_contour_3)

    @QtCore.Slot(str)
    def write_to_textedit(self, text: str):
        """Append text to the QTextEdit."""
        cursor = self.visu_ui.TextEdit.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        if text.startswith("[bold]"):
            self.format.setFontWeight(QtGui.QFont.Bold)
            text = text[6:]
            cursor.mergeCharFormat(self.format)
        else:
            self.format.setFontWeight(QtGui.QFont.Normal)
            cursor.mergeCharFormat(self.format)

        cursor.insertText(text)
        self.visu_ui.TextEdit.setTextCursor(cursor)
        self.visu_ui.TextEdit.ensureCursorVisible()

    @QtCore.Slot(int)
    def update_progressbar(self, val):
        """updates progressbar with the current progress data"""
        self.progress_bar.setValue(val)

    @QtCore.Slot(list)
    def update_numpad_txt(self, positons):
        """updates the emited input from the numpad"""
        self.num_input_x.display(positons[0])
        self.num_input_y.display(positons[1])
        self.num_input_z.display(positons[2])

    @QtCore.Slot(list)
    def update_motor_status_txt(self, motor_status):
        """sets and updates the status text of the motors"""
        if not motor_status[0] and motor_status[3]:
            self.x_activ.setText(" MotorX: AKTIV   ")
            self.x_activ.setStyleSheet("background-color: red")
        else:
            self.x_activ.setText(" MotorX: INAKTIV ")
            self.x_activ.setStyleSheet("background-color: lightgreen")

        if not motor_status[1] and motor_status[3]:
            self.y_activ.setText(" MotorY: AKTIV   ")
            self.y_activ.setStyleSheet("background-color: red")
        else:
            self.y_activ.setText(" MotorY: INAKTIV ")
            self.y_activ.setStyleSheet("background-color: lightgreen")

        if not motor_status[2] and motor_status[3]:
            self.z_activ.setText(" MotorZ: AKTIV   ")
            self.z_activ.setStyleSheet("background-color: red")
        else:
            self.z_activ.setText(" MotorZ: INAKTIV ")
            self.z_activ.setStyleSheet("background-color: lightgreen")

    @QtCore.Slot(str)
    def update_process_status_txt(self, status):
        """updates all the process relevant signaltext onm the statusbar"""
        if status == "visu_only_activ":
            self.process_status_txt = "onlyVisual"
            status = self.process_status_txt_old
        elif status == "visu_only_inactiv":
            self.process_status_txt = ""
            status = self.process_status_txt_old

        if status == 'NOP':
            self.process_status_txt_old = status
            self.process_status_label.setText(
                f" {self.process_status_txt} NOP  ")
            self.process_status_label.setStyleSheet(
                "background-color: lightgray")
        elif status == "kal":
            self.process_status_txt_old = status
            self.process_status_label.setText(
                f" {self.process_status_txt} Kalibration AKTIV ")
            self.process_status_label.setStyleSheet("background-color: yellow")
        elif status == "kon":
            self.process_status_txt_old = status
            self.process_status_label.setText(
                f" {self.process_status_txt} Konturing AKTIV ")
            self.process_status_label.setStyleSheet("background-color: yellow")
        elif status == "Error":
            self.process_status_txt_old = status
            self.process_status_label.setText(
                f" {self.process_status_txt} Error ")
            self.process_status_label.setStyleSheet("background-color: red")

    @QtCore.Slot(list)
    def update_start_stop_txt(self, status):
        """updates the start stop status text and color in the progressbar"""
        start_label, stop_label = status
        if start_label:
            self.start_label.setText(" Start: AKTIV   ")
            self.start_label.setStyleSheet("background-color: yellow")
        else:
            self.start_label.setText(" Start: INAKTIV   ")
            self.start_label.setStyleSheet("background-color: lightgray")

        if stop_label:
            self.stop_label.setText(" Stop: AKTIV   ")
            self.stop_label.setStyleSheet("background-color: red")
        else:
            self.stop_label.setText(" Stop: INAKTIV   ")
            self.stop_label.setStyleSheet("background-color: lightgreen")

    @QtCore.Slot()
    def update_distance_input(self):
        """is needed for updating the distance input in the spinner boxes"""
        self.visu_ui.xStartSpinBox.setValue(MotorSteuerung.GetPosition(0))
        self.visu_ui.yStartSpinBox.setValue(MotorSteuerung.GetPosition(1))
        self.visu_ui.zStartSpinBox.setValue(MotorSteuerung.GetPosition(2))

    @QtCore.Slot(str)
    def emit_num(self, num):
        """handels the input from the numpad widget"""
        spinner_box = {"v": self.visu_ui.vSpinBox, "X": self.visu_ui.xStartSpinBox,
                       "Y": self.visu_ui.yStartSpinBox, "Z": self.visu_ui.zStartSpinBox}
        if num in ("v", "X", "Y", "Z"):
            self.num_buffer = num
        if num == "enter" and len(self.num_buffer):
            spinner_box[self.num_buffer[0]].setValue(
                float(self.num_buffer[2:]))
            self.num_buffer = self.num_buffer[:-1]
        elif len(self.num_buffer) == 0:
            self.numpad_ui.lcdNumbpad.display("notSeT")
            print("WARNING! numbpad axis not set! please select an axis")
            return
        else:
            if all((not self.num_buffer.startswith("X"), not self.num_buffer.startswith("Y"),
                    not self.num_buffer.startswith("Z"), not self.num_buffer.startswith("v"))):
                return
            if self.num_buffer[0:4] != "vv0." and self.num_buffer.startswith("v"):
                self.num_buffer = "vv0."
            if num == "delete":
                self.num_buffer = self.num_buffer[:-1]
            elif len(self.num_buffer) < 7:
                self.num_buffer += num
            self.numpad_ui.lcdNumbpad.display(str(self.num_buffer[2:]))


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.showMaximized()
    res = app.exec_()
    mainWin.gl_widget.free_recources()
    sys.exit(res)
