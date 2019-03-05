# -*- coding: utf-8 -*-

import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc

import flask

import figures
import layouts
import workers

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

server = app.server

app.config['suppress_callback_exceptions'] = True

app.layout = layouts.app_layout()



######################################################################################

# App Callbacks

######################################################################################
    
# Save raw data from pulse files from the upload component
# in hidden html.Divs.
@app.callback(Output('data-tab1', 'children'),
              [Input('upload-files', 'contents')],
              [State('upload-files', 'filename'),
               State('data-tab1', 'children')])
def read_store_uploaded_files(list_of_contents, list_of_names, current_data):
    
    if list_of_contents is not None:
        sorted_contents = [x for _,x in sorted(zip(list_of_names, list_of_contents))]
        sorted_filenames = sorted(list_of_names)
        list_of_data = [workers.load_data(c, n) for c, n in zip(sorted_contents, sorted_filenames)]

        children = [workers.update_database(list_of_data, current_data)]

        return children
    

# Generate 3D scatter plots for all data stored in Tab 1
@app.callback(Output('3d-pulse-figs', 'children'),
              [Input('data-tab1', 'children')])
def generate_scatter3d(raw_pulse_data):
    if raw_pulse_data is not None:
        raw_data = dict(raw_pulse_data[0]['props']['data'])
        children = [figures.scatter3d(raw_data[k], k) for k in raw_data.keys()]

        return children

    

# Generate dropdown in Tab 2 based on uploaded data in Tab 1
@app.callback(Output('amu-dropdown-container', 'children'),
              [Input('data-tab1', 'children')])
def update_amu_dropdown(raw_pulse_data):
    if raw_pulse_data is not None:
        raw_data = dict(raw_pulse_data[0]['props']['data'])
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
              Input('data-tab1', 'children'),
              Input('amu-dropdown', 'value')])
def update_baseline_corr_slider(corr, raw_pulse_data, amu):
    if amu is not None:
        dataset = dict(raw_pulse_data[0]['props']['data'])[amu]
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
               Input('baseline-corr-radioitems', 'value'),
               Input('time-range-slider', 'value'),
               Input('sg-radioitems', 'value'),
               Input('sg-window-size-slider', 'value'),
               Input('sg-order-slider', 'value')])
def perform_correction(raw_pulse_data, amu, corr, timespan, smooth, window_size, order):

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
        
        return [dcc.Store(id='temp', data=corrected_dataset), x]

# Read the temp data and plot the average pulse 
@app.callback(Output('avg-fig-tab2', 'children'),
              [Input('temp-data', 'children')])
def plot_avg_pulse(stuff):
    if stuff is not None:
        data, x = stuff
        pulse_data = data['props']['data']
        children = [figures.scatter(pulse_data, type_of_pulse=x)]

        return children


# Read temp data and append the data under the amu as the key in the overall data dict
@app.callback(Output('data-tab2', 'children'),
              [Input('temp-data', 'children')],
              [State('data-tab2', 'children')])
def store_pulses(stuff, current_data):
    if stuff is not None:
        data, x = stuff
        pulse_data = data['props']['data']
        children = [workers.store_pp_pulses(current_data, pulse_data, x)]
        
        return children


# Monitor and create new link for dynamically modified data, when new data is stored
# in the temp stoarge as the preprocessing is performed by the user.
# The href component of the download button is updated through the
# Flask server route and an xlsx file is generated for download
@app.callback(Output('download-link-1', 'href'),
              [Input('temp-data', 'children')])
def update_link1(stuff):
    data, x = stuff
    pulse_data = data['props']['data']
    amu = '{0:0.1f}'.format(pulse_data['amu'])
    workers.write_temp(pulse_data, x)
    
    return '/dash/url?value={0}'.format(amu)

# Update link 2
@app.callback(Output('download-link-2', 'href'),
              [Input('temp-data', 'children')])
def update_link2(stuff):
    data, x = stuff
    pulse_data = data['props']['data']
    amu = '{0:0.1f}'.format(pulse_data['amu'])
    workers.write_temp(pulse_data, x)
    
    return '/dash/url?value={0}'.format(amu)


# Defining the route for the download link
@app.server.route('/dash/url')
def download_xlsx():
    amu = flask.request.args.get('value')
    downloadlink = workers.create_download_link(amu)

    return downloadlink


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


# Update the inert normalization dropdown based on the amu keys stored in the
# global data dict.
@app.callback(Output('inert-dropdown', 'options'),
              [Input('data-tab2', 'children')])
def update_inert_dropdown(current_data):
    if current_data is not None:
        amus = dict(current_data[0]['props']['data']).keys()
        options = [{'label': '{0}'.format(amu),
                    'value': '{0}'.format(amu)} for amu in amus]
    
        return options
    

@app.callback(Output('inert-output', 'children'),
              [Input('inert-dropdown', 'value')],
              [State('data-tab2', 'children')])
def update_text_do_norm(amu_inert, current_data):
    if amu_inert is not None:
        pulse_data_all = dict(current_data[0]['props']['data'])
        workers.inert_normalization(amu_inert, pulse_data_all)
        return 'Inert species AMU chosen: {0}'.format(amu_inert)


# Update inert normalization download link based on inert-dropdown choice
# Combined xlsx is created on the fly when download button is clicked and
# user the latest data from tab 2
@app.callback(Output('download-link-3', 'href'),
              [Input('inert-dropdown', 'value'),
               Input('data-tab2', 'children')])
def update_link3(amu_inert, value):
    if amu_inert is not None:
        return '/dash/url2?value={0}'.format(amu_inert)

# Defining the route for the download link
@app.server.route('/dash/url2')
def download_xlsx_inert():
    amu_inert = flask.request.args.get('value')
    downloadlink = workers.create_download_link_norm(amu_inert)

    return downloadlink

if __name__ == '__main__':
    app.run_server(debug=True)

