from __future__ import print_function

import pickle

import numpy as np
import os
import matplotlib.pyplot as plt
import torch

from tqdm import tqdm
from torch.utils.data import DataLoader
from libs.retinanet.dataloader import collater
from libs.service_defs import ReportException
from torch.autograd import Variable


def compute_overlap(a, b):
    """
    Parameters
    ----------
    a: (N, 4) ndarray of float
    b: (K, 4) ndarray of float
    Returns
    -------
    overlaps: (N, K) ndarray of overlap between boxes and query_boxes
    """
    area = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])

    iw = np.minimum(np.expand_dims(a[:, 2], axis=1), b[:, 2]) - np.maximum(np.expand_dims(a[:, 0], 1), b[:, 0])
    ih = np.minimum(np.expand_dims(a[:, 3], axis=1), b[:, 3]) - np.maximum(np.expand_dims(a[:, 1], 1), b[:, 1])

    iw = np.maximum(iw, 0)
    ih = np.maximum(ih, 0)

    ua = np.expand_dims((a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1]), axis=1) + area - iw * ih

    ua = np.maximum(ua, np.finfo(float).eps)

    intersection = iw * ih

    return intersection / ua


def _compute_ap(recall, precision):
    """ Compute the average precision, given the recall and precision curves.
    Code originally from https://github.com/rbgirshick/py-faster-rcnn.
    # Arguments
        recall:    The recall curve (list).
        precision: The precision curve (list).
    # Returns
        The average precision as computed in py-faster-rcnn.
    """
    # correct AP calculation
    # first append sentinel values at the end
    mrec = np.concatenate(([0.], recall, [1.]))
    mpre = np.concatenate(([0.], precision, [0.]))

    # compute the precision envelope
    for i in range(mpre.size - 1, 0, -1):
        mpre[i - 1] = np.maximum(mpre[i - 1], mpre[i])

    # to calculate area under PR curve, look for points
    # where X axis (recall) changes value
    i = np.where(mrec[1:] != mrec[:-1])[0]

    # and sum (\Delta recall) * prec
    ap = np.sum((mrec[i + 1] - mrec[i]) * mpre[i + 1])
    return ap


def _get_detections(dataset, retinanet, device, score_threshold=0.05, max_detections=100, save_path=None):
    """ Get the detections from the retinanet using the generator.
    The result is a list of lists such that the size is:
        all_detections[num_images][num_classes] = detections[num_detections, 4 + num_classes]
    # Arguments
        dataset         : The generator used to run images through the retinanet.
        retinanet           : The retinanet to run on the images.
        score_threshold : The score confidence threshold to use.
        max_detections  : The maximum number of detections to use per image.
        save_path       : The path to save the images with visualized detections to.
    # Returns
        A list of lists containing the detections for each image in the generator.
    """
    all_detections = [[None for i in range(dataset.num_classes())] for j in range(len(dataset))]

    retinanet.eval()

    with torch.no_grad():

        for index in tqdm(range(len(dataset)), total=len(dataset)):
            data = dataset[index]
            scale = data['scale']

            # run network
            if torch.cuda.is_available():
                scores, labels, boxes = retinanet(data['img'].permute(2, 0, 1).cuda().float().unsqueeze(dim=0))
            else:
                scores, labels, boxes = retinanet(data['img'].permute(2, 0, 1).float().unsqueeze(dim=0))
            scores = scores.cpu().numpy()
            labels = labels.cpu().numpy()
            boxes  = boxes.cpu().numpy()

            # correct boxes for image scale
            boxes /= scale

            # select indices which have a score above the threshold
            indices = np.where(scores > score_threshold)[0]
            if indices.shape[0] > 0:
                # select those scores
                scores = scores[indices]

                # find the order with which to sort the scores
                scores_sort = np.argsort(-scores)[:max_detections]

                # select detections
                image_boxes      = boxes[indices[scores_sort], :]
                image_scores     = scores[scores_sort]
                image_labels     = labels[indices[scores_sort]]
                image_detections = np.concatenate([image_boxes, np.expand_dims(image_scores, axis=1), np.expand_dims(image_labels, axis=1)], axis=1)

                # copy detections to all_detections
                for label in range(dataset.num_classes()):
                    all_detections[index][label] = image_detections[image_detections[:, -1] == label, :-1]
            else:
                # copy detections to all_detections
                for label in range(dataset.num_classes()):
                    all_detections[index][label] = np.zeros((0, 5))

            print('{}/{}'.format(index + 1, len(dataset)), end='\r')

    return all_detections



