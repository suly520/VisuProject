""""this moduel does this"""
import ctypes
from math import ceil
import pyrr
import numpy as np
import OpenGL.GL
from OpenGL.GL.shaders import compileProgram, compileShader
from PIL import Image
from PySide2 import QtCore, QtGui, QtOpenGL

from Tools import MotorSteuerung, ObjLoader, vNeu


class GLWidget(QtOpenGL.QGLWidget):
    """Widget class containing all tools for handling servo motors and exchanging data between
      GLWidget and MainWindow
      TODO: Make the OOP concept more clear > better structure and better encapsulation
      """
    updateProgress = QtCore.Signal(int)
    updateLCD = QtCore.Signal(list)
    updateMotorStatus = QtCore.Signal(list)
    updateStatus = QtCore.Signal(str)
    updateStartStop = QtCore.Signal(list)
    updateSpinnerVal = QtCore.Signal()

    def __init__(self, parent=None):
        super(GLWidget, self).__init__(parent)
        self.motor_steering = MotorSteuerung()

        self.middle_button = False
        self.left_button = False
        self.right_button = False
        self.trans_view_z = 0
        self.double_click_count = 0

        self.direction_vec = [0, 0, 0]
        self.freq_vec = [0, 0, 0]
        self.v_vec = [0.0007, 0.0007, 0.0007]
        self.max_freq_vec = [1000, 1000, 1000]
        self.min_freq_vec = [0, 0, 0]
        self.max_visu_area_vec = [4.5, 4.5, 1.75]
        self.min_visu_area_vec = [0, 0, 0]

        self.cycle_start = False
        self.cycle_stop = False
        self.is_set = False
        self.visu_check_vec = [False, False, False]
        self.visu_check_x, self.visu_check_y, self.visu_check_z = self.visu_check_vec

        self.freq_pos_list = (MotorSteuerung.GetPosition(
            0), MotorSteuerung.GetPosition(1), MotorSteuerung.GetPosition(2))
        self.actual_pos_x, self.actual_pos_y, self.actual_pos_z = [
            self.change_unit(i, pose) for i, pose in enumerate(self.freq_pos_list, 0)]
        self.visu_start_pos_x = self.visu_start_pos_y = self.visu_start_pos_z = 0
        self.visu_target_point_x = self.visu_target_point_y = self.visu_target_point_z = 0
        self.overall_distance_x = self.overall_distance_y = self.overall_distance_z = 0
        self.distance_x = self.distance_y = self.distance_z = 0
        self.vmax = 0

        """GUI"""
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

        """for steering"""
        self.calibration_active = False
        self.contouring_active = False
        self.auto_start = False
        self.next_step_ready = True
        self.current_step = 0
        self.old_step = 0
        self.contouring_file = None
        self.visu_only_activ = False

        self.projection_matrix = pyrr.matrix44.create_perspective_projection_matrix(
            45, 1280 / 720, 0.1, 100)
        self.view_matrix = pyrr.matrix44.create_look_at(pyrr.Vector3(
            [0, 0, 25]), pyrr.Vector3([0, 0, 0]), pyrr.Vector3([0, 1, 0]))
        self.visu_rotation_x = self.rotation_matrix_y = 0
        self.zoom = 1
        self.old_rotation_vec = list()
        self.old_translation_vec = list()
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
        self.texture_files = "./TexturFiles/STEP.jpg"
        self.obj_files = [
            "./ObjFiles/X.obj",
            "./ObjFiles/Y.obj",
            "./ObjFiles/Z.obj",
        ]
        loaded_objects = self.load_objects()
        self.obj_indices = loaded_objects[0]
        self.obj_buffers = loaded_objects[1]
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.main_procedure)
        timer.start()

    def initializeGL(self):
        """initializes all vertecies, buffer and the WidgetDisplay"""
        OpenGL.GL.glEnable(OpenGL.GL.GL_DEPTH_TEST)
        textures = OpenGL.GL.glGenTextures(1)
        self.load_texture(self.texture_files, textures)
        obj_properties = self.create_obj_properties(self.obj_buffers)
        self.vert_buf_obj = obj_properties[0]
        self.vert_arr_obj = obj_properties[1]
        OpenGL.GL.glClearColor(0, 1, 2, 1)

    def paintGL(self):
        """paintGL() draws the scene"""
        OpenGL.GL.glClear(OpenGL.GL.GL_COLOR_BUFFER_BIT |
                          OpenGL.GL.GL_DEPTH_BUFFER_BIT)
        self.translate_view()
        for i, _ in enumerate(self.obj_indices, 0):
            OpenGL.GL.glBindVertexArray(self.vert_arr_obj[i])
            OpenGL.GL.glUniformMatrix4fv(
                self.model_loc, 1, OpenGL.GL.GL_FALSE, self.translation_list[i])
            OpenGL.GL.glDrawArrays(
                OpenGL.GL.GL_TRIANGLES, 0, len(self.obj_indices[i]))

    def resizeGL(self, width, height):
        """settings for the viewport"""
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
        """sends the shader to the gpu and returns a shader object"""
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
        shader = compileProgram(
            compileShader(vertex_src, OpenGL.GL.GL_VERTEX_SHADER),
            compileShader(fragment_src, OpenGL.GL.GL_FRAGMENT_SHADER))
        OpenGL.GL.glUseProgram(shader)
        return shader

    @staticmethod
    def create_obj_properties(bufferlist):
        """returns a tuple containing vertex array object and vertex buffer object"""
        vertex_array_object = OpenGL.GL.glGenVertexArrays(len(
            bufferlist))
        vertex_buffer_object = OpenGL.GL.glGenBuffers(len(bufferlist))

        for i, buffer in enumerate(bufferlist, 0):
            if len(bufferlist) == 1:
                i = 0
            OpenGL.GL.glBindVertexArray(vertex_array_object[i])
            OpenGL.GL.glBindBuffer(
                OpenGL.GL.GL_ARRAY_BUFFER, vertex_buffer_object[i])
            OpenGL.GL.glBufferData(
                OpenGL.GL.GL_ARRAY_BUFFER, buffer.nbytes, buffer, OpenGL.GL.GL_STATIC_DRAW)
            OpenGL.GL.glEnableVertexAttribArray(0)
            OpenGL.GL.glVertexAttribPointer(0, 4, OpenGL.GL.GL_FLOAT, OpenGL.GL.GL_FALSE,
                                            buffer.itemsize * 8, ctypes.c_void_p(0))
            OpenGL.GL.glEnableVertexAttribArray(1)
            OpenGL.GL.glVertexAttribPointer(1, 4, OpenGL.GL.GL_FLOAT, OpenGL.GL.GL_FALSE,
                                            buffer.itemsize * 8, ctypes.c_void_p(12))
            OpenGL.GL.glEnableVertexAttribArray(2)
            OpenGL.GL.glVertexAttribPointer(2, 4, OpenGL.GL.GL_FLOAT, OpenGL.GL.GL_FALSE,
                                            buffer.itemsize * 8, ctypes.c_void_p(20))
        return vertex_array_object, vertex_buffer_object

    def load_objects(self):
        """creates a tuple containing a list of all object indecies and buffers 
        from the self.obj_files list"""
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
        """laods and assigns the texture return the texture"""
        OpenGL.GL.glBindTexture(OpenGL.GL.GL_TEXTURE_2D, texture)
        OpenGL.GL.glTexParameteri(OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_WRAP_S,
                                  OpenGL.GL.GL_REPEAT)
        OpenGL.GL.glTexParameteri(OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_WRAP_T,
                                  OpenGL.GL.GL_REPEAT)
        OpenGL.GL.glTexParameteri(OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_MIN_FILTER,
                                  OpenGL.GL.GL_LINEAR)
        OpenGL.GL.glTexParameteri(OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_MAG_FILTER,
                                  OpenGL.GL.GL_LINEAR)

        image = Image.open(path)
        image = image.transpose(Image.FLIP_TOP_BOTTOM)
        img_data = image.convert("RGBA").tobytes()

        OpenGL.GL.glTexImage2D(OpenGL.GL.GL_TEXTURE_2D, 0, OpenGL.GL.GL_RGBA, image.width,
                               image.height, 0, OpenGL.GL.GL_RGBA, OpenGL.GL.GL_UNSIGNED_BYTE,
                               img_data)
        return texture

    def change_unit(self, axis, inp, to_frequency=False):
        """scales the input to the desired min max value"""
        if not to_frequency:
            outp = inp * \
                self.max_visu_area_vec[axis] / self.max_freq_vec[axis]
        if to_frequency:
            outp = inp * self.max_freq_vec[axis] / \
                self.max_visu_area_vec[axis]
        return outp

    def steering(self):
        """forwards/emits the motion signals to/to the motor module
            TODO: use overloading or a seperate function to allow visual only for
                  better readability and avoiding the multiple branches"""
        if not self.cycle_stop and not self.is_set and \
                (self.calibration_active or self.contouring_active):
            self.set_auto_pos()
            if self.current_step > self.old_step and self.auto_start:
                self.old_step = self.current_step
                if self.calibration_active and self.current_step > 0 or self.contouring_active and \
                        self.current_step > 1:
                    self.start_procedure()

        self.distance_x = self.visu_target_point_x - self.actual_pos_x
        self.distance_y = self.visu_target_point_y - self.actual_pos_y
        self.distance_z = self.visu_target_point_z - self.actual_pos_z

        self.visu_pos_vec = [self.actual_pos_x,
                             self.actual_pos_y, self.actual_pos_z]
        self.traget_pos_vec = [self.visu_target_point_x,
                               self.visu_target_point_y, self.visu_target_point_z]
        self.s_vec = [self.distance_x, self.distance_y, self.distance_z]

        eng_settings = vNeu(self.distance_x, self.distance_y,
                            self.distance_z, self.vmax)

        if self.cycle_start and not self.cycle_stop:
            if not self.visu_only_activ:
                self.freq_pos_list = self.motor_steering.GetMotorPosition()
                for i, pose in enumerate(self.visu_pos_vec):
                    self.stepper(
                        i, pose, self.traget_pos_vec[i], self.s_vec[i], eng_settings[i])

                self.actual_pos_x, self.actual_pos_y, self.actual_pos_z = [
                    self.change_unit(i, poses) for i, poses in enumerate(self.freq_pos_list, 0)]
            else:
                self.actual_pos_x, self.actual_pos_y, self.actual_pos_z = [
                    self.stepper(
                        i, pose, self.traget_pos_vec[i], self.s_vec[i], eng_settings[i])
                    for i, pose in enumerate(self.visu_pos_vec, 0)]
                self.freq_pos_list = [int(self.change_unit(i, poses, to_frequency=True))
                                      for i, poses in enumerate(self.visu_pos_vec, 0)]
            if not self.is_set:
                if not self.contouring_active:
                    print('..:: Start ::..')
                self.is_set = True
                self.visu_start_pos_x = self.actual_pos_x
                self.visu_start_pos_y = self.actual_pos_y
                self.visu_start_pos_z = self.actual_pos_z
                self.overall_distance_x = self.distance_x
                self.overall_distance_y = self.distance_y
                self.overall_distance_z = self.distance_z
                if not self.visu_only_activ:
                    self.motor_steering.Start(self.direction_vec, self.v_vec, self.freq_vec,
                                              self.max_freq_vec, self.min_freq_vec,
                                              eng_settings[3:6])
            if not self.visu_only_activ:
                self.motor_check_x, self.motor_check_y, self.motor_check_z, _ = \
                    self.motor_check_list = self.motor_steering.GetMotorStatus() + \
                        (self.cycle_start,)
            else:
                self.visu_check_vec = (
                    self.visu_check_x, self.visu_check_y, self.visu_check_z)

            if all(self.motor_check_list) or (self.visu_only_activ and all(self.visu_check_vec)):
                self.cycle_start = False
                self.is_set = False
                self.visu_check_x = False
                self.visu_check_y = False
                self.visu_check_z = False
                if self.calibration_active or self.contouring_active:
                    self.current_step += 1
                    self.next_step_ready = True
            self.update_stats_on_main_win()

    def set_auto_pos(self):
        """is for automated steering while contouring or calibrating
        TODO: add a interpolation funktionality"""
        step_vec = [[0, 0, 0], [4, 4, 1.7], [0, 0, 0],
                    [4, 4, 0], [0, 0, 1.7], [4, 4, 0],
                    [0, 0, 0], [4, 0, 1.7], [0, 4, 0],
                    [4, 0, 1.7], [0, 0, 0], [4, 0, 0],
                    [0, 4, 1.7], [4, 0, 0], [0, 4, 0],
                    [4, 0, 0], [0, 0, 1.7], [4, 0, 0],
                    [0, 0, 0], [0, 4, 1.7], [0, 0, 0],
                    [0, 4, 0], [0, 0, 1.7], [0, 4, 0],
                    [0, 0, 0], [0, 0, 1.7], [0, 0, 0], "ENDE"]

        actual_pos_vec = [self.actual_pos_x,
                          self.actual_pos_y, self.actual_pos_z]
        if self.next_step_ready:
            if self.calibration_active:
                if step_vec[self.current_step] == actual_pos_vec:
                    self.current_step += 1

                if step_vec[self.current_step] != "ENDE":
                    steps = step_vec[self.current_step]
                    print("SchrittNR.", self.current_step,
                          step_vec[self.current_step])
                else:
                    self.calibration_switch()
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
                    self.conturing_switch()
                    self.update_stats_on_main_win()
                    self.updateProgress.emit(100)
                    if not pos_fail:
                        print("conturing done")
                    else:
                        print("\b..::ERROR::..", end=" ")
                        print(
                            f"Konturvorgabe out of range! Kunturpos: {pos_fail} ")

            if (self.calibration_active or self.contouring_active):
                self.next_step_ready = False
                target_points = [self.change_unit(
                    i, pos, to_frequency=True) for i, pos in enumerate(steps, 0)]
                self.move_to_x(target_points[0])
                self.move_to_y(target_points[1])
                self.move_to_z(target_points[2])

    def stepper(self, axis, actual, desired, distance, vel):
        """
            steps and commands for the steppermotor
            # TODO change to only returnig function
        """
        if not self.cycle_stop:
            if distance > 0 and not self.cycle_stop:
                actual += vel
                self.direction_vec[axis] = 0

            elif distance < 0 and not self.cycle_stop:
                actual -= vel
                self.direction_vec[axis] = 1

            if distance > 0 and actual >= desired or distance < 0 and \
                    actual <= desired or distance == 0:
                actual = desired
                if self.visu_only_activ:
                    if axis == 0:
                        self.visu_check_x = True
                    elif axis == 1:
                        self.visu_check_y = True
                    elif axis == 2:
                        self.visu_check_z = True
            if self.visu_only_activ:
                return actual

    def update_stats_on_main_win(self):
        """updates status of UI (progressbar, motorstatus, poscounter, startstop)"""
        if not self.calibration_active or self.contouring_active:
            self.record_progress()
        else:
            self.updateProgress.emit(int(ceil(self.current_step*3.703703704)))

        self.updateLCD.emit(self.freq_pos_list)
        self.updateMotorStatus.emit(self.motor_check_list)
        self.updateStartStop.emit([self.cycle_start, self.cycle_stop])

    def record_progress(self):
        """takes the actual values for of positions and calculates the progress in percente"""
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
        """describes the mouse behaviour in the 3D visualisation mainly for rotate or tranlation"""
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
                mouse_pos_x += 1  # left
            elif abs(delta_mouse_pos_x) > abs(delta_mouse_pos_y) and delta_mouse_pos_x < 0:
                mouse_pos_x -= 1  # right
            elif abs(delta_mouse_pos_y) > abs(delta_mouse_pos_x) and delta_mouse_pos_y > 0:
                mouse_pos_y += 1  # up
            elif abs(delta_mouse_pos_y) > abs(delta_mouse_pos_x) and delta_mouse_pos_y < 0:
                mouse_pos_y -= 1  # dow

        new_view_pos_x = QtGui.QMouseEvent.x(event)
        new_view_pos_y = QtGui.QMouseEvent.y(event)
        old_pos = [new_view_pos_x, new_view_pos_y]

        if self.left_button:
            self.old_rotation_vec = old_pos
            self.visu_rotation_x = mouse_pos_y/150
            self.visu_rotation_y = mouse_pos_x/60
            self.rotate_view()

        elif self.middle_button or self.right_button:
            self.old_translation_vec = old_pos
            translate_view_x = -mouse_pos_x * 0.1
            translate_view_y = mouse_pos_y * 0.1
            if not self.right_button:
                self.view_translation_matrix = pyrr.Matrix44.from_translation(
                    [translate_view_x, translate_view_y, 0])
            else:
                if abs(translate_view_x) > abs(translate_view_y):
                    self.view_translation_matrix = pyrr.Matrix44.from_translation(
                        [0, 0, translate_view_x])
                else:
                    self.view_translation_matrix = pyrr.Matrix44.from_translation(
                        [0, 0, translate_view_y])
            self.view_matrix = pyrr.matrix44.multiply(
                self.view_translation_matrix, self.view_matrix)
            self.resizeGL(self.width(), self.height())
        return super(). mouseMoveEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """handles the mousbutten click/press events for the 3D modrl view"""
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

    # def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
    #   """should translate the view in a specific range"""
    #   if event.button() == QtCore.Qt.MouseButton.RightButton:
    #     if self.double_click_count < 5:
    #       self.trans_view_z = 1.5
    #     elif self.double_click_count < 15:
    #       self.trans_view_z = -1.5
    #     else:
    #       self.double_click_count = -1
    #     #print(self.double_click_count)
    #     self.view_translation_matrix = pyrr.Matrix44.from_translation(
    #       [0, 0, self.trans_view_z])
    #     self.view_matrix = pyrr.matrix44.multiply(
    #       self.view_translation_matrix, self.view_matrix)
    #     self.double_click_count += 1
    #     self.resizeGL(self.width(), self.height())
    #   return super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event: QtGui.QWheelEvent):
        """handles the weel events for zooming the 3D model view"""
        weel_rot_angle = event.delta() / 8
        weelstep = weel_rot_angle / 15

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

    def translate_view(self):
        """translates the view of the 3D model"""
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

    def rotate_view(self):
        """rotate the view of the 3D model"""
        self.rotation_matrix_y = pyrr.Matrix44.from_y_rotation(
            self.visu_rotation_y)
        self.rotation_matrix_x = pyrr.Matrix44.from_x_rotation(
            self.visu_rotation_x)

        self.view_matrix = pyrr.matrix44.multiply(
            self.rotation_matrix_y, self.view_matrix)
        self.view_matrix = pyrr.matrix44.multiply(
            self.rotation_matrix_x, self.view_matrix)
        self.resizeGL(self.width(), self.height())

    def main_procedure(self):
        """calls all the functions for the main procedure"""
        self.steering()
        self.translate_view()
        self.updateGL()

    def setup_starting(self):
        """prepares then members to auto start for contouring and calibrating"""
        self.cycle_start = False
        self.motor_steering.HardStopping()
        self.motor_check_list = [True, True, True, self.cycle_start]
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
    def free_recources(self):
        """Helper to clean up resources."""
        self.makeCurrent()
        OpenGL.GL.glDeleteBuffers(3)
        OpenGL.GL.glDeleteVertexArrays(3)

    @QtCore.Slot(int)
    def move_to_x(self, target_motor_pos):
        """moves the 3D object as an result of the motor position in x direction"""
        current_motor_pos_x = MotorSteuerung.GetPosition(0)
        self.freq_vec[0] = target_motor_pos - current_motor_pos_x
        self.freq_vec[0] = abs(int(ceil(self.freq_vec[0])))
        target_motor_pos = self.change_unit(0, target_motor_pos)
        self.visu_target_point_x = target_motor_pos

    @QtCore.Slot(int)
    def move_to_y(self, target_motor_pos):
        """moves the 3D object as an result of the motor position in y direction"""
        current_motor_pos_y = MotorSteuerung.GetPosition(1)
        self.freq_vec[1] = target_motor_pos - current_motor_pos_y
        self.freq_vec[1] = abs(int(ceil(self.freq_vec[1])))
        target_motor_pos = self.change_unit(1, target_motor_pos)
        self.visu_target_point_y = target_motor_pos

    @QtCore.Slot(int)
    def move_to_z(self, target_motor_pos):
        """moves the 3D object as an result of the motor position in z direction"""
        current_motor_pos_z = MotorSteuerung.GetPosition(2)
        self.freq_vec[2] = target_motor_pos - current_motor_pos_z
        self.freq_vec[2] = abs(int(ceil(self.freq_vec[2])))
        target_motor_pos = self.change_unit(2, target_motor_pos)
        self.visu_target_point_z = target_motor_pos

    @QtCore.Slot(bool)
    def start_procedure(self):
        """starts a automated procedure like calibration or conturing"""
        if not self.cycle_start and not self.cycle_stop:
            if self.distance_x or self.distance_y or self.distance_z or \
               self.calibration_active or self.contouring_active:
                self.cycle_start = True
                if self.calibration_active or self.contouring_active:
                    self.auto_start = True
        else:
            self.cycle_start = False
            if self.cycle_stop:
                print('Stop is activ')
        self.updateStartStop.emit([self.cycle_start, self.cycle_stop])

    @QtCore.Slot(bool)
    def pause_procedure(self):
        """pauses or stops a procedure"""
        if not self.cycle_stop:
            self.cycle_stop = True
            if not self.visu_only_activ and self.cycle_start:
                self.motor_steering.Stopping()
        else:
            self.cycle_stop = False
            if not self.visu_only_activ:
                self.motor_steering.ClearStop()
        self.updateStartStop.emit([self.cycle_start, self.cycle_stop])

    @QtCore.Slot(bool)
    def stop_procedure(self):
        """hard stops the procedure"""
        if not self.visu_only_activ and self.cycle_start:
            self.setup_starting()
        self.cycle_start = False
        if self.calibration_active:
            self.calibration_active = False
            print("[info]Calibration has Stopped")
        if self.contouring_active:
            self.contouring_active = False
            print("[info]Contouring has Stopped")

    @QtCore.Slot(bool)
    def calibration_switch(self):
        """starts or stops calibration mode"""
        if self.calibration_active:
            self.calibration_active = False
            self.setup_starting()
            print('Calibration is done')
        else:
            if not self.contouring_active:
                self.calibration_active = True
                print('Calibration is selected PRESS START')
                self.updateStatus.emit('cal')
            else:
                print("[bold]..::ERROR::..")
                print("Contouring und calibration ", end='')
                print("can not be used at the same time!")

    @QtCore.Slot(bool)
    def conturing_switch(self):
        """starts or stops contouring mode"""
        self.generated_pos_vec = None
        if self.contouring_active:
            self.contouring_active = False
            self.contouring_file = None
            self.setup_starting()
        else:
            if not self.calibration_active:
                if not self.contouring_file is None:
                    self.contouring_active = True
                    print("Contouring is selected PRESS START")
                    self.generated_pos_vec = ObjLoader.PosGenerate(
                        self.contouring_file)
                    self.updateStatus.emit('con')
                else:
                    print("..::ERROR::..\nNo file")
            else:
                print("..::ERROR::..\nContouring und calibration ", end='')
                print("can not be used at the same time!")

    @QtCore.Slot(float)
    def set_velocity(self, speed):
        """sets the max velocity of thea axis"""
        self.vmax = speed

    @QtCore.Slot(float)
    def reset_view(self):
        """resets the view on the 3D object to a default"""
        self.view_matrix = pyrr.matrix44.create_look_at(pyrr.Vector3(
            [5, 0, 20]), pyrr.Vector3([0, 0, 0]), pyrr.Vector3([0, 1, 0]))
        self.rotate_view()

    @QtCore.Slot(float)
    def visu_only_switch(self):
        """activates or deactivates the only visualisation function which
           starts the process without emiting signals to the steering"""
        if not self.visu_only_activ:
            self.visu_only_activ = True
            self.updateStatus.emit("visu_only_activ")
            self.motor_check_list = [False, False, False, False]
            print("[info]Visualisation only ON")
        elif self.visu_only_activ and not self.is_set:
            self.updateStatus.emit("visu_only_inactiv")
            self.visu_only_activ = False
            print("[info]Visualisierung only OFF")
        else:
            print(
                "[warning]the current running cycle needs to be completed before switching modes")

    @QtCore.Slot(bool)
    def clear_pos(self):
        """clears the position of the posfiles and sets them to zero also 
        resets the visu to pos zero"""
        pos_files = ("./Tools/X.txt", "./Tools/Y.txt", "./Tools/Z.txt")
        for pos_file in pos_files:
            with open(pos_file, "w", encoding="utf8") as file:
                file.write('0')
        self.actual_pos_x = 0
        self.actual_pos_y = 0
        self.actual_pos_z = 0
        self.updateSpinnerVal.emit()

    @QtCore.Slot(bool)
    def select_contour_1(self):
        """selects a file for the contoutring function
        TODO: Make the contouring more efficent"""
        self.contouring_file = "./ObjFiles/HTL.obj"
        print("[info]Contouring file: ", self.contouring_file)

    @QtCore.Slot(bool)
    def select_contour_2(self):
        """selects a file for the contoutring function"""
        self.contouring_file = "./ObjFiles/HalloWelt.obj"
        print("[info]Contouring file: ", self.contouring_file)

    @QtCore.Slot(bool)
    def select_contour_3(self):
        """selects a file for the contoutring function"""
        self.contouring_file = "C:/HAHAHA3"
        print("[info]Contouring file: ", self.contouring_file)
