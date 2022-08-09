import datetime


class BaseDataManager:


    def __init__(self, parent, baseDataDirectory = './'):
        self.parent = parent
        self.baseDataDirectory = baseDataDirectory
        self.uids2DataDesc = {}
        self.uids2datetime = {}
        self.data = {}


    def ListAvailableData(self, dt_start: datetime.datetime, dt_end: datetime.datetime):
        raise NotImplementedError()


    def ReadSourceData(self, dataSourceFile):
        raise NotImplementedError()

