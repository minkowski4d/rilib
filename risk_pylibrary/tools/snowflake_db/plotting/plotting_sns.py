import numpy as np


def format_percentage(value: float, percentage_decimals=2) -> str:
    return str(int(value * 10 ** (2 + percentage_decimals)) / 100) + "%"


def show_values_on_bars(axs, is_percentage=False, percentage_decimals=2):
    """Adds the values on top of the bars for barplots in Seaborn

    Notes:
    Modified from https://stackoverflow.com/a/51535326/8294752
    """

    def _show_on_single_plot(ax, is_percentage=is_percentage):
        for p in ax.patches:
            _x = p.get_x() + p.get_width() / 2
            _y = p.get_y() + p.get_height()
            if is_percentage:
                value = format_percentage(
                    p.get_height(), percentage_decimals=percentage_decimals
                )
            else:
                value = "{:.2f}".format(p.get_height())
            ax.text(_x, _y, value, ha="center")

    if isinstance(axs, np.ndarray):
        for idx, ax in np.ndenumerate(axs):
            _show_on_single_plot(ax)
    else:
        _show_on_single_plot(axs)
