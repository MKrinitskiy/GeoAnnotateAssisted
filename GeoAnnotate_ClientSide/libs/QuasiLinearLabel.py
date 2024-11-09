from datetime import datetime

class QuasiLinearLabel:
    def __init__(self, name, uid, dt, points, sourcedata_fname):
        """
        Initialize a QuasiLinearLabel.

        :param name: Name of the label
        :param uid: Unique identifier for the label
        :param dt: Date and time associated with the label
        :param points: List of points defining the piecewise straight line
        :param sourcedata_fname: Identifier for the source data
        """
        self.name = name
        self.uid = uid
        self.dt = dt
        self.points = points  # List of points, each point is a dict with 'lat' and 'lon'
        self.sourcedata_fname = sourcedata_fname

    @classmethod
    def from_db_row_dict(cls, row_dict):
        """
        Create a QuasiLinearLabel from a database row dictionary.

        :param row_dict: Dictionary containing database row data
        :return: QuasiLinearLabel instance
        """
        label = QuasiLinearLabel(None, None, None, [], None)
        label.name = row_dict['label_name']
        label.uid = row_dict['label_uid']
        label.dt = row_dict['label_dt']
        label.sourcedata_fname = row_dict['sourcedata_fname']

        # Assuming points are stored as a list of tuples in the database
        points = row_dict['points']  # This should be a list of tuples [(lat, lon), ...]
        label.points = [{'lat': lat, 'lon': lon} for lat, lon in points]
        return label
