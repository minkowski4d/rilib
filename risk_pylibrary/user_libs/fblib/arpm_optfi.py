#!/usr/bin/env python
# -*- coding: UTF-8 -*-


# Author: Fabio Balloni

# Python Modules
import numpy as np
import scipy
import os

# Plotting
from matplotlib import pyplot as plt




def black_scholes_model(S, K, rf, sigma, tau, direction, verbose):
    """
    The Black–Scholes(-Merton) model

    @param S: underyling price, e.g. 100
    @param K: strike price, e.g. 115
    @param rf: riskfree rate, e.g. 0.01
    @param sigma: underlying volatility, e.g. 0.2%
    @param tau: time span (holding period until maturity), e.g. 150
    @param direction: str, 'call' or 'put'
    @param verbose: 1 or 0
    @return: price, delta, d1 and d2
    """

    if verbose:
        print('\n\t Calculating d_1 and d_2 with the Black-Scholes-Merton model')

    # Calculating d_1 and d_2:
    d1 = (np.log(S / K) + (rf + 0.5 * sigma ** 2) * tau) / (sigma * np.sqrt(tau))
    d2 = d1 - sigma * np.sqrt(tau)

    # Calculating the price
    if direction == 'call':
        price = S * scipy.stats.norm.cdf(d1) - K * np.exp(-rf*tau) * scipy.stats.norm.cdf(d2)

    elif direction == 'put':
        price = K * np.exp(-rf * tau) * scipy.stats.norm.cdf(-d2) - S * scipy.stats.norm.cdf(-d1)

    # Calculating the delta
    if verbose:
        print('\t Calculating the delta')
    if direction == 'call':
        delta = scipy.stats.norm.cdf(d1)
    if direction == 'put':
        delta = -scipy.stats.norm.cdf(-d1)


    return price, delta, d1, d2


def black_model(F, K, rf, sigma, tau, direction, verbose):
    """
    The Black (or Black76 model)

    @param F: underlying price, e.g. 100
    @param K: strike price, e.g. 115
    @param rf: riskfree rate, e.g. 0.01
    @param sigma: underlying volatility, e.g. 0.2
    @param tau: time span (holding period until maturity), e.g. 150
    @param direction: str, 'call' or 'put'
    @param verbose: 1 or 0
    @return: price, delta, d1 and d2
    """

    if verbose:
        print('\n\t Calculating d_1 and d_2 with the Black model')

    # Calculating d_1 and d_2:
    d1 = (np.log(F / K) + 0.5 * sigma ** 2 * tau) / (sigma * np.sqrt(tau))
    d2 = d1 - sigma * np.sqrt(tau)

    # Calculating the price
    if direction == 'call':
        price = np.exp(-rf * tau) * (F * scipy.stats.norm.cdf(d1) - K * scipy.stats.norm.cdf(d2))

    elif direction == 'put':
        price = np.exp(-rf * tau) * (K * scipy.stats.norm.cdf(-d2) - F * scipy.stats.norm.cdf(-d1))

    # Calculating the delta
    if verbose:
        print('\t Calculating the delta')
    if direction == 'call':
        delta = scipy.stats.norm.cdf(d1)
    if direction == 'put':
        delta = -scipy.stats.norm.cdf(-d1)

    return price, delta, d1, d2


def option_contour_plot(s_start, s_end, tau_start, tau_end, K, rf, sigma, model, direction,verbose):
    """
    Option Price contour plot. Chart over underlying price and time span (holding period).
    Contour lines and color bar are the option's prices


    @param s_start: start price, e.g. 100
    @param s_end: end price, e.g. 120
    @param tau_start: start time, e.g. 1
    @param tau_end: end time, e.g. 150
    @param K: strike price, e.g. 115
    @param rf: riskfree rate, e.g. 0.01
    @param sigma: underlying volatility, e.g. 0.2
    @param model: str, option pricing model, e.g. 'bsm' or 'black'
    @param direction: str, 'call' or 'put'
    @param verbose: 1 or 0
    @return: figure
    """

    # Define the range for underlying prices S and expiry T
    s_values = np.linspace(s_start, s_end, 200)  # underlying prices from 90 to 105
    T_values = np.linspace(tau_start/365, tau_end/365, 200)  # Maturity times from 1 day to 120 days

    # Create a meshgrid for the inputs
    S, T = np.meshgrid(s_values, T_values)

    # Compute the put option prices for the grid
    if model == 'bsm':
        opt_prices, opt_deltas, opt_d1s, opt_d2s = black_scholes_model(S, K, rf, sigma, T, direction, verbose)
    elif model == 'black':
        opt_prices, opt_deltas, opt_d1s, opt_d2s = black_model(S, K, rf, sigma, T, direction, verbose)


    # Plot the contour plot
    fig_opt_price = plt.figure(figsize=(10,6),facecolor="white")
    contour = plt.contourf(S, T, opt_prices, levels=15, cmap="coolwarm")
    plt.colorbar(contour,label="Option Price")
    contour_lines = plt.contour(S, T, opt_prices, levels=15, colors='black', linewidths=0.5)
    plt.clabel(contour_lines, inline=True, fontsize=8)

    # Add labels and title
    plt.xlabel("Underlying Price")
    plt.ylabel("Time span")
    plt.title("European %s option price (%s model) at K=%s"%(direction,model,K))

    # Show the plot
    return fig_opt_price



