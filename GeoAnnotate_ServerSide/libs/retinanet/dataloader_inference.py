from __future__ import print_function, division

import pickle
import sys
import os
import torch
import numpy as np
import random
import csv

from torch.utils.data import Dataset as torchDataset
from torchvision import transforms, utils
from torch.utils.data.sampler import Sampler

import skimage.io
import skimage.transform
import skimage.color
import skimage
import cv2
import imgaug.augmenters as iaa
import threading
from sklearn.utils import shuffle
from libs.sat_service_defs import *
from libs.u_interpolate import *
from libs.scaling import *





class threadsafe_iter:
    """
    Takes an iterator/generator and makes it thread-safe by
    serializing call to the `next` method of given iterator/generator.
    """
    def __init__(self, it):
        self.it = it
        self.lock = threading.Lock()

    def __iter__(self):
        return self

    def __next__(self):
        with self.lock:
            return next(self.it)


def get_objects_i_generator(objects_count):
    """Cyclic generator of paths indices
    """
    current_objects_id = 0
    while True:
        yield current_objects_id
        current_objects_id = (current_objects_id + 1) % objects_count




class InferenceDataset(torchDataset):
    """CSV dataset."""

    def __init__(self, fnames_list_pickle_file = None, class_list = '', caches_path = '', transform=None):
        self.fnames_list_pickle_file = fnames_list_pickle_file
        self.class_list = class_list
        self.caches_path = caches_path
        self.transform = transform

        #region load classes file
        try:
            with open(self.class_list, 'r', newline='') as file:
                self.classes = self.load_classes(csv.reader(file, delimiter=','))
        except ValueError as e:
            raise (ValueError('invalid CSV class file: {}: {}'.format(self.class_list, e)))

        self.labels = {}
        for key, value in self.classes.items():
            self.labels[value] = key
        #endregion

        #region read files list
        try:
            with open(self.fnames_list_pickle_file, 'rb') as f:
                self.image_names = pickle.load(f)
        except ValueError as e:
            raise (ValueError('could not open files list: {}: {}'.format(self.fnames_list_pickle_file, e)))
        #endregion

        #region read cached constants and masks
        print('loading pre-calculated interpolation constants...')
        self.interpolation_constants = dict()
        for sat_label in ['MSG1', 'MSG2', 'MSG3', 'MSG4']:
            fname = os.path.join(self.caches_path, 'interpolation_constants_%s.pkl' % sat_label)
            with open(fname, 'rb') as f:
                interpolation_constants_dict = pickle.load(f)
            self.interpolation_constants[sat_label] = interpolation_constants_dict

        print('loading pre-calculated shared_masks...')
        self.shared_masks = dict()
        for sat_label in ['MSG1', 'MSG2', 'MSG3', 'MSG4']:
            fname = os.path.join(self.caches_path, 'shared_mask_%s.npy' % sat_label)
            self.shared_masks[sat_label] = np.load(fname)
        #endregion


    def nc2ndarray(self, nc_fname):
        data_lats, data_lons, ch5, ch9, btd, sat_label, dt_str = read_ncfile_data(nc_fname)
        # data_lats, data_lons = np.array(data_lats), np.array(data_lons)

        interpolation_inds = self.interpolation_constants[sat_label]['interpolation_inds']
        interpolation_wghts = self.interpolation_constants[sat_label]['interpolation_wghts']
        interpolation_shape = self.interpolation_constants[sat_label]['interpolation_shape']
        # lats_proj = self.interpolation_constants[sat_label]['lats_proj']
        # lons_proj = self.interpolation_constants[sat_label]['lons_proj']
        shared_mask = self.shared_masks[sat_label]

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

        gray_mask = (ch9_interpolated_ma>=norm_constants.ch9_thresh) & (ch5_interpolated_ma>=norm_constants.ch5_thresh)
        gray_mask = gray_mask & (btd_interpolated_ma<=norm_constants.btd_thresh)
        channels = [ch9_interpolated_ma_normed[..., np.newaxis], btd_interpolated_ma_normed[..., np.newaxis], ch5_interpolated_ma_normed[..., np.newaxis]]
        scaled_image = np.concatenate(channels, axis=-1)
        scaled_image = (scaled_image*255).astype(np.uint8)
        scaled_image_highlighted = scaled_image * (1-gray_mask)[...,np.newaxis] + cv2.cvtColor(cv2.cvtColor(scaled_image, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB) * gray_mask[...,np.newaxis]
        scaled_image_highlighted[shared_mask,:] = 0

        scaled_image_highlighted = np.array(scaled_image_highlighted)

        return scaled_image_highlighted


    def _parse(self, value, function, fmt):
        try:
            return function(value)
        except ValueError as e:
            raise ValueError(fmt.format(e)) from None


    def load_classes(self, csv_reader):
        result = {}

        for line, row in enumerate(csv_reader):
            line += 1

            try:
                class_name, class_id = row
            except ValueError:
                raise (ValueError('line {}: format should be \'class_name,class_id\''.format(line)))
            class_id = self._parse(class_id, int, 'line {}: malformed class ID: {{}}'.format(line))

            if class_name in result:
                raise ValueError('line {}: duplicate class name: \'{}\''.format(line, class_name))
            result[class_name] = class_id
        return result


    def __len__(self):
        return len(self.image_names)



    def __getitem__(self, idx):
        img, nc_fname = self.load_image(idx)
        sample = {'img': img, 'nc_fname': nc_fname}
        if self.transform:
            sample = self.transform(sample)

        return sample

    def load_image(self, image_index):
        img = self.nc2ndarray(self.image_names[image_index])
        return (img.astype(np.float32) / 255.0), self.image_names[image_index]


    def name_to_label(self, name):
        return self.classes[name]

    def label_to_name(self, label):
        return self.labels[label]

    def num_classes(self):
        return max(self.classes.values()) + 1

    def image_aspect_ratio(self, image_index):
        arr = self.nc2ndarray(self.image_names[image_index])
        return float(arr.shape[1]) / float(arr.shape[0])



def collater(data):

    imgs = [s['img'] for s in data]
    nc_fnames = [s['nc_fname'] for s in data]
    try:
        scales = [s['scale'] for s in data]
    except:
        scales = [1.0 for s in data]
        
    widths = [int(s.shape[0]) for s in imgs]
    heights = [int(s.shape[1]) for s in imgs]
    batch_size = len(imgs)

    max_width = np.array(widths).max()
    max_height = np.array(heights).max()

    padded_imgs = torch.zeros(batch_size, max_width, max_height, 3)

    for i in range(batch_size):
        img = imgs[i]
        padded_imgs[i, :int(img.shape[0]), :int(img.shape[1]), :] = img if isinstance(img, torch.Tensor) else torch.from_numpy(img)

    padded_imgs = padded_imgs.permute(0, 3, 1, 2)

    return {'img': padded_imgs, 'scale': scales, 'nc_fnames': nc_fnames}


class Resizer(object):
    """Convert ndarrays in sample to Tensors."""

    def __init__(self, min_side=512, max_side=1024):
        self.min_side = min_side
        self.max_side = max_side

    def __call__(self, sample):
        image = sample['img']
        nc_fname = sample['nc_fname']

        rows, cols, cns = image.shape

        smallest_side = min(rows, cols)

        # rescale the image so the smallest side is min_side
        scale = self.min_side / smallest_side
        if scale < 1.0:
            scale = 1.0

        # check if the largest side is now greater than max_side, which can happen
        # when images have a large aspect ratio
        largest_side = max(rows, cols)

        if largest_side * scale > self.max_side:
            scale = self.max_side / largest_side

        # resize the image with the computed scale
        if (abs(scale-1.0) > 1e-6 ):
            image = skimage.transform.resize(image, (int(round(rows * scale)), int(round((cols * scale)))))
        rows, cols, cns = image.shape

        pad_w = (32 - rows % 32) if (rows % 32 > 0) else 0
        pad_h = (32 - cols % 32)  if (cols % 32 > 0) else 0

        new_image = np.zeros((rows + pad_w, cols + pad_h, cns)).astype(np.float32)
        new_image[:rows, :cols, :] = image.astype(np.float32)

        return {'img': torch.from_numpy(new_image), 'scale': scale, 'nc_fname': nc_fname}


class Augmenter(object):
    """Convert ndarrays in sample to Tensors."""

    def __call__(self, sample, flip_x=0.5):

        if np.random.rand() < flip_x:
            image = sample['img']
            nc_fname = sample['nc_fname']
            image = image[:, ::-1, :]

            rows, cols, channels = image.shape

            sample = {'img': image, 'nc_fname': nc_fname}

        return sample


class Normalizer(object):

    def __init__(self):
        self.mean = np.array([[[0.485, 0.456, 0.406]]])
        self.std = np.array([[[0.229, 0.224, 0.225]]])

    def __call__(self, sample):

        image = sample['img']
        nc_fname = sample['nc_fname']

        return {'img':((image.astype(np.float32)-self.mean)/self.std), 'nc_fname': nc_fname}


class UnNormalizer(object):
    def __init__(self, mean=None, std=None):
        if mean == None:
            self.mean = [0.485, 0.456, 0.406]
        else:
            self.mean = mean
        if std == None:
            self.std = [0.229, 0.224, 0.225]
        else:
            self.std = std

    def __call__(self, tensor):
        """
        Args:
            tensor (Tensor): Tensor image of size (C, H, W) to be normalized.
        Returns:
            Tensor: Normalized image.
        """
        for t, m, s in zip(tensor, self.mean, self.std):
            t.mul_(s).add_(m)
        return tensor


class AspectRatioBasedSampler(Sampler):

    def __init__(self, data_source, batch_size, drop_last):
        self.data_source = data_source
        self.batch_size = batch_size
        self.drop_last = drop_last
        self.groups = self.group_images()

    def __iter__(self):
        random.shuffle(self.groups)
        for group in self.groups:
            yield group

    def __len__(self):
        if self.drop_last:
            return len(self.data_source) // self.batch_size
        else:
            return (len(self.data_source) + self.batch_size - 1) // self.batch_size

    def group_images(self):
        # determine the order of the images
        order = list(range(len(self.data_source)))
        order.sort(key=lambda x: self.data_source.image_aspect_ratio(x))

        # divide into groups, one group = one batch
        return [[order[x % len(order)] for x in range(i, i + self.batch_size)] for i in range(0, len(order), self.batch_size)]
