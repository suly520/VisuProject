from Tools import numpad
from Tools.numpad import Ui_Numpad
import sys

from Tools import MotorSteuerung, ObjLoader, vNeu, Ui_VisoWidget
from PySide2 import QtCore, QtWidgets, QtOpenGL, QtGui
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
from math import ceil
from PIL import Image
import pyrr


class GLWidget(QtOpenGL.QGLWidget):
    """Signale für das Verknüpfen zum MainWindow"""
    updateProgress = QtCore.Signal(int)
    updateLCD = QtCore.Signal(list)
    updateMotorStatus = QtCore.Signal(list)
    updateStatus = QtCore.Signal(str)
    updateStartStop = QtCore.Signal(list)
    updateSpinnerVal = QtCore.Signal()
    

    def __init__(self, parent=None):
        super(GLWidget,self).__init__(parent)
        """Objecte für das Handhaben der Servomotoren und den Austausch von Daten zwischen GLWidget und MainWindow"""
        self.Steuer = MotorSteuerung() #mit diesem Object wird der Zugang zur Steuerungseinheit festgelegt
        self.Main4Updating = MainWindow(False) # False als argument bewirkt das nur die zu updatenden elemente initialisiert wird 


        self.middleBut = False
        self.leftBut = False
        self.rightBut = False
        self.transZview = 0
        self.doubleClickCount = 0

        """Listen und Variablen mit informationen für Raspberry"""
        self.directionList = [0, 0, 0]
        self.pulseList = [0, 0, 0]
        self.vList = [0.0007, 0.0007, 0.0007]
        self.pulsMaxList = [1000, 1000, 1000]
        self.pulsMinList = [0, 0, 0]
        self.visMaxList = [4.5, 4.5, 1.75]
        self.visMinList = [0, 0, 0]

        '''Bedingungen für den Allgemeinen Ablauf'''
        self.zyklStart = False
        self.zyklStop = False
        self.isSet = False
        self.visuCheckList = [False, False, False]
        self.xVisuCheck, self.yVisuCheck, self.zVisuCheck = self.visuCheckList
        

        """Positions-, Weg und Geschwindigkeitsvariablen für den Allgemeinen Ablauf"""
        #Die PositionsDaten werden direkt von der Steuereinheit geladen
        self.pulsPoslist = (MotorSteuerung.GetPosition(0), MotorSteuerung.GetPosition(1), MotorSteuerung.GetPosition(2))
        #Es gibt die Einheit Pulse und eine Einheit für die Visualisierung mit ChangeUnit() werden die Pulse umgewandelt
        self.xIst, self.yIst, self.zIst= [self.ChangeUnit(i, pose) for i, pose in enumerate(self.pulsPoslist, 0)]
        self.xStart = self.yStart = self.zStart = 0
        self.xZiel = self.yZiel = self.zZiel = 0
        self.xGesamt = self.yGesamt = self.zGesamt = 0
        self.sx = self.sy = self.sz = 0 
        self.vmax = 0
        
        """Für die GUI"""
        #Verknüpfungen zu den Slots der Grafischenoberfläche 
        self.updateProgress.connect(self.Main4Updating.UpdateProgressBar)
        self.updateLCD.connect(self.Main4Updating.UpdateLCD)
        self.updateMotorStatus.connect(self.Main4Updating.UpdateMotor)
        self.updateStatus.connect(self.Main4Updating.UpdateStatus)
        self.updateStartStop.connect(self.Main4Updating.UpdateStartStop)
        self.updateSpinnerVal.connect(self.Main4Updating.UpdateSpinerVal)
        self.x4Prog = self.y4Prog = self.z4Prog = 0
        
        """Für definierte Funktionen der Steuerung"""
        #Die zwei Hauptfunktionen sind Kalibrieren und Konturing außerdem gibt es noch die Möglichkeit onlyVisual
        self.kalibration = False
        self.kontur = False
        self.autoStart = False # Wird dann Aktiv wenn kontur oder kali ausgewählt wurden und zyklStart True ist (zyklStart muss ausgeschaltet werden)
        self.nextStep = True # Dient als Indikator das der der nächste Schritt ausgewählt werden kann 
        self.step = 0 # step ist der Momentane Schritt der Kontur oder der Kalibration
        self.oldstep = 0 # wird benötigt um den momentanen Schritt der Kontur oder Kalibration festustellen 
        self.konturFile = None # Ist ein Platzhalter für einen Pfad zum Konturfile !!! Konturfiles müssen angefertigt werden und müssen definierte Maße nicht überschreitten !!!
        self.onlyVis = False #Diese Variable ist für die Funktion die MotorSteureung wegzuschalten
        
        """Alle 3D-Objekte, Matritzen, Files Für die 3D_Visualisierung"""
        #Matrizen Für die Ansicht der Objekte
        self.projectionM = pyrr.matrix44.create_perspective_projection_matrix(45, 1280 / 720, 0.1, 100)
        self.viewM = pyrr.matrix44.create_look_at(pyrr.Vector3([0, 0, 25]), pyrr.Vector3([0, 0, 0]), pyrr.Vector3([0, 1, 0]))
        # diese variablen sind für das Drehen bzw Scalieren der Ansicht um die 3D Objecte 
        self.rotationX = self.rotationYM = 0 
        self.zoom = 1
        self.oldRotpos = list()
        self.oldTranspos = list()
        #Matritzen für das Positionieren und Bewegen der Objekte
        self.xachsePosM = self.yachsePosM = self.zachsePosM = pyrr.matrix44.create_from_translation(pyrr.Vector3([0, -3, 0]))  # y-5
        self.moveList = [self.xachsePosM, self.xachsePosM, self.xachsePosM]
        self.transxM = pyrr.Matrix44.from_translation([0, 0, self.xIst])
        self.transyM = pyrr.Matrix44.from_translation([self.yIst, 0, 0])
        self.transzM = pyrr.Matrix44.from_translation([0, -self.zIst, 0])
        #Textur- und Objfilepfade 
        self.texturFiles = "./TexturFiles/STEP.jpg"
        self.objFiles = [
            "./ObjFiles/X.obj",
            "./ObjFiles/Y.obj",
            "./ObjFiles/Z.obj",
        ]
        #Ladend der Informationen für das Shaderprogramm
        objList = self.LoadObjList()
        self.indecisList = objList[0]
        self.bufferList = objList[1]
        #Timer führt die gewählte Funktion(self.Ablauf) aus ist für die Event-loop verantwortlich.
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.Ablauf)
        timer.start()

    @staticmethod
    def d(*args, **kwargs):
        print(*args, file=sys.stderr, **kwargs)