#region threading
class thread_killer(object):
    """Boolean object for signaling a worker thread to terminate"""

    def __init__(self):
        self.to_kill = False

    def __call__(self):
        return self.to_kill

    def set_tokill(self, tokill):
        self.to_kill = tokill


def threaded_batches_feeder(tokill, batches_queue, dataset_generator):
    while tokill() == False:
        for sample in dataset_generator:
            batches_queue.put(sample, block=True)
            if tokill() == True:
                return


def threaded_cuda_batches(tokill, cuda_batches_queue, batches_queue, DEVICE):
    while tokill() == False:
        sample = batches_queue.get(block=True)
        img, scales = sample['img'], sample['scale']
        img = Variable(img.float()).to(DEVICE)
        scales = torch.from_numpy(np.array(scales))
        scales = Variable(scales).to(DEVICE)
        cuda_batches_queue.put((img, scales), block=True)

        if tokill() == True:
            return
#endregion



#
# def _get_detections_threaded(dataset, retinanet, device, score_threshold=0.05, max_detections=100, save_path=None):
#     """ Get the detections from the retinanet using the generator.
#     The result is a list of lists such that the size is:
#         all_detections[num_images][num_classes] = detections[num_detections, 4 + num_classes]
#     # Arguments
#         dataset         : The generator used to run images through the retinanet.
#         retinanet           : The retinanet to run on the images.
#         score_threshold : The score confidence threshold to use.
#         max_detections  : The maximum number of detections to use per image.
#         save_path       : The path to save the images with visualized detections to.
#     # Returns
#         A list of lists containing the detections for each image in the generator.
#     """
#     all_detections = [[None for i in range(dataset.num_classes())] for j in range(len(dataset.image_names))]
#
#     retinanet.eval()
#
#     val_steps = len(dataset)
#     print('validation dataset contains %d files; with batch_size=%d it is %d batches per epoch' % (len(dataset.image_names), dataset.batch_size, val_steps))
#
#     # region data preprocessing threads starting
#     batches_queue_length = 8
#     preprocess_workers = 8
#
#     test_batches_queue = Queue(maxsize=batches_queue_length)
#     test_cuda_batches_queue = Queue(maxsize=4)
#     test_thread_killer = thread_killer()
#     test_thread_killer.set_tokill(False)
#
#     for _ in range(preprocess_workers):
#         thr = Thread(target=threaded_batches_feeder, args=(test_thread_killer, test_batches_queue, dataset))
#         thr.start()
#
#     test_cuda_transfers_thread_killer = thread_killer()
#     test_cuda_transfers_thread_killer.set_tokill(False)
#     test_cudathread = Thread(target=threaded_cuda_batches,
#                              args=(test_cuda_transfers_thread_killer, test_cuda_batches_queue, test_batches_queue, device))
#     test_cudathread.start()
#     # endregion
#
#     with torch.no_grad():
#         for batch_idx in tqdm(range(val_steps), total=val_steps):
#             img, batch_scales = test_cuda_batches_queue.get(block=True)
#
#             # run network
#             batch_scores, batch_labels, batch_boxes = retinanet(img)
#             batch_scores = batch_scores.detach().cpu().numpy()
#             batch_labels = batch_labels.detach().cpu().numpy()
#             batch_boxes  = batch_boxes.detach().cpu().numpy()
#             if len(batch_scores) == 0:
#                 for img_idx in range(len(img)):
#                     index = img_idx + batch_idx * dataset.batch_size
#                     if index >= len(all_detections)-1:
#                         break
#                     for label in range(dataset.num_classes()):
#                         all_detections[index][label] = np.zeros((0, 5))
#                 continue
#
#             batch_scales = batch_scales.detach().cpu().numpy()
#
#             # correct boxes for image scale
#             batch_boxes /= [box/scale for box,scale in zip(batch_boxes, batch_scales)]
#
#             for img_idx in range(len(img)):
#                 index = img_idx + batch_idx*dataset.batch_size
#                 # select indices which have a score above the threshold
#
#                 scores = batch_scores[img_idx]
#                 boxes = batch_boxes[img_idx]
#                 labels = batch_labels[img_idx]
#                 indices = np.where(scores > score_threshold)[0]
#                 if indices.shape[0] > 0:
#                     # select those scores
#                     scores = scores[indices]
#
#                     # find the order with which to sort the scores
#                     scores_sort = np.argsort(-scores)[:max_detections]
#
#                     # select detections
#                     image_boxes      = boxes[indices[scores_sort], :]
#                     image_scores     = scores[scores_sort]
#                     image_labels     = labels[indices[scores_sort]]
#                     image_detections = np.concatenate([image_boxes, np.expand_dims(image_scores, axis=1), np.expand_dims(image_labels, axis=1)], axis=1)
#
#                     # copy detections to all_detections
#                     for label in range(dataset.num_classes()):
#                         all_detections[index][label] = image_detections[image_detections[:, -1] == label, :-1]
#                 else:
#                     # copy detections to all_detections
#                     for label in range(dataset.num_classes()):
#                         all_detections[index][label] = np.zeros((0, 5))
#
#     # region stopping datapreprocessing threads
#     test_thread_killer.set_tokill(True)
#     test_cuda_transfers_thread_killer.set_tokill(True)
#     for _ in range(preprocess_workers):
#         try:
#             # Enforcing thread shutdown
#             test_batches_queue.get(block=True, timeout=1)
#             test_cuda_batches_queue.get(block=True, timeout=1)
#         except Empty:
#             pass
#     # endregion
#
#     return all_detections
#




