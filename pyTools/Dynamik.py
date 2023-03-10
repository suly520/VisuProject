from math import tan, atan


def vNeu(WegX, WegY, WegZ, vmax):
        vX = 0
        vY = 0
        vZ = 0
        WegX = abs(WegX)
        WegY = abs(WegY)
        WegZ = abs(WegZ)

        if WegX != 0 and WegY != 0:
            wYX = atan(WegY/WegX)
            wXY = atan(WegX/WegY)
        if WegY != 0 and WegZ != 0:
            wZY = atan(WegZ/WegY)
            wYZ = atan(WegY/WegZ)
        if WegX != 0 and WegZ != 0:
            wXZ = atan(WegX/WegZ)
            wZX = atan(WegZ/WegX)   
        if WegX == 0:
            wXY = wYX = wXZ = wZX = 0
        if WegY == 0:
            wYX = wXY = wYZ = wZY = 0
        if WegZ == 0:
            wZX = wXZ = wZY = wYZ = 0 
        
        if WegX == WegY == WegZ:
            vX = vY = vZ = vmax

        if WegX > WegY > WegZ:
            vX = vmax
            vY = vX * tan(wYX)
            vZ = vY * tan(wZY)
        if WegZ > WegX > WegY:
            vZ = vmax
            vX = vZ * tan(wXZ)
            vY = vX * atan(wYX)
        if WegY > WegZ > WegX:
            vY = vmax
            vZ = vY * tan(wZY)
            vX = vZ * atan(wXZ)

        if WegZ > WegY > WegX:
            vZ = vmax
            vY = vZ * tan(wYZ)
            vX = vY * atan(wXY)
        if WegX > WegZ > WegY:
            vX = vmax
            vZ = vX * tan(wZX)
            vY = vZ * atan(wYZ)
        if WegY > WegX > WegZ:
            vY = vmax
            vX = vY * tan(wXY)
            vZ = vX * atan(wZX)

        if WegX > WegY == WegZ:
            vX = vmax
            vY = vZ = vX * tan(wYX)
        if WegZ > WegX == WegY:
            vZ = vmax
            vX = vY = vZ * atan(wXZ)
        if WegY > WegZ == WegX:
            vY = vmax
            vZ = vX = vY * atan(wZY)

        if WegX < WegY == WegZ:
            vY = vZ = vmax
            vX = vY * tan(wXY)
        if WegZ < WegX == WegY:
            vX = vY = vmax
            vZ = vX * tan(wZX)
        if WegY < WegZ == WegX:
            vZ = vX = vmax
            vY = vZ * tan(wYZ)
        
        # MotorVariablenSetzen
        if WegX != 0:
            MotorX = True
        if WegY != 0:
            MotorY = True
        if WegZ != 0: 
            MotorZ = True
        return round(vX,6), round(vY,6), round(vZ,6), MotorX, MotorY, MotorZ

def motor(Achse, ist, v, soll, ziel, weg, ZyklStop, Direction):
        Xcheck = False
        Ycheck = False
        Zcheck = False
        
        if not ZyklStop:
            if weg > 0 and not ZyklStop:
                ist = ist + v
                if Achse == 0:
                    Direction[Achse] = 0
                if Achse == 1:
                    Direction[Achse] = 0
                if Achse == 2:
                    Direction[Achse] = 0
                    
            if weg < 0 and not ZyklStop:
                ist = ist - v
                if Achse == 0:
                    Direction[Achse] = 1
                if Achse == 1:
                    Direction[Achse] = 1
                if Achse == 2:
                    Direction[Achse] = 1
                    
            if weg > 0 and ist >= soll or weg < 0 and ist <= soll or weg == 0:
                ist = ziel
                if Achse == 0:
                    Xcheck = True
                if Achse == 1:
                    Ycheck = True
                if Achse == 2:
                    Zcheck = True
        
        return ist, Xcheck, Ycheck, Zcheck