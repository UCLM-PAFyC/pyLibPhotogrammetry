# authors:
# David Hernandez Lopez, david.hernandez@uclm.es
import os
import sys

current_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_path, '..'))

IMAGE_POINT_MEASURED = "Measured"
IMAGE_POINT_MATCHED = "Matched"
IMAGE_POINT_PROJECTED = "Projected"