def black_model_interest_sensitivity(F, K, rf, sigma, tau, direction):
    """
    Calculation of the interste rate sensitivity. The formula are achieved by building
    the derivative of dP/dy.

    @param F: underlying price, e.g. 100
    @param K: strike price, e.g. 115
    @param rf: riskfree rate, e.g. 0.01
    @param sigma: underlying volatility, e.g. 0.2
    @param tau: time span, e.g. 0.3 years
    @param direction: str, 'call' or 'put'
    @return: interest rate sensitivity
    """

    # Calculate prices, deltas etc
    opt_prices,opt_deltas,opt_d1s,opt_d2s = black_model(F, K, rf, sigma, tau, direction, 0)


    # Compute interest rate sensitivity
    if direction == 'call':
        ir_sensitivity = np.exp(-rf * tau) * (F * scipy.stats.norm.cdf(opt_d1s) # Sensitivity of N(d1)
                                              - K * (-tau / (sigma * np.sqrt(tau)))*scipy.stats.norm.pdf(opt_d2s)) # Sensitivity of N(d2)
    elif direction == 'put':

        ir_sensitivity = + np.exp(-rf * tau) * (
                - K * (-scipy.stats.norm.pdf(opt_d2s) * tau / (sigma * np.sqrt(tau)))  # Sensitivity of N(-d2)
                - tau * F * scipy.stats.norm.cdf(-opt_d1s)  # Sensitivity of F with respect to r
                - F * (-scipy.stats.norm.pdf(opt_d1s) * tau / (sigma * np.sqrt(tau)))) # Sensitivity of N(-d1)


    return ir_sensitivity



def plot_black_model_interest_sensitivity(f_start, f_end, tau_start, tau_end, K, rf, direction, sigma):
    """
    3D contour plot of the interest sensitivity over underlying price and time span

    Time span start and end points need to be given in days. Adjustment for years is applied
    within the function

    @param f_start: underlying price start, e.g. 100
    @param f_end: underlying price end, e.g. 100
    @param tau_start: time span start in days, e.g. 1
    @param tau_end: time span end in days, e.g. 150
    @param K: strike price, e.g. 115
    @param rf: riskfree rate, e.g. 0.01
    @param direction: 'call' or 'put'
    @param sigma: underlying volatility, e.g. 0.2
    @return: figure
    """

    # Define parameters for plotting
    F_range = np.linspace(f_start, f_end, 100)
    T_range = np.linspace(tau_start/365, tau_end/365, 100)

    # Calculate Black Model Call Duration over the ranges
    F_mesh,T_mesh = np.meshgrid(F_range, T_range)
    opt_ir_sens_values = np.zeros_like(F_mesh)

    for i in range(F_mesh.shape[0]):
        for j in range(F_mesh.shape[1]):
            F = F_mesh[i,j]
            tau = T_mesh[i,j]
            opt_ir_sens_values[i,j] = black_model_interest_sensitivity(F, K, rf, sigma, tau/365, direction)

    # Plot the results
    fig_opt_ir_sens = plt.figure(figsize=(10,7))
    ax = fig_opt_ir_sens.add_subplot(111, projection='3d')
    ax.plot_surface(F_mesh, T_mesh, opt_ir_sens_values, cmap='coolwarm', edgecolor='none')#viridis
    ax.set_xlabel('Future Price')
    ax.set_ylabel('Maturity Time (years)')
    ax.set_zlabel('Option Interest Rate Sensitivity (Duration)')
    plt.title('Black Model: %s option interest rate sensitivity at K=%s'%(direction,K))

    return fig_opt_ir_sens



