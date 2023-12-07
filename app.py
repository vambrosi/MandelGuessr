import os
import json
from random import randrange

from tkinter import *
from tkinter.ttk import *

from numpy import float64, int64
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from plots import FigureWrapper, SetView

if os.name == "nt":
    from ctypes import windll

    windll.shcore.SetProcessDpiAwareness(2)


class SetViewer(Tk):
    """
    Creates a window to explore a dynamical system (DSystem).
    """

    def __init__(self):
        Tk.__init__(self)

        with open("roots10.json", "r") as f:
            self.roots = json.load(f)

        self.roots = [complex(root[0], root[1]) for root in self.roots]
        self.hyperbolic_center = self.roots[randrange(len(self.roots))]
        self.points = 0

        self.wm_title("MandelGuessr")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.fig_wrap = FigureWrapper()

        self.geometry("650x420")

        self.mandel_hint = SetView(
            self.fig_wrap,
            self.fig_wrap.fig.add_subplot(1, 2, 1),
            self.hyperbolic_center,
            1e-5,
            find_zoom=True,
        )
        self.hint_diam = self.mandel_hint.diam

        self.mandel_view = SetView(
            self.fig_wrap,
            self.fig_wrap.fig.add_subplot(1, 2, 2),
            -0.5 + 0.0j,
            4.0,
        )

        self.shortcuts = {"z", "x", "r", "s"}

        self.put_figure()
        self.put_options()

        self.update_idletasks()

    def put_figure(self):
        self.canvas = FigureCanvasTkAgg(self.fig_wrap.fig, master=self)
        self.canvas.get_tk_widget().rowconfigure(0, weight=1)
        self.canvas.get_tk_widget().columnconfigure(0, weight=1)
        self.canvas.get_tk_widget().grid(row=0, column=0, columnspan=6)
        self.canvas.mpl_connect("key_press_event", self.shortcut_handler)
        self.canvas.mpl_connect("motion_notify_event", self.update_pointer)

    def put_options(self):
        self.options = Frame(self)
        self.options.grid(row=1, column=0)

        # Pointer coordinates
        Label(self.options, text="Pointer:").grid(row=0, column=0, padx=5, sticky="w")
        self.pointer_x = Entry(self.options, width=20)
        self.pointer_x.grid(row=0, column=1, padx=5, pady=5)
        self.pointer_x["state"] = "readonly"

        self.pointer_y = Entry(self.options, width=20)
        self.pointer_y.grid(row=0, column=2, padx=5, pady=5)
        self.pointer_y["state"] = "readonly"

        # Dynamical parameters
        self.esc_radius_label = Label(self.options, text="Esc Radius:")
        self.esc_radius_label.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.esc_radius = Entry(self.options, width=10)
        self.esc_radius.insert(0, self.fig_wrap.esc_radius)
        self.esc_radius.bind("<Return>", self.update_esc_radius)
        self.esc_radius.grid(row=0, column=4, padx=5, pady=5, sticky="w")

        self.max_iter_label = Label(self.options, text="Max Iter:")
        self.max_iter_label.grid(row=0, column=5, padx=5, pady=5, sticky="w")
        self.max_iter = Entry(self.options, width=10)
        self.max_iter.insert(0, self.fig_wrap.max_iter)
        self.max_iter.bind("<Return>", self.update_max_iter)
        self.max_iter.grid(row=0, column=6, padx=5, pady=5, sticky="w")

    def shortcut_handler(self, event):
        key = event.key

        if key in self.shortcuts and event.inaxes == self.mandel_view.ax:
            self.canvas.get_tk_widget().config(cursor="watch")

            view = self.mandel_view
            pointer = view.img_to_z_coords(event.xdata, event.ydata)

            # 's' is not listed because it doesn't change center or diam
            if key == "z":  # zooms in
                view.diam /= 2
                view.center = 0.5 * view.center + 0.5 * pointer
            elif key == "x":  # zooms out
                view.diam *= 2
                view.center = 2 * view.center - pointer
            elif key == "s":  # zooms out
                view.center = pointer
            elif key == "r":  # resets center and diam
                view.center = view.init_center
                view.diam = view.init_diam

            view.update_plot()
            self.canvas.draw_idle()
            self.canvas.get_tk_widget().config(cursor="")

        elif key == "g" and event.inaxes == self.mandel_view.ax:
            view = self.mandel_view
            pointer = view.img_to_z_coords(event.xdata, event.ydata)

            dist = abs(self.hyperbolic_center - pointer)

            zs = [pointer, self.hyperbolic_center]

            if 1.5 * dist > self.hint_diam:
                view.diam = 1.5 * dist
            else:
                view.diam = self.hint_diam

            view.center = 0.5 * self.hyperbolic_center + 0.5 * pointer
            view.update_plot()

            xs, ys = view.z_to_img_coords(zs)
            view.dist_plt.set_data(xs, ys)
            self.canvas.draw_idle()

            if dist > self.hint_diam:
                self.points += int((4 / dist) ** 0.5)
            else:
                self.points += int((4 / self.hint_diam) ** 0.5)

            print(self.points)

    def update_plot(self, all=True):
        # In case there is only one plot
        # self.mandel_hint.update_plot(all=all)
        self.mandel_view.update_plot(all=all)
        self.canvas.draw_idle()
        self.canvas.get_tk_widget().focus_set()

    def update_pointer(self, event):
        if event.inaxes == self.mandel_view.ax:
            self.pointer_x["state"] = self.pointer_y["state"] = "active"
            view = self.mandel_view

            pointer = view.img_to_z_coords(event.xdata, event.ydata)

            self.pointer_x.delete(0, END)
            self.pointer_x.insert(0, pointer.real)
            self.pointer_y.delete(0, END)
            self.pointer_y.insert(0, pointer.imag)
            self.pointer_x["state"] = self.pointer_y["state"] = "readonly"

    def update_esc_radius(self, event):
        self.canvas.get_tk_widget().config(cursor="watch")
        self.fig_wrap.esc_radius = float64(event.widget.get())
        self.update_plot()
        self.canvas.get_tk_widget().config(cursor="")
        self.canvas.get_tk_widget().focus_set()

    def update_max_iter(self, event):
        self.canvas.get_tk_widget().config(cursor="watch")
        self.fig_wrap.max_iter = int64(event.widget.get())
        self.update_plot()
        self.canvas.get_tk_widget().config(cursor="")
        self.canvas.get_tk_widget().focus_set()
