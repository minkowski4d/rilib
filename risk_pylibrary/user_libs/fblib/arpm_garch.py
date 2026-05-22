#!/usr/bin/env python
# -*- coding: UTF-8 -*-


# Author: Fabio Balloni

# Python Modules
import numpy as np
import pandas as pd
import scipy
import os

# Plotting
from matplotlib import pyplot  as plt
import matplotlib.gridspec as gridspec
from matplotlib.ticker import PercentFormatter



def generate_random_returns(mu=None, sigma2=None, sim_len=None):
    """
    Returns are generated via Monte Carlo Method by using mean, drift and number of observations of the historical
    S&P 500 returns (01-01-2001 to 23-02-2023).
    Mean: 0.000272
    Standard Deviation: 0.012193

    @return: dataframe
    """

    # Parameter Definition:
    if mu is None: mu = 0.000272
    if sigma2 is None: sigma2 = 0.012193
    if sim_len is None: sim_len = 5000

    # MonteCarlo Random Return Generator:
    rets_sim = np.random.normal(mu, sigma2, sim_len)

    # Formatting:
    rets = pd.DataFrame(rets_sim, columns=['returns'])

    return rets



def standard_garch_likelihood(parameters, rets):
    """
    Calculate negative log-likelihood for GARCH(1,1) model.
    """

    # Assign Variables
    c_variable, a_variable, b_variable = parameters

    # Set horizon T and epsilon
    T = len(rets)
    epsilon = rets - rets.mean()

    # Assign conditional variance output
    sigma2 = np.zeros(T)
    sigma2[0] = rets.var()

    for t in range(1, T):
        sigma2[t] = (c_variable + a_variable * epsilon[t - 1] ** 2 + b_variable * sigma2[t - 1])

    loglik = -0.5 * np.sum(np.log(2 * np.pi) + np.log(sigma2) + epsilon ** 2 / sigma2)

    # loglik needs to be returned with a negative sign because of the optimisation over minimise

    return -loglik



def gjr_garch_likelihood(parameters, rets):
    """
    Calculate negative log-likelihood for GJR-GARCH(1,1,1) model based on returns, variance
    """

    # Assign Variables
    c_variable, a_variable, d_variable, b_variable = parameters

    # Set horizon T and epsilon
    T = len(rets)
    epsilon = rets - rets.mean()

    # Assign conditional variance output
    sigma2 = np.zeros(T)
    sigma2[0] = rets.var()

    for t in range(1, T):
        sigma2[t] = (c_variable + a_variable * epsilon[t - 1] ** 2
                     + d_variable * epsilon[t - 1] ** 2 * (epsilon[t - 1] < 0) # =0 with d_variable=0 -> standard garch
                     + b_variable * sigma2[t - 1])

    loglik = -0.5 * np.sum(np.log(2 * np.pi) + np.log(sigma2) + epsilon ** 2 / sigma2)

    # loglik needs to be returned with a negative sign because of the optimisation over minimise

    return -loglik



def calculate_conditional_volatility(results, rets, garch_model):
    """
    Conditional GARCH volatility function. Addresses two types of GARCH models
    @param results: dictionary, optimisation results
    @param rets: dataframe of decimal returns
    @param garch_model: str, 'standard' or 'gjr'
    @return: np.array, conditional volatility
    """

    # Calculate conditional volatility
    sigma2 = np.zeros(len(rets))
    epsilon = rets.iloc[:, 0] - rets.iloc[:,0].mean()

    # Initialize conditional variance
    sigma2[0] = rets.iloc[:,0].var()

    # Recursively calculate conditional variances
    for t in range(1, len(rets)):
        if garch_model == 'standard':
            # Set parameters
            c_variable, a_variable, b_variable = results.x
            sigma2[t] = (c_variable + a_variable * epsilon[t - 1] ** 2 + b_variable * sigma2[t - 1])

        elif garch_model == 'gjr':
            # Set parameters
            c_variable, a_variable, d_variable, b_variable = results.x
            sigma2[t] = (c_variable + a_variable * epsilon[t - 1] ** 2
                         + d_variable * epsilon[t - 1] ** 2 * (epsilon[t - 1] < 0)  # =0 with d_variable=0 -> standard garch
                         + b_variable * sigma2[t - 1])


    return np.sqrt(sigma2)  # Return standard deviations



