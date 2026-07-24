# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

from osgeo import gdal, osr, ogr

class GdalErrorHandler(object):
    def __init__(self):
        self.err_level = gdal.CE_None
        self.err_no = 0
        self.err_msg = ''

    def handler(self, err_level, err_no, err_msg):
        self.err_level = err_level
        self.err_no = err_no
        self.err_msg = err_msg
err = GdalErrorHandler()
gdal.PushErrorHandler(err.handler)
gdal.UseExceptions()  # Exceptions will get raised on anything >= gdal.CE_Failure
assert err.err_level == gdal.CE_None, 'the error level starts at 0'

from ..defs import defs_graphos as defs_gr
from ..core.Sensor import Sensor
from ..core.CalibrationGraphos import CalibrationGraphos

SENSOR_INTEGER_NO_VALUE = -9999
SENSOR_DOUBLE_NO_VALUE = -9999.999
SENSOR_GEOMETRY_SIDE_NUMBER_OF_POINTS = 33
SENSOR_GEOMETRY_PRECISION = 6
SENSOR_OUTER_POINT_PERCENTAGE_FOCAL_PLANE_TOLERANCE = 10.0

class SensorGraphos(Sensor):
    def __init__(self,
                 at_block):
        super().__init__(at_block)
        self.make = None
        self.model = None
        self.serial_number = None
        self.sensor_size = None
        self.calibration_undistorted_by_class = {} # initial, adjusted
        # self.normalize_sensitivity = None
        # self.layer_index = None
        # self.data_type_as_string = None
        # self.black_level = None
        # self.sensitivity = None
        # self.vignetting = {} # self.vignetting[i][j] = value

    def from_camera_to_sensor(self,
                              x, y, z,
                              rotation):
        str_error = ''
        within = False
        withinAfterUndistortion = False
        position_image = None
        position_undistorted_image = None
        calibration_type = next(iter(self.calibration_by_class))
        calibration = self.calibration_by_class[calibration_type]
        if (calibration.type.casefold() != defs_gr.GRAPHOS_SENSOR_CALIBRATION_TYPE_OPENCV_1.casefold()):
            str_error = ('For sensor: {} calibration type: {} is not valid\nmust be {}'.
                         format(self.label, calibration.type, defs_gr.GRAPHOS_SENSOR_CALIBRATION_TYPE_OPENCV_1))
            return str_error, within, withinAfterUndistortion, position_image, position_undistorted_image
        str_error = self.at_block.project.opencv_tools.from_camera_to_sensor(x, y, z, rotation, calibration)


        return str_error, within, withinAfterUndistortion, position_image, position_undistorted_image

    def get_focal(self):
        str_error = ''
        focal = None
        if not defs_gr.GRAPHOS_XML_SENSOR_CALIBRATION_TAG in self.calibration_by_class:
            str_error = ('For sensor: {} not found calibration class: {}'.
                         format(self.label, defs_gr.GRAPHOS_XML_SENSOR_CALIBRATION_TAG))
            return str_error, focal
        calibration = self.calibration_by_class[defs_gr.GRAPHOS_XML_SENSOR_CALIBRATION_TAG]
        if (calibration.type.casefold() != defs_gr.GRAPHOS_SENSOR_CALIBRATION_TYPE_OPENCV_1.casefold()):
            str_error = ('For sensor: {} calibration type: {} is not valid\nmust be {}'.
                         format(self.label, calibration.type, defs_gr.GRAPHOS_SENSOR_CALIBRATION_TYPE_OPENCV_1))
            return str_error, focal
        focal_x = calibration.parameters[defs_gr.GRAPHOS_XML_SENSOR_CALIBRATION_FX_TAG]
        focal_y = calibration.parameters[defs_gr.GRAPHOS_XML_SENSOR_CALIBRATION_FY_TAG]
        focal = (focal_x + focal_y) / 2.
        return str_error, focal

    def set_from_xml(self,
                     xml_element):
        str_error = ''
        #id
        if not defs_gr.GRAPHOS_XML_SENSOR_ATTRIBUTE_ID in xml_element:
            str_error = ('Not exists attribute: {} in sensor in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_SENSOR_ATTRIBUTE_ID, self.at_block.file_path))
            return str_error
        str_id = xml_element[defs_gr.GRAPHOS_XML_SENSOR_ATTRIBUTE_ID]
        try:
            self.id = int(str_id)
        except ValueError:
            str_error = ('Attribute: {} in sensor in XML file:\n{}\n must be an integer: {}'.
                         format(defs_gr.GRAPHOS_XML_SENSOR_ATTRIBUTE_ID, self.at_block.file_path, str_id))
            return str_error
        if self.id in self.at_block.sensor_by_id:
            str_error = ('Exists previous sensor id: {} in sensor in XML file:\n{}'.
                         format(str(self.id), self.file_path,))
            return str_error
        # Make
        if not defs_gr.GRAPHOS_XML_SENSOR_MAKE_TAG in xml_element:
            str_error = ('Not exists attribute: {} in sensor in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_SENSOR_MAKE_TAG, self.at_block.file_path))
            return str_error
        make = xml_element[defs_gr.GRAPHOS_XML_SENSOR_MAKE_TAG]
        self.make = make
        # model
        if not defs_gr.GRAPHOS_XML_SENSOR_MODEL_TAG in xml_element:
            str_error = ('Not exists attribute: {} in sensor in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_SENSOR_MODEL_TAG, self.at_block.file_path))
            return str_error
        model = xml_element[defs_gr.GRAPHOS_XML_SENSOR_MODEL_TAG]
        self.model = model
        # serial_number
        if not defs_gr.GRAPHOS_XML_SENSOR_SERIAL_NUMBER_TAG in xml_element:
            str_error = ('Not exists attribute: {} in sensor in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_SENSOR_SERIAL_NUMBER_TAG, self.at_block.file_path))
            return str_error
        serial_number = xml_element[defs_gr.GRAPHOS_XML_SENSOR_SERIAL_NUMBER_TAG]
        self.serial_number = serial_number
        # calibration_type best than sensor_type
        if not defs_gr.GRAPHOS_XML_SENSOR_TYPE_TAG in xml_element:
            str_error = ('Not exists attribute: {} in sensor in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_SENSOR_TYPE_TAG, self.at_block.file_path))
            return str_error
        calibration_type = xml_element[defs_gr.GRAPHOS_XML_SENSOR_TYPE_TAG]
        calibration_type = calibration_type
        if (calibration_type.casefold() != defs_gr.GRAPHOS_SENSOR_CALIBRATION_TYPE_OPENCV_1.casefold()):
            str_error = ('Invalid calibration type in XML file:\n{}'.
                         format(self.type))
            return str_error
        # band_name
        if not defs_gr.GRAPHOS_XML_SENSOR_BAND_NAME_TAG in xml_element:
            str_error = ('Not exists attribute: {} in sensor in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_SENSOR_BAND_NAME_TAG, self.at_block.file_path))
            return str_error
        band_name = xml_element[defs_gr.GRAPHOS_XML_SENSOR_BAND_NAME_TAG]
        self.band_name = band_name
        #width
        if not defs_gr.GRAPHOS_XML_SENSOR_WIDTH_TAG in xml_element:
            str_error = ('Not exists attribute: {} in sensor in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_SENSOR_WIDTH_TAG, self.at_block.file_path))
            return str_error
        str_width = xml_element[defs_gr.GRAPHOS_XML_SENSOR_WIDTH_TAG]
        try:
            self.width = int(str_width)
        except ValueError:
            str_error = ('Attribute: {} in sensor in XML file:\n{}\n must be an integer: {}'.
                         format(defs_gr.GRAPHOS_XML_SENSOR_WIDTH_TAG, self.at_block.file_path, str_width))
            return str_error
        #height
        if not defs_gr.GRAPHOS_XML_SENSOR_HEIGHT_TAG in xml_element:
            str_error = ('Not exists attribute: {} in sensor in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_SENSOR_HEIGHT_TAG, self.at_block.file_path))
            return str_error
        str_height = xml_element[defs_gr.GRAPHOS_XML_SENSOR_HEIGHT_TAG]
        try:
            self.height = int(str_height)
        except ValueError:
            str_error = ('Attribute: {} in sensor in XML file:\n{}\n must be an integer: {}'.
                         format(defs_gr.GRAPHOS_XML_SENSOR_HEIGHT_TAG, self.at_block.file_path, str_height))
            return str_error
        #focal_length
        if not defs_gr.GRAPHOS_XML_SENSOR_FOCAL_TAG in xml_element:
            str_error = ('Not exists attribute: {} in sensor in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_SENSOR_FOCAL_TAG, self.at_block.file_path))
            return str_error
        str_focal_length = xml_element[defs_gr.GRAPHOS_XML_SENSOR_FOCAL_TAG]
        try:
            self.focal_length = float(str_focal_length)
        except ValueError:
            str_error = ('Attribute: {} in sensor in XML file:\n{}\n must be a float: {}'.
                         format(defs_gr.GRAPHOS_XML_SENSOR_FOCAL_TAG, self.at_block.file_path, str_focal_length))
            return str_error
        #sensor_size
        if not defs_gr.GRAPHOS_XML_SENSOR_SENSOR_SIZE_TAG in xml_element:
            str_error = ('Not exists attribute: {} in sensor in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_SENSOR_SENSOR_SIZE_TAG, self.at_block.file_path))
            return str_error
        str_sensor_size = xml_element[defs_gr.GRAPHOS_XML_SENSOR_SENSOR_SIZE_TAG]
        try:
            self.sensor_size = float(str_sensor_size)
        except ValueError:
            str_error = ('Attribute: {} in sensor in XML file:\n{}\n must be a float: {}'.
                         format(defs_gr.GRAPHOS_XML_SENSOR_SENSOR_SIZE_TAG, self.at_block.file_path, str_sensor_size))
            return str_error
        # pixel_size is not self.sensor_size / sqrt(height**2 + widht **2)
        #bits_per_pixel
        if not defs_gr.GRAPHOS_XML_SENSOR_BITS_PER_PIXEL_TAG in xml_element:
            str_error = ('Not exists attribute: {} in sensor in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_SENSOR_BITS_PER_PIXEL_TAG, self.at_block.file_path))
            return str_error
        str_bits_per_pixel = xml_element[defs_gr.GRAPHOS_XML_SENSOR_BITS_PER_PIXEL_TAG]
        try:
            self.bits_per_pixel = int(str_bits_per_pixel)
        except ValueError:
            str_error = ('Attribute: {} in sensor in XML file:\n{}\n must be an integer: {}'.
                         format(defs_gr.GRAPHOS_XML_SENSOR_BITS_PER_PIXEL_TAG, self.at_block.file_path, str_bits_per_pixel))
            return str_error
        # calibrations
        if not defs_gr.GRAPHOS_XML_SENSOR_CALIBRATION_TAG in xml_element:
            str_error = ('Not exists element: {} in sensor: {} in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_SENSOR_CALIBRATION_TAG, self.label, self.at_block.file_path))
            return str_error
        calibration_element = xml_element[defs_gr.GRAPHOS_XML_SENSOR_CALIBRATION_TAG]
        calibrations_list = []
        if isinstance(calibration_element, list):
            calibrations_list = calibration_element
        else:
            calibrations_list.append(calibration_element)
        for i in range(len(calibrations_list)):
            calibration_element = calibrations_list[i]
            calibration = CalibrationGraphos(self, calibration_type)
            str_error = calibration.set_from_xml(calibration_element)
            if str_error:
                str_error = ('Loading calibration position: {}\n in sensor: {} in XML file:\n{}'.
                             format(str(i+1), self.label, self.at_block.file_path))
                return str_error
            self.calibration_by_class[calibration.kind] = calibration
        # CalibrationUndistorted
        if not defs_gr.GRAPHOS_XML_SENSOR_CALIBRATION_UNDISTORTED_TAG in xml_element:
            str_error = ('Not exists element: {} in sensor: {} in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_SENSOR_CALIBRATION_UNDISTORTED_TAG, self.label,
                                self.at_block.file_path))
            return str_error
        calibration_undistorted_element = xml_element[defs_gr.GRAPHOS_XML_SENSOR_CALIBRATION_UNDISTORTED_TAG]
        calibrations_undistorted_list = []
        if isinstance(calibration_undistorted_element, list):
            calibrations_undistorted_list = calibration_undistorted_element
        else:
            calibrations_undistorted_list.append(calibration_undistorted_element)
        for i in range(len(calibrations_undistorted_list)):
            calibration_element = calibrations_undistorted_list[i]
            calibration = CalibrationGraphos(self, calibration_type)
            str_error = calibration.set_from_xml(calibration_element)
            if str_error:
                str_error = ('Loading calibration position: {}\n in sensor: {} in XML file:\n{}'.
                             format(str(i+1), self.label, self.at_block.file_path))
                return str_error
            self.calibration_undistorted_by_class[calibration.kind] = calibration
        return str_error

