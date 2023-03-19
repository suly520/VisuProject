import ctypes
from math import ceil
import sys
import pyrr
import OpenGL.GL
from OpenGL.GL.shaders import compileProgram, compileShader
from PIL import Image
from PySide2 import QtCore, QtGui, QtOpenGL, QtWidgets
import numpy as np
from Tools import MotorSteuerung, ObjLoader, Ui_VisoWidget, vNeu
from Tools.numpad import Ui_Numpad


class GLWidget(QtOpenGL.QGLWidget):
    """Signale für das Verknüpfen zum MainWindow"""
    updateProgress = QtCore.Signal(int)
    updateLCD = QtCore.Signal(list)
    updateMotorStatus = QtCore.Signal(list)
    updateStatus = QtCore.Signal(str)
    updateStartStop = QtCore.Signal(list)
    updateSpinnerVal = QtCore.Signal()

    def __init__(self, parent=None):
        """Objecte für das Handhaben der Servomotoren und den Austausch 
        von Daten zwischen GLWidget und MainWindow"""
        super(GLWidget, self).__init__(parent)
        # mit diesem Object wird der Zugang zur Steuerungseinheit festgelegt
        self.motor_steering = MotorSteuerung()
        # False als argument bewirkt das nur die zu updatenden elemente initialisiert wird
        self.main_win_obj_for_updating = MainWindow(False)

        self.middle_button = False
        self.left_button = False
        self.right_button = False
        self.trans_view_z = 0
        self.double_click_count = 0

        """Listen und Variablen mit informationen für Raspberry"""
        self.direction_vec = [0, 0, 0]
        self.freq_vec = [0, 0, 0]
        self.v_vec = [0.0007, 0.0007, 0.0007]
        self.max_freq_vec = [1000, 1000, 1000]
        self.min_freq_vec = [0, 0, 0]
        self.max_visu_area_vec = [4.5, 4.5, 1.75]
        self.min_visu_area_vec = [0, 0, 0]

        '''Bedingungen für den Allgemeinen Ablauf'''
        self.zykl_start = False
        self.zykl_stop = False
        self.is_set = False
        self.visu_check_vec = [False, False, False]
        self.visu_check_x, self.visu_check_y, self.visu_check_z = self.visu_check_vec

        """Positions-, Weg und Geschwindigkeitsvariablen für den Allgemeinen Ablauf"""
        # Die PositionsDaten werden direkt von der Steuereinheit geladen
        self.freq_pos_list = (MotorSteuerung.GetPosition(
            0), MotorSteuerung.GetPosition(1), MotorSteuerung.GetPosition(2))
        # Es gibt die Einheit Pulse und eine Einheit für die Visualisierung
        # mit change_unit() werden die Pulse umgewandelt
        self.actual_pos_x, self.actual_pos_y, self.actual_pos_z = [
            self.change_unit(i, pose) for i, pose in enumerate(self.freq_pos_list, 0)]
        self.visu_start_pos_x = self.visu_start_pos_y = self.visu_start_pos_z = 0
        self.visu_target_point_x = self.visu_target_point_y = self.visu_target_point_z = 0
        self.overall_distance_x = self.overall_distance_y = self.overall_distance_z = 0
        self.distance_x = self.distance_y = self.distance_z = 0
        self.vmax = 0

        """Für die GUI"""
        # Verknüpfungen zu den Slots der Grafischenoberfläche
        self.updateProgress.connect(
            self.main_win_obj_for_updating.UpdateProgressBar)
        self.updateLCD.connect(self.main_win_obj_for_updating.UpdateLCD)
        self.updateMotorStatus.connect(
            self.main_win_obj_for_updating.UpdateMotor)
        self.updateStatus.connect(self.main_win_obj_for_updating.UpdateStatus)
        self.updateStartStop.connect(
            self.main_win_obj_for_updating.UpdateStartStop)
        self.updateSpinnerVal.connect(
            self.main_win_obj_for_updating.UpdateSpinerVal)
        self.progress_x = self.progress_y = self.progress_z = 0

        self.vert_arr_obj: OpenGL.GL.ArrayDatatype
        self.vert_buf_obj: OpenGL.GL.ArrayDatatype
        self.model_loc: OpenGL.GL.shaders.ShaderProgram
        self.proj_loc: OpenGL.GL.shaders.ShaderProgram
        self.view_m_loc: OpenGL.GL.shaders.ShaderProgram
        self.visu_pos_vec: list
        self.traget_pos_vec: list
        self.s_vec: list
        self.motor_check_x: bool
        self.motor_check_y: bool
        self.motor_check_z: bool
        self.motor_check_list: tuple
        self.visu_rotation_y: float
        self.view_translation_matrix: pyrr.Matrix44
        self.zoom_matrix: pyrr.Matrix44
        self.target_matrix_x: np.ndarray
        self.target_matrix_y: np.ndarray
        self.target_matrix_z: np.ndarray
        self.rotation_matrix_x: pyrr.Matrix44
        self.generated_pos_vec: list

        """Für definierte Funktionen der steering"""
        # Die zwei Hauptfunktionen sind Kalibrieren und Konturing außerdem gibt
        # es noch die MöGL.glichkeit onlyVisual
        self.calibration_active = False
        self.contouring_active = False
        # Wird dann Aktiv wenn kontur oder kali ausgewählt wurden und zyklStart
        # True ist (zyklStart muss ausgeschaltet werden)
        self.auto_start = False
        # Dient als Indikator das der der nächste Schritt ausgewählt werden kann
        self.next_step_ready = True
        self.current_step = 0  # step ist der Momentane Schritt der Kontur oder der Kalibration
        # wird benötigt um den momentanen Schritt der Kontur oder Kalibration festustellen
        self.old_step = 0
        # Ist ein Platzhalter für einen Pfad zum Konturfile !!! Konturfiles müssen angefertigt
        self.contouring_file = None
        # werden und müssen definierte Maße nicht überschreitten !!!
        # Diese Variable ist für die Funktion die MotorSteureung wegzuschalten
        self.visu_only_activ = False

        """Alle 3D-Objekte, Matritzen, Files Für die 3D_Visualisierung"""
        # Matrizen Für die Ansicht der Objekte
        self.projection_matrix = pyrr.matrix44.create_perspective_projection_matrix(
            45, 1280 / 720, 0.1, 100)
        self.view_matrix = pyrr.matrix44.create_look_at(pyrr.Vector3(
            [0, 0, 25]), pyrr.Vector3([0, 0, 0]), pyrr.Vector3([0, 1, 0]))
        # diese variablen sind für das Drehen bzw Scalieren der Ansicht um die 3D Objecte
        self.visu_rotation_x = self.rotation_matrix_y = 0
        self.zoom = 1
        self.old_rotation_vec = list()
        self.old_translation_vec = list()
        # Matritzen für das Positionieren und Bewegen der Objekte
        self.axis_matrix_x = pyrr.matrix44.create_from_translation(
            pyrr.Vector3([0, -3, 0]))  # y-5
        self.axis_matrix_y = self.axis_matrix_z = self.axis_matrix_x
        self.translation_list = [self.axis_matrix_x,
                                 self.axis_matrix_x, self.axis_matrix_x]
        self.translation_matrix_x = pyrr.Matrix44.from_translation(
            [0, 0, self.actual_pos_x])
        self.translation_matrix_y = pyrr.Matrix44.from_translation(
            [self.actual_pos_y, 0, 0])
        self.translation_matrix_z = pyrr.Matrix44.from_translation(
            [0, -self.actual_pos_z, 0])
        # Textur- und Objfilepfade
        self.texture_files = "./TexturFiles/STEP.jpg"
        self.obj_files = [
            "./ObjFiles/X.obj",
            "./ObjFiles/Y.obj",
            "./ObjFiles/Z.obj",
        ]
        # Ladend der Informationen für das Shaderprogramm
        loaded_objects = self.load_objects()
        self.obj_indices = loaded_objects[0]
        self.obj_buffers = loaded_objects[1]
        # Timer führt die gewählte Funktion(self.Ablauf) aus ist für die Event-loop verantwortlich.
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.Ablauf)
        timer.start()