def run_garch_analysis(rets, garch_model='standard', verbose=False):
    """
    GARCH analysis function
    @param rets: dataframe, decimal returns
    @param garch_model: str, 'standard' or 'gjr'
    @param verbose: boolean, prints message if True
    @return: dataframe, sigma as conditional volatility
    """

    if verbose:
        print("****************************************************************\n")
        print("1. Generating Random Returns\n")


    # Set GARCH environment
    if garch_model == 'standard':
        garch_likelihood = standard_garch_likelihood
        # Setting Start Values for Optimizer Iterations
        start_values = np.array([0.01, 0.01, 0.01])

        # Setting Boundaries
        bounds = [(1e-6, None), (1e-6, 1), (1e-6, 1)]
        # Setting Standard GARCH constraint
        constr_fun = lambda x: 1 - (x[1] + x[2])

    elif garch_model == 'gjr':
        garch_likelihood = gjr_garch_likelihood
        start_values = np.array([0.01, 0.01, 0.01, 0.01])

        # Setting Boundaries
        bounds = [(1e-6, None), (1e-6, None), (1e-6, 1), (1e-6, 1)]
        # Setting Standard GARCH constraint
        constr_fun = lambda x: 1 - (x[1] - x[2] / 2 - x[3])


    # Optimize likelihood
    estimates = scipy.optimize.minimize(garch_likelihood,
                                        start_values,
                                        args=(np.asarray(rets.iloc[:, 0]),),
                                        method='L-BFGS-B',
                                        bounds=bounds,
                                        constraints={'type': 'ineq', 'fun': constr_fun},
                                        options={'maxiter': 1000, 'ftol': 1e-5})

    # Evaluate Estimates
    if estimates.success is False:
        raise Exception('\t\t Optimization failed')

    # Calculate conditional volatility
    sigma = calculate_conditional_volatility(estimates, rets, garch_model)

    return sigma



