import json

class BasemapFrame:
    def __init__(self, projection:str, llcrnrlon: float, llcrnrlat: float, urcrnrlon: float, urcrnrlat: float):
        self.llcrnrlon = llcrnrlon
        self.llcrnrlat = llcrnrlat
        self.urcrnrlon = urcrnrlon
        self.urcrnrlat = urcrnrlat
        self.projection = projection


    def to_json(self):
        return json.dumps(self.__dict__)

    @classmethod
    def from_json(cls, json_data):
        return cls(**json.loads(json_data))