#!/usr/bin/env python
# -*- coding: utf8 -*-
import sys
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
from lxml import etree
import codecs
import uuid
from .MCSlabel import MCSlabel
import os, re
from datetime import datetime
from .ServiceDefs import ReportException

PASCAL_XML_EXT = '.PASCAL.xml'
MCC_XML_EXT = '.MCC.xml'
ENCODE_METHOD = 'utf-8'

class ArbitraryXMLWriter:

    def __init__(self, localImgPath, imgSize):
        self.imgSize = imgSize
        self.boxlist = []
        self.localImgPath = localImgPath
        self.verified = False

    def prettify(self, elem):
        """
            Return a pretty-printed XML string for the Element.
        """
        rough_string = ElementTree.tostring(elem, 'utf8')
        root = etree.fromstring(rough_string)
        return etree.tostring(root, pretty_print=True, encoding=ENCODE_METHOD).replace("  ".encode(), "\t".encode())

    def genXML(self):
        """
            Return XML root
        """
        # Check conditions
        if self.imgSize is None:
            return None

        top = Element('annotation')
        # if self.verified:
        #     top.set('verified', 'yes')

        # folder = SubElement(top, 'folder')
        # folder.text = self.foldername

        # filename = SubElement(top, 'filename')
        # filename.text = self.filename

        if self.localImgPath is not None:
            localImgPath = SubElement(top, 'filename')
            localImgPath.text = self.localImgPath

        size_part = SubElement(top, 'size')
        width = SubElement(size_part, 'width')
        height = SubElement(size_part, 'height')
        depth = SubElement(size_part, 'depth')
        width.text = str(self.imgSize[1])
        height.text = str(self.imgSize[0])
        if len(self.imgSize) == 3:
            depth.text = str(self.imgSize[2])
        else:
            depth.text = '1'

        return top

    def addEllipse(self, ellipse_shape):
        curr_label = ellipse_shape.label
        ellipse_properties = {'lon0': curr_label.pts['pt0']['lon'],
                              'lat0': curr_label.pts['pt0']['lat'],
                              'lon1': curr_label.pts['pt1']['lon'],
                              'lat1': curr_label.pts['pt1']['lat'],
                              'lon2': curr_label.pts['pt2']['lon'],
                              'lat2': curr_label.pts['pt2']['lat']}
        ellipse_properties['name'] = curr_label.name
        ellipse_properties['uid'] = curr_label.uid
        self.boxlist.append(ellipse_properties)

    def appendObjects(self, top):
        for each_object in self.boxlist:
            object_item = SubElement(top, 'object')

            uid = SubElement(object_item, 'uid')
            uid.text = each_object['uid']

            name = SubElement(object_item, 'name')
            name.text = each_object['name']

            ellipse = SubElement(object_item, 'ellipse')

            lon0 = SubElement(ellipse, 'lon0')
            lon0.text = str(each_object['lon0'])
            lat0 = SubElement(ellipse, 'lat0')
            lat0.text = str(each_object['lat0'])
            lon1 = SubElement(ellipse, 'lon1')
            lon1.text = str(each_object['lon1'])
            lat1 = SubElement(ellipse, 'lat1')
            lat1.text = str(each_object['lat1'])
            lon2 = SubElement(ellipse, 'lon2')
            lon2.text = str(each_object['lon2'])
            lat2 = SubElement(ellipse, 'lat2')
            lat2.text = str(each_object['lat2'])


    def save(self, targetFile=None):
        root = self.genXML()
        self.appendObjects(root)
        out_file = None
        if targetFile is None:
            out_file = codecs.open(
                self.filename + MCC_XML_EXT, 'w', encoding=ENCODE_METHOD)
        else:
            out_file = codecs.open(targetFile, 'w', encoding=ENCODE_METHOD)

        prettifyResult = self.prettify(root)
        out_file.write(prettifyResult.decode('utf8'))
        out_file.close()


class ArbitraryXMLReader:

    def __init__(self, filepath):
        self.labels = []
        self.filepath = filepath
        self.verified = False
        try:
            self.parseXML()
        except Exception as ex:
            print('unable to parse XML label file: \n%s' % self.filepath)
            raise Exception('unable to parse XML label file: \n%s' % self.filepath)

    def getLabels(self):
        return self.labels

    # def addLabel(self, label_name, bndbox, uid, dt):
    #     latlonPoints = [(lon0, lat0), (lon1, lat1), (lon2, lat2)]


    def parseXML(self):
        assert self.filepath.endswith(MCC_XML_EXT), "Unsupported file format"
        parser = etree.XMLParser(encoding=ENCODE_METHOD)
        xmltree = ElementTree.parse(self.filepath, parser=parser).getroot()

        for object_iter in xmltree.findall('object'):
            ellipse = object_iter.find("ellipse")
            label_name = object_iter.find('name').text
            try:
                uid = object_iter.find('uid').text
            except:
                # uid = str(uuid.uuid4()).replace('-', '')
                uid = str(uuid.uuid4())

            try:
                uid = object_iter.find('uid').text
            except:
                # uid = str(uuid.uuid4()).replace('-', '')
                uid = str(uuid.uuid4())

            loaded_dt_from_xml = False
            try:
                dt = object_iter.find('datetime').text
            except:
                loaded_dt_from_xml = False

            if not loaded_dt_from_xml:
                try:
                    # parse datetime from filename
                    # W_XX-EUMETSAT-Darmstadt,VIS+IR+IMAGERY,MSG1+SEVIRI_C_EUMG_20180630143011.MCC.xml
                    regex = r'.+(MSG\d)\+SEVIRI_C_EUMG_(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})\.MCC\.xml'
                    base_filepath = os.path.basename(self.filepath)
                    m = re.match(regex, base_filepath)
                    sat_name, year, month, day, hour, minute, second = m.groups()
                    # ('MSG1', '2018', '06', '30', '14', '30', '11')
                    dt = datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
                except Exception as ex:
                    ReportException('./errors.log', ex)

            lon0 = float(ellipse.find('lon0').text)
            lat0 = float(ellipse.find('lat0').text)
            lon1 = float(ellipse.find('lon1').text)
            lat1 = float(ellipse.find('lat1').text)
            lon2 = float(ellipse.find('lon2').text)
            lat2 = float(ellipse.find('lat2').text)
            pt0 = {'lat': lat0, 'lon': lon0}
            pt1 = {'lat': lat1, 'lon': lon1}
            pt2 = {'lat': lat2, 'lon': lon2}
            pts = {'pt0': pt0, 'pt1': pt1, 'pt2': pt2}

            # self.addLabel(label_name, ellipse, uid, dt)
            # self.addLabel(MCSlabel(label_name, uid, dt, pts))
            self.labels.append(MCSlabel(label_name, uid, dt, pts))
        return True
