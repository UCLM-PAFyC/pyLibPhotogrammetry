# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

from osgeo import gdal, ogr

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
        self.focal_length = None # initial in mm
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
        self.geometry_pixels = None

    def get_epipolar_line_from_segment(self, first_segment_pto, second_segment_pto):
        str_error = ''
        first_pto = second_pto = None
        if self.geometry_pixels is None:
            columns = self.width
            rows = self.height
            wkt_geometry = "POLYGON(("
            wkt_geometry += ('{:6f}'.format(0))
            wkt_geometry += " "
            wkt_geometry += ('{:6f}'.format(0))
            wkt_geometry += ","
            wkt_geometry += ('{:6f}'.format(columns - 1))
            wkt_geometry += " "
            wkt_geometry += ('{:6f}'.format(0))
            wkt_geometry += ","
            wkt_geometry += ('{:6f}'.format(columns - 1))
            wkt_geometry += " "
            wkt_geometry += ('{:6f}'.format(rows - 1))
            wkt_geometry += ","
            wkt_geometry += ('{:6f}'.format(0))
            wkt_geometry += " "
            wkt_geometry += ('{:6f}'.format(rows - 1))
            wkt_geometry += ","
            wkt_geometry += ('{:6f}'.format(0))
            wkt_geometry += " "
            wkt_geometry += ('{:6f}'.format(0))
            wkt_geometry += "))"
            try:
                self.geometry_pixels = ogr.CreateGeometryFromWkt(wkt_geometry)
            except Exception as e:
                # str_error = 'GDAL Error: ' + e.args[0]
                # str_error = ('Setting geometry in sensor: {}\nGDAL error:\n{}}'.
                #              format(self.label, e.args[0]))
                str_error = ('Error setting geometry pixels in sensor: {} from WKT'.
                             format(self.label))
                return str_error, first_pto, second_pto
        wkt_geometry = "LINESTRING("
        wkt_geometry += ('{:.3f} {:.3f}'.format(first_segment_pto[0], first_segment_pto[1]))
        wkt_geometry += (',{:.3f} {:.3f})'.format(second_segment_pto[0], second_segment_pto[1]))
        segment_geometry = None
        try:
            segment_geometry = ogr.CreateGeometryFromWkt(wkt_geometry)
        except Exception as e:
            # str_error = 'GDAL Error: ' + e.args[0]
            # str_error = ('Setting geometry in sensor: {}\nGDAL error:\n{}}'.
            #              format(self.label, e.args[0]))
            str_error = ('Error setting geometry in sensor: {} from WKT'.
                         format(self.label))
            return str_error, first_pto, second_pto
        if self.geometry_pixels.Contains(segment_geometry):
            first_pto = []
            first_pto.append(first_segment_pto[0])
            first_pto.append(first_segment_pto[1])
            second_pto = []
            second_pto.append(second_segment_pto[0])
            second_pto.append(second_segment_pto[1])
        elif segment_geometry.Intersects(self.geometry_pixels):
            segment_geometry_intersection = None
            try:
                segment_geometry_intersection = segment_geometry.Intersection(self.geometry_pixels)
            except Exception as e:
                # str_error = 'GDAL Error: ' + e.args[0]
                # str_error = ('Setting geometry in sensor: {}\nGDAL error:\n{}}'.
                #              format(self.label, e.args[0]))
                str_error = ('Error intersecting segment in sensor: {} from WKT'.
                             format(self.label))
                return str_error, first_pto, second_pto
            segment_geometry_intersection_name = None
            # wkt = segment_geometry_intersection.ExportToWkt()
            try:
                segment_geometry_intersection_name = segment_geometry_intersection.GetGeometryName()
            except Exception as e:
                # str_error = 'GDAL Error: ' + e.args[0]
                # str_error = ('Setting geometry in sensor: {}\nGDAL error:\n{}}'.
                #              format(self.label, e.args[0]))
                str_error = ('Error getting name of type of intersection segment in sensor: {}'.
                             format(self.label))
                return str_error, first_pto, second_pto
            # if segment_geometry_intersection.type == ogr.wkbLineString:
            if segment_geometry_intersection_name.casefold() == "LINESTRING".casefold():
                first_pto = segment_geometry_intersection.GetPoint(0)
                second_pto = segment_geometry_intersection.GetPoint(1)
                # first_pto.append(segment_geometry_intersection.getX(0))
                # first_pto.append(segment_geometry_intersection.getY(0))
                # second_pto = []
                # second_pto.append(segment_geometry_intersection.getX(1))
                # second_pto.append(segment_geometry_intersection.getY(1))
        return str_error, first_pto, second_pto


