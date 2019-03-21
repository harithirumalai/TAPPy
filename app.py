# -*- coding: utf-8 -*-

import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc

import flask
from flask_caching import Cache

import figures
import layouts
import workers
import os
import shutil

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# Local cache settings
cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache-directory',
    'CACHE_THRESHOLD': 50  # should be equal to maximum number of active users
})
cache.clear()

# Enable multithreading through the "Server" call
server = app.server

app.config['suppress_callback_exceptions'] = True

# Set up app layouts
app.layout = layouts.app_layout()


# Create a TAPSuite-data folder in the user's home directory to store temp files
home = os.path.expanduser('~')
savedir = os.path.join(home, 'TAPSuite-data')
if not os.path.exists(savedir):
    os.mkdir(savedir)
else:
    shutil.rmtree(savedir)
    os.mkdir(savedir)


######################################################################################

# App Callbacks

######################################################################################
    
# Save raw data from pulse files from the upload component
# in hidden html.Divs.
@app.callback(Output('data-tab1', 'children'),
              [Input('upload-files', 'contents')],
              [State('upload-files', 'filename'),
               State('data-tab1', 'children')])
@cache.memoize()
def read_store_uploaded_files(list_of_contents, list_of_names, current_data):
    
    if list_of_contents is not None:
        sorted_contents = [x for _,x in sorted(zip(list_of_names, list_of_contents))]
        sorted_filenames = sorted(list_of_names)
        list_of_data = [workers.load_data(c, n) for c, n in zip(sorted_contents, sorted_filenames)]

        children = [workers.update_database(list_of_data, current_data)]

        return children

    
# Store 25 randomly generated pulses in the "condensed-data-tab1" dcc.Storage component
# Use these data in the preprocessing section for faster responses.
@app.callback(Output('condensed-data-tab1', 'data'),
              [Input('data-tab1', 'children')],
              [State('condensed-data-tab1', 'data')])
@cache.memoize()
def store_condensed_tab1(raw_pulse_data, current_cond_data):
    if raw_pulse_data is not None:
        data = workers.store_condensed(raw_pulse_data, current_cond_data)

        return data
                

# Generate 3D scatter plots for all data stored in Tab 1
@app.callback(Output('3d-pulse-figs', 'children'),
              [Input('condensed-data-tab1', 'data')])
def generate_scatter3d(raw_data):
    if raw_data is not None:
        children = [figures.scatter3d(raw_data[k], k) for k in raw_data.keys()]

        return children

    
# Generate dropdown in Tab 2 based on uploaded data in Tab 1
@app.callback(Output('amu-dropdown-container', 'children'),
              [Input('condensed-data-tab1', 'data')])
def update_amu_dropdown(raw_data):
    if raw_data is not None:
        amus = raw_data.keys()
        
        children = [dcc.Dropdown(id='amu-dropdown',
                            options=[{'label': '{0}'.format(amu),
                                      'value': '{0}'.format(amu)}
                                     for amu in amus],

                            style={'width': '49%', 'display': 'inline-block'})]
        return children


# Generate the baseline correction timespan RangeSlider based on whether
# baseline correction is enabled for the AMU chosen by user
@app.callback(Output('baseline-corr-slider', 'children'),
              [Input('baseline-corr-radioitems', 'value'),
               Input('amu-dropdown', 'value')],
              [State('condensed-data-tab1', 'data')])
def update_baseline_corr_slider(corr, amu, raw_data):
    if amu is not None:
        dataset = raw_data[amu]
        children = layouts.baseline_corr_slider(dataset, disable=not(corr))

        return children


# Display the timespan chosen by the RangeSlider
@app.callback(Output('slider-output', 'children'),
              [Input('time-range-slider', 'value')])
def update_time_intervals(time_int):
    if time_int != [1, 1]:
        return 'Time interval chosen: {}'.format(time_int)
    else:
        return 'Baseline correction disabled'


# Display the Savitzky-Golay smoothing components based on user choice
@app.callback(Output('sg-order-slider', 'disabled'),
              [Input('sg-radioitems', 'value')])
def display_sg_order_slider(smooth):
    if smooth is True:
        return False
    else:
        return True

@app.callback(Output('sg-window-size-slider', 'disabled'),
              [Input('sg-order-slider', 'disabled')])
def display_sg_window_slider(order):
    return order


# Update the Savitzky-Golay window size slider based on Order input
@app.callback(Output('sg-window-size-container', 'children'),
              [Input('sg-order-slider', 'value')])
def update_sg_window_size(order):
    return layouts.sg_window_size_slider(order)

    
# Take input from the all input fields
# - baseline correction enabled or disabled
# - baseline correction time span
# - pulse smoothing enabled or disabled
# - pulse smoothing arguments, order and window size

# Perform all operations as set by the user.
# Store corrected data in temp storage. This can be accessed by the user
# to download xlsx files for the chosen amu.
@app.callback(Output('temp-data', 'children'),
              [Input('data-tab1', 'children'),
               Input('amu-dropdown', 'value'),
               Input('time-range-slider', 'value'),
               Input('sg-window-size-slider', 'value'),
               Input('sg-order-slider', 'value')],
              [State('baseline-corr-radioitems', 'value'),
               State('sg-radioitems', 'value')])
