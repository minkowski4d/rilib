#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python modules
import sys
from datetime import datetime as _datetime

class ProgressBar:
    """
        displays animated progress bar

    Usage:
        ids=some list
        p=Progressbar(len(ids))
        for i,id in enumerate(ids):
            p.animate(i+1)
            #do some stuff with id
    """

    def __init__(self, iterations, show_numbers=False, show_ETA=False):
        self.iterations = iterations
        self.prog_bar = '[]'
        self.fill_char = '*'
        self.width = 50
        self.show_numbers = show_numbers
        self.show_ETA = show_ETA
        self.start_dt = _datetime.now()
        self.__update_amount(0)
        self.animate = self.animate_ipython

    def animate_ipython(self, iter):

        self.update_iteration(iter)
        if iter < self.iterations:
            print('\r', self, end=' ')
        else:
            print('\r', self)
            if self.show_ETA:
                el = (_datetime.now() - self.start_dt).seconds
                print("Elapsed time: %02i:%02i:%02i" % (
                int(el / 3600.0), int((el % 3600.0) / 60.0), int((el % 3600.0 % 60.0))))
        sys.stdout.flush()

    def update_iteration(self, elapsed_iter):
        self.__update_amount((elapsed_iter / float(self.iterations)) * 100.0)
        if self.show_numbers:
            self.prog_bar += (' %' + str(len(str(self.iterations))) + 'd of %s') % (elapsed_iter, self.iterations)
        if self.show_ETA:
            sec_elapsed = _datetime.now() - self.start_dt
            avg = sec_elapsed / elapsed_iter
            self.prog_bar += ' ETA:%s' % ((self.iterations - elapsed_iter) * avg + _datetime.now()).strftime(
                '%Y-%m-%d %H:%M:%S')

    def __update_amount(self, new_amount):
        percent_done = int(round((new_amount / 100.0) * 100.0))
        all_full = self.width - 2
        num_hashes = int(round((percent_done / 100.0) * all_full))
        self.prog_bar = '[' + self.fill_char * num_hashes + ' ' * (all_full - num_hashes) + ']'
        pct_place = int((len(self.prog_bar) / 2) - len(str(percent_done)))
        pct_string = '%d%%' % percent_done
        self.prog_bar = self.prog_bar[0:pct_place] +\
                        (pct_string + self.prog_bar[pct_place + len(pct_string):])

    def __str__(self):
        return str(self.prog_bar)
