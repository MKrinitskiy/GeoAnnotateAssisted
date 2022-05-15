import os, cv2, hashlib, json, re, traceback, fnmatch, datetime, pathlib

import numpy as np
from netCDF4 import Dataset
from .sat_operations import *
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
import sys
from xml import etree
from .u_interpolate import interpolate_data
from .scaling import *
from .sat_values import *


def orthodrome(pt1, pt2):
    return np.sqrt(np.sum(((pt2-pt1)*(np.asarray([np.cos(np.pi*pt1[1]/180), 1.])) * 111.3)**2))



def read_ncfile_data(fname):
    with Dataset(fname, 'r') as ds:
        sat_label, dt_str = infer_ncfile_info_from_fname(fname)
        sat_constants = sat_values(sat_label)

        lats = ds.variables['lat'][:]
        lons = ds.variables['lon'][:]
        mask = lats.mask

        ch5 = ds.variables['ch5'][:]
        ch5.mask = mask
        ch5 = t_brightness_calculate(ch5, sat_constants, 'ch5')

        ch9 = ds.variables['ch9'][:]
        ch9.mask = mask
        ch9 = t_brightness_calculate(ch9, sat_constants, 'ch9')

        btd = ch5 - ch9
        btd.mask = mask
        btd.mask[btd > 50.] = True
    return lats, lons, ch5, ch9, btd, sat_label, dt_str



def read_ncfile_latlons(fname):
    with Dataset(fname, 'r') as ds:
        sat_label, dt_str = infer_ncfile_info_from_fname(fname)

        lats = ds.variables['lat'][:]
        lons = ds.variables['lon'][:]
    return lats, lons, sat_label, dt_str


def infer_ncfile_info_from_fname(fname):
    with Dataset(fname, 'r') as ds:
        wmo_filname = ds.wmo_filename
        reex = '.+(MSG\d).+(\d{14})\.nc'
        match = re.match(reex, wmo_filname)
        sat_label = match.groups()[0]
        dt_str = match.groups()[1]

    return sat_label, dt_str



def point_inside_contour(contour, point):
    return bool(cv2.pointPolygonTest(contour, point, False)==1.)


def dict_hash(dict_to_hash):
    hashvalue = hashlib.sha256(json.dumps(dict_to_hash, sort_keys=True).encode())
    return hashvalue.hexdigest()



def xy2latlon(xypoint, lats_proj, lons_proj):
    # x: float, columns-related thus dim-1
    # y: float, rows-related thus dim-0
    xypoint = np.squeeze(np.array(xypoint))
    xi = int(np.round(xypoint[0]))
    yi = int(np.round(xypoint[1]))
    return np.array([lats_proj[yi, xi], lons_proj[yi, xi]])


def closest_xypoint(latlonpoint, lats_proj, lons_proj):
    dlat = lats_proj - latlonpoint[1]
    dlon = lons_proj - latlonpoint[0]
    darc_sqr = dlat ** 2 + dlon ** 2
    closest_pt_idx = np.unravel_index(np.argmin(darc_sqr), darc_sqr.shape)  # row and column indices!
    closest_pt_y = closest_pt_idx[0]  # row number - so y value
    closest_pt_x = closest_pt_idx[1]  # column number - so x value
    return np.array([closest_pt_x, closest_pt_y])

def intersection_area(img_with_ellipse, contour):
    cont_image = cv2.drawContours(np.zeros_like(img_with_ellipse, dtype=np.uint8), [contour], 0, 255, -1)
    intersection = cv2.bitwise_and(cont_image, img_with_ellipse)
    return (intersection / 255).sum()



#region rectangles operations
# rectangle is: x,y,w,h
# x,y - coordinates of the lower-left corner
# w - width (pixels)
# h - height (pixels)
def rect_union(a,b):
    # rects here in x,y,w,h format!

    x = min(a[0], b[0])
    y = min(a[1], b[1])
    w = max(a[0]+a[2], b[0]+b[2]) - x
    h = max(a[1]+a[3], b[1]+b[3]) - y
    return (x, y, w, h)

def rect_intersection(a,b):
    # rects here in x,y,w,h format!

    x = max(a[0], b[0])
    y = max(a[1], b[1])
    w = min(a[0]+a[2], b[0]+b[2]) - x
    h = min(a[1]+a[3], b[1]+b[3]) - y
    if w<0 or h<0: return None # or (0,0,0,0) ?
    return (x, y, w, h)


def check_if_intersects(rect1, rect2):
    # rects here in x,y,w,h format!
    return (rect_intersection(rect1, rect2) is not None)

def check_if_none_intersects(test_rect, other_rects):
    # rects here in x,y,w,h format!

    for rect in other_rects:
        if check_if_intersects(test_rect, rect):
            return False
    return True

def CheckIfNoneOfLabelsBreaks(labelsBBoxes, subimgRect):
    # bboxes here in x,y,w,h format!

    final = True
    for labelBBox in labelsBBoxes:
        # check if there is no partial intersection - either subRect is completely inside or completely outside the MSCsRects
        final = final & ((rect_intersection(labelBBox, subimgRect) == labelBBox) | (
                    rect_intersection(labelBBox, subimgRect) is None))
        if not final:
            break
    return final


