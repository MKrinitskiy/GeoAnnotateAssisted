from __future__ import print_function, division
import sys
import os
import torch
import numpy as np
import random
import csv

from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, utils
from torch.utils.data.sampler import Sampler
from pycocotools.coco import COCO

import skimage.io
import skimage.transform
import skimage.color
import skimage
import cv2
import imgaug.augmenters as iaa
from imgaug.augmentables.segmaps import SegmentationMapsOnImage
import threading
from sklearn.utils import shuffle


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


class CSVEllipseDataset_threaded(Dataset):
    def __init__(self, train_file, class_list, batch_size=1, shuffle=True, transform=None, augment = False, crops_per_snapshot = 8, crop_size = (512,512), debug=False):

        self.train_file = train_file
        self.class_list = class_list
        self.transform = transform

        #region parse the provided class file
        try:
            with open(self.class_list, 'r', newline='') as file:
                self.classes = self.load_classes(csv.reader(file, delimiter=','))
        except ValueError as e:
            raise (ValueError('invalid CSV class file: {}: {}'.format(self.class_list, e)))

        self.labels = {}
        for key, value in self.classes.items():
            self.labels[value] = key
        #endregion

        #region parse annotations csv file
        # lines should be of format "img_path, x1, y1, x2, y2, x3, y3, class_name"
        try:
            with open(self.train_file, 'r', newline='') as file:
                self.image_data = self._read_annotations(csv.reader(file, delimiter=','), self.classes)
        except ValueError as e:
            raise (ValueError('invalid CSV annotations file: {}: {}'.format(self.train_file, e)))
        #endregion

        self.image_names = list(self.image_data.keys())
        self.obj_indices = np.arange(len(self.image_names))

        self.batch_size = batch_size
        self.shuffle = shuffle
        self.augment = augment
        self.debug = debug
        self.lock = threading.Lock()  # mutex for input path
        self.yield_lock = threading.Lock()  # mutex for generator yielding of batch
        self.init_count = 0
        self.objects_id_generator = threadsafe_iter(get_objects_i_generator(len(self.image_names)))
        self.crops_per_snapshot = crops_per_snapshot
        self.crop_size = crop_size
        self.cache = {}

        if self.augment:
            self.seq = iaa.Sequential([iaa.Fliplr(0.5),
                                       iaa.Flipud(0.5),
                                       iaa.GaussianBlur(sigma=(0, 5)),
                                       iaa.Affine(rotate=(-180, 180),
                                                  translate_percent={'x': (-0.1, 0.1), 'y': (-0.1, 0.1)},
                                                  shear={'x': (-15, 15), 'y': (-15, 15)})],
                                      random_order=True)
            self.crop = iaa.CropToFixedSize(self.crop_size[0], self.crop_size[1])
            self.crop_augmentations = iaa.Sequential([iaa.Cutout(nb_iterations=(1, 3), size=0.3, squared=False, cval=0),
                                                      iaa.CoarseDropout((0.0, 0.05), size_percent=(0.02, 0.25))],
                                                     random_order=True)
        else:
            self.seq = iaa.Identity()

    def _parse(self, value, function, fmt):
        """
        Parse a string into a value, and format a nice ValueError if it fails.
        Returns `function(value)`.
        Any `ValueError` raised is catched and a new `ValueError` is raised
        with message `fmt.format(e)`, where `e` is the caught `ValueError`.
        """
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
        l = len(self.image_names) / (self.batch_size/self.crops_per_snapshot)
        if ((l - int(l)) > 0.0):
            l = int(l) + 1
        return int(l)

    def __iter__(self):
        while True:
            with self.lock:
                if (self.init_count == 0):
                    if self.shuffle:
                        self.shuffle_data()
                    self.samples = []
                    self.init_count = 1

            for idx in self.objects_id_generator:
                img = self.load_image(self.obj_indices[idx])

                # annot = self.load_annotations(self.obj_indices[idx], img)
                #region load annotations and augment them along with the image
                annotation_list = self.image_data[self.image_names[self.obj_indices[idx]]]

                if len(annotation_list) > 0:
                    ellipse_img = np.zeros(img.shape[:2], dtype=np.uint8)
                    for annotation_idx, a in enumerate(annotation_list):
                        # some annotations have basically no width / height, skip them
                        pt0_x = a['x1']
                        pt1_x = a['x2']
                        pt2_x = a['x3']
                        pt0_y = a['y1']
                        pt1_y = a['y2']
                        pt2_y = a['y3']

                        # plot the ellipse to get bbox
                        p0 = np.array([pt0_x, pt0_y])
                        p1 = np.array([pt1_x, pt1_y])
                        p2 = np.array([pt2_x, pt2_y])
                        pc = 0.5 * (p0 + p1)
                        v01 = p1 - p0
                        vc2 = p2 - pc
                        a = np.linalg.norm(v01) / 2
                        b = np.sqrt((vc2[1] ** 2) / (1 - (vc2[0] / a) ** 2))
                        ang = np.arccos((v01 / np.linalg.norm(v01))[0]) * 180 / np.pi
                        ang = ang * np.sign(v01[1])

                        ellipse_img = cv2.ellipse(ellipse_img,
                                                  (int(pc[0]), int(pc[1])),
                                                  (int(a), int(b)), ang, 0, 360, annotation_idx+1, -1)

                    segmap = SegmentationMapsOnImage(ellipse_img, shape=img.shape)
                    if self.debug:
                        img_mesh = np.zeros_like(img)
                        for x in np.linspace(0, img_mesh.shape[1]-1, 20, endpoint=True):
                            img_mesh[:,int(x),:] = 255
                        for y in np.linspace(0, img_mesh.shape[0]-1, 20, endpoint=True):
                            img_mesh[int(y), :, :] = 255
                        img = img+img_mesh
                        img = np.clip(img, 0, 255)

                    img, segmaps_aug = self.seq(image=img, segmentation_maps=segmap)
                    for crop_index in range(self.crops_per_snapshot):
                        annotations = np.zeros((0, 5))

                        img_crop, segmaps_crop = self.crop(image=img, segmentation_maps=segmaps_aug)
                        img_crop, segmaps_crop = self.crop_augmentations(image = img_crop, segmentation_maps = segmaps_crop)
                        segmaps_crop_arr = np.squeeze(segmaps_crop.arr)
                        segmaps_crop_arr[img_crop[:,:,0]==0] = 0

                        for annotation_idx, a in enumerate(annotation_list):
                            curr_annotation_segmap = (segmaps_crop_arr == (annotation_idx+1)).astype(np.uint8)*255
                            if curr_annotation_segmap.sum() > 0:
                                bbox = cv2.boundingRect(curr_annotation_segmap)  # x,y,w,h
                                x, y, w, h = bbox
                                annotation = np.zeros((1, 5))
                                annotation[0, 0] = x
                                annotation[0, 1] = y
                                annotation[0, 2] = x + w
                                annotation[0, 3] = y + h
                                annotation[0, 4] = self.name_to_label(a['class'])
                                annotations = np.append(annotations, annotation, axis=0)
                        sample = {'img': img_crop, 'annot': annotations}
                #endregion

                        if self.transform:
                            sample = self.transform(sample)

                        with self.yield_lock:
                            if (len(self.samples)) < self.batch_size:
                                self.samples.append(sample)
                            if len(self.samples) % self.batch_size == 0:
                                samples = collater(self.samples)
                                yield samples
                                self.samples = []

            with self.lock:
                self.init_count = 0
                if self.shuffle:
                    self.landmarks_frame = shuffle(self.landmarks_frame)

    def shuffle_data(self):
        self.obj_indices = shuffle(self.obj_indices)


    def load_image(self, image_index):
        if self.image_names[image_index] in self.cache:
            img = self.cache[self.image_names[image_index]]
        else:
            img = np.load(self.image_names[image_index])
            self.cache[self.image_names[image_index]] = img

        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

        return img.astype(np.float32) / 255.0


    def _read_annotations(self, csv_reader, classes):
        result = {}
        for line, row in enumerate(csv_reader):
            line += 1

            try:
                img_file, x1, y1, x2, y2, x3, y3, class_name = row[:8]
            except ValueError:
                raise ValueError('line {}: format should be \'img_file,x1,y1,x2,y2,x3,y3,class_name\' or \'img_file,,,,,\''.format(line)) from None

            if img_file not in result:
                result[img_file] = []

            # If a row contains only an image path, it's an image without annotations.
            if (x1, y1, x2, y2, x3, y3, class_name) == ('', '', '', '', '', '', 'mcc'):
                continue

            x1 = self._parse(x1, int, 'line {}: malformed x1: {{}}'.format(line))
            y1 = self._parse(y1, int, 'line {}: malformed y1: {{}}'.format(line))
            x2 = self._parse(x2, int, 'line {}: malformed x2: {{}}'.format(line))
            y2 = self._parse(y2, int, 'line {}: malformed y2: {{}}'.format(line))
            x3 = self._parse(x3, int, 'line {}: malformed x2: {{}}'.format(line))
            y3 = self._parse(y3, int, 'line {}: malformed y2: {{}}'.format(line))

            # check if the current class name is correctly present
            if class_name not in classes:
                raise ValueError('line {}: unknown class name: \'{}\' (classes: {})'.format(line, class_name, classes))

            result[img_file].append({'x1': x1, 'x2': x2, 'x3': x3, 'y1': y1, 'y2': y2, 'y3': y3, 'class': class_name})
        return result

    def name_to_label(self, name):
        return self.classes[name]

    def label_to_name(self, label):
        return self.labels[label]

    def num_classes(self):
        return max(self.classes.values()) + 1

    def image_aspect_ratio(self, image_index):
        arr = np.load(self.image_names[image_index], mmap_mode='r')
        return float(arr.shape[1]) / float(arr.shape[0])