def run_value_at_risk_backtest(rets_orig, bt_length=1500, scaling_factor=5000, qtl=0.99, loss_distr='normal', plot=False, verbose=True):
    """
    This function performs the actual backtest of the Value-At-Risk by using a parametric appraoch for the GARCH models.
    Additionally, a historical simulation is calculated with a window of 250 days.

    A scaling factor is applied to the returns in order to guarantee convergence of the optimisation.

    Conditional volatility can be either multplied with the z-score of the normal distribution or the student-t distribution
    (5 degrees of freedom) for simulating heavy tails in the market and opting for a more conservative approach.

    @param rets_orig: dataframe, decimal returns
    @param bt_length: integer, lookback period, default: 1500
    @param scaling_factor: integer, multiplcation factor of decimal returns, default: 5000
    @param qtl: decimal, quantile, default: 0.99
    @param loss_distr: str, 'normal' or 't'
    @param plot:
    @param verbose:
    @return:
    """



    if verbose:
        print("\n****************************************************************\n")
        print("Initialising Value-At-Risk backtest\n")

    # Set returns
    rets = rets_orig.copy()
    rets = rets[-bt_length:]

    if verbose: print("\tCalculating GARCH conditional variance\n")

    # Set output
    out = rets.copy()
    out.columns = ['Returns']
    out['Conditional Variance - GARCH'] = run_garch_analysis(rets * scaling_factor, garch_model='standard')/scaling_factor
    out['Conditional Variance - GJR GARCH'] = run_garch_analysis(rets * scaling_factor, garch_model='gjr')/scaling_factor


    if verbose: print("\tCalculating parametric Value-At-Risk")

    # Derive z-scores for given distribution:
    if verbose: print("\t\t Applying z-score of %s distribution \n"%loss_distr)
    if loss_distr == 'normal':
        z_score_qtl = scipy.stats.norm.ppf(1-qtl)
    elif loss_distr == 't':
        z_score_qtl = scipy.stats.t.ppf(1-qtl, 5)

    # Calculate parametric VaR
    out['GARCH VaR 1D, %s Confidence' % "{:.0%}".format(qtl)] = out['Conditional Variance - GARCH'] * z_score_qtl
    out['GJR GARCH VaR 1D, %s Confidence' % "{:.0%}".format(qtl)] = out['Conditional Variance - GJR GARCH'] * z_score_qtl

    # Add historical simulation VaR for comparison purpose. As an example on a 250 days lookback window
    out['Hist. Simulation VaR 1D, %s Confidence' % "{:.0%}".format(qtl)] = out['Returns'].rolling(250).quantile(1 - qtl).values

    # Shift returns by -1 fpr plotting purpose as VaR is forecasted
    out['Returns Shifted'] = out['Returns'].shift(-1)
    out = out.dropna()


    if plot:
        if verbose:
            print("****************************************************************\n")
            print("Plotting results\n")

            print("****************************************************************\n")
            print("\t\t Plotting GJR GARCH Backtest\n")


        # GJR GARCH plot
        fig_garch_gjr = plt.figure(figsize=(12, 5), facecolor="white")
        gs = gridspec.GridSpec(1, 1, wspace=0, hspace=0, bottom=0.1, left=0.08, right=0.95, top=0.9)
        ax0 = plt.subplot(gs[0])
        out['GJR GARCH VaR 1D, %s Confidence'%"{:.0%}".format(qtl)].plot(ax=ax0, legend=False)

        # Set returns and exceedances colors
        c = []
        for idx in out.index:
            if out.loc[idx, 'Returns Shifted'] > out.loc[idx, 'GJR GARCH VaR 1D, %s Confidence'%"{:.0%}".format(qtl)]:
                c.append('#000000')
            elif out.loc[idx, 'Returns Shifted'] < out.loc[idx, 'GJR GARCH VaR 1D, %s Confidence'%"{:.0%}".format(qtl)]:
                c.append('#820909')

        # Draw returns and exceedances scatter
        c = np.array(c, dtype='object')
        labels = {'#820909': "1% Exceedance", '#000000': "No Exceedance"}
        markers = {'#820909': 'x', '#000000': 'o'}
        marker_sizes = {'#820909': 10, '#000000': 5.5}
        for color in np.unique(c):
            sel = c == color
            ax0.scatter(out.index[sel], out.loc[sel, 'Returns Shifted'],
                        s=marker_sizes[color],
                        marker=markers[color],
                        c=c[sel],
                        label=labels[color])

        # Format canvas
        ax0.set_title('Parametric VaR - GJR GARCH VaR 1D, %s Confidence'%"{:.0%}".format(qtl))
        ax0.legend(frameon=True,loc='best')
        plt.gca().yaxis.set_major_formatter(PercentFormatter(1))

        # Save figure
        fig_garch_gjr.savefig('VaR_GJR_GARCH_bt_%s.jpeg'%loss_distr, dpi=300, bbox_inches='tight')
        plt.close(fig_garch_gjr)


        # Standard GARCH plot
        if verbose:
            print("****************************************************************\n")
            print("\t\t Plotting Standard GARCH Backtest\n")

        fig_garch_standard = plt.figure(figsize=(12, 5), facecolor="white")
        gs = gridspec.GridSpec(1, 1, wspace=0,hspace=0, bottom=0.01, left=0.08, right=0.95, top=0.75)
        ax1 = plt.subplot(gs[0])
        out['GARCH VaR 1D, %s Confidence' % "{:.0%}".format(qtl)].plot(ax=ax1,color='#2CD5C4', legend=False)

        # Set returns and exceedances colors
        c = []
        for idx in out.index:
            if out.loc[idx, 'Returns Shifted'] > out.loc[idx, 'GARCH VaR 1D, %s Confidence'%"{:.0%}".format(qtl)]:
                c.append("#000000")
            elif out.loc[idx, 'Returns Shifted'] < out.loc[idx, 'GARCH VaR 1D, %s Confidence'%"{:.0%}".format(qtl)]:
                c.append("#820909")

        # Draw returns and exceedances scatter
        c = np.array(c, dtype="object")
        labels = {"#820909": "1% Exceedance", "#000000": "No Exceedance"}
        markers = {"#820909": "x", "#000000": "o"}
        marker_sizes = {"#820909": 10, "#000000": 5.5}
        for color in np.unique(c):
            sel = c == color
            ax1.scatter(out.index[sel], out.loc[sel, 'Returns Shifted'],
                        s=marker_sizes[color],
                        marker=markers[color],
                        c=c[sel],
                        label=labels[color])

        # Format canvas
        ax1.set_title('Parametric VaR - GARCH VaR 1D, %s Confidence'% "{:.0%}".format(qtl))
        ax1.legend(frameon=True, loc='best')
        plt.gca().yaxis.set_major_formatter(PercentFormatter(1))

        fig_garch_standard.savefig('VaR_Standard_GARCH_bt_%s.jpeg'%loss_distr,dpi=300,bbox_inches='tight')
        plt.close(fig_garch_standard)



        # Historical Simulation plot
        if verbose:
            print("****************************************************************\n")
            print("\t\t Plotting Historical Simulation Backtest\n")

        fig_hs = plt.figure(figsize=(12, 5), facecolor="white")
        gs = gridspec.GridSpec(1, 1, wspace=0,hspace=0, bottom=0.01, left=0.08, right=0.95, top=0.75)
        ax2 = plt.subplot(gs[0])

        # Slicing at first full window
        out['Hist. Simulation VaR 1D, %s Confidence' % "{:.0%}".format(qtl)].plot(ax=ax2, color='#e2ae1d',legend=False)

        # Set returns and exceedances colors
        c = []
        for idx in out.index:
            if out.loc[idx, 'Returns Shifted'] > out.loc[idx, 'Hist. Simulation VaR 1D, %s Confidence' % "{:.0%}".format(qtl)]:
                c.append("#000000")
            elif out.loc[idx, 'Returns Shifted'] < out.loc[idx, 'Hist. Simulation VaR 1D, %s Confidence' % "{:.0%}".format(qtl)]:
                c.append("#820909")

        # Draw returns and exceedances scatter
        c = np.array(c, dtype="object")
        labels = {"#820909": "1% Exceedance", "#000000": "No Exceedance"}
        markers = {"#820909": "x", "#000000": "o"}
        marker_sizes = {"#820909": 10, "#000000": 5.5}
        for color in np.unique(c):
            sel = c == color
            ax2.scatter(out.index[sel], out.loc[sel, 'Returns Shifted'],
                        s=marker_sizes[color],
                        marker=markers[color],
                        c=c[sel],
                        label=labels[color])

        # Format canvas
        ax2.set_title('Historical Simulation VaR 1D, %s Confidence'% "{:.0%}".format(qtl))
        ax2.legend(frameon=True,loc='best')
        plt.gca().yaxis.set_major_formatter(PercentFormatter(1))

        fig_hs.savefig('VaR_HS_bt.jpeg',dpi=300,bbox_inches='tight')
        plt.close(fig_hs)



        # VaR comparison plot
        if verbose:
            print("****************************************************************\n")
            print("\t\t Plotting VaR Comparison\n")

        fig_vaR_comp = plt.figure(figsize=(12, 5), facecolor="white")
        gs = gridspec.GridSpec(1, 1, wspace=0,hspace=0, bottom=0.01, left=0.08, right=0.95, top=0.75)
        ax3 = plt.subplot(gs[0])
        out['GJR GARCH VaR 1D, %s Confidence' % "{:.0%}".format(qtl)].plot(ax=ax3,legend=False)
        out['GARCH VaR 1D, %s Confidence' % "{:.0%}".format(qtl)].plot(ax=ax3,color='#2CD5C4',legend=False)
        out['Hist. Simulation VaR 1D, %s Confidence' % "{:.0%}".format(qtl)].plot(ax=ax3, color='#e2ae1d',legend=False)

        # Format canvas
        ax3.set_title('VaR Comparison - GJR GARCH vs Standard GARCH vs Historical Simulation')
        ax3.legend(frameon=True,loc='best')
        plt.gca().yaxis.set_major_formatter(PercentFormatter(1))

        fig_vaR_comp.savefig('VaR_comparison_%s.jpeg'%loss_distr,dpi=300,bbox_inches='tight')
        plt.close(fig_vaR_comp)



    return out


if __name__ == "__main__":
    rets_orig = pd.read_pickle('sp500_returns.pkl')
    out = run_value_at_risk_backtest(rets_orig,
                                     scaling_factor=5000,
                                     qtl=0.99,
                                     loss_distr='normal',
                                     bt_length=1750,
                                     plot=True,
                                     verbose=True)