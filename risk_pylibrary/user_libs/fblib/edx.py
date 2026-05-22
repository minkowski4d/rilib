
#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python Modules
import os
import numpy as np
import six as _six
from datetime import date, timedelta, datetime as _datetime

import pandas as pd




def perceptron(vecs, labels, len_sim):

    n = len(vecs)
    theta = np.array([0,0])
    theta_0 = 0
    for t in range(0, len_sim):
        for i in range(0, n):
            if (labels[i] * np.dot(vecs[i], theta)) <= 0:
                theta = theta + labels[i] * vecs[i]
                theta_0 = theta_0 + labels[i]
                print(theta, theta_0)

    return theta