def _get_detections_multiple(dataset, retinanet, device, score_threshold=0.05, max_detections=100, save_path=None):
    """ Get the detections from the retinanet using the generator.
    The result is a list of lists such that the size is:
        all_detections[num_images][num_classes] = detections[num_detections, 4 + num_classes]
    # Arguments
        dataset         : The generator used to run images through the retinanet.
        retinanet           : The retinanet to run on the images.
        score_threshold : The score confidence threshold to use.
        max_detections  : The maximum number of detections to use per image.
        save_path       : The path to save the images with visualized detections to.
    # Returns
        A list of lists containing the detections for each image in the generator.
    """
    all_detections = [[None for i in range(dataset.num_classes())] for j in range(len(dataset))]

    retinanet.eval()

    val_dataloader = DataLoader(dataset, num_workers=16, collate_fn=collater, batch_size=12)

    with torch.no_grad():
        for batch_index, batch in tqdm(enumerate(val_dataloader), total = len(val_dataloader)):
        # for index in tqdm(range(len(dataset)), total=len(dataset)):
        #     data = dataset[index]
            img = batch['img']
            batch_scales = batch['scale']

            # run network
            batch_scores, batch_labels, batch_boxes = retinanet.forward(img.to(device).float())
            batch_scores = batch_scores.cpu().numpy()
            batch_labels = batch_labels.cpu().numpy()
            batch_boxes  = batch_boxes.cpu().numpy()

            # correct boxes for image scale
            batch_boxes = [boxes/scale for boxes,scale in zip(batch_boxes, batch_scales)]

            for img_idx in range(len(batch['img'])):
                index = img_idx + batch_index*val_dataloader.batch_size
                # select indices which have a score above the threshold

                scores = batch_scores[img_idx]
                boxes = batch_boxes[img_idx]
                labels = batch_labels[img_idx]
                indices = np.where(scores > score_threshold)[0]
                if indices.shape[0] > 0:
                    # select those scores
                    scores = scores[indices].reshape((-1,))

                    # find the order with which to sort the scores
                    scores_sort = np.argsort(-scores)[:max_detections].reshape((-1,))

                    # select detections
                    image_boxes      = boxes[indices[scores_sort], ...].reshape((-1,4))
                    image_scores     = scores[scores_sort]
                    image_labels     = labels[indices[scores_sort]]
                    image_detections = np.concatenate([image_boxes, np.expand_dims(image_scores, axis=-1), image_labels], axis=1)

                    # copy detections to all_detections
                    for label in range(dataset.num_classes()):
                        all_detections[index][label] = image_detections[image_detections[:, -1] == label, :-1]
                else:
                    # copy detections to all_detections
                    for label in range(dataset.num_classes()):
                        all_detections[index][label] = np.zeros((0, 5))

            # print('{}/{}'.format(index + 1, len(dataset)), end='\r')

    return all_detections



def _get_annotations(generator):
    """ Get the ground truth annotations from the generator.
    The result is a list of lists such that the size is:
        all_detections[num_images][num_classes] = annotations[num_detections, 5]
    # Arguments
        generator : The generator used to retrieve ground truth annotations.
    # Returns
        A list of lists containing the annotations for each image in the generator.
    """
    all_annotations = [[None for i in range(generator.num_classes())] for j in range(len(generator))]

    for i in range(len(generator)):
        # load the annotations
        annotations = generator.load_annotations(i)

        # copy detections to all_annotations
        for label in range(generator.num_classes()):
            all_annotations[i][label] = annotations[annotations[:, 4] == label, :4].copy()

        print('{}/{}'.format(i + 1, len(generator)), end='\r')

    return all_annotations


