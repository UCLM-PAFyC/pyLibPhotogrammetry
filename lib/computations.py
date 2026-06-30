# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import os
import sys
import math
import numpy as np
import quaternion
import copy

FLOAT_EPS = np.finfo(float).eps

def angle_axis2mat(theta, vector, is_normalized=False):
    x, y, z = vector
    if not is_normalized:
        n = math.sqrt(x * x + y * y + z * z)
        x = x / n
        y = y / n
        z = z / n
    c, s = math.cos(theta), math.sin(theta)
    C = 1 - c
    xs, ys, zs = x * s, y * s, z * s
    xC, yC, zC = x * C, y * C, z * C
    xyC, yzC, zxC = x * yC, y * zC, z * xC
    return np.array(
        [
            [x * xC + c, xyC - zs, zxC + ys],
            [xyC + zs, y * yC + c, yzC - xs],
            [zxC - ys, yzC + xs, z * zC + c],
        ]
    )

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

def rectify_stereo_cameras(K1, K2, qvec, tvec):
    # help: https://github.com/nipy/nibabel/blob/master/nibabel/quaternions.py#L36
    H1 = None
    H2 = None
    Q = None
    angle = 0.0
    axis = np.array([1.0, 0, 0])
    w, x, y, z = qvec
    vec = np.asarray([x, y, z])
    n = math.sqrt(x * x + y * y + z * z)
    try:
        identity_thresh = np.finfo(vec.dtype).eps * 3.
    except ValueError:  # integer type
        identity_thresh = FLOAT_EPS * 3
    if n >= identity_thresh:
        angle = 2. * math.atan2(n, abs(w))
        axis = vec / n
    angle *= -0.5
    R2 = angle_axis2mat(angle, vec)
    R1 = R2
    R1 = np.transpose(R1)
    t = np.dot(R2, tvec)
    x_unit_vector = np.array([1.0, 0, 0])
    if np.inner(t, x_unit_vector) < 0.:
        x_unit_vector *= -1.
    rotation_axis = np.cross(t, x_unit_vector)
    R_x = np.identity(3, dtype=float)
    if np.linalg.norm(rotation_axis) >= identity_thresh:
        angle = math.acos(abs(np.inner(t, x_unit_vector) ) / (np.linalg.norm(t) * 1.0))
        # angle = math.acos(abs(np.inner(t, x_unit_vector) ) / (np.linalg.norm(t) * np.linalg.norm(x_unit_vector)))
        R_x = angle_axis2mat(angle, rotation_axis/np.linalg.norm(rotation_axis))
    R1 = np.dot(R_x, R1)
    R2 = np.dot(R_x, R2)
    t = np.dot(R_x, t)
    K = np.identity(3, dtype=float)
    camera1MeanFocalLength = (K1[0,0] + K1[1, 1]) / 2.
    camera2MeanFocalLength = (K2[0,0] + K2[1, 1]) / 2.
    camera1PrincipalPointX=K1[0,2]
    camera1PrincipalPointY=K1[1,2]
    camera2PrincipalPointX=K2[0,2]
    camera2PrincipalPointY=K2[1,2]
    min_focal = camera1MeanFocalLength
    if camera2MeanFocalLength < min_focal:
        min_focal = camera2MeanFocalLength
    K[0, 0] = min_focal
    K[1, 1] = K[0, 0]
    K[0, 2] = camera1PrincipalPointX
    K[1, 2] = (camera1PrincipalPointY + camera2PrincipalPointY) / 2.
    H1 = np.dot(R1, np.linalg.inv(K1))
    H1 = np.dot(K, H1)
    H2 = np.dot(R2, np.linalg.inv(K2))
    H2 = np.dot(K, H2)
    Q = np.identity(4, dtype=float)
    Q[3, 0] = -K[1, 2]
    Q[3, 1] = -K[0, 2]
    Q[3, 2] = K[0, 0]
    Q[2, 3] = -1 / t[0]
    Q[3, 3] = 0
    return H1, H2, Q