def plot_black_model_price_sensitivity(f_start, f_end, tau_start, tau_end, K, rf, direction, sigma):
    """
    3D contour plot of the price sensitivity over underlying price and time span

    Time span start and end points need to be given in days. Adjustment for years is applied
    within the function

    @param f_start: underlying price start, e.g. 100
    @param f_end: underlying price end, e.g. 100
    @param tau_start: time span start in days, e.g. 1
    @param tau_end: time span end in days, e.g. 150
    @param K: strike price, e.g. 115
    @param rf: riskfree rate, e.g. 0.01
    @param direction: 'call' or 'put'
    @param sigma: underlying volatility, e.g. 0.2
    @return: figure
    """

    # Define parameters for plotting
    F_range = np.linspace(f_start, f_end, 100)
    T_range = np.linspace(tau_start/365, tau_end/365, 100)

    # Calculate Black Model Call Duration over the ranges
    F_mesh,T_mesh = np.meshgrid(F_range, T_range)
    opt_prx_sens_values = np.zeros_like(F_mesh)

    for i in range(F_mesh.shape[0]):
        for j in range(F_mesh.shape[1]):
            F = F_mesh[i,j]
            tau = T_mesh[i,j]
            opt_prx_sens_values[i,j] = black_model(F, K, rf, sigma, tau, direction, 0)[1]

    # Plot the results
    fig_opt_ir_sens = plt.figure(figsize=(10,7))
    ax = fig_opt_ir_sens.add_subplot(111, projection='3d')
    ax.plot_surface(F_mesh, T_mesh, opt_prx_sens_values, cmap='coolwarm', edgecolor='none')#viridis
    ax.set_xlabel('Future Price')
    ax.set_ylabel('Maturity Time (years)')
    ax.set_zlabel('Option Price Sensitivity (Delta)')
    plt.title('Black Model: %s option price sensitivity at K=%s'%(direction,K))

    return fig_opt_ir_sens


if __name__ == "__main__":

    print("****************************************************************\n")
    print("On Options On Fixed Income Futures\n")

    print("\n******** Pricing: Black-Scholes-Merton vs. Black\n")

    print("\tUsing the following inputs for option pricing")
    print("\t\t Underlying price: 110")
    print("\t\t Strike price: 115")
    print("\t\t Riskfree rate: 5%")
    print("\t\t Underlying volatility: 20%")
    print("\t\t Time span: 150 days")

    print("\tPricing with Black-Scholes-Merton")
    # Executing BSM:
    price_bsm, delta_bsm, d1_bsm, d2_bsm = black_scholes_model(110, 115, 0.05, 0.2, 150, 'put', 0)

    print("\t\t Put Option price (BSM): %s"%np.round(price_bsm,2))
    print("\t\t Put Delta (BSM)       : %s" % np.round(delta_bsm,2))

    print("\tPricing with Black")
    # Executing BSM:
    price_bl, delta_bl, d1_bl, d2_bl = black_model(110, 115, 0.05, 0.2, 150, 'put', 0)

    print("\t\t Put Option price (Black): %s" % np.round(price_bl, 2))
    print("\t\t Put Delta (Black)       : %s" % np.round(delta_bl, 2))

    print("\n******** Pricing: contour plots for Black-Scholes-Merton and Black\n")

    print("\tPlotting deltas for Black-Scholes-Merton")
    # Plotting
    fig_opt_delta_bsm = option_contour_plot(105, 115, 1, 120, 110, 0.05, 0.2, 'bsm', 'put', 0)
    fig_opt_delta_black = option_contour_plot(105, 115, 1, 120, 110, 0.05, 0.2, 'black', 'put', 0)
    fig_opt_delta_black_3D = plot_black_model_interest_sensitivity(105,115,1,250,110,0.05,'put',0.2)

    # Saving .jpegs
    fig_opt_delta_bsm.savefig('opt_price_bsm.jpeg', dpi=600)
    fig_opt_delta_black.savefig('opt_price_black.jpeg', dpi=600)
    fig_opt_delta_black_3D.savefig('opt_price_3D_put_black.jpeg', dpi=600)


    print("\n******** Interest Rate Sensitivity: Black model\n")

    print("\tCalculating the interest rate sensitivity with the Black model")

    ir_sens = black_model_interest_sensitivity(110, 115, 0.05, 0.2, 150, 'put')

    print("\t\t Put Option interest rate sensitivity (Black): %s" % np.round(ir_sens,2))


    print("\n******** Interest rate sensitivity: 3D contour plots for Black model\n")
    # Plotting
    fig_opt_ir = plot_black_model_interest_sensitivity(105, 115, 1, 250, 110, 0.05, 'put', 0.2)

    # Saving .jpeg
    fig_opt_ir.savefig('opt_ir_3D_put_black.jpeg', dpi=600)






