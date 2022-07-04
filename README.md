# AI-assisted GeoAnnotate
client-server python app for labeling climate events in multimodal geospatial data with some fancy labels

AI-assisted GeoAnnotate is an extension of the client-only labeling app [GeoAnnotate](https://github.com/MKrinitskiy/GeoAnnotate) for climate problems.

Originally it was forked from https://github.com/tzutalin/labelImg

Modifications were made in order to fit the current problem requirements:

- Labels of an elliptic form;
- Source data in NetCDF format which have to be projected;
- Various scales of the projection.

Client-server version is developed in order to address low performance of client-side PC.



**2020-04 update**

- manual tracking features added

**(2022-05 update)**

- AI-assistant added based on RetinaNet identification CNN

AI-assisted version is implemented in order to address the issue of highly time-consumiing MCS labeling. Instead of creating the labels "from the scratch", an expert is supposed to assess and correct the ones pre-computed by AI-assistant.

**2022-07-02 update**

- MC labels (rounded label shapes) for MCs (mesocyclones) and PLs (polar lows) implemented (client-side only so far; CNN identification is not implemented yet). The CLI argument of client-side app `--labels-type` (either `MCS`, or `MC`, or `PL` may be specified; `MCS` by default) manages this behaviour.

- server-side CNN may be turned off using the preferences record namely `detection_use_neural_assistance` in `.GeoAnnotateSettings.pkl`  pickled dictionary.

- server-side neural tracking feature (yet to be implemented) may be turned off using the preferences record namely `tracking_use_neural_assistance` in `.GeoAnnotateSettings.pkl`  pickled dictionary.
