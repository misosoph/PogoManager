# -*- coding: utf-8 -*-
"""
Created on Mon Aug  1 10:16:37 2016

@author: jleong
"""

#!flask/bin/python
from app import app
app.run(debug=True, host= '0.0.0.0', port=8787)#, ssl_context=('poke.key','poke.pub'))