# OpenGL Grundfunktionen für PySide2 / init, draw, resize /
    def initializeGL(self):
        """Hier wird alles (Vertecies, Buffer und WidgetDisplay) 
        für das Zeichnen initialisiert(vorbereitet)"""
        OpenGL.GL.glEnable(OpenGL.GL.GL_DEPTH_TEST)
        textures = OpenGL.GL.glGenTextures(1)
        self.load_texture(self.texture_files, textures)
        obj_properties = self.create_obj_properties(self.obj_buffers)
        self.vert_buf_obj = obj_properties[0]
        self.vert_arr_obj = obj_properties[1]
        OpenGL.GL.glClearColor(0, 1, 2, 1)

    def paintGL(self):
        """paintGL() zeichnet die Scene"""
        OpenGL.GL.glClear(OpenGL.GL.GL_COLOR_BUFFER_BIT |
                          OpenGL.GL.GL_DEPTH_BUFFER_BIT)
        self.SetTrans()  # mit  SetTrans wird die Matrix Translation neu gezeichnet
        for i, _ in enumerate(self.obj_indices, 0):
            OpenGL.GL.glBindVertexArray(self.vert_arr_obj[i])
            OpenGL.GL.glUniformMatrix4fv(
                self.model_loc, 1, OpenGL.GL.GL_FALSE, self.translation_list[i])
            OpenGL.GL.glDrawArrays(
                OpenGL.GL.GL_TRIANGLES, 0, len(self.obj_indices[i]))

    def resizeGL(self, width, height):
        """Hier wird die Einstellung des Viewports (Modelansicht)
        an die Größe des Fensters angepasst"""
        OpenGL.GL.glViewport(0, 0, width, height)
        shader = self.create_shader()
        self.model_loc = OpenGL.GL.glGetUniformLocation(shader, "model")
        self.proj_loc = OpenGL.GL.glGetUniformLocation(shader, "projection")
        self.view_m_loc = OpenGL.GL.glGetUniformLocation(shader, "view")
        OpenGL.GL.glUniformMatrix4fv(
            self.proj_loc, 1, OpenGL.GL.GL_FALSE, self.projection_matrix)
        OpenGL.GL.glUniformMatrix4fv(
            self.view_m_loc, 1, OpenGL.GL.GL_FALSE, self.view_matrix)

    @staticmethod
    def create_shader():
        """Hier werden die Shaderprogramme erstellt und an die GPU als Schnittstelle gesendet"""
        vertex_src = """
        # version 300 es

        layout(location = 0) in vec3 a_position;
        layout(location = 1) in vec2 a_texture;

        uniform mat4 model;
        uniform mat4 projection;
        uniform mat4 view;
      
        out vec2 v_texture;

        void main()
        {
            gl_Position = projection * view * model * vec4(a_position, 1.0); 
            v_texture = a_texture;
        }
        """

        fragment_src = """
        # version 300 es
    
        precision mediump float;

        in vec2 v_texture;

        out vec4 out_color;

        uniform sampler2D s_texture;

        void main()
        {
            out_color = texture(s_texture, v_texture);
        }
        """
        # compileProgramm compeliert die Shaderprogramme für die GPU
        shader = compileProgram(compileShader(vertex_src, OpenGL.GL.GL_VERTEX_SHADER),
                                compileShader(fragment_src, OpenGL.GL.GL_FRAGMENT_SHADER))
        # mit OpenGL.GL.glUseProgramm werden die Shaderprogramme
        # ausgewählt und dienen als Schnittstelle für die GPU
        OpenGL.GL.glUseProgram(shader)
        return shader

    @staticmethod
    def create_obj_properties(bufferlist):
        """Hier werden die Vertex Array- und Vertex Buffer Objekte erstellt"""
        vertex_array_object = OpenGL.GL.glGenVertexArrays(len(
            bufferlist))    # enthält die Informationen zu den Vertexdaten aus den
        # vertex_buffer_object's
        # (Datenformat, welches vertex_buffer_object , ...)
        # es enthält die eigendlichen Vertexdaten der Objekte
        vertex_buffer_object = OpenGL.GL.glGenBuffers(len(bufferlist))

        for i, buffer in enumerate(bufferlist, 0):
            if len(bufferlist) == 1:
                i = 0
            # das vertex_array_object wird an den index i gebunden
            OpenGL.GL.glBindVertexArray(vertex_array_object[i])

            # das vertex_buffer_object wird an den index i gebunden
            OpenGL.GL.glBindBuffer(
                OpenGL.GL.GL_ARRAY_BUFFER, vertex_buffer_object[i])
            # die Vertexdaten werden im vertex_buffer_object deklariert
            OpenGL.GL.glBufferData(
                OpenGL.GL.GL_ARRAY_BUFFER, buffer.nbytes, buffer, OpenGL.GL.GL_STATIC_DRAW)

            # Hier werden die Atribute der einzelnen Bufferelemte zugeordenet und angepielt
            # vertices
            OpenGL.GL.glEnableVertexAttribArray(0)
            OpenGL.GL.glVertexAttribPointer(
                0, 4, OpenGL.GL.GL_FLOAT, OpenGL.GL.GL_FALSE,
                buffer.itemsize * 8, ctypes.c_void_p(0))
            # textures
            OpenGL.GL.glEnableVertexAttribArray(1)
            OpenGL.GL.glVertexAttribPointer(
                1, 4, OpenGL.GL.GL_FLOAT, OpenGL.GL.GL_FALSE,
                buffer.itemsize * 8, ctypes.c_void_p(12))
            # normals
            OpenGL.GL.glEnableVertexAttribArray(2)
            OpenGL.GL.glVertexAttribPointer(
                2, 4, OpenGL.GL.GL_FLOAT, OpenGL.GL.GL_FALSE,
                buffer.itemsize * 8, ctypes.c_void_p(20))

        return vertex_array_object, vertex_buffer_object

    def load_objects(self):
        """Hier werden die Objecte für die 3D-Visulation geladen und eine indeciesliste 
        und Bufferliste erstellt"""
        obj_indices = []
        obj_buffers = []
        for obj_file in self.obj_files:
            if len(obj_file) == 1:
                indecies, buffers = ObjLoader.LoadModel(self.obj_files)
            indecies, buffers = ObjLoader.LoadModel(obj_file)
            obj_indices.append(indecies)
            obj_buffers.append(buffers)
        return obj_indices, obj_buffers

    @staticmethod
    def load_texture(path, texture):
        """Hier werden die Texturen geladen und an das Object gebunden"""
        OpenGL.GL.glBindTexture(OpenGL.GL.GL_TEXTURE_2D, texture)
        # Parameter für das Texturen wrapping
        OpenGL.GL.glTexParameteri(
            OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_WRAP_S, OpenGL.GL.GL_REPEAT)
        OpenGL.GL.glTexParameteri(
            OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_WRAP_T, OpenGL.GL.GL_REPEAT)
        # Parameter für die Texturfilterung
        OpenGL.GL.glTexParameteri(
            OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_MIN_FILTER, OpenGL.GL.GL_LINEAR)
        OpenGL.GL.glTexParameteri(
            OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_MAG_FILTER, OpenGL.GL.GL_LINEAR)
        # load image
        image = Image.open(path)
        image = image.transpose(Image.FLIP_TOP_BOTTOM)
        img_data = image.convert("RGBA").tobytes()

        OpenGL.GL.glTexImage2D(OpenGL.GL.GL_TEXTURE_2D, 0, OpenGL.GL.GL_RGBA, image.width,
                image.height, 0, OpenGL.GL.GL_RGBA, OpenGL.GL.GL_UNSIGNED_BYTE, img_data)
        return texture

    def change_unit(self, achse, inp, to_frequency=False):
        """Ist für das umwandeln von Pulsen in Visualisierungseinheit"""
        if not to_frequency:
            outp = inp * \
                self.max_visu_area_vec[achse] / self.max_freq_vec[achse]
        if to_frequency:
            outp = inp * self.max_freq_vec[achse] / \
                self.max_visu_area_vec[achse]
        return outp

    def steering(self):
        """Hier werden die Position gesetzt welche die Maschine anfahren und 
        visualisiert werden soll"""

        # Diese Bedingung ist für das setzten der Kalibrations- bzw. Konturposition
        if not self.zykl_stop and not self.is_set and (self.calibration_active or self.contouring_active):
            self.set_auto_pos()
            # ist step größer old_step ist der Schritt gesetzt
            # worden und kann automatisch gestartet werden
            if self.current_step > self.old_step and self.auto_start:
                self.old_step = self.current_step
                if self.calibration_active and self.current_step > 0 or self.contouring_active and self.current_step > 1:
                    self.ZyklusStart()

        # der Weg wird für die Berechnung der Geschwindigkeit benötigt und auf Grund
        # des Vorzeichens für der Motordrehrichtung gebraucht
        self.distance_x = self.visu_target_point_x - self.actual_pos_x
        self.distance_y = self.visu_target_point_y - self.actual_pos_y
        self.distance_z = self.visu_target_point_z - self.actual_pos_z

        self.visu_pos_vec = [self.actual_pos_x,
                             self.actual_pos_y, self.actual_pos_z]
        self.traget_pos_vec = [self.visu_target_point_x,
                               self.visu_target_point_y, self.visu_target_point_z]
        self.s_vec = [self.distance_x, self.distance_y, self.distance_z]

        # gibt die Geschwindigkeit und ob der moter eingeschaltet werden soll zurück
        eng_settings = vNeu(self.distance_x, self.distance_y,
                            self.distance_z, self.vmax)

        if self.zykl_start and not self.zykl_stop:
            if not self.visu_only_activ:
                # die aktuelle Position des Motors
                self.freq_pos_list = self.motor_steering.GetMotorPosition()
                for i, pose in enumerate(self.visu_pos_vec):
                    # Drehrichtungsbestimmung
                    self.stepper(
                        i, pose, self.traget_pos_vec[i], self.s_vec[i], eng_settings[i])

                self.actual_pos_x, self.actual_pos_y, self.actual_pos_z = [
                    self.change_unit(i, poses) for i, poses in enumerate(self.freq_pos_list, 0)]
                # position für die Visualisierung

            else:
                self.actual_pos_x, self.actual_pos_y, self.actual_pos_z = [
                    self.stepper(
                        i, pose, self.traget_pos_vec[i], self.s_vec[i], eng_settings[i])
                    for i, pose in enumerate(self.visu_pos_vec, 0)]
                # um die aktuelle Motorposition zu simulieren muss der Visu wert in Pulse
                # umgewandelt werden
                self.freq_pos_list = [int(self.change_unit(i, poses, to_frequency=True))
                                      for i, poses in enumerate(self.visu_pos_vec, 0)]

            if not self.is_set:  # um die MotorSteuerung nicht ständig aus und einzuschalten
                # und gewisse Variablen zu setzen die nur einmal betätigt
                #  werden sollen
                if not self.contouring_active:
                    print('..:: Start ::..')
                self.is_set = True
                self.visu_start_pos_x = self.actual_pos_x
                self.visu_start_pos_y = self.actual_pos_y
                self.visu_start_pos_z = self.actual_pos_z
                # wird benötigt für das Kalkulieren der Prozesslänge für den Progressbar
                self.overall_distance_x = self.distance_x
                self.overall_distance_y = self.distance_y
                self.overall_distance_z = self.distance_z
                if not self.visu_only_activ:
                    self.motor_steering.Start(self.direction_vec, self.v_vec, self.freq_vec,
                                              self.max_freq_vec, self.min_freq_vec, eng_settings[3:6])

            if not self.visu_only_activ:
                self.motor_check_x, self.motor_check_y, self.motor_check_z = self.motor_steering.GetMotorStatus()
                self.motor_check_list = (self.motor_check_x, self.motor_check_y,
                                         self.motor_check_z, self.zykl_start)
            else:
                self.visu_check_vec = (
                    self.visu_check_x, self.visu_check_y, self.visu_check_z)

            if all(self.motor_check_list) or (self.visu_only_activ and all(self.visu_check_vec)):
                self.zykl_start = False
                self.is_set = False
                self.visu_check_x = False
                self.visu_check_y = False
                self.visu_check_z = False
                if self.calibration_active or self.contouring_active:
                    self.current_step += 1
                    self.next_step_ready = True
            self.update_stats_on_main_win()

    def set_auto_pos(self):
        """is for automated steering while contouring or calibrating"""
        step_vec = [
            [0, 0, 0], [4, 4, 1.7], [0, 0, 0], [4, 4, 0], [
                0, 0, 1.7], [4, 4, 0], [0, 0, 0],
            [4, 0, 1.7], [0, 4, 0], [4, 0, 1.7], [
                0, 0, 0], [4, 0, 0], [0, 4, 1.7],
            [4, 0, 0], [0, 4, 0], [4, 0, 0], [
                0, 0, 1.7], [4, 0, 0], [0, 0, 0],
            [0, 4, 1.7], [0, 0, 0], [0, 4, 0], [
                0, 0, 1.7], [0, 4, 0], [0, 0, 0],
            [0, 0, 1.7], [0, 0, 0], "ENDE"
        ]

        actual_pos_vec = [self.actual_pos_x, self.actual_pos_y, self.actual_pos_z]
        if self.next_step_ready:
            if self.calibration_active:
                if step_vec[self.current_step] == actual_pos_vec:
                    self.current_step += 1

                if step_vec[self.current_step] != "ENDE":
                    steps = step_vec[self.current_step]
                    print("SchrittNR.", self.current_step,
                          step_vec[self.current_step])
                else:
                    self.KalibrationSwitch()
                    self.update_stats_on_main_win()
                    self.updateProgress.emit(100)
                    print("Kallibrierung abgeschlossen")

            elif self.contouring_active:
                self.current_step += 1
                pos_fail = None

                try:
                    steps = next(self.generated_pos_vec)
                    for i, j in enumerate(steps, 0):
                        if i == 2 and float(j) > 0 and float(j) < 1.75:
                            steps[i] = float(j)
                        elif float(j) > 0 and float(j) < 4.5:
                            steps[i] = float(j) * 2
                        else:
                            pos_fail = steps[i]
                            raise StopIteration
                except StopIteration:
                    self.KonturSwitch()
                    self.update_stats_on_main_win()
                    self.updateProgress.emit(100)
                    if not pos_fail:
                        print("Konturing abgeschlossen")
                    else:
                        print(
                            f"..::ERROR::.. Konturvorgabe out of range! Kunturpos: {pos_fail} ")

            if (self.calibration_active or self.contouring_active):
                self.next_step_ready = False
                target_points = [self.change_unit(
                    i, pos, to_frequency=True) for i, pos in enumerate(steps, 0)]
                self.move_to_x(target_points[0])
                self.move_to_y(target_points[1])
                self.move_to_z(target_points[2])

    def stepper(self, achse, ist, soll, weg, vel):
        """steps and commands for the steppermotor"""
        if not self.zykl_stop:
            if weg > 0 and not self.zykl_stop:
                ist += vel
                self.direction_vec[achse] = 0

            elif weg < 0 and not self.zykl_stop:
                ist -= vel
                self.direction_vec[achse] = 1

            if weg > 0 and ist >= soll or weg < 0 and ist <= soll or weg == 0:
                ist = soll
                if self.visu_only_activ:
                    if achse == 0:
                        self.visu_check_x = True
                    elif achse == 1:
                        self.visu_check_y = True
                    elif achse == 2:
                        self.visu_check_z = True
            if self.visu_only_activ:
                return ist

    def update_stats_on_main_win(self):
        """updates stats of UI (progressbar, motorstatus, poscounter, startstop)"""
        if not self.calibration_active or self.contouring_active:
            self.record_progress()
        else:
            self.updateProgress.emit(int(ceil(self.current_step*3.703703704)))

        self.updateLCD.emit(self.freq_pos_list)
        self.updateMotorStatus.emit(self.motor_check_list)
        self.updateStartStop.emit([self.zykl_start, self.zykl_stop])

    def record_progress(self):
        if self.overall_distance_x != 0 and self.distance_x != 0:
            self.progress_x = abs(self.distance_x * 100 /
                                  abs(self.overall_distance_x))
            self.updateProgress.emit(int(ceil(100 - self.progress_x)))
        elif self.overall_distance_x != 0 and self.distance_x == 0:
            self.progress_x = abs(self.distance_x * 100 /
                                  abs(self.overall_distance_x))
            self.updateProgress.emit(int(ceil(self.progress_x)))
        elif self.overall_distance_y != 0 and self.distance_y != 0:
            self.progress_y = abs(self.distance_y * 100 /
                                  abs(self.overall_distance_y))
            self.updateProgress.emit(int(ceil(100 - self.progress_y)))
        elif self.overall_distance_y != 0 and self.distance_y == 0:
            self.progress_y = abs(self.distance_y * 100 /
                                  abs(self.overall_distance_y))
            self.updateProgress.emit(int(ceil(self.progress_y)))
        elif self.overall_distance_z != 0 and self.distance_z != 0:
            self.progress_z = abs(self.distance_z * 100 /
                                  abs(self.overall_distance_z))
            self.updateProgress.emit(int(ceil(100 - self.progress_z)))
        elif self.overall_distance_z != 0 and self.distance_z == 0:
            self.progress_z = abs(self.actual_pos_z *
                                  100 / abs(self.overall_distance_z))
            self.updateProgress.emit(int(ceil(self.progress_z)))

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        """describes the mouse behaviour in the 3D visualisation"""
        mouse_pos_x = 0
        mouse_pos_y = 0
        old_pos = []
        if self.middle_button or self.right_button:
            old_pos = self.old_translation_vec
        elif self.left_button:
            old_pos = self.old_rotation_vec
        if old_pos:
            old_mouse_pos_x = old_pos[0]
            old_mouse_pos_y = old_pos[1]

            delta_mouse_pos_x = old_mouse_pos_x - QtGui.QMouseEvent.x(event)
            delta_mouse_pos_y = old_mouse_pos_y - QtGui.QMouseEvent.y(event)

            if abs(delta_mouse_pos_x) > abs(delta_mouse_pos_y) and delta_mouse_pos_x > 0:
                mouse_pos_x += 1  # links
            elif abs(delta_mouse_pos_x) > abs(delta_mouse_pos_y) and delta_mouse_pos_x < 0:
                mouse_pos_x -= 1  # rechts
            elif abs(delta_mouse_pos_y) > abs(delta_mouse_pos_x) and delta_mouse_pos_y > 0:
                mouse_pos_y += 1  # oben
            elif abs(delta_mouse_pos_y) > abs(delta_mouse_pos_x) and delta_mouse_pos_y < 0:
                mouse_pos_y -= 1  # unten

        newPosX = QtGui.QMouseEvent.x(event)
        newPosY = QtGui.QMouseEvent.y(event)
        old_pos = [newPosX, newPosY]

        if self.left_button:
            self.old_rotation_vec = old_pos
            self.visu_rotation_x = mouse_pos_y/150
            self.visu_rotation_y = mouse_pos_x/60
            self.SetViewRotation()

        elif self.middle_button or self.right_button:
            self.old_translation_vec = old_pos
            transX = -mouse_pos_x * 0.1
            transY = mouse_pos_y * 0.1
            if not self.right_button:
                self.view_translation_matrix = pyrr.Matrix44.from_translation(
                    [transX, transY, 0])
            else:
                if abs(transX) > abs(transY):
                    self.view_translation_matrix = pyrr.Matrix44.from_translation(
                        [0, 0, transX])
                else:
                    self.view_translation_matrix = pyrr.Matrix44.from_translation(
                        [0, 0, transY])
            self.view_matrix = pyrr.matrix44.multiply(
                self.view_translation_matrix, self.view_matrix)
            self.resizeGL(self.width(), self.height())
        return super(). mouseMoveEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self.left_button = False
            self.right_button = False
            self.middle_button = True
        elif event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.middle_button = False
            self.right_button = False
            self.left_button = True
        elif event.button() == QtCore.Qt.MouseButton.RightButton:
            self.middle_button = False
            self.left_button = False
            self.right_button = True
        else:
            self.middle_button = False
            self.left_button = False
            self.right_button = False
        return super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            if self.double_click_count < 5:
                self.trans_view_z = 1.5
            elif self.double_click_count < 15:
                self.trans_view_z = -1.5
            else:
                self.double_click_count = -1
            print(self.double_click_count)
            self.view_translation_matrix = pyrr.Matrix44.from_translation(
                [0, 0, self.trans_view_z])
            self.view_matrix = pyrr.matrix44.multiply(
                self.view_translation_matrix, self.view_matrix)
            self.double_click_count += 1
            self.resizeGL(self.width(), self.height())
        return super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event: QtGui.QWheelEvent):
        gradWeel = event.delta() / 8
        weelstep = gradWeel / 15

        if weelstep < 0:
            self.zoom = 0.9
        else:
            self.zoom = 1.1

        self.zoom_matrix = pyrr.Matrix44.from_scale(
            [self.zoom, self.zoom, self.zoom])
        self.view_matrix = pyrr.matrix44.multiply(
            self.zoom_matrix, self.view_matrix)
        self.resizeGL(self.width(), self.height())
        return super().wheelEvent(event)

    def SetTrans(self):
        self.translation_matrix_x = pyrr.Matrix44.from_translation(
            [0, 0, self.actual_pos_x])
        self.translation_matrix_y = pyrr.Matrix44.from_translation(
            [self.actual_pos_y, 0, 0])
        self.translation_matrix_z = pyrr.Matrix44.from_translation(
            [0, -self.actual_pos_z, 0])

        self.target_matrix_x = self.axis_matrix_x
        self.target_matrix_y = pyrr.matrix44.multiply(
            self.translation_matrix_x, self.axis_matrix_y)
        self.target_matrix_z = pyrr.matrix44.multiply(
            self.translation_matrix_x, self.axis_matrix_z)
        self.target_matrix_z = pyrr.matrix44.multiply(
            self.translation_matrix_y, self.target_matrix_z)
        self.target_matrix_z = pyrr.matrix44.multiply(
            self.translation_matrix_z, self.target_matrix_z)

        self.translation_list[0] = self.target_matrix_x
        self.translation_list[1] = self.target_matrix_y
        self.translation_list[2] = self.target_matrix_z

    def SetViewRotation(self):
        self.rotation_matrix_y = pyrr.Matrix44.from_y_rotation(
            self.visu_rotation_y)
        self.rotation_matrix_x = pyrr.Matrix44.from_x_rotation(
            self.visu_rotation_x)

        self.view_matrix = pyrr.matrix44.multiply(
            self.rotation_matrix_y, self.view_matrix)
        self.view_matrix = pyrr.matrix44.multiply(
            self.rotation_matrix_x, self.view_matrix)
        self.resizeGL(self.width(), self.height())

    def Ablauf(self):
        self.steering()
        self.SetTrans()
        self.updateGL()

    def ResetToStart(self):
        self.zykl_start = False
        self.motor_steering.HardStopping()
        self.motor_check_list = [True, True, True, self.zykl_start]
        self.current_step = 0
        self.old_step = 0
        self.next_step_ready = True
        self.actual_pos_x, self.actual_pos_y, self.actual_pos_z = [self.change_unit(
            i, pose) for i, pose in enumerate(self.freq_pos_list, 0)]
        self.updateStatus.emit('NOP')
        self.updateSpinnerVal.emit()  # Setzt die SpinerBox Werte auf die aktuelle Position
        self.update_stats_on_main_win()

