# authors:
# David Hernandez Lopez, david.hernandez@uclm.es
import os
import sys

current_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_path, '..'))
# sys.path.insert(0, '..')

GRAPHOS_DOCUMENT_TAG = "GraphosCameras"
GRAPHOS_AT_BLOCK_LABEL = "ATBlock"
