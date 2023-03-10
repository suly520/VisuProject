
import sys
win = 'win32'
lin = 'linux'


if sys.platform  == win: from GPIOEmulator.EmulatorGUI import GPIO
if sys.platform  == lin: import RPi.GPIO as GPIO

import threading
from time import sleep
import numpy as np
from math import exp
from threading import RLock
lck = threading.Lock()





class PosError(Exception):
    """Wird aufgerufen wenn ein Positionierungsfehler vorliegt"""
    pass

class StopProcess(Exception):
    """Wird für das Stoppen der funktion benötigt"""
    pass

class MotorSteuerung:
    
    def __init__(self, list pinList = [17, 5, 16, 27, 6, 20, 22, 13, 21]):
        cdef list achsList = [0, 1, 2] # die Zahlen sollen die Achse repräsentieren 0 = X / 1 = Y / 2 = Z 
        self.pinList = pinList   
        cdef list pulsPinList = self.pinList[0:3]
        cdef list dirPinList = self.pinList[3:6]
        cdef list enaPinList = self.pinList[6:9]
        cdef list checklist = [0, 0, 0]
        cdef int i
        cdef bint xCheck = False, yCheck= False, zCheck= False  
       
        GPIO.setmode(GPIO.BCM)
        self.achsList = achsList   
        self.pulsPinList = pulsPinList 
        self.dirPinList = dirPinList
        self.enaPinList = enaPinList
        self.checklist = checklist
        self.xCheck = xCheck
        self.yCheck = yCheck
        self.zCheck = zCheck 
        self.posList = [self.GetPosition(0),self.GetPosition(1),self.GetPosition(2)]

        self.stop = threading.Event()
        self.hardStop = threading.Event()
        self.XStop = threading.Event()
        self.YStop = threading.Event()
        self.ZStop = threading.Event()
        self.stopList = [self.XStop, self.YStop, self.ZStop]
        

        if sys.platform == win:
            try:
                for i in range(len(self.pinList)-3): GPIO.setup(int(self.pinList[i]), GPIO.OUT)
                for i in range(len(self.enaPinList)): GPIO.setup(int(self.enaPinList[i]), GPIO.IN)
            except:
                pass
    

    def StartSteuerThr(self, int achse):
        SteuerThread = threading.Thread(target= self.Steuerung, args=(

            self.achsList[achse], self.pulsPinList[achse], self.dirPinList[achse], 

            self.enaPinList[achse], self.dirList[achse], self.pulsList[achse], self.vList[achse],

            self.endMax[achse], self.endMin[achse], self.posList

            ))
        
        SteuerThread.start()

    @staticmethod
    def GetPosition(int achse, tuple posFiles = ("./Tools/X.txt", "./Tools/Y.txt","./Tools/Z.txt")):
        global lck
        cdef list pos
        cdef str posStr
        cdef int posInt = 0
        cdef str posFile

        posFile = posFiles[achse]
        lck.acquire()
        with open(posFile,"r") as f:
            posStr = f.readline()
        posInt = int(posStr)
        lck.release()
        return posInt

    @staticmethod
    def Checkpos(int achse, int direction, int pulse, int endMax, int endMin):
        cdef int achsPos = MotorSteuerung.GetPosition(achse)
    
        try:
            if achsPos == endMax and direction == 0 and pulse != 0:
                raise PosError
        except PosError:
            print(f"\nAchse {achse}: Die Ausführung mit der gewählten Bewegungsrichtung würde die untere ENDpos überschreiten\n")
            sys.exit()

        try:
            if achsPos  == endMin and direction == 1 and pulse != 0:
                raise PosError
        except PosError:
            print(f"\nAchse {achse}: Die Ausführung mit der gewählten Bewegungsrichtung würde die obere ENDpos überschreiten\n")
            sys.exit()

        try:
            if achsPos  > endMax or achsPos < endMin: 
                raise PosError
        except PosError:
            print(f"\nAchse {achse}: Die momentane Position befindet sich außerhalb des richtigen Wertebereiches\n")
            sys.exit()

        try:
            if (achsPos - pulse) < endMin and direction == 1:
                raise PosError
        except PosError:
            print(f"\nAchse {achse}: Das angegebene Ziel würde die untere Position übeerschreiten\nAktuellePos: {achsPos}\nPos nacher: {achsPos-pulse}\nPulse: {pulse}\n")
            sys.exit()

        try:
            if (achsPos + pulse) > endMax and direction == 0:
                raise PosError
        except PosError:
            print(f"\nAchse {achse}: Das angegebene Ziel würde die obere Endposition überschreiten\nAktuellePos: {achsPos}\nPos nacher: {achsPos+pulse}\nPulse: {pulse}\n")
            sys.exit()

        return achsPos

    def Steuerung(self, int achse, int pulPIN, int dirPIN, int enaPIN, int direction, int pulse, double vmax, int endMax, int endMin, position, tuple posFiles = ("./Tools/X.txt", "./Tools/Y.txt","./Tools/Z.txt")):
        cdef int achsPos = self.Checkpos(achse, direction, pulse, endMax, endMin)
        cdef int i = 0
        cdef int count = 0
        cdef str posFile 
        cdef tuple pinList
        cdef str achsprint
        cdef str vekt
        cdef double const #vmax = 0.0007 vmin = 0.0015
        cdef double vmin = 0.0010
        cdef double T
        cdef double j
        cdef int slowdownCounter = 0

        
        try:
            const = 0.0008 #getestet durch geogebra nur bei 0.0007
            if vmax < 0.0007:
                j = 0.0007 - vmax
                const += j
            if vmax > 0.0007:
                j = 0.0007 - vmax
                const -= j 
            beginFast = int(pulse * 2/10)
            endFast = int(pulse * 8/10)
            T = 275/(1400/beginFast) #getesteter wert durch geogebra eine art zeitkonstante
            v = vmax + const*exp(-1/T*0) #Formel erstellt durch testen in geogebra bei puls 2/10*Pulse => v = 0.0007 bei puls 0 => v = 0.001
        except ZeroDivisionError:
            beginFast = 0
            endFast = 0
            v = 0
        
        if sys.platform  == lin:
            pinList = (pulPIN, dirPIN, enaPIN)
            GPIO.setup(pinList, GPIO.OUT)

        GPIO.output(dirPIN,direction)
        try:
            with RLock():
                posFile = posFiles[achse]
                with open(posFile,"w") as file:
                    if count == pulse:
                        file.write(f"{achsPos}")
                        file.close()

                    while count != pulse:
                        if not self.stop.isSet() and not self.hardStop.isSet():
                            if count < beginFast:
                                v = vmax + const*exp(-1/T*count)
                            if count > endFast:
                                slowdownCounter += 1
                                v = vmin - const*exp(-1/T*slowdownCounter)
                            file.seek(0)
                            GPIO.output(pulPIN,0)
                            sleep(v)
                            GPIO.output(pulPIN,1)
                            count += 1
                            sleep(v)
                            
                            if direction == 0: achsPos += 1
                            if direction == 1: achsPos -= 1
                            position[achse] = achsPos
                            file.write(f"{achsPos}")
                            file.truncate()

                            if achsPos > endMax:
                                print(f"ENDPOS {achse}: {endMax} überschritten")
                                break

                            if achsPos < endMin:
                                print(f"ENDPOS {achse}: {endMin} unterschritten")
                                break
                        elif self.hardStop.isSet():
                            position[achse] = achsPos
                            break
                        else:
                            print("Zyklus wurde angehalten")
                            while self.stop.isSet():
                                sleep(0.2)
                                pass
        except:
            with open(posFile,"w") as file:
                file.write(f"{achsPos}")
                file.close()
        finally:
            self.stopList[achse].set()
            if sys.platform == lin: GPIO.cleanup(pinList)
            if sys.platform == win:
                GPIO.output(pulPIN,0) 
                GPIO.output(dirPIN,0)
                GPIO.cleanup()
            sys.exit()

    def Stopping(self):
        print("..::Stop::..")
        self.stop.set()

    def HardStopping(self):
        print("..::HardStop::..")
        self.hardStop.set()
        
    def ClearStop(self):
        self.stop.clear()
    
    def GetMotorPosition(self):
        return self.posList

    def GetMotorStatus(self):
        if self.XStop.isSet():
            self.XStop.clear()
            self.xCheck = True
        if self.YStop.isSet():
            self.YStop.clear()
            self.yCheck = True
        if self.ZStop.isSet():
            self.ZStop.clear()
            self.zCheck = True
        return self.xCheck, self.yCheck, self.zCheck

    def Start(self, list direction, list vL, list pulsList, list Max, list Min, tuple motorStartCondition):
        self.xCheck = self.yCheck = self.zCheck = False
        self.hardStop.clear()
        self.dirList = direction
        self.vList = vL
        self.pulsList = pulsList
        self.endMax = Max 
        self.endMin = Min
        self.motorStartCondition = motorStartCondition

        for i, condition in enumerate(self.motorStartCondition, 0):
            if condition: self.StartSteuerThr(i)
            else: self.stopList[i].set()
