from GPIOEmulator.EmulatorGUI import GPIO
#import RPi.GPIO as GPIO
from time import sleep
import sys
import concurrent.futures

class PosError(Exception):
        pass

class MotorSteuerung:

    def __init__(self, MotorX, MotorY, MotorZ):
        self.AchsList = (0, 1, 2) # Nummerierung der Achsen für das Steuerungsprogramm (Positionscheck X, Y, Z)
        self.PulsPinList = (17,5,16)
        self.DirPinList = (27,6,20)
        self.EnaPinList = (22,13,21)
        self.EndPinList = ()
        self.Direction = (0,0,1)
        self.Runden = (500,2000,4000)
        self.vList = (0.0001, 0.0007, 0.0007)
        self.ENDMax = (14000, 14000, 14000)
        self.ENDMin = (0, 0, 0)

        self.newXpos = 0
        self.newYpos = 0
        self.newZpos = 0

        self.MotorX = MotorX
        self.MotorY = MotorY
        self.MotorZ = MotorZ
    
    
    def thr (self, LiEl):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            th = executor.submit(
                MotorSteuerung.Steuerung, self.AchsList[LiEl], self.PulsPinList[LiEl], self.DirPinList[LiEl], 
                self.EnaPinList[LiEl], self.Direction[LiEl], self.Runden[LiEl], self.vList[LiEl],
                self.ENDMax[LiEl], self.ENDMin[LiEl])
            return_value = th.result() + 1
            print(return_value)
            return return_value

    @staticmethod
    def Filecheck():
        count = 0
        X = list()
        Y = list()
        Z = list()

        #with open("/home/pi/Documents/NewVis/position.txt","r") as file:
        with open("position.txt","r") as file:
            posi=file.readline()
            file.close()

        for i in posi:
            if i != ' ' and count == 0:
                X.append(i)

            if i != ' ' and count == 1:
                Y.append(i)
        
            if i != ' ' and count == 2:
                Z.append(i)
        
            if i == ' ':
                count = count + 1

        X = "".join(X)  
        Y = "".join(Y)  
        Z = "".join(Z) 

        X = int(X)
        Y = int(Y)
        Z = int(Z)
        return X, Y, Z

    @staticmethod
    def Steuerung(Achse, PulPIN, DirPIN, EnaPIN, Dir, Rounds, v, ENDMax, ENDMin):
        Pose = MotorSteuerung.Filecheck()
        AchsPos = Pose[Achse]

        if AchsPos == ENDMax and Dir == 0:
            raise PosError

        if AchsPos  == ENDMin and Dir == 1:
            raise PosError
        
        if AchsPos  > ENDMax or AchsPos < ENDMin: 
            raise PosError

        if (AchsPos + Rounds) > ENDMin and Dir == 1:
            print(f"\nDas Angegebene Ziel würde die untere Position unterschreiten\nAktuellePos: {AchsPos}\n")
            raise PosError

        if (AchsPos + Rounds) > ENDMax and Dir == 0:
            print(f"\nDas angegebene Ziel würde die obere Endposition überschreiten\nAktuellePos: {AchsPos}\n")
            raise PosError
        
        i=0
        BreakOff=False
        PINList = (PulPIN, DirPIN, EnaPIN)
        GPIO.setmode(GPIO.BCM)
        #GPIO.setup(PINList, GPIO.OUT) LINUX !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        GPIO.setup(PINList[0], GPIO.OUT)
        GPIO.setup(PINList[1], GPIO.OUT)
        GPIO.setup(PINList[2], GPIO.IN)
        


        GPIO.output(DirPIN,Dir)
        #GPIO.output(EnaPIN,1)  Linux !!!!!!!!!!!!!!!!!!!!!!!!!!!
        sleep(0.5)

        print(f' Richtung {Dir}')
        print(f' OUTPUT {PulPIN} aktiv')

        #if GPIO.input(EnaPIN) == 1: Linux !!!!!!!!!!!!!!!
        if GPIO.input(EnaPIN) == 0:
            for i in range(Rounds):
                GPIO.output(PulPIN,0)
                sleep(v)
                #if GPIO.input(EnaPIN) == 0: Linux !!!!!!!!!!!!!!!!!!!!!!!!
                if GPIO.input(EnaPIN) == 1:
                    GPIO.output(PulPIN,0)
                    print("break")
                GPIO.output(PulPIN,1)
                sleep(v)
                
                if Dir == 0:
                    AchsPos = AchsPos + 1
                if Dir == 1:
                    AchsPos = AchsPos - 1
                if AchsPos > ENDMax:
                    print(f"ENDPOS {Achse}: {ENDMax} überschritten")
                    break
                if AchsPos < ENDMin:
                    print(f"ENDPOS {Achse}: {ENDMin} unterschritten")
                    break

                #if GPIO.input(EnaPIN) == 0: Linucx !!!!!!!!!!!!!!!!!!!!!!!!!!!
                if GPIO.input(EnaPIN) == 1:
                    while GPIO.input(EnaPIN) == 0:
                        GPIO.output(PulPIN,0)
        GPIO.output(PulPIN,0)
        #GPIO.cleanup(PINList) Linux !!!!!!!!!!!!!!!!!!!!!!
        GPIO.cleanup()

        print(f'  OUTPUT {PulPIN} inaktiv')
        
        return int(i)

    def start(self):
        thX = 0
        thY = 0
        thZ = 0

        if self.MotorX and self.MotorY and self.MotorZ:
            thX = self.thr(0)
            #thX = thX[0]
            thY = self.thr(1)
            #thY = thY[0]
            thZ = self.thr(2)
            #thZ = thZ[0]
        elif self.MotorX and self.MotorY:
            thX = self.thr(0)
            #thX = thX[0]
            thY = self.thr(1)
            #thY = thY[0]
        elif self.MotorX and self.MotorZ:
            thX = self.thr(0)
            # thX = thX[0]
            thZ = self.thr(2)
            #thZ = thZ[0]
        elif self.MotorY and self.MotorZ:
            thY = self.thr(1)
            #thY = thY[0]
            thZ = self.thr(2)
            #thZ = thZ[0]
        elif self.MotorX:
            thX = self.thr(0)
            #thX = thX[0]
        elif self.MotorY:
            thY = self.thr(1)
            #thY = thY[0]
        elif self.MotorZ:
            thZ = self.thr(2)
            #thZ = thZ[0]

        Pose = self.Filecheck()

        posXi = Pose[0]
        posYi = Pose[1]
        posZi = Pose[2]

        #print(posXi, posYi, posZi)

        if self.Direction[0] == 0:
            self.newXpos = posXi + thX
        if self.Direction[0] == 1:
            self.newXpos = posXi - thX

        if self.Direction[1] == 0:
            self.newYpos = posYi + thY
        if self.Direction[1] == 1:
            self.newYpos = posYi - thY

        if self.Direction[2] == 0:
            self.newZpos = posZi + thZ
        if self.Direction[2] == 1:
            self.newZpos = posZi - thZ

        print(self.newXpos)

        with open("position.txt","w") as file:
            file.write(f'{self.newXpos} {self.newYpos} {self.newZpos}')
            file.close()

if __name__ == '__main__':
    m = MotorSteuerung(True, False, False)
    m.start()