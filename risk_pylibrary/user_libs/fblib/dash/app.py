# Import required libraries

import copy
import pathlib
import dash
import math
from datetime import datetime as _datetime, date
import pandas as pd
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import dash_table
#TRLIB  import visdcc
import importlib

# Import Python Modules
import sys
import numpy as np
import os, sys
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(os.path.dirname(os.path.dirname(currentdir)))
sys.path.append(parentdir)


print("**********************************************************************************************************************")

# get relative data folder
PATH = pathlib.Path(__file__).parent


# *************** Load Modules ***************
from risk_pylibrary import cache_data as cad
from risk_pylibrary.tools import config as cf

# *************** Execute Preliminary Codes ***************
# 1. Cache Data
cad.cache_load()
df_prx = cf.cache_prices


# *************** Starting Dash App Code ***************
app = dash.Dash(__name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}])
server = app.server

layout = dict(
    autosize=True,
    automargin=True,
    margin=dict(l=30, r=30, b=20, t=40),
    hovermode="closest",
    plot_bgcolor="#F9F9F9",
    paper_bgcolor="#F9F9F9",
    legend=dict(font=dict(size=10), orientation="h"),
    title="Dummy",
)
# Print Test
# Create app layout
app.layout = html.Div(
    [
        dcc.Store(id="aggregate_data"),
        html.Div(id="output-clientside"),
        html.Div(
            html.Div(
                [html.Div(
                    [html.Img(
                        src=app.get_asset_url("trade_republic_logo.png"),
                        id="risk-logo-image_0",
                        style={"height": "80px", "width": "auto", "margin-bottom": "25px"})],
                    className="one-third column"),
                    html.Div([
                        html.Div([
                            html.H2("Trade Republic - Risk Reporting", style={"margin-bottom": "0px"})
                        ])
                    ],
                        className = "one-half column", id = "title")],
                id="header", className="row flex-display", style={"margin-bottom": "25px"})
        ),
        html.Div(
            dcc.Tabs([
                dcc.Tab(label='Constantine', children=[
                    html.Div([html.H3("Description", style = {"margin-bottom": "0px"})
                              ])
                ]),
                dcc.Tab(label='Caracalla', children=[
                    html.Div([html.H3("Description", style = {"margin-bottom": "0px"})
                              ]),
                    dcc.Tabs([
                        dcc.Tab(label='Statistics', children=[], selected_style = {'padding': '6px'}),
                        dcc.Tab(label='Model Validation', children=[], selected_style = {'padding': '6px'}),
                        dcc.Tab(label='Data Quality', children=[], selected_style = {'padding': '6px'})
                    ], colors={"primary" : "#fab432"}, style = {'height': '44px'})
                ]),
                dcc.Tab(label='Tiberius', children=[
                    html.Div([html.H3("Description", style = {"margin-bottom": "0px"})
                              ])
                ]),
            ], style = {'fontWeight': 'bold'})
        ),
    ],
    id="mainContainer",
    style={"display": "flex", "flex-direction": "column"},
)

# Main
if __name__ == "__main__":
    app.run_server(debug=True)

