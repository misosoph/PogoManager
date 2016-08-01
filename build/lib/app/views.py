# -*- coding: utf-8 -*-
"""
Created on Mon Aug  1 10:15:27 2016

@author: jleong
"""

from app import app
from flask import Flask, render_template, redirect, url_for, request
import logging 

import os
import sys
import json
import time
import pprint
import logging
import getpass
import argparse
# import Pokemon Go API lib
from pgoapi import pgoapi
from pgoapi import utilities as util

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
log = logging.getLogger(__name__)

# route for handling the login page logic
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # instantiate pgoapi
        api = pgoapi.PGoApi()

    # parse position
        position = util.get_pos_by_name('New York, NY')
        if not position:
            log.error('Your given location could not be found by name')
            return
    
        # set player position on the earth
        api.set_position(*position)
    
        if not api.login('google', request.form['username'], request.form['password'], app_simulation = True):
            contents = 'Login failed for '+request.form['username']
        else:
            # get player profile + inventory call (thread-safe/chaining example)
            # ----------------------
            req = api.create_request()
            req.get_player()
            req.get_inventory()
            response_dict = req.call()
            contents = ('Response dictionary (get_player + get_inventory): \n\r{}'.format(pprint.PrettyPrinter(indent=4).pformat(response_dict)))    
            return render_template('results.html', contents=contents)
    return render_template('index.html')