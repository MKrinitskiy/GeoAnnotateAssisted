import datetime


class BaseDataManager:


    def __init__(self, parent, baseDataDirectory = './src_data/', source_data_file = './src_data/source_data_file.nc'):
        self.parent = parent
        self.baseDataDirectory = baseDataDirectory
        self.source_data_file = source_data_file
        self.uids2DataDesc = {}
        self.uids2datetime = {}
        self.data = {}


    def ListAvailableData(self, dt_start: datetime.datetime, dt_end: datetime.datetime):
        raise NotImplementedError()


    def ReadSourceData(self, dataItemIdentifier):
        raise NotImplementedError()