def evaluate(generator,
             retinanet,
             device,
             iou_threshold=0.5,
             score_threshold=0.05,
             max_detections=100,
             save_path=None,
             epoch = 0):
    """ Evaluate a given dataset using a given retinanet.
    # Arguments
        generator       : The generator that represents the dataset to evaluate.
        retinanet           : The retinanet to evaluate.
        iou_threshold   : The threshold used to consider when a detection is positive or negative.
        score_threshold : The score confidence threshold to use for detections.
        max_detections  : The maximum number of detections to use per image.
        save_path       : The path to save precision recall curve of each label.
    # Returns
        A dict mapping class names to mAP scores.
    """



    # gather all detections and annotations

    all_detections     = _get_detections_multiple(generator, retinanet, score_threshold=score_threshold, max_detections=max_detections, save_path=save_path, device = device)
    # all_detections     = _get_detections(generator, retinanet, score_threshold=score_threshold, max_detections=max_detections, save_path=save_path, device = device)
    # all_detections     = _get_detections_threaded(generator, retinanet, score_threshold=score_threshold, max_detections=max_detections, save_path=save_path, device = device)
    all_annotations    = _get_annotations(generator)

    average_precisions = {}
    recalls = {}
    precisions = {}
    scores_sorted = {}

    for label in range(generator.num_classes()):
        false_positives = np.zeros((0,))
        true_positives  = np.zeros((0,))
        scores          = np.zeros((0,))
        num_annotations = 0.0

        for i in range(len(generator)):
            detections           = all_detections[i][label]
            annotations          = all_annotations[i][label]
            num_annotations     += annotations.shape[0]
            detected_annotations = []

            for d in detections:
                scores = np.append(scores, d[4])

                if annotations.shape[0] == 0:
                    false_positives = np.append(false_positives, 1)
                    true_positives  = np.append(true_positives, 0)
                    continue

                overlaps            = compute_overlap(np.expand_dims(d, axis=0), annotations)
                assigned_annotation = np.argmax(overlaps, axis=1)
                max_overlap         = overlaps[0, assigned_annotation]

                if max_overlap >= iou_threshold and assigned_annotation not in detected_annotations:
                    false_positives = np.append(false_positives, 0)
                    true_positives  = np.append(true_positives, 1)
                    detected_annotations.append(assigned_annotation)
                else:
                    false_positives = np.append(false_positives, 1)
                    true_positives  = np.append(true_positives, 0)

        # no annotations -> AP for this class is 0 (is this correct?)
        if num_annotations == 0:
            average_precisions[label] = 0, 0
            continue

        # sort by score
        indices         = np.argsort(-scores)
        scores_sorted[label] = scores[indices]
        false_positives = false_positives[indices]
        true_positives  = true_positives[indices]

        # compute false positives and true positives
        false_positives = np.cumsum(false_positives)
        true_positives  = np.cumsum(true_positives)

        # compute recall and precision
        recall    = true_positives / num_annotations
        precision = true_positives / np.maximum(true_positives + false_positives, np.finfo(np.float64).eps)

        # compute average precision
        average_precision  = _compute_ap(recall, precision)
        average_precisions[label] = average_precision, num_annotations
        recalls[label] = recall
        precisions[label] = precision


    try:
        if save_path != None:
            dict1 = {'precisions': precisions, 'recalls': recalls, 'scores_sorted': scores_sorted, 'average_precisions': average_precisions}
            with open(os.path.join(save_path, 'metrics_epoch%04d.pkl' % epoch), 'wb') as f:
                pickle.dump(dict1, f)
    except Exception as ex:
        ReportException()

    try:
        print('\nmAP:')
        for label in range(generator.num_classes()):
            label_name = generator.label_to_name(label)
            print('{}: {}'.format(label_name, average_precisions[label][0]))
            precision = precisions[label]
            recall = recalls[label]
            scores = scores_sorted[label]



            if save_path!=None:
                f = plt.figure(figsize=(6,4), dpi=300)
                plt.plot(recall,precision)
                plt.xlabel('Recall')
                plt.ylabel('Precision')
                plt.title('Precision Recall curve')
                f.patch.set_facecolor('white')
                plt.savefig(save_path+'/'+label_name+'_precision_recall_epoch%04d.jpg'%epoch)
                plt.close()

                f = plt.figure(figsize=(6, 4), dpi=300)
                f1_scores = 2*precision*recall/(precision+recall)
                plt.plot(scores, f1_scores)
                plt.xlabel('score')
                plt.ylabel('f1 score')
                f.patch.set_facecolor('white')
                plt.savefig(save_path + '/' + label_name + '_F1score_epoch%04d.jpg' % epoch)
                plt.close()
    except Exception as ex:
        ReportException()

    return average_precisions, recalls, precisions
    # return average_precisions

