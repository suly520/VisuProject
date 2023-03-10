#from Tools import MotorSteuerung as ms

#ms = ms()

#ms.Start([1,1,1], [0.0007,0.0007,0.0007], [3000,3000,3000], [10000,10000,10000], [0,0,0], (True,False,False))

with open('./Tools/X.txt',"w") as file:
    i = 1000
    while i > 0:
        i -= 1
        file.seek(0)
        file.write(str(i))
        file.truncate()



