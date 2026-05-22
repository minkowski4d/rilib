#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import numpy as np
from scipy.stats import kurtosis, skew


# Define constants for SRI categories
MARKET_RISK_CLASSES = {
    1: "Very Low Risk",
    2: "Low Risk",
    3: "Medium-Low Risk",
    4: "Medium Risk",
    5: "Medium-High Risk",
    6: "High Risk",
    7: "Very High Risk",
}

CREDIT_RISK_CLASSES = {
    1: "Very Low Risk",
    2: "Low Risk",
    3: "Medium-Low Risk",
    4: "Medium Risk",
    5: "Medium-High Risk",
    6: "High Risk",
}

def calculate_market_risk_category(volatility: float) -> int:
    """
    Calculate the market risk category based on volatility.
    Args:
        volatility (float): Annualized standard deviation of returns.
    Returns:
        int: Market risk category (1-7).
    """
    if volatility < 0.005:
        return 1
    elif volatility < 0.05:
        return 2
    elif volatility < 0.12:
        return 3
    elif volatility < 0.20:
        return 4
    elif volatility < 0.30:
        return 5
    elif volatility < 0.80:
        return 6
    else:
        return 7


def calculate_credit_risk_category(credit_rating: str) -> int:
    """
    Map a credit rating to a credit risk category.
    Args:
        credit_rating (str): Credit rating (e.g., "AAA", "BB").
    Returns:
        int: Credit risk category (1-6).
    """
    rating_map = {
        "AAA": 1, "AA": 1, "A": 2, "BBB": 3,
        "BB": 4, "B": 5, "CCC": 6, "CC": 6, "C": 6
    }
    return rating_map.get(credit_rating.upper(), 6)


def calculate_vev_cornish_fisher(rets_orig, verbose):
    """
    Calculate the Value at End of Volatility (VeV) using the Cornish-Fisher expansion.

    See: https://www.esma.europa.eu/sites/default/files/library/jc_2017_49_priips_flow_diagram_risk_reward_rev.pdf

    Args:
        returns (np.ndarray): Array of historical returns.
    Returns:
        float: Adjusted annualized volatility.

    """
    
    # Slice Incoming Returns for 5 years or 1280 observations (see paragraph 10 of Annex II)
    # Using 365 (number of days) – 104 (number of weekend days) – 5 (public holidays) = 256 days
    rets = np.asarray(rets_orig[-1280:])

    # Set Moments:
    # Number of observations in the period 256*5=1280
    m_0 = 1280
    m_1 = np.mean(rets)
    m_2 = np.var(rets)
    m_3 = np.sum((rets - m_1)**3) / m_0
    m_4 = np.sum((rets - m_1)**4) / m_0

    # Set sigma, mu_1 (skew) and mu_2 (kurtosis):
    sigma = np.sqrt(m_2)
    mu_1 = m_3 / sigma**3
    mu_2 = m_4 / sigma**4 - 3


    # Calculate VaRs:
    # Return Space
    vaR_ret_space = sigma * np.sqrt(10) * (-1.96 + 0.474 * mu_1/np.sqrt(10) - 0.0687 * mu_2/10 + 0.146 * mu_1**2)/10 - 0.5 * sigma**2 * 10
    
    # Rescale to Price Space
    vev = (np.sqrt(3.842 - 2 * vaR_ret_space) - 1.96)/np.sqrt(10/250)

    if verbose:
        print("\nCalculating SRI ************************************************************\n")
        print("Moments: \n")
        for ith_mom in [m_0, m_1, m_2, m_3, m_4]:
            print("\t\t m_%s = %s"%(str([m_0, m_1, m_2, m_3, m_4].index(ith_mom)),ith_mom))
        
        print("\n Volatility sigma, Skew mu_1 and Excess Kurtosis mu_2 \n")
        print("\t\t sigma = %s"%sigma)
        print("\t\t mu_1 = %s"%mu_1)
        print("\t\t mu_2 = %s"%mu_2)

        print("VaRs: \n")
        print("\t\t VaR Return Space = %s"%vaR_ret_space)
        print("\t\t VaR Price Space = %s"%vev)


    return vev, calculate_market_risk_category(vev)



def calculate_sri(market_risk: int, credit_risk: int) -> int:
    """
    Calculate the Summary Risk Indicator (SRI).
    Args:
        market_risk (int): Market risk category (1-7).
        credit_risk (int): Credit risk category (1-6).
    Returns:
        int: SRI (1-7).
    """
    return max(market_risk, credit_risk)

# Example usage
def main(historical_returns, verbose):
    # Inputs
    #historical_returns = np.array([0.001, -0.002, 0.003, 0.004, -0.001])  # Example: daily returns
    credit_rating = "BB"      # Example: BB credit rating

    # Calculate adjusted annualized volatility (VeV using Cornish-Fisher)
    annual_volatility = calculate_vev_cornish_fisher(historical_returns, verbose)

    # Calculate risk categories
    market_risk_category = calculate_market_risk_category(annual_volatility[0])
    #credit_risk_category = calculate_credit_risk_category(credit_rating)

    # Calculate SRI
    #sri = calculate_sri(market_risk_category, credit_risk_category)
    sri = market_risk_category

    # Output results
    print("Adjusted Annualized Volatility (VeV):", annual_volatility)
    print("Market Risk Category:", MARKET_RISK_CLASSES[market_risk_category])
    #print("Credit Risk Category:", CREDIT_RISK_CLASSES[credit_risk_category])
    print("Summary Risk Indicator (SRI):", sri)

if __name__ == "__main__":
    main()