# Widgets Slots
    @QtCore.Slot()
    def FreeRecources(self):
        """Helper to clean up resources."""
        self.makeCurrent()
        OpenGL.GL.glDeleteBuffers(3)
        OpenGL.GL.glDeleteVertexArrays(3)

    @QtCore.Slot(int)
    def move_to_x(self, ziel):
        xIst = MotorSteuerung.GetPosition(0)
        # self.change_unit(0, self.actual_pos_x, to_frequency = True
        self.freq_vec[0] = ziel - xIst
        self.freq_vec[0] = abs(int(ceil(self.freq_vec[0])))
        ziel = self.change_unit(0, ziel)
        self.visu_target_point_x = ziel

    @QtCore.Slot(int)
    def move_to_y(self, ziel):
        yIst = MotorSteuerung.GetPosition(1)
        # self.change_unit(1, self.actual_pos_y, to_frequency = True)
        self.freq_vec[1] = ziel - yIst
        self.freq_vec[1] = abs(int(ceil(self.freq_vec[1])))
        ziel = self.change_unit(1, ziel)
        self.visu_target_point_y = ziel

    @QtCore.Slot(int)
    def move_to_z(self, ziel):
        zIst = MotorSteuerung.GetPosition(2)
        # self.change_unit(2, self.actual_pos_z, to_frequency = True)
        self.freq_vec[2] = ziel - zIst
        self.freq_vec[2] = abs(int(ceil(self.freq_vec[2])))
        ziel = self.change_unit(2, ziel)
        self.visu_target_point_z = ziel

    @QtCore.Slot(bool)
    def ZyklusStart(self):
        if not self.zykl_start and not self.zykl_stop:
            if self.distance_x or self.distance_y or self.distance_z or self.calibration_active or self.contouring_active:
                self.zykl_start = True
                if self.calibration_active or self.contouring_active:
                    self.auto_start = True
        else:
            self.zykl_start = False
            if self.zykl_stop:
                print("Stop ist aktiv")
        self.updateStartStop.emit([self.zykl_start, self.zykl_stop])

    @QtCore.Slot(bool)
    def ZyklusStop(self):
        if not self.zykl_stop:
            self.zykl_stop = True
            if not self.visu_only_activ and self.zykl_start:
                self.motor_steering.Stopping()
        else:
            self.zykl_stop = False
            if not self.visu_only_activ:
                self.motor_steering.ClearStop()
        self.updateStartStop.emit([self.zykl_start, self.zykl_stop])

    @QtCore.Slot(bool)
    def ZyklusHardStop(self):
        if not self.visu_only_activ and self.zykl_start:
            self.ResetToStart()
        self.zykl_start = False

    @QtCore.Slot(bool)
    def KalibrationSwitch(self):
        if self.calibration_active:
            self.calibration_active = False
            self.ResetToStart()
            print('Kalibration OFF')
        else:
            if not self.contouring_active:
                self.calibration_active = True
                self.updateStatus.emit('kal')
                print('Kalibration ON')
            else:
                print(
                    "..::ERROR::..\nKonturing und Kallibration kann nicht OpenGL.GL.gleichzeitig verwendet werden")

    @QtCore.Slot(bool)
    def KonturSwitch(self):
        self.generated_pos_vec = None
        if self.contouring_active:
            self.contouring_active = False
            self.contouring_file = None
            self.ResetToStart()
        else:
            if not self.calibration_active:
                if self.contouring_file != None:
                    self.contouring_active = True
                    print("Konturing gestartet")
                    self.generated_pos_vec = ObjLoader.PosGenerate(
                        self.contouring_file)
                    self.updateStatus.emit('kon')
                else:
                    print("..::ERROR::..\nKein File vorhanden")
            else:
                print(
                    "..::ERROR::..\nKonturing ist wärend einer Kalibration nicht möGL.glich !!")

    @QtCore.Slot(float)
    def SetSpeed(self, speed):
        self.vmax = speed

    @QtCore.Slot(float)
    def ResetViewpos(self):
        self.view_matrix = pyrr.matrix44.create_look_at(pyrr.Vector3(
            [5, 0, 20]), pyrr.Vector3([0, 0, 0]), pyrr.Vector3([0, 1, 0]))
        self.SetViewRotation()

    @QtCore.Slot(float)
    def SetToVis(self):
        if not self.visu_only_activ:
            self.visu_only_activ = True
            self.updateStatus.emit("visu_only_activ")
            self.motor_check_list = [False, False, False, False]
            print("Visualisierung only ON")
        elif self.visu_only_activ and not self.is_set:
            self.updateStatus.emit("notonlyVis")
            self.visu_only_activ = False
            print("Visualisierung only OFF")
        else:
            print(
                "Der Zyklus muss beendet werden um die Visualisierung beenden zun können")

    @QtCore.Slot(bool)
    def SetDefaultPos(self):
        posFiles = ("./Tools/X.txt", "./Tools/Y.txt", "./Tools/Z.txt")

        for posFile in posFiles:
            with open(posFile, "w", encoding="utf8") as f:
                f.write('0')
        self.actual_pos_x = 0
        self.actual_pos_y = 0
        self.actual_pos_z = 0
        self.updateSpinnerVal.emit()

    @QtCore.Slot(bool)
    def SetKonturFile1(self):
        self.contouring_file = "./ObjFiles/HTL.obj"
        print("KonturFile: ", self.contouring_file)

    @QtCore.Slot(bool)
    def SetKonturFile2(self):
        self.contouring_file = "./ObjFiles/HalloWelt.obj"
        print("KonturFile: ", self.contouring_file)

    @QtCore.Slot(bool)
    def SetKonturFile3(self):
        self.contouring_file = "C:/HAHAHA3"
        print("KonturFile: ", self.contouring_file)


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, initGLWidget=True, parent=None):
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

        self.InitStatusTools()
        if initGLWidget == True:
            self.CreateActionMenu()
            self.InitGLWidget()
            self.InitDockAble()

    def __del__(self):
        # Restore sys.stdout
        sys.stdout = sys.__stdout__

    def InitGLWidget(self):

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

    def InitStatusTools(self):
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

    def InitDockAble(self):
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

        self.ui.vSpinBox.valueChanged.connect(self.glWidget.SetSpeed)
        self.ui.vSpinBox.setValue(0.008)

        self.ui.startButton.clicked.connect(self.glWidget.ZyklusStart)
        self.ui.stopButton.clicked.connect(self.glWidget.ZyklusStop)
        self.ui.hardstopButton.clicked.connect(self.glWidget.ZyklusHardStop)
        self.ui.kalButton.clicked.connect(self.glWidget.KalibrationSwitch)
        self.ui.resetVis.clicked.connect(self.glWidget.ResetViewpos)
        self.ui.onlyVisual.clicked.connect(self.glWidget.SetToVis)
        self.ui.clearPos.clicked.connect(self.glWidget.SetDefaultPos)
        self.ui.Bahn.clicked.connect(self.glWidget.KonturSwitch)
        self.ui.numBut.clicked.connect(self.InitNum)

        self.ui.toolButton.setMenu(self.menu)
        self.ui.toolButton.clicked.connect(self.ui.toolButton.showMenu)
        self.Kontur1.triggered.connect(self.glWidget.SetKonturFile1)
        self.Kontur2.triggered.connect(self.glWidget.SetKonturFile2)
        self.Kontur3.triggered.connect(self.glWidget.SetKonturFile3)

    def CreateActionMenu(self):
        self.menu = QtWidgets.QMenu("Konturen", self)
        self.Kontur1 = QtWidgets.QAction("Kontur1", self)
        self.Kontur2 = QtWidgets.QAction("Kontur2", self)
        self.Kontur3 = QtWidgets.QAction("Kontur3", self)
        self.menu.addAction(self.Kontur1)
        self.menu.addAction(self.Kontur2)
        self.menu.addAction(self.Kontur3)

    @QtCore.Slot(str)
    def NormalOutputWritten(self, text):
        """Append text to the QTextEdit."""
        cursor = self.ui.TextEdit.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
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
        elif status == "notonlyVis":
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
            print("ha")
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


class EmittingStream(QtCore.QObject):
    textWritten = QtCore.Signal(str)

    def write(self, text):
        self.textWritten.emit(str(text))


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.showMaximized()
    res = app.exec_()
    mainWin.glWidget.FreeRecources()
    sys.exit(res)
