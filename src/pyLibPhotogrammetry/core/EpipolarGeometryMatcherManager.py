# authors:
# David Hernandez Lopez, david.hernandez@uclm.es
from math import floor, ceil
import numpy as np
import cv2

import os, sys
from datetime import datetime
import psutil

from ..defs import defs_project as defs_project
from ..defs import defs_processes
from ..defs import defs_images as defs_img
#from ..core.ProjectPhotogrammetry import ProjectPhotogrammetry
from ..core.ATBlockMetashape import ATBlockMetashape
from ..core.ATBlockGraphos import ATBlockGraphos

class EpipolarGeometryMatcherManager():
    def __init__(self, project):
        self.project = project
        self.tile_size = -1
        self.tile_x = -1
        self.tile_y = -1
        self.load_image_by_id = {}

    def load_tile_in_memory(self, tile_size, tile_x, tile_y):
        str_error = ''
        loaded_tile = False
        if tile_size == self.tile_size:
            if tile_x == self.tile_x and tile_y == self.tile_y:
                loaded_tile = True
                return str_error, loaded_tile
        if (not tile_size in self.project.imagesTilesImagesIdBySize
                or not tile_size in self.project.imagesMaximumRamMBsBySize
                or not tile_size in self.project.imagesTileRamMBsBySize):
            str_error = "EpipolarGeometryMatcherManager.load_tile_in_memory"
            str_error += ("Not exists tile size: {}".format(str(tile_size)))
            return str_error, loaded_tile
        # not tile in container but not an error
        if (not tile_x in self.project.imagesTilesImagesIdBySize[tile_size]
                or not tile_x in self.project.imagesTileRamMBsBySize[tile_size]):
            return str_error, loaded_tile
        if (not tile_y in self.project.imagesTilesImagesIdBySize[tile_size][tile_x]
                or not tile_y in self.project.imagesTileRamMBsBySize[tile_size][tile_x]):
            return str_error, loaded_tile
        images_to_load = self.project.imagesTilesImagesIdBySize[tile_size][tile_x][tile_y]
        for image_loaded_id in self.load_image_by_id:
            if not image_loaded_id in images_to_load:
                self.load_image_by_id.pop(image_loaded_id)
        if len(self.project.at_block_by_label) != 1:
            str_error = "EpipolarGeometryMatcherManager.load_tile_in_memory"
            str_error += ("Valid only for project with one ATBlock")
            return str_error, loaded_tile
        at_block_label = next(iter(self.project.at_block_by_label))
        at_block = self.project.at_block_by_label[at_block_label]
        for camera_id in at_block.camera_by_id:
            if camera_id in self.load_image_by_id:
                continue
            camera = at_block.camera_by_id[camera_id]
            camera_enabled = camera.get_enabled()  # multisensor ...
            undistorted_image_file_name = camera.undistort_image_file_path
            if undistorted_image_file_name is not None:
                if os.path.exists(undistorted_image_file_name):
                    img = cv2.imread(undistorted_image_file_name, cv2.IMREAD_IGNORE_ORIENTATION | cv2.IMREAD_GRAYSCALE)
                    if img is None:
                        str_error = "EpipolarGeometryMatcherManager.load_tile_in_memory"
                        str_error += ("\nError opening image:\n{}".format(undistorted_image_file_name))
                        return str_error, loaded_tile
                    self.load_image_by_id[camera_id] = img
        if len(self.load_image_by_id) > 0:
            self.tile_size = tile_size
            self.tile_x = tile_x
            self.tile_y = tile_y
            loaded_tile = True
        return str_error, loaded_tile