# OpenGL Grundfunktionen für PySide2 / init, draw, resize /
    def initializeGL(self):
        """Hier wird alles (Vertecies, Buffer und WidgetDisplay) für das Zeichnen initialisiert(vorbereitet)"""
        glEnable(GL_DEPTH_TEST)
        textures = glGenTextures(1)
        self.LoadTexture(self.texturFiles, textures)
        VAO_VBOlist = self.CreateVAOandVBO(self.bufferList)
        self.VBO = VAO_VBOlist[0]
        self.VAO = VAO_VBOlist[1]
        glClearColor(0, 1, 2, 1)
   
    def paintGL(self):
        """paintGL() zeichnet die Scene"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.SetTrans() #mit  SetTrans wird die Matrix Translation neu gezeichnet
        for i in range(len(self.indecisList)):
            glBindVertexArray(self.VAO[i])
            glUniformMatrix4fv(self.model_loc, 1, GL_FALSE, self.moveList[i])
            glDrawArrays(GL_TRIANGLES, 0, len(self.indecisList[i]))

    def resizeGL(self, width, height):
        """Hier wird die Einstellung des Viewports (Modelansicht) an die Größe des Fensters angepasst"""
        glViewport(0, 0, width, height)
        shader = self.CreateShader()
        self.model_loc = glGetUniformLocation(shader, "model")
        self.proj_loc = glGetUniformLocation(shader, "projection")
        self.viewM_loc = glGetUniformLocation(shader, "view") 
        glUniformMatrix4fv(self.proj_loc, 1, GL_FALSE, self.projectionM)
        glUniformMatrix4fv(self.viewM_loc, 1, GL_FALSE, self.viewM)
      
    @staticmethod
    def CreateShader():
        """Hier werden die Shaderprogramme erstellt und an die GPU als Schnittstelle gesendet"""
        vertexSrc = """
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

        fragmentSrc = """
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
        shader = compileProgram(compileShader(vertexSrc, GL_VERTEX_SHADER), compileShader(fragmentSrc, GL_FRAGMENT_SHADER))
        glUseProgram(shader) # mit glUseProgramm werden die Shaderprogramme ausgewählt und dienen als Schnittstelle für die GPU 
        return shader
    
    @staticmethod
    def CreateVAOandVBO(bufferlist):
        """Hier werden die Vertex Array- und Vertex Buffer Objekte erstellt"""
        VAO = glGenVertexArrays(len(bufferlist)) # enthält die Informationen zu den Vertexdaten aus den VBO's (Datenformat, welches VBO , ...)
        VBO = glGenBuffers(len(bufferlist)) # es enthält die eigendlichen Vertexdaten der Objekte
        
        for i, buffer in enumerate(bufferlist, 0):
            if len(bufferlist) == 1: i = 0
            glBindVertexArray(VAO[i]) # das VAO wird an den index i gebunden 

            glBindBuffer(GL_ARRAY_BUFFER, VBO[i]) # das VBO wird an den index i gebunden 
            glBufferData(GL_ARRAY_BUFFER, buffer.nbytes, buffer, GL_STATIC_DRAW) # die Vertexdaten werden im VBO deklariert

            """Hier werden die Atribute der einzelnen Bufferelemte zugeordenet und angepeilt"""
            # vertices
            glEnableVertexAttribArray(0)
            glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, buffer.itemsize * 8, ctypes.c_void_p(0))
            # textures
            glEnableVertexAttribArray(1)
            glVertexAttribPointer(1, 4, GL_FLOAT, GL_FALSE, buffer.itemsize * 8, ctypes.c_void_p(12))
            # normals
            glEnableVertexAttribArray(2)
            glVertexAttribPointer(2, 4, GL_FLOAT, GL_FALSE, buffer.itemsize * 8, ctypes.c_void_p(20))
            
        return VAO,VBO
    
    def LoadObjList(self):
        """Hier werden die Objecte für die 3D-Visulation geladen und eine indeciesliste und Bufferliste erstellt"""
        indecisList = []
        bufferList = []
        for objFile in self.objFiles:
            if len(objFile) == 1:
                indecies, buffers = ObjLoader.LoadModel(self.objFiles)
            indecies, buffers = ObjLoader.LoadModel(objFile)
            indecisList.append(indecies)
            bufferList.append(buffers)
        return indecisList, bufferList  

    @staticmethod
    def LoadTexture(path, texture):
        """Hier werden die Texturen geladen und an das Object gebunden"""
        glBindTexture(GL_TEXTURE_2D, texture)
        # Parameter für das Texturen wrapping
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        # Parameter für die Texturfilterung
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        # load image
        image = Image.open(path)
        image = image.transpose(Image.FLIP_TOP_BOTTOM)
        imgData = image.convert("RGBA").tobytes()

        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, image.width, image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, imgData)
        return texture

    def ChangeUnit(self, achse, inp, toPuls= False):
        """Ist für das umwandeln von Pulsen in Visualisierungseinheit"""
        if not toPuls:
            outp = inp * self.visMaxList[achse] / self.pulsMaxList[achse]
        if toPuls:
            outp = inp * self.pulsMaxList[achse] / self.visMaxList[achse]
        return outp

    def Steuerung(self):
        """Hier werden die Position gesetzt welche die Maschine anfahren und visualisiert werden soll"""

        # Diese Bedingung ist für das setzten der Kalibrations- bzw. Konturposition
        if not self.zyklStop and not self.isSet and (self.kalibration or self.kontur): 
            self.SetAutoPos()
            if self.step > self.oldstep and self.autoStart: # ist step größer oldstep ist der Schritt gesetzt worden und kann automatisch gestartet werden 
                self.oldstep = self.step 
                if self.kalibration and self.step > 0 or self.kontur and self.step > 1:
                    self.ZyklusStart()

        # der Weg wird für die Berechnung der Geschwindigkeit benötigt und auf Grund des Vorzeichens für der Motordrehrichtung gebraucht
        self.sx = self.xZiel - self.xIst
        self.sy = self.yZiel - self.yIst
        self.sz = self.zZiel - self.zIst

         
        self.visuPoslist = [self.xIst, self.yIst, self.zIst]
        self.aimPoslist = [self.xZiel, self.yZiel, self.zZiel]
        self.slist = [self.sx, self.sy, self.sz]

        motorSettings = vNeu(self.sx, self.sy, self.sz, self.vmax) # gibt die Geschwindigkeit und ob der moter eingeschaltet werden soll zurück
        
        if self.zyklStart and not self.zyklStop:
            if not self.onlyVis:
                self.pulsPoslist = self.Steuer.GetMotorPosition() # die aktuelle Position des Motors
                for i, pose in enumerate(self.visuPoslist):
                    self.Stepper(i, pose, self.aimPoslist[i], self.slist[i], motorSettings[i]) # Drehrichtungsbestimmung

                self.xIst, self.yIst, self.zIst = [self.ChangeUnit(i, poses) for i, poses in enumerate(self.pulsPoslist, 0)] # position für die Visualisierung

            else:
                self.xIst, self.yIst, self.zIst = [self.Stepper(i, pose, self.aimPoslist[i], self.slist[i], motorSettings[i]) for i, pose in enumerate(self.visuPoslist, 0)]
                self.pulsPoslist= [int(self.ChangeUnit(i, poses, toPuls = True)) for i, poses in enumerate(self.visuPoslist, 0)] # um die aktuelle Motorposition zu simulieren muss der Visu wert in Pulse umgewandelt werden

            if not self.isSet: # um die MotorSteuerung nicht ständig aus und einzuschalten und gewisse Variablen zu setzen die nur einmal betätigt werden sollen
                if not self.kontur: print('..:: Start ::..')
                self.isSet = True
                self.xStart = self.xIst
                self.yStart = self.yIst
                self.zStart = self.zIst
                self.xGesamt = self.sx # wird benötigt für das Kalkulieren der Prozesslänge für den Progressbar
                self.yGesamt = self.sy
                self.zGesamt = self.sz
                if not self.onlyVis:
                    self.Steuer.Start(self.directionList, self.vList, self.pulseList, self.pulsMaxList, self.pulsMinList, motorSettings[3:6])
            
            if not self.onlyVis:
                self.xMotorCheck, self.yMotorCheck, self.zMotorCheck = self.Steuer.GetMotorStatus()
                self.checkList = (self.xMotorCheck, self.yMotorCheck, self.zMotorCheck, self.zyklStart)
            else:
                self.visuCheckList = (self.xVisuCheck, self.yVisuCheck, self.zVisuCheck)


            if all(self.checkList) or (self.onlyVis and all(self.visuCheckList)):
                self.zyklStart = False
                self.isSet = False
                self.xVisuCheck = False
                self.yVisuCheck = False
                self.zVisuCheck = False
                if self.kalibration or self.kontur:
                    self.step += 1
                    self.nextStep = True
            self.UpdateStausMainWindow()

    def SetAutoPos(self): 
        schrittliste = [
                        [0, 0, 0], [4, 4, 1.7], [0, 0, 0], [4, 4, 0], [0, 0, 1.7], [4, 4, 0], [0, 0, 0], 
                        [4, 0, 1.7], [0, 4, 0], [4, 0, 1.7], [0, 0, 0], [4, 0, 0], [0, 4, 1.7], 
                        [4, 0, 0], [0, 4, 0], [4, 0, 0], [0, 0, 1.7], [4, 0, 0], [0, 0, 0], 
                        [0, 4, 1.7], [0, 0, 0], [0, 4, 0], [0, 0, 1.7], [0, 4, 0], [0, 0, 0], 
                        [0, 0, 1.7], [0, 0, 0], "ENDE"
        ]

        if self.nextStep:
            if self.kalibration:
                if schrittliste[self.step] == [self.xIst, self.yIst, self.zIst]: 
                    self.step += 1
        
                if not schrittliste[self.step] == "ENDE":
                    Schritte = schrittliste[self.step]
                    print("SchrittNR.",self.step,schrittliste[self.step])
                else:
                    self.KalibrationSwitch()
                    self.UpdateStausMainWindow()
                    self.updateProgress.emit(100)
                    print("Kallibrierung abgeschlossen")
                
            elif self.kontur:
                self.step += 1
                posFail = None
                
                try:
                    Schritte = next(self.posGen) 
                    for i, j in enumerate(Schritte, 0):
                        if i == 2 and float(j) > 0 and float(j) < 1.75:
                            Schritte[i] = float(j)
                        elif float(j) > 0 and float(j) < 4.5:
                            Schritte[i] = float(j) * 2
                        else:
                            posFail = Schritte[i]
                            raise StopIteration
                except StopIteration:
                    self.KonturSwitch()
                    self.UpdateStausMainWindow()
                    self.updateProgress.emit(100)
                    if not posFail:
                        print("Konturing abgeschlossen")
                    else:
                        print(f"..::ERROR::.. Konturvorgabe out of range! Kunturpos: {posFail} ")

            if (self.kalibration or self.kontur):
                self.nextStep = False
                pulsMovePoses = [self.ChangeUnit(i, pos, toPuls = True) for i, pos in enumerate(Schritte, 0)]
                self.MoveX(pulsMovePoses[0])
                self.MoveY(pulsMovePoses[1])
                self.MoveZ(pulsMovePoses[2]) 
        
    def Stepper(self, achse, ist, soll, weg, v):
        if not self.zyklStop:
            if weg > 0 and not self.zyklStop: 
                ist += v
                self.directionList[achse] = 0

            elif weg < 0 and not self.zyklStop: 
                ist -= v
                self.directionList[achse] = 1

            if weg > 0 and ist >= soll or weg < 0 and ist <= soll or weg == 0:
                ist = soll
                if self.onlyVis:
                    if achse == 0: self.xVisuCheck = True
                    elif achse == 1: self.yVisuCheck = True
                    elif achse == 2: self.zVisuCheck = True
            if self.onlyVis:
                return ist
    
    def UpdateStausMainWindow(self):
        if not self.kalibration or self.kontur:
                self.CollData4Probar()
        else:
            self.updateProgress.emit(int(ceil(self.step*3.703703704)))

        self.updateLCD.emit(self.pulsPoslist)
        self.updateMotorStatus.emit(self.checkList)
        self.updateStartStop.emit([self.zyklStart, self.zyklStop])
                                      
    def CollData4Probar(self):
        if self.xGesamt != 0 and self.sx != 0:
            self.x4Prog = abs(self.sx * 100 / abs(self.xGesamt))
            self.updateProgress.emit(int(ceil(100 - self.x4Prog)))
        elif self.xGesamt != 0 and self.sx == 0:
            self.x4Prog = abs(self.sx * 100 / abs(self.xGesamt))
            self.updateProgress.emit(int(ceil(self.x4Prog)))
        elif self.yGesamt != 0 and self.sy != 0:
            self.y4Prog = abs(self.sy * 100 / abs(self.yGesamt))
            self.updateProgress.emit(int(ceil(100 - self.y4Prog)))
        elif self.yGesamt != 0 and self.sy == 0:
            self.y4Prog = abs(self.sy * 100 / abs(self.yGesamt))
            self.updateProgress.emit(int(ceil(self.y4Prog)))
        elif self.zGesamt != 0 and self.sz != 0:
            self.z4Prog = abs(self.sz * 100 / abs(self.zGesamt))
            self.updateProgress.emit(int(ceil(100 - self.z4Prog)))    
        elif self.zGesamt != 0 and self.sz == 0:
            self.z4Prog = abs(self.zIst * 100 / abs(self.zGesamt))
            self.updateProgress.emit(int(ceil(self.z4Prog)))
    
    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        posX = 0
        posY = 0 
        oldPosList = []
        if self.middleBut or self.rightBut:
            oldPosList = self.oldTranspos
        elif self.leftBut:
            oldPosList = self.oldRotpos
        if len(oldPosList):
            xold = oldPosList[0]
            yold = oldPosList[1]

            deltaX = xold - QtGui.QMouseEvent.x(event)
            deltaY = yold - QtGui.QMouseEvent.y(event)

            if abs(deltaX) > abs(deltaY) and deltaX > 0: posX += 1 #links
            elif abs(deltaX) > abs(deltaY) and deltaX < 0: posX -= 1 #rechts  
            elif abs(deltaY) > abs(deltaX) and deltaY > 0: posY += 1 #oben 
            elif abs(deltaY) > abs(deltaX) and deltaY < 0: posY -= 1 #unten
        
        newPosX = QtGui.QMouseEvent.x(event)
        newPosY = QtGui.QMouseEvent.y(event)
        oldPosList = [newPosX, newPosY]

        if self.leftBut: 
            self.oldRotpos = oldPosList
            self.rotationX = posY/150
            self.rotationY = posX/60
            self.SetViewRotation()
       

        elif self.middleBut or self.rightBut:
            self.oldTranspos = oldPosList
            transX = -posX * 0.1
            transY = posY * 0.1
            if not self.rightBut:
                self.viewTransM = pyrr.Matrix44.from_translation([transX, transY, 0])
            else:
                if abs(transX) > abs(transY): 
                    self.viewTransM = pyrr.Matrix44.from_translation([0, 0, transX])
                else:
                    self.viewTransM = pyrr.Matrix44.from_translation([0, 0, transY])
            self.viewM = pyrr.matrix44.multiply(self.viewTransM, self.viewM) 
            self.resizeGL(self.width(),self.height())
        return super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self.leftBut = False
            self.rightBut = False
            self.middleBut = True
        elif event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.middleBut = False
            self.rightBut = False
            self.leftBut = True
        elif event.button() == QtCore.Qt.MouseButton.RightButton:
            self.middleBut = False
            self.leftBut = False
            self.rightBut = True
        else:
            self.middleBut = False
            self.leftBut = False
            self.rightBut = False
        return super().mousePressEvent(event)
    
    
    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            if self.doubleClickCount < 5: 
                self.transZview = 1.5
            elif self.doubleClickCount < 15:
                self.transZview = -1.5
            else:
                self.doubleClickCount = -1
            print(self.doubleClickCount)
            self.viewTransM = pyrr.Matrix44.from_translation([0, 0, self.transZview])
            self.viewM = pyrr.matrix44.multiply(self.viewTransM, self.viewM) 
            self.doubleClickCount += 1
            self.resizeGL(self.width(),self.height()) 
        return super().mouseDoubleClickEvent(event)
    
   
    def wheelEvent(self, event: QtGui.QWheelEvent):
        gradWeel = event.delta() / 8
        weelstep = gradWeel / 15
        
        if weelstep < 0: self.zoom = 0.9
        else: self.zoom = 1.1

        self.zoomM = pyrr.Matrix44.from_scale([self.zoom, self.zoom, self.zoom])
        self.viewM = pyrr.matrix44.multiply(self.zoomM, self.viewM)
        self.resizeGL(self.width(),self.height())
        return super().wheelEvent(event)

    def SetTrans(self):
        self.transxM = pyrr.Matrix44.from_translation([0, 0, self.xIst])
        self.transyM = pyrr.Matrix44.from_translation([self.yIst, 0, 0])
        self.transzM = pyrr.Matrix44.from_translation([0, -self.zIst, 0])

        self.moveToXM = self.xachsePosM
        self.moveToYM = pyrr.matrix44.multiply(self.transxM, self.yachsePosM)
        self.moveToZM = pyrr.matrix44.multiply(self.transxM, self.zachsePosM)
        self.moveToZM = pyrr.matrix44.multiply(self.transyM, self.moveToZM)
        self.moveToZM = pyrr.matrix44.multiply(self.transzM, self.moveToZM)

        self.moveList[0] = self.moveToXM
        self.moveList[1] = self.moveToYM
        self.moveList[2] = self.moveToZM
    
    def SetViewRotation(self):
        self.rotationYM = pyrr.Matrix44.from_y_rotation(self.rotationY)
        self.rotationXM = pyrr.Matrix44.from_x_rotation(self.rotationX)

        self.viewM  = pyrr.matrix44.multiply(self.rotationYM, self.viewM)
        self.viewM  = pyrr.matrix44.multiply(self.rotationXM, self.viewM)
        self.resizeGL(self.width(),self.height())

    def Ablauf(self):
        self.Steuerung()
        self.SetTrans()
        self.updateGL()
    
    def ResetToStart(self):
        self.zyklStart = False
        self.Steuer.HardStopping()
        self.checkList = [True, True, True, self.zyklStart]
        self.step = 0
        self.oldstep = 0
        self.nextStep = True
        self.xIst, self.yIst, self.zIst = [self.ChangeUnit(i, pose) for i, pose in enumerate(self.pulsPoslist, 0)]
        self.updateStatus.emit('NOP')
        self.updateSpinnerVal.emit()# Setzt die SpinerBox Werte auf die aktuelle Position
        self.UpdateStausMainWindow()
         
# Widgets Slots
    @QtCore.Slot() 
    def FreeRecources(self):
        """Helper to clean up resources."""
        self.makeCurrent()
        glDeleteBuffers(3)
        glDeleteVertexArrays(3)
    
    @QtCore.Slot(int) 
    def MoveX(self, ziel):
        xIst = MotorSteuerung.GetPosition(0)
        self.pulseList[0] = ziel - xIst #self.ChangeUnit(0, self.xIst, toPuls = True
        self.pulseList[0] = abs(int(ceil(self.pulseList[0])))
        ziel = self.ChangeUnit(0, ziel)
        self.xZiel = ziel
     
    @QtCore.Slot(int) 
    def MoveY(self, ziel):
        yIst = MotorSteuerung.GetPosition(1)
        self.pulseList[1] = ziel - yIst#self.ChangeUnit(1, self.yIst, toPuls = True)
        self.pulseList[1] = abs(int(ceil(self.pulseList[1])))
        ziel = self.ChangeUnit(1, ziel)
        self.yZiel = ziel

    @QtCore.Slot(int) 
    def MoveZ(self, ziel):
        zIst = MotorSteuerung.GetPosition(2)
        self.pulseList[2] = ziel - zIst#self.ChangeUnit(2, self.zIst, toPuls = True)
        self.pulseList[2] = abs(int(ceil(self.pulseList[2])))
        ziel = self.ChangeUnit(2, ziel) 
        self.zZiel = ziel

    @QtCore.Slot(bool)   
    def ZyklusStart(self):
        if not self.zyklStart and not self.zyklStop:
            if self.sx or self.sy or self.sz or self.kalibration or self.kontur:
                self.zyklStart = True
                if self.kalibration or self.kontur:
                    self.autoStart = True
        else:
            self.zyklStart = False
            if self.zyklStop: print("Stop ist aktiv")
        self.updateStartStop.emit([self.zyklStart, self.zyklStop])
      
    @QtCore.Slot(bool)
    def ZyklusStop(self):
        if not self.zyklStop:
            self.zyklStop = True
            if not self.onlyVis and self.zyklStart:
                self.Steuer.Stopping()
        else:
            self.zyklStop = False
            if not self.onlyVis:
                self.Steuer.ClearStop()
        self.updateStartStop.emit([self.zyklStart, self.zyklStop])

    @QtCore.Slot(bool)
    def ZyklusHardStop(self):
        if not self.onlyVis and self.zyklStart:
            self.ResetToStart()
        self.zyklStart = False
    
    @QtCore.Slot(bool)
    def KalibrationSwitch(self):
        if self.kalibration:
            self.kalibration = False
            self.ResetToStart()
            print('Kalibration OFF') 
        else:
            if not self.kontur:
                self.kalibration = True
                self.updateStatus.emit('kal')
                print('Kalibration ON')
            else: print("..::ERROR::..\nKonturing und Kallibration kann nicht gleichzeitig verwendet werden")

    @QtCore.Slot(bool)
    def KonturSwitch(self):
        self.posGen = None
        if self.kontur:
            self.kontur = False
            self.konturFile = None
            self.ResetToStart()
        else:
            if not self.kalibration:
                if self.konturFile != None:
                    self.kontur = True
                    print("Konturing gestartet")
                    self.posGen = ObjLoader.PosGenerate(self.konturFile)
                    self.updateStatus.emit('kon')
                else: print("..::ERROR::..\nKein File vorhanden")
            else: print("..::ERROR::..\nKonturing ist wärend einer Kalibration nicht möglich !!")
                
    @QtCore.Slot(float)
    def SetSpeed(self, speed): 
        self.vmax = speed
    
    @QtCore.Slot(float)
    def ResetViewpos(self):
        self.viewM = pyrr.matrix44.create_look_at(pyrr.Vector3([5, 0, 20]), pyrr.Vector3([0, 0, 0]), pyrr.Vector3([0, 1, 0]))
        self.SetViewRotation()

    @QtCore.Slot(float)
    def SetToVis(self):
        if not self.onlyVis:
            self.onlyVis = True
            self.updateStatus.emit("onlyVis")
            self.checkList =[False, False, False, False]
            print("Visualisierung only ON")
        elif self.onlyVis and not self.isSet:
            self.updateStatus.emit("notonlyVis")
            self.onlyVis = False
            print("Visualisierung only OFF")
        else:
            print("Der Zyklus muss beendet werden um die Visualisierung beenden zun können")
    
    @QtCore.Slot(bool)
    def SetDefaultPos(self):
        posFiles = ("./Tools/X.txt", "./Tools/Y.txt","./Tools/Z.txt")

        for posFile in posFiles:
            with open(posFile,"w") as f:
                f.write('0')
        self.xIst = 0
        self.yIst = 0
        self.zIst = 0
        self.updateSpinnerVal.emit()

    @QtCore.Slot(bool)
    def SetKonturFile1(self):
        self.konturFile ="./ObjFiles/HTL.obj"
        print("KonturFile: ",self.konturFile)
    
    @QtCore.Slot(bool)
    def SetKonturFile2(self):
        self.konturFile ="./ObjFiles/HalloWelt.obj"
        print("KonturFile: ",self.konturFile)

    @QtCore.Slot(bool)
    def SetKonturFile3(self):
        self.konturFile ="C:/HAHAHA3"
        print("KonturFile: ",self.konturFile)


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, initGLWidget = True, parent = None):
        super(MainWindow, self).__init__(parent)
        self.ui = Ui_VisoWidget()
        self.docked = QtWidgets.QDockWidget("Dock", self)
        self.docked.setWidget(self.ui.setupUi(self.docked))

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
        self.glWidgetArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.glWidgetArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.glWidgetArea.setSizePolicy(QtWidgets.QSizePolicy.Ignored,
                QtWidgets.QSizePolicy.Ignored)
        self.glWidgetArea.setMinimumSize(50, 50)
        sys.stdout = EmittingStream()
        self.connect(sys.stdout, QtCore.SIGNAL('textWritten(QString)'),self.NormalOutputWritten)

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
        #self.numdocked.maximumSize()
        self.numdocked.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.setCorner(QtCore.Qt.Corner.BottomLeftCorner,QtCore.Qt.BottomDockWidgetArea)
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
        
        self.docked.setAllowedAreas(QtCore.Qt.BottomDockWidgetArea | QtCore.Qt.TopDockWidgetArea)
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

        self.ui.xStartSpinBox.valueChanged.connect(self.glWidget.MoveX)
        self.ui.xStartSpinBox.setRange(self.glWidget.pulsMinList[0], self.glWidget.pulsMaxList[0])
        self.ui.xStartSpinBox.setSingleStep(100)
        self.ui.xStartSpinBox.setValue(MotorSteuerung.GetPosition(0))
        	
        self.ui.yStartSpinBox.valueChanged.connect(self.glWidget.MoveY)
        self.ui.yStartSpinBox.setRange(self.glWidget.pulsMinList[1], self.glWidget.pulsMaxList[1])
        self.ui.yStartSpinBox.setSingleStep(100)	
        self.ui.yStartSpinBox.setValue(MotorSteuerung.GetPosition(1))
        	
        self.ui.zStartSpinBox.valueChanged.connect(self.glWidget.MoveZ)
        self.ui.zStartSpinBox.setRange(self.glWidget.pulsMinList[2], self.glWidget.pulsMaxList[2])
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
        self.Kontur1 = QtWidgets.QAction("Kontur1",self)
        self.Kontur2 = QtWidgets.QAction("Kontur2",self)
        self.Kontur3 = QtWidgets.QAction("Kontur3",self)
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
        if status == "onlyVis":
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
            self.prozessStatus.setText(f" {self.visuStattxt} Kalibration AKTIV ")
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
            if self.number[0] == "v": self.ui.vSpinBox.setValue(float(self.number[2:]))
            if self.number[0] == "X": self.ui.xStartSpinBox.setValue(int(self.number[2:]))
            if self.number[0] == "Y": self.ui.yStartSpinBox.setValue(int(self.number[2:]))
            if self.number[0] == "Z": self.ui.zStartSpinBox.setValue(int(self.number[2:]))
        else:
            if len(self.number) != 0:
                if self.number[0] == "X" or  self.number[0] == "Y" or self.number[0] ==  "Z" or self.number[0] == "v":
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