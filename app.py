import os
import json
from random import randrange
from time import sleep

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
        self.pause_var = BooleanVar(self, False)
        self.protocol("WM_DELETE_WINDOW", self.closing)

        with open("roots.json", "r") as f:
            self.roots = json.load(f)

        self.roots = [complex(root[0], root[1]) for root in self.roots]
        self.hyperbolic_center = self.roots.pop(randrange(len(self.roots)))
        self.points = 0

        self.wm_title("MandelGuessr")
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        self.fig_wrap = FigureWrapper()

        self.geometry("750x440")

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
        self.put_points()
        self.put_options()
        self.put_instructions()

        self.update_idletasks()

    def put_instructions(self):
        props = dict(facecolor="white", alpha=0.75)
        instructions = "\n".join(
            (
                "Find the hyperbolic component center!",
                "",
                "---SHORTCUTS---",
                "",
                "Z: Zoom in     ",
                "X: Zoom out    ",
                "S: Pans view   ",
                "G: Guess center",
                "",
                "Press any key to start!",
            )
        )
        text = self.fig_wrap.fig.text(
            0.50,
            0.50,
            instructions,
            horizontalalignment="center",
            verticalalignment="center",
            wrap=True,
            bbox=props,
            family="monospace",
        )
        self.pause_var.set(True)
        self.wait_variable(self.pause_var)
        text.remove()

    def finish_round(self):
        props = dict(facecolor="white", alpha=0.75)
        points_str = "\n".join(
            (
                f"Points in this round:       {self.points_last_round:15d}",
                f"Distance to correct center: {self.dist:2.13f}",
                "",
                "Press any key to continue!",
            )
        )
        text = self.fig_wrap.fig.text(
            0.50,
            0.1,
            points_str,
            horizontalalignment="center",
            wrap=True,
            bbox=props,
            family="monospace",
        )
        self.pause_var.set(True)
        self.canvas.draw()
        self.wait_variable(self.pause_var)
        text.remove()

    def put_points(self):
        self.points_frame = Frame(self)
        self.points_frame.grid(row=0, column=0)

        Label(self.points_frame, text="Total Points:").grid(
            row=0, column=0, padx=5, sticky="w"
        )
        self.points_counter = Entry(self.points_frame, width=20)
        self.points_counter.insert(0, self.points)
        self.points_counter.grid(row=0, column=1, padx=5, pady=5)
        self.points_counter["state"] = "readonly"

        Label(self.points_frame, text="Points Last Round:").grid(
            row=0, column=2, padx=5, sticky="w"
        )
        self.round_counter = Entry(self.points_frame, width=20)
        self.round_counter.insert(0, self.points)
        self.round_counter.grid(row=0, column=3, padx=5, pady=5)
        self.round_counter["state"] = "readonly"

    def put_figure(self):
        self.canvas = FigureCanvasTkAgg(self.fig_wrap.fig, master=self)
        self.canvas.get_tk_widget().rowconfigure(0, weight=1)
        self.canvas.get_tk_widget().columnconfigure(0, weight=1)
        self.canvas.get_tk_widget().grid(row=1, column=0)
        self.canvas.mpl_connect("key_press_event", self.shortcut_handler)
        self.canvas.mpl_connect("motion_notify_event", self.update_pointer)

    def put_options(self):
        self.options = Frame(self)
        self.options.grid(row=3, column=0)

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

    def closing(self):
        self.destroy()
        self.pause_var.set(False)
        exit(0)

    def shortcut_handler(self, event):
        key = event.key

        if self.pause_var.get():
            self.pause_var.set(False)
            self.canvas.draw_idle()
            return

        elif key in self.shortcuts and event.inaxes == self.mandel_view.ax:
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

            self.dist = abs(self.hyperbolic_center - pointer)

            zs = [pointer, self.hyperbolic_center]

            if 1.5 * self.dist > self.hint_diam:
                view.diam = 1.5 * self.dist
            else:
                view.diam = self.hint_diam

            view.center = 0.5 * self.hyperbolic_center + 0.5 * pointer

            xs, ys = view.z_to_img_coords(zs)
            view.dist_plt.set_data(xs, ys)
            view.update_plot()

            if self.dist > self.hint_diam:
                self.points_last_round = int(4 / self.dist)
            else:
                self.points_last_round = int(4 / self.hint_diam)

            self.points += self.points_last_round

            self.points_counter["state"] = "active"
            self.points_counter.delete(0, END)
            self.points_counter.insert(0, self.points)
            self.points_counter["state"] = "readonly"

            self.round_counter["state"] = "active"
            self.round_counter.delete(0, END)
            self.round_counter.insert(0, self.points_last_round)
            self.round_counter["state"] = "readonly"

            self.finish_round()
            self.new_hint()

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

    def new_hint(self):
        if len(self.roots) == 0:
            return
        self.hyperbolic_center = self.roots.pop(randrange(len(self.roots)))
        self.mandel_hint.init_center = self.hyperbolic_center
        self.mandel_hint.init_diam = 1e-5
        # print("Current root:", self.hyperbolic_center)
        # print("Remaining roots:", len(self.roots))

        self.mandel_hint.update_plot()
        self.mandel_hint.find_zoom()
        self.hint_diam = self.mandel_hint.diam

        self.mandel_view.dist_plt.set_data([], [])
        self.mandel_view.center = self.mandel_view.init_center
        self.mandel_view.diam = self.mandel_view.init_diam
        self.mandel_view.update_plot()

        self.canvas.draw_idle()
