# -*- coding: utf-8 -*-

import dash_html_components as html
import dash_core_components as dcc

import numpy as np
import plotly.graph_objs as go
import matplotlib.pyplot as plt

colors = plt.rcParams['axes.prop_cycle'].by_key()['color']

def scatter3d(pulse_data, k):
    n_time_pts = len(pulse_data['times'])
    index = pulse_data['index']
    n_pulses = len(pulse_data['pulses'])

    xdata = np.array([pulse_data['times'],]*n_pulses)
    zdata = pulse_data['pulses']
    ydata = np.array([[i+1]*n_time_pts for i in range(n_pulses)])
    

    fig = html.Div([
        html.H5('AMU={0}'.format(k)),
        dcc.Graph(
            id='3d_fig-{0}'.format(k),
            
            figure={'data': [go.Scatter3d(x=x1, z=z1, y=y1,
                                          mode='lines',
                                          name='AMU={0:0.1f}'.format(pulse_data['amu']),
                                          showlegend=False,
                                          line={'width':1.0,
                                                'color':colors[index]},
                                          opacity=1)
                             for x1, z1, y1 in zip(xdata, zdata, ydata)],
                    
                    'layout': go.Layout(scene={'xaxis': {'title': {'text': 'Time (s)',
                                                                   'font': {'size': 20}},
                                                         'visible': True,
                                                         'type': 'linear',
                                                         'tickmode': 'auto',
                                                         'nticks': 6},
                                               'yaxis': {'title': {'text': 'Pulse #',
                                                                   'font': {'size': 20}},
                                                         'visible': True,
                                                         'type': 'linear'},
                                               'zaxis': {'title': {'text': 'Signal (V)',
                                                                   'font': {'size': 20}},
                                                         'visible': True,
                                                         'type': 'linear',
                                                         'tickmode': 'auto',
                                                         'nticks': 6,
                                                         'exponentformat': 'E'}},
                                        autosize=True,
                                        height=600, width=800,
                                        margin={'l': 20, 'b': 20, 't': 0, 'r': 0})
            },
            config={'showSendToCloud': True}),
        html.Hr()],
                    
        style={'width': '49%', 'display': 'inline-block', 'textAlign': 'center'}) 

    return fig

def scatter(pulse_data, type_of_pulse):
    k = pulse_data['index']
    fig = html.Div([
        dcc.Graph(
            id='avg_fig-{0}'.format(pulse_data['index']),
            figure={'data': [go.Scattergl(x=pulse_data['times'],
                                        y=np.mean(pulse_data[type_of_pulse], axis=0),
                                        name='{0:0.1f}'.format(pulse_data['amu']),
                                        mode='lines',
                                        opacity=1.0,
                                        line={'color':colors[k]})],
                    
                    'layout': go.Layout(xaxis={'title': {'text': 'Time (s)',
                                                         'font': {'size': 20}},
                                               'ticks': 'outside',
                                               'tickwidth': 2,
                                               'showgrid': True},
                                        yaxis={'title': {'text': 'Signal (V)',
                                                         'font': {'size': 20}},
                                               'ticks': 'outside',
                                               'exponentformat': 'E',
                                               'tickwidth': 2,
                                               'showgrid': True},
                                        hovermode='closest',
                                        showlegend=True,
                                        height=450,
                                        margin={'l': 80, 'b': 80, 't': 40, 'r': 0})},
            config={'showSendToCloud': True})],
                   
        style={'width': '99%', 'display': 'inline-block'})

    return fig
