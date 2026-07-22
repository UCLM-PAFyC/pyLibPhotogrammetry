# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import numpy as np

from pyLibPhotogrammetry.core.ObjectPoint import ObjectPoint

class ObjectPointGraphos(ObjectPoint):
    def __init__(self,
                 at_block):
        super().__init__(at_block)
        self.position_enu = None

    def initialize(self,name,x,y,z, crs_id):
        str_error = ''
        self.id = name
        self.label = name
        position = [[x, y, z]]
        str_error = self.crs_tools.operation(crs_id, self.at_block.crs_id, position)
        if str_error:
            str_error = ('In GCP: {}\n{}\nError in CRSs operation:\n{}'.
                         format(self.label, str_error))
            return str_error
        self.position = np.array(position[0])
        self.position_crs_source = position
        if self.at_block.crs_id != self.at_block.crs_ecef_id:
            position_ecef = [self.position.tolist()]
            str_error = self.crs_tools.operation(self.at_block.crs_id, self.at_block.crs_ecef_id, position_ecef)
            if str_error:
                str_error = ('In GCP: {}\nError in CRSs operation:\n{}'.
                             format(self.label, str_error))
                return str_error
            self.position_ecef = np.array(position_ecef[0])
        else:
            self.position_ecef = np.array(self.position.tolist())
        if self.at_block.crs_id != self.at_block.crs_geo3d_id:
            position_geo3d = [self.position.tolist()]
            str_error = self.crs_tools.operation(self.at_block.crs_id, self.at_block.crs_geo3d_id, position_geo3d)
            if str_error:
                str_error = ('In GCP: {}\nError in CRSs operation:\n{}'.
                             format(self.label, str_error))
                return str_error
            self.position_geo3d = np.array(position_geo3d[0])
        else:
            self.position_geo3d = np.array(self.position.tolist())
        position_enu = [self.position.tolist()]
        str_error = self.crs_tools.operation(self.at_block.crs_id, self.at_block.crs_enu_id, position_enu)
        if str_error:
            str_error = ('In GCP: {}\nError in CRSs operation:\n{}'.
                         format(self.label, str_error))
            return str_error
        self.position_enu = np.array(position_enu[0])
        self.enabled = True
        return str_error
