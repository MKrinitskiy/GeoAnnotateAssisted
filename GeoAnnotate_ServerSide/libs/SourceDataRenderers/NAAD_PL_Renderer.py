from .BaseRenderer import BaseRenderer
from matplotlib import pyplot as plt
import cv2
import numpy as np
from libs.u_interpolate import interpolate_data
import io
from libs.scaling import norm_constants




class NAAD_PL_Renderer(BaseRenderer):
    def __init__(self, parent):
        super().__init__(parent)

    def PlotBasemapBackground(self):
        BasemapFigure = plt.figure(figsize=(4, 4), dpi=self.parent.dpi)
        ax = plt.Axes(BasemapFigure, [0., 0., 1., 1.])
        ax.set_axis_off()
        BasemapFigure.add_axes(ax)
        self.parent.bm.drawcoastlines(linewidth=0.1)
        self.parent.bm.fillcontinents(color=(0.95, 0.95, 0.95))
        m = self.parent.bm.drawmeridians([self.parent.sourceDataManager.lons.min() + i * (self.parent.sourceDataManager.lons.max() - self.parent.sourceDataManager.lons.min()) / 5. for i in range(6)], linewidth=0.3)
        p = self.parent.bm.drawparallels([self.parent.sourceDataManager.lats.min() + i * (self.parent.sourceDataManager.lats.max() - self.parent.sourceDataManager.lats.min()) / 5. for i in range(6)], linewidth=0.3)
        cs = self.parent.bm.contour(self.parent.sourceDataManager.lons, self.parent.sourceDataManager.lats,
                                    self.parent.sourceDataManager.data['msl'], latlon=True, levels=np.arange(norm_constants.msl_vmin, norm_constants.msl_vmax, 2.0),
                                    colors='black', linewidths=0.1)
        ax.clabel(cs, inline=True, fontsize=3)

        plt.axis("off")

        with io.BytesIO() as buf:
            BasemapFigure.savefig(buf, dpi=self.parent.dpi, format='png', pad_inches=0, bbox_inches='tight')
            buf.seek(0)
            img = cv2.imdecode(np.copy(np.asarray(bytearray(buf.read()), dtype=np.uint8)), cv2.IMREAD_COLOR)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w, c = img.shape
        self.parent.BasemapLayerImage = np.copy(img)
        plt.close(BasemapFigure)


    def PlotDataLayer(self):
        for dataname, cmap, vmin, vmax in zip(self.parent.channelNames, self.parent.channelColormaps, self.parent.channelVmin, self.parent.channelVmax):
            data = self.parent.sourceDataManager.data[dataname]
            data_interpolated = interpolate_data(data,
                                                 self.parent.interpolation_constants['interpolation_inds'],
                                                 self.parent.interpolation_constants['interpolation_wghts'],
                                                 self.parent.interpolation_constants['interpolation_shape'])

            self.parent.DataInterpolated[dataname] = np.copy(data_interpolated)

            data_interpolated_normed10 = (data_interpolated - vmin) / (vmax - vmin)
            img = (cmap(data_interpolated_normed10)[:, :, :-1] * 255).astype(np.uint8)
            img = cv2.flip(img, 0)
            self.parent.DataLayerImage[dataname] = np.copy(img)[:, :, ::-1]