def CheckIfAtLeastOneLabelRect(LabelsRects, subimgRect):
    #rects here in x,y,w,h format!

    final = False
    for labelRect in LabelsRects:
        final = final | (rect_intersection(labelRect, subimgRect) == labelRect)
        if final:
            break
    return final


def cut_sample_bboxes(labels_outer_bboxes, orig_img_size=(1716, 2168), sample_size=(512, 512), samples_per_snapshot=1):
    #bboxes and rects here in x,y,w,h format!

    selected_rects = []

    for smpl_idx in range(samples_per_snapshot):
        accepted = False
        while not accepted:
            tl_x = np.random.randint(0, orig_img_size[1] - sample_size[1])
            tl_y = np.random.randint(0, orig_img_size[0] - sample_size[0])
            subimg_rect = (tl_x, tl_y, sample_size[0], sample_size[1])

            accepted = CheckIfNoneOfLabelsBreaks(labels_outer_bboxes, subimg_rect) & CheckIfAtLeastOneLabelRect(
                labels_outer_bboxes, subimg_rect)

        selected_rects.append(subimg_rect)

    return selected_rects


#endregion rectangles operations


def prime_factors(n):
    """Returns all the prime factors of a positive integer"""
    factors = []
    d = 2
    while n > 1:
        while n % d == 0:
            factors.append(d)
            n /= d
        d = d + 1

    return factors


def uniques(items):
    unique = []
    for value in items:
        if value not in unique:
            unique.append(value)
    return unique


def nc2ndarray(nc_fname: str, interpolation_constants: dict, shared_masks: dict, return_source_data = False):
    data_lats, data_lons, ch5, ch9, btd, sat_label, dt_str = read_ncfile_data(nc_fname)
    data_lats, data_lons = np.array(data_lats), np.array(data_lons)

    interpolation_inds = interpolation_constants[sat_label]['interpolation_inds']
    interpolation_wghts = interpolation_constants[sat_label]['interpolation_wghts']
    interpolation_shape = interpolation_constants[sat_label]['interpolation_shape']
    lats_proj = interpolation_constants[sat_label]['lats_proj']
    lons_proj = interpolation_constants[sat_label]['lons_proj']
    shared_mask = shared_masks[sat_label]

    ch5_interpolated = interpolate_data(ch5, interpolation_inds, interpolation_wghts, interpolation_shape)
    ch5_interpolated_ma = np.ma.asarray(ch5_interpolated)
    ch5_interpolated_ma.mask = shared_mask
    ch5_interpolated_ma.data[np.isnan(ch5_interpolated)] = 0.
    ch5_interpolated_ma.mask[np.isnan(ch5_interpolated)] = True
    ch5_interpolated_ma_normed = scale_ch5(ch5_interpolated_ma)

    ch9_interpolated = interpolate_data(ch9, interpolation_inds, interpolation_wghts, interpolation_shape)
    ch9_interpolated_ma = np.ma.asarray(ch9_interpolated)
    ch9_interpolated_ma.mask = shared_mask
    ch9_interpolated_ma.data[np.isnan(ch9_interpolated)] = 0.
    ch9_interpolated_ma.mask[np.isnan(ch9_interpolated)] = True
    ch9_interpolated_ma_normed = scale_ch9(ch9_interpolated_ma)

    btd_interpolated = interpolate_data(btd, interpolation_inds, interpolation_wghts, interpolation_shape)
    btd_interpolated_ma = np.ma.asarray(btd_interpolated)
    btd_interpolated_ma.mask = shared_mask
    btd_interpolated_ma.data[np.isnan(btd_interpolated)] = 0.
    btd_interpolated_ma.mask[np.isnan(btd_interpolated)] = True
    btd_interpolated_ma_normed = scale_btd(btd_interpolated_ma)

    gray_mask = (ch9_interpolated_ma >= norm_constants.ch9_thresh) & (ch5_interpolated_ma >= norm_constants.ch5_thresh)
    gray_mask = gray_mask & (btd_interpolated_ma <= norm_constants.btd_thresh)
    channels = [ch9_interpolated_ma_normed[..., np.newaxis], btd_interpolated_ma_normed[..., np.newaxis],
                ch5_interpolated_ma_normed[..., np.newaxis]]
    scaled_image = np.concatenate(channels, axis=-1)
    scaled_image = (scaled_image * 255).astype(np.uint8)
    scaled_image_highlighted = scaled_image * (1 - gray_mask)[..., np.newaxis] + cv2.cvtColor(
        cv2.cvtColor(scaled_image, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB) * gray_mask[..., np.newaxis]
    scaled_image_highlighted[shared_mask, :] = 0

    if return_source_data:
        return scaled_image_highlighted, ch5_interpolated_ma_normed, ch9_interpolated_ma_normed, btd_interpolated_ma_normed, data_lons, data_lats, sat_label, dt_str
    else:
        return scaled_image_highlighted, sat_label, dt_str