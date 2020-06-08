"""
Declares several global variables that are used throughout the project.
Status dictionary gets updated to reflect the state of each course script 
gets module data for.
ROOT_DIR is the filepath to the src folder.

@authors: markoprodanovic
"""
import os


def init():
    '''
    Initializes status object and src directory file path
    '''
    global status
    status = {}
    global ROOT_DIR
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
