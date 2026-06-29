# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import os
import sys
import math
import numpy as np
import quaternion
import copy

def concatenate_quaternions(first_quaternion_as_vector, second_quaternion_as_vector):
    normalized_qvec1 = normalize_quaternion(first_quaternion_as_vector)
    normalized_qvec2 = normalize_quaternion(second_quaternion_as_vector)
    quat1 = np.quaternion(normalized_qvec1[0], normalized_qvec1[1], normalized_qvec1[2], normalized_qvec1[3])
    quat2 = np.quaternion(normalized_qvec2[0], normalized_qvec2[1], normalized_qvec2[2], normalized_qvec2[3])
    concatenated_quaternion = quat2 * quat1
    output_as_vector = np.zeros(4)
    output_as_vector[0] = concatenated_quaternion.w
    output_as_vector[1] = concatenated_quaternion.x
    output_as_vector[2] = concatenated_quaternion.y
    output_as_vector[3] = concatenated_quaternion.z
    return output_as_vector

def invert_quaternion(input_quaternion_as_vector):
    output_quaternion_as_vector = copy.deepcopy(input_quaternion_as_vector)
    for i in range(1,4):
        output_quaternion_as_vector[i] = -1. * output_quaternion_as_vector[i]
    return output_quaternion_as_vector

def normalize_quaternion(input_quaternion_as_vector):
    output_quaternion_as_vector = copy.deepcopy(input_quaternion_as_vector)
    norm = np.linalg.norm(output_quaternion_as_vector)
    if norm == 0.0:
        output_quaternion_as_vector[0] = 1.
    else:
        output_quaternion_as_vector /= norm
    return output_quaternion_as_vector / np.linalg.norm(output_quaternion_as_vector)

def quaternion_rotate_point(input_quaternion_as_vector, input_point):
    normalized_qvec = normalize_quaternion(input_quaternion_as_vector)
    quat = np.quaternion(normalized_qvec[0], normalized_qvec[1], normalized_qvec[2], normalized_qvec[3])
    point = np.quaternion(0, input_point[0], input_point[1], input_point[2])
    rotated_point = quat * point * quat.conjugate()
    output_point = np.zeros(3)
    output_point[0] = rotated_point.x
    output_point[1] = rotated_point.y
    output_point[2] = rotated_point.z
    return output_point
