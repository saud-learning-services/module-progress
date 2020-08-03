"""
Declares several global variables that are used throughout the project.

* The status dictionary gets updated to reflect the success/failed state of each course (and relevant errors)
* ROOT_DIR is the filepath to the src folder

"""
import os

status = {}
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
