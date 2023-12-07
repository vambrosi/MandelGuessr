from numpy import zeros, float64, nan, log2, isnan, mean
from matplotlib import colormaps
from matplotlib.figure import Figure
from numba import jit, prange


@jit(nopython=True)
def escape_time(c, max_iter, esc_radius):
    """
    Computes how long it takes for a point to escape to infinity.
    Uses renormalization to make the output continuous.
    """
    z = 0
    for i in range(max_iter):
        if abs(z) >= esc_radius:
            return (i + 1 - log2(log2(abs(z)))) / 64

        z = z**2 + c

    return nan


@jit(nopython=True)
def color_shift_scale(img, shift):
    return (img + shift) % 1


@jit(nopython=True, parallel=True)
def mandel_grid(center, diam, grid, max_iter, esc_radius):
    """
    Find the escape time of a critical point along a grid of parameters.
    The critical point depends on the value of the parameter.
    """
    h = grid.shape[0]
    w = grid.shape[1]

    # Assumes that diam is the length of the grid in the x direction
    delta = diam / w

    # Computes the complex number in the southwest corner of the grid
    # Assumes dimensions are even so center is not a point in the grid
    # This is why there is an adjustment of half delta on each direction
    z0 = center - delta * complex(w, h) / 2 + delta * (0.5 + 0.5j)

    for n in prange(w):
        dx = n * delta
        for m in prange(h):
            dy = m * delta
            c = z0 + complex(dx, dy)
            grid[m, n] = escape_time(c, max_iter, esc_radius)


class FigureWrapper:
    """
    Stores the settings and the Figure object of the main figure.
    """

    def __init__(self):
        # Initialize all settings with default values

        # Graphics settings and figure object
        self.width_pxs = 1000
        self.height_pxs = 1000
        self.color_shift = 0.0
        self.fig = Figure(figsize=(20, 10), layout="compressed")
        self.cmap = colormaps.get_cmap("twilight")
        self.cmap.set_bad(color=self.cmap(0.5))

        # Dynamical parameters
        self.max_iter = 256
        self.esc_radius = 100.0


class SetView:
    """
    Wrapper for plot of a set in the complex plane (Julia or Mandelbrot).
    """

    def __init__(self, fig_wrap, ax, center, diam, find_zoom=False):
        # Initialize all settings
        self.init_center = center
        self.init_diam = diam

        self.fig_wrap = fig_wrap
        self.img = zeros(
            (self.fig_wrap.height_pxs, self.fig_wrap.width_pxs), dtype=float64
        )
        self.ax = ax
        self.ax.set_axis_off()

        mandel_grid(
            self.center,
            self.diam,
            self.img,
            fig_wrap.max_iter,
            fig_wrap.esc_radius,
        )

        if find_zoom:
            self.find_zoom(is_init=True)
            x, y = self.z_to_img_coords(self.center)
            (self.dist_plt,) = self.ax.plot([x], [y], "ro-")
        else:
            (self.dist_plt,) = self.ax.plot([], [], "ro-", alpha=0.75)

        self.plt = self.ax.imshow(
            color_shift_scale(self.img, self.fig_wrap.color_shift),
            cmap=self.fig_wrap.cmap,
            vmin=0.0,
            vmax=1.0,
            origin="lower",
            interpolation_stage="rgba",
        )

    @property
    def init_center(self):
        return self._init_center

    @init_center.setter
    def init_center(self, center):
        self._init_center = center
        self.center = center

    @property
    def init_diam(self):
        return self._init_diam

    @init_diam.setter
    def init_diam(self, diam):
        self._init_diam = diam
        self.diam = diam

    def update_plot(self, all=True):
        """
        Plots the set in self.ax (plot reference is stored in self.plt).
        """
        if all:
            mandel_grid(
                self.center,
                self.diam,
                self.img,
                self.fig_wrap.max_iter,
                self.fig_wrap.esc_radius,
            )

        self.plt.set_data(color_shift_scale(self.img, self.fig_wrap.color_shift))

    def img_to_z_coords(self, xdata, ydata):
        h = self.img.shape[0]
        w = self.img.shape[1]
        delta = self.diam / w

        sw = self.center - delta * complex(w, h) / 2 + delta * (0.5 + 0.5j)
        return sw + xdata * delta + ydata * delta * 1.0j

    def z_to_img_coords(self, z):
        h = self.img.shape[0]
        w = self.img.shape[1]
        delta = self.diam / w

        sw = self.center - delta * complex(w, h) / 2 + delta * (0.5 + 0.5j)
        img_coords = (z - sw) / delta

        return img_coords.real, img_coords.imag

    def find_zoom(self, is_init=False):
        ratio = mean(isnan(self.img))
        # print("NAN ratio:", ratio, "\tDiameter:", self.diam)

        lower = 0.02
        ideal = 0.04
        upper = 0.06

        for _ in range(20):
            if ratio > 4e-8:
                self.diam /= (ideal / ratio)**(1/2)
            else:
                self.diam /= 1000

            mandel_grid(
                self.center,
                self.diam,
                self.img,
                512,
                100.0,
            )
            ratio = mean(isnan(self.img))
            # print("NAN ratio:", ratio, "\tDiameter:", self.diam)

            if lower < ratio < upper or self.diam > 0.05:
                break

        mandel_grid(
            self.center,
            self.diam,
            self.img,
            2048,
            100.0,
            )

        if not is_init:
            self.plt.set_data(color_shift_scale(self.img, self.fig_wrap.color_shift))