def perform_correction(raw_pulse_data, amu, timespan, window_size, order, corr, smooth):
    if amu is not None:        
        if corr is True and smooth is True:
            x = 'baseline corr smooth pulses'
        elif corr is True and smooth is False:
            x = 'baseline corr pulses'
        elif corr is False and smooth is True:
            x = 'smooth pulses'
        else:
            x = 'pulses'

        dataset = dict(raw_pulse_data[0]['props']['data'])[amu]
        corrected_dataset = workers.correct_data(dataset, x, timespan, corr,
                                                 smooth, window_size, order)
        params = [amu, x, timespan, corr, smooth, window_size, order]

        temp_data = {}
        temp_data['data'] = corrected_dataset
        temp_data['params'] = params
        
        return [dcc.Store(id='blah', data=temp_data), x]

    
# Read the temp data and plot the average pulse 
@app.callback(Output('avg-fig-tab2', 'children'),
              [Input('temp-data', 'children')])
def plot_avg_pulse(stuff):
    if stuff is not None:
        temp_data, x = stuff
        pulse_data = temp_data['props']['data']['data']
        children = [figures.scatter(pulse_data, type_of_pulse=x)]

        return children


# Monitor and create new link for dynamically modified data, when new data is stored
# in the temp stoarge as the preprocessing is performed by the user.
# The href component of the download button is updated through the
# Flask server route and an xlsx file is generated for download
@app.callback(Output('download-link-1', 'href'),
              [Input('temp-data', 'children'),
               Input('amu-dropdown', 'value')],
              [State('data-tab1', 'children')])
def update_link1(temp_data_amu, amu, raw_data_dict):
    if amu is not None:
        raw_data = dict(raw_data_dict[0]['props']['data'])[amu]
        amu, x, timespan, corr, smooth, window_size, order = temp_data_amu[0]['props']['data']['params']

        corrected_dataset = workers.correct_data(raw_data, x, timespan, corr,
                                                     smooth, window_size, order)
        
        workers.write_temp(corrected_dataset, x)
        return '/dash/url?value={0}'.format(amu)

    
# Defining the route for the download link and making the xslx available
@app.server.route('/dash/url')
def download_xlsx():
    amu = flask.request.args.get('value')
    downloadlink = workers.create_download_link(amu)
    return downloadlink

    
# Append temp params to existing params in the "temp-data-full" dcc.Store component
@app.callback(Output('full-temp-data', 'data'),
              [Input('temp-data', 'children')],
              [State('full-temp-data', 'data')])
def append_temp_data(stuff, current_temp_data):
    if stuff is not None:
        temp_data, _ = stuff
        data = workers.append_to_temp_data_full(temp_data, current_temp_data)
        return data
           

# Reset data correction sliders to Disabled when amu is changed by user
@app.callback(Output('baseline-corr-radioitems', 'value'),
              [Input('amu-dropdown', 'value')])
def reset_bc_slider(amu):
    return False

# Reset Savitzky Golay sliders when amu is changed by user
@app.callback(Output('sg-radioitems', 'value'),
              [Input('amu-dropdown', 'value')])
def reset_sg_sliders(amu):
    return False


# Apply corrections to full dataset from "data-tab1" based on params stored in "temp-data-full" based on user's choice in "all-corr-radioitems"
@app.callback(Output('data-tab2', 'data'),
              [Input('all-corr-radioitems', 'value'),
               Input('full-temp-data', 'data')],
              [State('data-tab1', 'children'),
               State('data-tab2', 'data')])
def correct_store_pulses(all_corr, temp_data, raw_data_dict, current_temp_data):
    if all_corr is True:
        return workers.correct_full_data(temp_data, raw_data_dict, current_temp_data)


# Display message whether apply-all is enabled or not
@app.callback(Output('apply-all', 'children'),
              [Input('all-corr-radioitems', 'value')])
def corr_status(value):
    if value is True:
        return 'Corrections applied to full data'


# Update the inert normalization dropdown based on the amu keys stored in the
# global data dict.
@app.callback(Output('inert-dropdown-container', 'children'),
              [Input('data-tab2', 'data')])
def update_inert_dropdown(current_data):
    if current_data is not None:
        amus = current_data.keys()
        children = [dcc.Dropdown(id='inert-dropdown',
                                 options=[{'label': '{0}'.format(amu),
                                           'value': '{0}'.format(amu)}
                                          for amu in amus],

                                 style={'width': '99%', 'display': 'inline-block'})]
        return children
    

# Inert normalize all data based on amu choice by user
@app.callback(Output('inert-output', 'children'),
              [Input('inert-dropdown', 'value')],
              [State('data-tab2', 'data')])
def update_text_do_norm(amu_inert, current_data):
    if amu_inert is not None:
        workers.inert_normalization(amu_inert, current_data)
        return 'Inert species AMU chosen: {0}'.format(amu_inert)


# Update inert normalization download link based on inert-dropdown choice
# Combined xlsx is created on the fly when download button is clicked and
# user the latest data from tab 2
@app.callback(Output('download-link-2', 'href'),
              [Input('inert-dropdown', 'value')])
def update_link2(amu_inert):
    if amu_inert is not None:
        return '/dash/url2?value={0}'.format(amu_inert)

# Defining the route for the download link
@app.server.route('/dash/url2')
def download_xlsx_inert():
    amu_inert = flask.request.args.get('value')
    downloadlink = workers.create_download_link_norm(amu_inert)

    return downloadlink

# Run the app
if __name__ == '__main__':
#    app.run_server(debug=True)
    app.run_server(debug=True, processes=6)

