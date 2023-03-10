
import time


from GPIOEmulator.EmulatorGUI import GPIO

import threading

#import RPi.GPIO as GPIO

from time import sleep

import sys

import socket




class PosError(Exception):
    """Wird aufgerufen wenn ein Positionierungsfehler vorliegt"""
    pass

class Stop(Exception):
    """Wird für das Stoppen der funktion benötigt"""
    pass

class MotorSteuerung:
    
    def __init__(self, PinList = [17, 5, 16, 27, 6, 20, 22, 13, 21]):

        #GPIO.setmode(GPIO.BOARD)
        GPIO.setmode(GPIO.BCM)
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.AchsList = (0, 1, 2) # Nummerierung der Achsen für das Steuerungsprogramm (Positionscheck X, Y, Z)
                            #BOARD    
                            # (11,29,36)
                            # (13,31,38)
                            # (15,33,21)

                            #BCM
        self.PinList = PinList
        #PinList =  (11,29,36,13,31,38,15,33,21)  
        self.PulsPinList = self.PinList[0:3]

        self.DirPinList = self.PinList[3:6]

        self.EnaPinList = self.PinList[6:9]

        self.checklist = [0, 0, 0]

        self.Stop = threading.Event()
        #self.starter = time.time()
        #self.Direction = (1,1,1)
        

        #self.Runden = (500,500,500)

        #self.vList = (0.0007, 0.0007, 0.0007)

        #self.ENDMax = (14000, 14000, 14000)

        #self.ENDMin = (0, 0, 0)

        try:
            for i in range(len(self.PinList)-3):
                GPIO.setup(int(self.PinList[i]), GPIO.OUT)
            
            for i in range(len(self.EnaPinList)):
                GPIO.setup(int(self.EnaPinList[i]), GPIO.IN)
        except:
            pass



    

        self.EndPinList = ()

        self.newXpos = 0

        self.newYpos = 0

        self.newZpos = 0

    

    

    

    def thr (self, LiEl):
        

        th = threading.Thread(target= self.Steuerung, args=(

            self.AchsList[LiEl], self.PulsPinList[LiEl], self.DirPinList[LiEl], 

            self.EnaPinList[LiEl], self.Direction[LiEl], self.Runden[LiEl], self.vList[LiEl],

            self.ENDMax[LiEl], self.ENDMin[LiEl], self.client

            ),daemon = True)

        retVal = th.start()
        

        return retVal
    




    def Filecheck():
        #FilePath = "/home/pi/Desktop/NewVis2.0"
        FilePath = "C:/Users/suly5/Desktop/NewVis2.0/PositionFiles"
            
        with open(f"{FilePath}/X.txt","r") as fx,open(f"{FilePath}/Y.txt","r") as fy,open(f"{FilePath}/Z.txt","r") as fz:
            X = fx.readlines()
            Y = fy.readlines()
            Z = fz.readlines()


            X = "".join(X)
            Y = "".join(Y)
            Z = "".join(Z)

        return int(X), int(Y), int(Z)


    def checkpos(Achse, Dir, Rounds, ENDMax, ENDMin, client=None):
        
        Pose = MotorSteuerung.Filecheck()

        AchsPos = Pose[Achse]


        try:
            if AchsPos == ENDMax and Dir == 0 and Rounds != 0:
                raise PosError
        except PosError:
            print(f"\nAchse {Achse}: Die Ausführung mit der gewählten Bewegungsrichtung würde die obere ENDpos überschreiten\n")
            print(MotorSteuerung().Steurterminal('steuer',0,(Achse)))
            sys.exit()

        try:
            if AchsPos  == ENDMin and Dir == 1 and Rounds != 0:

                raise PosError
        except PosError:
            print(f"\nAchse {Achse}: Die Ausführung mit der gewählten Bewegungsrichtung würde die untere ENDpos überschreiten\n")
            print(MotorSteuerung().Steurterminal('steuer',1,(Achse)))
            sys.exit()

        try:
            if AchsPos  > ENDMax or AchsPos < ENDMin: 
                raise PosError
        except PosError:
            print(f"\nAchse {Achse}: Die momentane Position befindet sich außerhalb des richtigen Wertebereiches\n")
            print(MotorSteuerung().Steurterminal('steuer',2,(Achse)))
            sys.exit()

        try:
            if (AchsPos - Rounds) < ENDMin and Dir == 1:
                raise PosError

        except PosError:
            print(f"\nAchse {Achse}: Das angegebene Ziel würde die untere Position unterschreiten\nAktuellePos: {AchsPos}\nPos nacher: {AchsPos-Rounds}\n")
            print(MotorSteuerung().Steurterminal('steuer',3,(Achse, AchsPos, AchsPos-Rounds)))
            sys.exit()

        print(Rounds)
        try:
            if (AchsPos + Rounds) > ENDMax and Dir == 0:
                raise PosError

        except PosError:
            print(f"\nAchse {Achse}: Das angegebene Ziel würde die obere Endposition überschreiten\nAktuellePos: {AchsPos}\nPos nacher: {AchsPos+Rounds}\n")
            print(MotorSteuerung().Steurterminal('steuer',4,(Achse, AchsPos, AchsPos+Rounds)))
            sys.exit()

        
        return AchsPos

    def Steuerung(self, Achse, PulPIN, DirPIN, EnaPIN, Dir, Rounds, v, ENDMax, ENDMin, client):
        
        AchsPos = MotorSteuerung.checkpos(Achse, Dir, Rounds, ENDMax, ENDMin, client)

        i=0

        BreakOff=False

        PINList = (PulPIN, DirPIN, EnaPIN)

        #GPIO.setup(PINList, GPIO.OUT) #LINUX !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        #GPIO.setup(PulPIN,GPIO.OUT)
        #GPIO.setup(DirPIN,GPIO.OUT)
        #GPIO.setup(EnaPIN,GPIO.IN)

        GPIO.output(DirPIN,Dir)

        #GPIO.output(EnaPIN,1)  #Linux !!!!!!!!!!!!!!!!!!!!!!!!!!!

        #sleep(0.5)
        
        client.connect(('127.0.0.1', '65432'))
        Mess = f' Richtung {Dir}\nOUTPUT {PulPIN} aktiv'
        client.send(Mess.encode('UTF-8'))
        #print(f' Richtung {Dir}\nOUTPUT {PulPIN} aktiv')

        #if GPIO.input(EnaPIN) == 1: #Linux !!!!!!!!!!!!!!!

        #if GPIO.input(EnaPIN) == 0:

        try:
            count = 0
            if Achse == 0:
                #PosFile = "/home/pi/Desktop/NewVis2.0/X.txt"
                PosFile = "C:/Users/suly5/Desktop/NewVis2.0/PositionFiles/X.txt"

            if Achse == 1:
                #PosFile = "/home/pi/Desktop/NewVis2.0/Y.txt"
                PosFile = "C:/Users/suly5/Desktop/NewVis2.0/PositionFiles/Y.txt"

            if Achse == 2:
                #PosFile = "/home/pi/Desktop/NewVis2.0/Z.txt"
                PosFile = "C:/Users/suly5/Desktop/NewVis2.0/PositionFiles/Z.txt"

            #if not self.Stop.isSet():
            #if GPIO.input(self.EnaPinList[0]) == 0 and GPIO.input(self.EnaPinList[1]) == 0 and GPIO.input(self.EnaPinList[2]) == 0:
            
            with open(PosFile,"w") as file:
                if count == Rounds:
                    file.write(f"{AchsPos}")
                    file.truncate()
                    file.close()

                while count != Rounds:
                    if not self.Stop.isSet():
                        file.seek(0)
                        GPIO.output(PulPIN,0)
                        sleep(v)
                        GPIO.output(PulPIN,1)
                        count = count + 1
                        sleep(v)
                        
                        if Dir == 0:
                                AchsPos = AchsPos + 1
                        
                        if Dir == 1:
                                AchsPos = AchsPos - 1

                        file.write(f"{AchsPos}")
                        file.truncate()

                        if AchsPos > ENDMax:
                            print(f"ENDPOS {Achse}: {ENDMax} überschritten")
                            print(MotorSteuerung().Steurterminal('steuer',7,(Achse,ENDMax)))
                            break

                        if AchsPos < ENDMin:
                            print(f"ENDPOS {Achse}: {ENDMin} unterschritten")
                            print(MotorSteuerung().Steurterminal('steuer',8,(Achse,ENDMin)))
                            break
                        
                    if self.Stop.isSet():
                        print( "Zyklus wurde angehalten")
                        print(MotorSteuerung().Steurterminal('steuer',9))
                        while self.Stop.isSet():
                            continue
                
            

            print(f'  OUTPUT {PulPIN} inaktiv')
            print(MotorSteuerung().Steurterminal('steuer',10))
            GPIO.output(PulPIN,0)

            #GPIO.cleanup(PINList) #Linux !!!!!!!!!!!!!!!!!!!!!!
            GPIO.cleanup()

        except:
            GPIO.output(PulPIN,0)
            
            with open(PosFile,"w") as file:
                file.write(f"{AchsPos}")
                file.close()

            print(f'  OUTPUT {PulPIN} inaktiv')

            self.Stop.clear()
            #end = time.time()
            #print('time =',end - self.starter)
        

    def stop(self):
        self.Stop.set()
    
    def starting(self):
        self.Stop.clear()

    def start(self, Dir, vL, Runden, Max, Min, MotorX, MotorY, MotorZ):
        self.Stop.clear()
        self.Direction = Dir
        self.vList = vL
        self.Runden = Runden
        self.ENDMax = Max 
        self.ENDMin = Min
        self.MotorX = MotorX
        self.MotorY = MotorY
        self.MotorZ = MotorZ
    
        sleep(5)
        if self.MotorX and self.MotorY and self.MotorZ:
            self.thr(0)
            self.thr(1)
            self.thr(2)

        elif self.MotorX and self.MotorY:
            self.thr(0)
            self.thr(1)

        elif self.MotorX and self.MotorZ:
            self.thr(0)
            self.thr(2)

        elif self.MotorY and self.MotorZ:
            self.thr(1)
            self.thr(2)

        elif self.MotorX:
            self.thr(0)

        elif self.MotorY:
            self.thr(1)

        elif self.MotorZ:
            self.thr(2)
        
    def Steurterminal(self, therm, Num, var=None):
        if therm == "steuer":
            code = (
                f"\nAchse {var[0]}: Die Ausführung mit der gewählten Bewegungsrichtung würde die obere ENDpos überschreiten\n",
                f"\nAchse {var[0]}: Die Ausführung mit der gewählten Bewegungsrichtung würde die untere ENDpos überschreiten\n",
                f"\nAchse {var[0]}: Die momentane Position befindet sich außerhalb des richtigen Wertebereiches\n",
                f"\nAchse {var[0]}: Das angegebene Ziel würde die untere Position unterschreiten\nAktuellePos: {var[1]}\nPos nacher: {var[2]}\n",
                f"\nAchse {var[0]}: Das angegebene Ziel würde die obere Endposition überschreiten\nAktuellePos: {var[1]}\nPos nacher: {var[2]}\n",
                f' Richtung {var[0]}',
                f' OUTPUT {var[0]} aktiv',
                f"ENDPOS {var[0]}: {var[1]} überschritten",
                f"ENDPOS {var[0]}: {var[1]} unterschritten",
                "Zyklus wurde angehalten",
                f'  OUTPUT {var[0]} inaktiv',
                f'  OUTPUT {var[0]} inaktiv'
            )   
        return code[Num]

if __name__ == '__main__':
    
    AnzahlPulse = (0, 0, 0)
    vListe = (0.0007, 0.0007, 0.0007)
    DirList = (1,1,1)
    Max = (10, 10, 10)
    Min = (0,0,0)
    

    m = MotorSteuerung(True, True, True)

    m.start(DirList, vListe, AnzahlPulse, Max, Min)
    
    x = input('press x')

    
    if x == 'x':
        m.stop()