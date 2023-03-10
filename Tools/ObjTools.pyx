import numpy as np
from numpy.lib.shape_base import split

class ObjLoader:
    buffer = []

    @staticmethod
    def SearchData(list dataValues, list coordinates, str skip, str dataType):
        cdef str data 
        for data in dataValues:
            if data == skip:
                continue
            if dataType == 'float':
                coordinates.append(float(data))
            elif dataType == 'int':
                coordinates.append(int(data)-1)

    @staticmethod 
    def CreateVertexBuffer(list indicesData, list vertices, list textures, list normals):
        cdef int i
        cdef int ind
        cdef int start
        cdef int end

        for i, ind in enumerate(indicesData):
            if i % 3 == 0: # sort the vertex coordinates
                start = ind * 3
                end = start + 3
                ObjLoader.buffer.extend(vertices[start:end])
            elif i % 3 == 1: # sort the texture coordinates
                start = ind * 2
                end = start + 2
                ObjLoader.buffer.extend(textures[start:end])
            elif i % 3 == 2: # sort the normal vectors
                start = ind * 3
                end = start + 3
                ObjLoader.buffer.extend(normals[start:end])
        
    @staticmethod
    def LoadModel(str file):
        cdef list vertCoords = [] # will contain all the vertex coordinates
        cdef list texCoords = [] # will contain all the texture coordinates
        cdef list normCoords = [] # will contain all the vertex normals

        cdef list allIndices = [] # will contain all the vertex, texture and normal indices
        cdef list indices = [] # will contain the indices for indexed drawing
        cdef list vertList = []
        cdef list ve = []
        cdef bytes line
        cdef str lineS

        with open(file, 'rb') as f:
            line = f.readline()
            lineS = line.decode()
            while lineS:
                values = lineS.split()
                if len(values):
                    if values[0] == 'v':
                        ObjLoader.SearchData(values, vertCoords, 'v', 'float')
                    elif values[0] == 'vt':
                        ObjLoader.SearchData(values, texCoords, 'vt', 'float')
                    elif values[0] == 'vn':
                        ObjLoader.SearchData(values, normCoords, 'vn', 'float')
                    elif values[0] == 'f':
                        for value in values[1:]:
                            try:
                                val = value.split('/')
                                ObjLoader.SearchData(val, allIndices, 'f', 'int')
                                indices.append(int(val[0])-1)
                            except ValueError:
                                val = value.split('//')
                                ObjLoader.SearchData(val, allIndices, 'f', 'int')
                                indices.append(int(val[0])-1)
                else: pass


                line = f.readline()
                lineS = line.decode()
            
        ObjLoader.CreateVertexBuffer(allIndices, vertCoords, texCoords, normCoords)
        
        buffer = ObjLoader.buffer.copy() # create a local copy of the buffer list, otherwise it will overwrite the static field buffer
        ObjLoader.buffer = [] # after copy, make sure to set it back to an empty list

        return np.array(indices, dtype='uint32'), np.array(buffer, dtype='float32')

    @staticmethod
    def PosGenerate(str file):
        cdef list values
        cdef bytes line
        for line in open(file, "rb"):
            values = line.split()
            if values[0] == b'v':
                yield [values[1].decode(), values[2].decode(), values[3].decode()]


                