def collater(data):
    imgs = [s['img'] for s in data]
    annots = [s['annot'] for s in data]
    scales = [s['scale'] for s in data]

    widths = [int(s.shape[0]) for s in imgs]
    heights = [int(s.shape[1]) for s in imgs]
    batch_size = len(imgs)

    max_width = np.array(widths).max()
    max_height = np.array(heights).max()

    padded_imgs = torch.zeros(batch_size, max_width, max_height, 3)

    for i in range(batch_size):
        img = imgs[i]
        padded_imgs[i, :int(img.shape[0]), :int(img.shape[1]), :] = img

    max_num_annots = max(annot.shape[0] for annot in annots)

    if max_num_annots > 0:

        annot_padded = torch.ones((len(annots), max_num_annots, 5)) * -1

        if max_num_annots > 0:
            for idx, annot in enumerate(annots):
                # print(annot.shape)
                if annot.shape[0] > 0:
                    annot_padded[idx, :annot.shape[0], :] = annot
    else:
        annot_padded = torch.ones((len(annots), 1, 5)) * -1

    padded_imgs = padded_imgs.permute(0, 3, 1, 2)

    return {'img': padded_imgs, 'annot': annot_padded, 'scale': scales}


class Resizer(object):
    """Convert ndarrays in sample to Tensors."""

    def __init__(self, min_side=512, max_side=1024):
        self.min_side = min_side
        self.max_side = max_side

    def __call__(self, sample):
        image, annots = sample['img'], sample['annot']

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

        annots[:, :4] *= scale

        return {'img': torch.from_numpy(new_image), 'annot': torch.from_numpy(annots), 'scale': scale}


class Augmenter(object):
    """Convert ndarrays in sample to Tensors."""

    def __call__(self, sample, flip_x=0.5):
        if np.random.rand() < flip_x:
            image, annots = sample['img'], sample['annot']
            image = image[:, ::-1, :]

            rows, cols, channels = image.shape

            x1 = annots[:, 0].copy()
            x2 = annots[:, 2].copy()

            x_tmp = x1.copy()

            annots[:, 0] = cols - x2
            annots[:, 2] = cols - x_tmp

            sample = {'img': image, 'annot': annots}

        return sample


class Normalizer(object):

    def __init__(self):
        self.mean = np.array([[[0.485, 0.456, 0.406]]])
        self.std = np.array([[[0.229, 0.224, 0.225]]])

    def __call__(self, sample):
        image, annots = sample['img'], sample['annot']

        return {'img': ((image.astype(np.float32) - self.mean) / self.std), 'annot': annots}


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
