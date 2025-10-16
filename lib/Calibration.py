# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import os
import sys
import math

current_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_path, '..'))
sys.path.append(os.path.join(current_path, '../..'))
# sys.path.insert(0, '..')
# sys.path.insert(0, '../..')

from pyLibPhotogrammetry.defs import defs_project

class Calibration:
    def __init__(self,
                 sensor):
        self.sensor = sensor
        self.type = None
        self.kind = None
        self.height = None # saved but ignored because use from sensor
        self.width = None # saved but ignored because use from sensor
        self.parameters = {}
