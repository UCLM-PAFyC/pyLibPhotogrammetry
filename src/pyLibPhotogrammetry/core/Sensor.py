# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

from ..defs import defs_metashape_markers as defs_msm

class Sensor:
    def __init__(self,
                 at_block):
        self.id = None
        self.label = None
        self.type = None
        self.at_block = at_block
        self.file_path = self.at_block.file_path
        self.height = None
        self.width = None
        self.pixel_size = None
        self.pixel_height = None
        self.pixel_width = None
        self.focal_length = None
        self.band_names = []
        self.master_id = defs_msm.METASHAPE_MARKERS_XML_SENSOR_NO_MASTER_ID
        self.rotation = None
        self.rotation_inv = None
        self.rotation_covariance = None
        self.calibration_by_class = {} # initial, adjusted
        self.calibration_covariance_params =[]
        self.calibration_covariance_values =None
        self.geometry = None
        self.pinhole_camera_model = None # K


