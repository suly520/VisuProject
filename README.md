# VisuProject

![plot](./images/preview.gif)

## Description



[GitHub Page](https://github.com/suly520/VisuProject)

The software application for 3-axis machine control was design in conjunction with a custom built circuit unit with a Raspberry Pi including motor controlers and other electronics, to control the machine. The program offers visualization with Pyside and OpenGl, GPIO emulation, coordinate guidance, and touchscreen capability. It has been optimized for performance using the Cython programming language and is currently under development. It has been "tested" on Windows (only for visualization) and Raspberry Pi OS (Linux).

**Currently most of the code and text is german in futur updates i will translate it to english**

## Installation

* packages:
  ```sh
  pip install PySide2
  pip install pyrr
  pip install PyOpenGL
  pip install cython
  pip install pillow
  pip install GPIOEmulator
  ```
  
* preparation:
  >install Python 3.10 # Or other PySide2 compatibe Python version #[PySide2 Info](https://pypi.org/project/PySide2/#:~:text=Programming%20Language,Python%20%3A%3A%203.10)
  >compile cython code
 
* compile cython code
  ```sh
  cd pathTo\VisuProject
  py .\Tools\setup.py build_ext --inplace
  ```
* run the application
  >start the "main_win.py" in the project folder
  
## Function Description
  
* Contouring:
![plot](./images/contouring.gif)
  
