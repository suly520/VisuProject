from setuptools import setup
from Cython.Build import cythonize

setup(ext_modules=cythonize('./Tools/Steuerungsklasse.pyx'))
setup(ext_modules=cythonize('./Tools/Dynamikcy.pyx'))
setup(ext_modules=cythonize('./Tools/ObjTools.pyx'))
