#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python Modules
import sys
import numpy as np
import matplotlib.pyplot as plt
from arch import arch_model
from scipy.stats import t, norm
import seaborn as sns
from datetime import datetime as _datetime, date, timedelta
import random
import pandas as pd





class almgren_chriss_model():


    def __init__(self, randomSeed, prx, sim_length, num_n):
        pass

        random.seed(randomSeed)

        self.prx_df = prx
        self.start_price = 100
        self.sigma = prx.std().iloc[0]
        self.sim_length = sim_length
        self.liquidation_time = 30 #holding period of 30 days
        self.tau = self.liquidation_time / num_n 



    def simulate_price(self):
        
        # Calculate the current stock price using arithmetic brownian motion
        price_sim = pd.DataFrame(index=range(self.sim_length))

        for k in range(self.sim_length):
            if k == 0:
                price_sim.loc[k, 'price'] = self.start_price + self.sigma * np.sqrt(self.tau) * random.normalvariate(0, 1) 
            else:
                price_sim.loc[k, 'price'] = price_sim.loc[k-1, 'price'] + self.sigma * np.sqrt(self.tau) * random.normalvariate(0, 1) 
            
        return price_sim


def plot_price_model(seed = 0, num_days = 1000):
    
    # Create a simulation environment
    env = almgren_chriss_model()

    # Reset the enviroment with the given seed
    env.reset(seed)

    # Create an array to hold the daily stock price for the given number of days
    price_hist = np.zeros(num_days)

    # Get the simulated stock price movement from the environment
    for i in range(num_days):
        _, _, _, info = env.step(i)    
        price_hist[i] = info.price
    
    # Print Average and Standard Deviation in Stock Price
    print('Average Stock Price: ${:,.2f}'.format(price_hist.mean()))
    print('Standard Deviation in Stock Price: ${:,.2f}'.format(price_hist.std()))
#     print('Standard Deviation of Random Noise: {:,.5f}'.format(np.sqrt(env.singleStepVariance * env.tau)))
    
    # Plot the price history for the given number of days
    price_df = pd.DataFrame(data = price_hist,  columns = ['Stock'], dtype = 'float64')
    ax = price_df.plot(colormap = 'cool', grid = False)
    ax.set_facecolor(color = 'k')
    ax = plt.gca()
    yNumFmt = mticker.StrMethodFormatter('${x:,.2f}')
    ax.yaxis.set_major_formatter(yNumFmt)
    plt.ylabel('Stock Price')
    plt.xlabel('days')
    plt.show()


def almgren_chriss_simple():

    # Almgren-Chriss model parameters
    T = 1.0  # Total time to execute (normalized to 1)
    N = 50  # Number of trading intervals
    X = 10000  # Total shares to sell
    sigma = 0.02  # Daily volatility of the stock price (as a fraction)
    eta = 0.01  # Permanent market impact coefficient
    gamma = 0.001  # Temporary market impact coefficient
    lambda_risk_aversion = 1e-6  # Risk aversion parameter

    # Discretize time
    time_intervals = np.linspace(0, T, N + 1)
    dt = T / N

    # Calculate kappa (determines the shape of the optimal trajectory)
    kappa = np.sqrt(lambda_risk_aversion * sigma**2 / gamma)

    # Calculate the optimal trading trajectory
    sinh_kappa_T = np.sinh(kappa * T)
    trajectory = np.array([
        X * (np.sinh(kappa * (T - t)) / sinh_kappa_T + (t / T)) for t in time_intervals
    ])

    # Calculate trading rates (shares to trade in each interval)
    trading_rates = np.diff(trajectory) / dt

    # Plot the results
    plt.figure(figsize=(12, 6))

    # Plot trajectory
    plt.subplot(2, 1, 1)
    plt.plot(time_intervals, trajectory, label="Cumulative Shares Sold", color="blue")
    plt.title("Almgren-Chriss Optimal Execution Trajectory")
    plt.xlabel("Time")
    plt.ylabel("Shares Remaining")
    plt.grid(True)
    plt.legend()

    # Plot trading rates
    plt.subplot(2, 1, 2)
    plt.bar(time_intervals[:-1], trading_rates, width=dt, color="orange", label="Trading Rate")
    plt.xlabel("Time")
    plt.ylabel("Shares Sold per Interval")
    plt.title("Trading Rates")
    plt.grid(True)
    plt.legend()

    plt.tight_layout()
    plt.show()
