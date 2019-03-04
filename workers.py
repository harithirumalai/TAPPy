# -*- coding: utf-8 -*-

import dash_html_components as html
import dash_core_components as dcc

import io
import base64
import numpy as np
import pandas as pd
from flask import send_file
import os
import shutil
from pandas import ExcelWriter
from scipy.integrate import trapz

import sys
sys.path.append(r'..')


from TAPSuite import read_raw
from TAPSuite import savitzky_golay

# Create a TAPSuite-data folder in the user's home directory to store files
home = os.path.expanduser('~')
savedir = os.path.join(home, 'TAPSuite-data')
if not os.path.exists(savedir):
    os.mkdir(savedir)
else:
    shutil.rmtree(savedir)
    os.mkdir(savedir)

    
# Function that obtains the filepath from the STATE of the callback and reads
# the pulse files using the TAPSuite.read_raw() function
def load_data(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    pulse_data = read_raw(io.BytesIO(decoded))

    return pulse_data
    #return save_data(pulse_data, filename)


def store_data(temp, data):
    if data is not None:        
        amu = '{0:0.1f}'.format(data[0][0])
        temp[amu] = data.tolist()
        return dcc.Store(id='pp-data', data=temp)

    else:
        return dcc.Store(id='pp-data', data=temp)


def append_data(temp, list_of_data):
    if len(list_of_data) is not None:
        for data in list_of_data:
            temp_data_amus = temp.keys()
            amu = '{0:0.1f}'.format(data['amu'])
            n = temp_data_amus.count(amu)

            if n > 0:
                amu = amu + '-{0}'.format(n+1)

            temp[amu] = data
        
        return dcc.Store(id='raw-data', data=temp)

    else:
        return dcc.Store(id='raw_data', data=temp)
    
    
def update_database(list_of_data, current_data):
    if current_data is not None:
        temp = dict(current_data[0]['props']['data'])
        return append_data(temp, list_of_data)

    else:
        temp = {}
        return append_data(temp, list_of_data)

# Function the saves temporary pre-processed .npy files and updates
# as the user makes changes in tab 2
def write_temp(data, x):
    t = data['times']
    amu = data['amu']
    tf = np.array(t).reshape(1, len(t))
    pulses = np.array(data[x])

    avg = np.mean(pulses, axis=0)
    avg1 = avg.reshape(1, len(avg))
        
    c1 = np.array([float(amu)] * pulses.shape[1])
    c1f = c1.reshape(1, len(c1))

    d1 = np.append(c1f, tf, axis=0)
    d2 = np.append(d1, avg1, axis=0)
    final_data = np.append(d2, pulses, axis=0)

    np.save('{0}.npy'.format(os.path.join(savedir, '{0:0.1f}'.format(amu))), final_data)

            

# Function that stores data on the fly based on pre-processing performed by
# the user. Updates the overall storage dict if it exists, else creates new dict
def store_pp_pulses(current_data, data, pulse_type):
    if data is not None:
        t = data['times']
        amu = data['amu']
        tf = np.array(t).reshape(1, len(t))
        pulses = np.array(data[pulse_type])

        avg = np.mean(pulses, axis=0)
        avg1 = avg.reshape(1, len(avg))
        
        c1 = np.array([float(amu)] * pulses.shape[1])
        c1f = c1.reshape(1, len(c1))

        d1 = np.append(c1f, tf, axis=0)
        d2 = np.append(d1, avg1, axis=0)
        final_data = np.append(d2, pulses, axis=0)

        if current_data is not None:
            temp = dict(current_data[0]['props']['data'])
            return store_data(temp, final_data)

        else:
            temp = {}
            return store_data(temp, final_data)

                         
# Function that reads raw data in Tab 1 and returns data set corresponding to
# the AMU chosen
def select_dataset(raw_data, amu):
    if raw_data and amu:
        dataset = raw_data[amu]
        return dataset


# Function that loads data and the baseline correction timespan as arguments
# and corrects the baseline for all pulses, returns the entire dataset
def correct_data(data, x, timespan, corr, smooth, window_size, order):
    pulses = np.array([np.array(pulse) for pulse in data['pulses']])
    times = np.array(data['times'])

    if corr is True:
        t1, t2 = timespan
        indx = (times>=t1) & (times<=t2)

        select_pulses = np.array([pulse[indx] for pulse in pulses])
        avg_spans = np.mean(select_pulses, axis=1)
        corr_pulses = np.array([pulse - avg_spans[i] for i, pulse in enumerate(pulses)])
    
        if smooth is True:
            smooth_pulses = np.array([savitzky_golay(pulse,
                                                     window_size=window_size,
                                                     order=order)
                                      for pulse in corr_pulses])
            data[x] = smooth_pulses
        else:
            data[x] = corr_pulses

    else:
        if smooth is True:
            smooth_pulses = np.array([savitzky_golay(pulse,
                                                     window_size=window_size,
                                                     order=order)
                                      for pulse in pulses])
            data[x] = smooth_pulses

        else:
            data[x] = pulses

    return data


def get_areas(pulses, t):
    areas = np.array([trapz(pulse, t) for pulse in pulses])

    return areas


def inert_normalization(amu_inert, pulses_data_all):
    
    normdir = os.path.join(savedir, 'normalized')
    if not os.path.exists(normdir):
        os.mkdir(normdir)        
    
    pulses_combined, amus = [], []
    for amu in pulses_data_all.keys():
        stuff = np.array(pulses_data_all[amu])
        amus.append(amu)
        pulses_combined.append(stuff[3:])
        times = stuff[1]


    inert_index = amus.index(amu_inert)
    pulses_areas = [get_areas(pulses, times) for pulses in pulses_combined]
    inert_areas = pulses_areas[inert_index]
    inert_coeffs = np.array(inert_areas / max(inert_areas))

    for (pulses, amu) in zip(np.array(pulses_combined), amus):
        norm_pulses = np.array([pulse/k for (pulse, k) in zip(pulses, inert_coeffs)])
        times_r = times.reshape(1, len(times))

        c1 = np.array([float(amu)] * norm_pulses.shape[1])
        c1f = c1.reshape(1, len(c1))
        
        avg = np.mean(norm_pulses, axis=0)
        avg1 = avg.reshape(1, len(avg))

        d1 = np.append(c1f, times_r, axis=0)
        d2 = np.append(d1, avg1, axis=0)
        final_pulses = np.append(d2, norm_pulses, axis=0)
         
        np.save('{0}-i.npy'.format(os.path.join(normdir, '{0}'.format(amu))), final_pulses)


# Function that creates a download link from a dynamic xlsx file created in the code.
# This creates a Flask server route with this downloadable link.
def create_download_link(amu):
    stuff = np.load(os.path.join(savedir, str(amu+'.npy')))

    cols = ['AMU'] + ['Time'] + ['Avg'] + [str(i) for i in range(1, stuff.shape[0]-2)]
    df = pd.DataFrame(np.transpose(stuff), columns=cols)
    amu = df['AMU'].iloc[0]
    del df['AMU']
    
    buf = io.BytesIO()
    excel_writer = ExcelWriter(buf)
    df.to_excel(excel_writer, sheet_name="Pulses", index=False)
    excel_writer.save()
    buf.seek(0)
    
    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        attachment_filename='AMU={0:0.1f}.xlsx'.format(amu),
        as_attachment=True,
        cache_timeout=0)


def create_download_link_norm(amu_inert):

    normdir = os.path.join(savedir, 'normalized')
    buf = io.BytesIO()
    excel_writer = ExcelWriter(buf)
    pulse_files = os.listdir(normdir)
    
    for pulse_file in pulse_files:
        stuff = np.load(os.path.join(normdir, pulse_file))

        cols = ['AMU'] + ['Time'] + ['Avg'] + [str(i)
                                               for i in range(1, stuff.shape[0]-2)]
        df = pd.DataFrame(np.transpose(stuff), columns=cols)
        amu = df['AMU'].iloc[0]
        del df['AMU']

        df.to_excel(excel_writer, sheet_name='{0:0.1f}'.format(amu), index=False)
    
    excel_writer.save()
    buf.seek(0)
    
    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        attachment_filename='{0}-inert-normalized.xlsx'.format(amu_inert),
        as_attachment=True,
        cache_timeout=0)
