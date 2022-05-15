import json
import os

import numpy as np
import torch

from .srvMCSlabel import srvMCSlabel
from .retinanet.dataloader_deployment import *
from .retinanet import *
import sys
import collections
from torchvision import transforms
from torch.utils.data import DataLoader
from .retinanet import csv_eval
from os.path import join, isfile, isdir
from torch.utils.tensorboard import SummaryWriter
from torch.autograd import Variable
from threading import Thread
from libs.retinanet import model as models
from libs.service_defs import ReportException


class CNNPredictor(object):
    def __init__(self, app_args):
        self.data_fnames = {}
        self.data_snapshots = {}
        self.data_snapshots_preprocessed = {}
        self.predictions = {}
        self.dataset = DeploymentDataset(app_args, transforms.Compose([Normalizer(), Resizer(max_side=3000)]))
        self.app_args = app_args

        if self.app_args.backbone_depth == 18:
            self.model = models.resnet18(num_classes = self.dataset.num_classes(), pretrained=False, fl_alpha=0.25, fl_gamma=2.0)
        elif self.app_args.backbone_depth == 34:
            self.model = models.resnet34(num_classes=self.dataset.num_classes(), pretrained=False, fl_alpha=0.25, fl_gamma=2.0)
        elif self.app_args.backbone_depth == 50:
            self.model = models.resnet50(num_classes=self.dataset.num_classes(), pretrained=False, fl_alpha=0.25, fl_gamma=2.0)
        elif self.app_args.backbone_depth == 101:
            self.model = models.resnet101(num_classes=self.dataset.num_classes(), pretrained=False, fl_alpha=0.25, fl_gamma=2.0)
        elif self.app_args.backbone_depth == 152:
            self.model = models.resnet152(num_classes=self.dataset.num_classes(), pretrained=False, fl_alpha=0.25, fl_gamma=2.0)
        else:
            raise ValueError('Unsupported model depth, must be one of 18, 34, 50, 101, 152')

        self.DEVICE = torch.device("cuda" if ('gpu' in self.app_args.__dict__.keys() and torch.cuda.is_available())
                                   else "cpu")


        try:
            self.model.load_state_dict(torch.load(self.app_args.model_snapshot, map_location=self.DEVICE))
            print('model weights loaded successfully')
        except:
            ReportException('./logs/error.log', None)

        self.model = self.model.to(self.DEVICE)
        self.model.eval()

    def GetPredictions(self, webapi_client_id: str, clear: bool = True):
        return self.predictions[webapi_client_id]


    def LoadSourceData(self, curr_fname: str, webapi_client_id: str):
        sample = self.dataset(curr_fname)
        self.data_fnames[webapi_client_id] = curr_fname
        self.data_snapshots[webapi_client_id] = sample


    def PreprocessSourceData(self, webapi_client_id: str):
        pass


    def ApplyCNN(self, webapi_client_id: str):
        # self.predictions[webapi_client_id] = [srvMCSlabel(sourcedata_fname=self.data_fnames[webapi_client_id]) for i in range(5)] # apply CNN here and register the predictions
        with torch.no_grad():
            img = self.data_snapshots[webapi_client_id]['img']
            batch_scales = np.array([1.0])
            # nc_fname = self.data_snapshots[webapi_client_id]['nc_fnames']
            try:
                img = img.to(self.DEVICE)
                img = torch.unsqueeze(img, 0)
                img = torch.permute(img, (0,3,1,2))
                img = img.float()
                batch_scores, batch_labels, batch_boxes = self.model.forward(img)
                # batch_boxes: [x1,y1,x2,y1]
            except:
                ReportException('./logs/error.log', None)
                self.predictions[webapi_client_id] = None
                return
            batch_scores = batch_scores.cpu().numpy()
            batch_labels = batch_labels.cpu().numpy()
            batch_boxes = batch_boxes.cpu().numpy()
        batch_boxes = [boxes / scale for boxes, scale in zip(batch_boxes, batch_scales)]

        scores = batch_scores[0,:,0]   # for the only one data snapshot in the list, for the only one class
        boxes = batch_boxes[0][:,:,0]  # for the only one data snapshot in the list, for the only one class
        # boxes: [x1,y1,x2,y1]
        labels = batch_labels[0,:,0]   # for the only one data snapshot in the list, for the only one class

        indices = np.where(scores > self.app_args.score_threshold)[0]
        # all_detections = dict()
        # all_detections[nc_fname] = dict()
        detections = dict()
        if indices.shape[0] > 0:
            # select those scores
            scores = scores[indices].reshape((-1,))

            # find the order with which to sort the scores
            scores_sorted = np.argsort(-scores)[:self.app_args.max_detections].reshape((-1,))

            # select detections
            image_boxes = boxes[indices[scores_sorted], ...].reshape((-1, 4))  # [x1,y1,x2,y1]
            image_scores = scores[scores_sorted]
            image_labels = labels[indices[scores_sorted]]
            image_detections = np.concatenate([image_boxes,
                                               np.expand_dims(image_scores, axis=-1),
                                               np.expand_dims(image_labels, axis=-1)], axis=1)

            # copy detections to all_detections
            for label_class_num in range(self.dataset.num_classes()):
                curr_class_detections = image_detections[image_detections[:, -1] == label_class_num, :-1]
                curr_class_detections_srvMCSlabel = []
                for row in curr_class_detections:
                    # [x1,y1,x2,y1] to srvMCSlabel
                    label = srvMCSlabel()
                    label.probability = row[4]
                    label.class_name = self.dataset.label_to_name(label_class_num)
                    sourcedata_fname = self.data_fnames[webapi_client_id]
                    sourcedata_basename = os.path.basename(sourcedata_fname)
                    sourcedata_meta = self.dataset.ncfiles_metadata_dict[sourcedata_basename]
                    # it is a dictionary. keys are nc-files basenames;
                    # values are in turn dictionaries with keys like the following:
                    # {'fullname': fn,
                    #  'sat_label': MSG_label(os.path.basename(fn)),
                    #  'datetimestr': datetimestr(os.path.basename(fn)),
                    #  'datetime': dt(os.path.basename(fn))}
                    label.sourcedata_fname = sourcedata_fname

                    label.dt = sourcedata_meta['datetime']
                    sat_label = sourcedata_meta['sat_label']
                    lats_proj = self.dataset.interpolation_constants[sat_label]['lats_proj']
                    lons_proj = self.dataset.interpolation_constants[sat_label]['lons_proj']
                    xy1pt = np.array([row[0], row[1]])
                    latlonpt1 = xy2latlon(xy1pt, lats_proj, lons_proj)
                    xy2pt = np.array([row[2], row[3]])
                    latlonpt2 = xy2latlon(xy2pt, lats_proj, lons_proj)
                    label.ltc_lon = latlonpt1[1]
                    label.ltc_lat = latlonpt1[0]
                    label.rbc_lon = latlonpt2[1]
                    label.rbc_lat = latlonpt2[0]
                    curr_class_detections_srvMCSlabel.append(label)

                detections[self.dataset.label_to_name(label_class_num)] = curr_class_detections_srvMCSlabel
        else:
            for label in range(self.dataset.num_classes()):
                detections[label] = None

        self.predictions[webapi_client_id] = detections
