#!/usr/bin/env python
# -*- coding: UTF-8 -*-


# Standard Models
import numpy as np

# Model Specific Modules
import statsmodels.api as sm
from scipy.optimize import curve_fit



def ols_predict(df, out_of_sample=True, pred_length=10, add_fit=False, scenario={'lin_damp':{'low':0.85,'high':1.15}}, verbose=True):
    """
    OLS PRediction Model
    @param df:
    @param out_of_sample:
    @param pred_length:
    @param add_fit:
    @param scenario:
    @param verbose:
    @return:
    """
    # Import Modules
    import matplotlib.pyplot as plt

    if verbose:
        print('Initialising OLS prediction *******************')
    x1 = np.linspace(df.iloc[:, 1].min(), df.iloc[:, 1].max(),len(df))
    X = df.iloc[:, 1].values
    X_const = sm.add_constant(X)
    y = df.iloc[:, 0].values

    if add_fit:
        # curve fit
        if verbose:
            print('\t Fitting curve with 4th grade polynom')
        parameters, covariance = curve_fit(polynom_fourth_grade, x1, y)
        fit_y = polynom_fourth_grade(x1, parameters[0], parameters[1], parameters[2], parameters[3], parameters[4])

    # Calling Statsmodel OLS modul
    ols_model = sm.OLS(y, X_const)
    ols_results = ols_model.fit()
    if verbose:
        print('\t %s'%ols_results.summary())

    # Predict y-values
    y_pred = ols_results.predict(X_const)

    if out_of_sample:
        # Create dictionary output
        dict_predict = dict()

        # Run Standard Prediction
        x1_oos = np.linspace(df.iloc[:, 1].max(), df.iloc[:, 1].max()*1.1, pred_length)
        X_oos_const = sm.add_constant(x1_oos)
        dict_predict['ols_oos_predict'] = ols_results.predict(X_oos_const)  # predict out of sample

        # Add scenarios
        if scenario is not None:
            for mod in scenario.keys():
                for scen in scenario[mod].keys():
                    x1_tmp = np.linspace(df.iloc[:, 1].max(), df.iloc[:, 1].max() * 1.1, pred_length)
                    x1_tmp[1:] = x1_tmp[1:] * scenario[mod][scen]
                    X_tmp_const = sm.add_constant(x1_tmp)
                    dict_predict[str(mod)+'_'+str(scen)] = ols_results.predict(X_tmp_const)  # predict out of sample



    fig, ax = plt.subplots()
    ax.plot(x1, y, "o", label="Data")
    if add_fit:
        ax.plot(x1, fit_y, "#ffA500", label="Fit")
    if out_of_sample:
        for prd_oos in dict_predict.keys():
            if prd_oos == 'ols_oos_predict':
                ax.plot(np.hstack((x1, x1_oos)), np.hstack((y_pred, dict_predict['ols_oos_predict'])), "r", label="OLS prediction")
            else:
                lbl = 'Optimistic' if prd_oos.split('_')[-1] == 'high' else 'Pessimistic'
                ax.plot(np.hstack((x1, x1_oos)), np.hstack((y_pred, dict_predict[prd_oos])), "r--", label=lbl)
    else:
        ax.plot(x1, y_pred, "r", label="OLS prediction")
    ax.legend(loc="best")

    return fig


def lsq(y, x, add_constant=True, stats=False):
    """
    quick and simple least squares implementation without relying on external packages
    """

    from numpy.linalg import inv

    if add_constant:
        x = np.c_[np.ones(x.shape[0]), x]
    inv_xx = inv(np.dot(x.T, x))
    xy = np.dot(x.T, y)
    b = np.dot(inv_xx, xy)
    out = np.empty((3, x.shape[1]))

    out[0, :] = b
    if stats:
        df_e = y.shape[0] - x.shape[1]
        e = y - np.dot(x, b)
        sse = np.dot(e, e)/df_e
        out[2, :] = np.diagonal(sse*inv_xx)
        se = np.sqrt(out[2, :])
        with np.errstate(divide = 'ignore', invalid = 'ignore'):
            out[1, :] = b/se
        return out
    else:
        return out[0, :]


def polynom_fourth_grade(x, A, B, C, D, E):

    y = A * x ** 4 + B * x ** 3 + C * x ** 2 + D * x + E

    return y
