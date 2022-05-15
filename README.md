# AI-assisted GeoAnnotate
client-server python app for labeling climate events in multimodal geospatial data with some fancy labels

AI-assisted GeoAnnotate is an extension of the client-only labeling app [GeoAnnotate](https://github.com/MKrinitskiy/GeoAnnotate) for climate problems.

Originally it was forked from https://github.com/tzutalin/labelImg

Modifications were made in order to fit the current problem requirements:

- Labels of an elliptic form;
- Source data in NetCDF format which have to be projected;
- Various scales of the projection.
- (2020-04 update) tracking features added
- (2022-05 update) AI-assistant based on RetinaNet identification CNN

Client-server version is developed in order to address low performance of client-side PC.

AI-assisted version is implemented in order to address the issue of highly time-consumiing MCS labeling. Instead of creating the labels "from the scratch", an expert is supposed to assess and correct the ones pre-computed by AI-assistant.

