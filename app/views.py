# -*- coding: utf-8 -*-
"""
Created on Mon Aug  1 10:15:27 2016

@author: jleong
"""

from app import app
from flask import render_template, request, make_response
import logging 
import os
import sys
import json
import StringIO
import csv

# import Pokemon Go API lib
from pgoapi import pgoapi
from pgoapi import utilities as util

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
log = logging.getLogger(__name__)

# route for handling the login page logic
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            pokemon_list = json.load(open('app/pokemon.en.json'))
        except IOError, error:
            print "The selected language is currently not supported"
            return render_template('results.html', contents=error)

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
            #req.get_player()
            req.get_inventory()
            response_dict = req.call()
            #contents = ('Response dictionary (get_player + get_inventory): \n\r{}'.format(pprint.PrettyPrinter(indent=4).pformat(response_dict)))    
            #print(contents)
            
            pokemons = []
            inventory_items = response_dict['responses'] \
                                           ['GET_INVENTORY'] \
                                           ['inventory_delta'] \
                                           ['inventory_items']

            
            si = StringIO.StringIO()
            cw = csv.writer(si)
            cw.writerow(['id',
                            'name',
                            'nickname',
                            'num',
                            'cp',
                            'attack',
                            'defense',
                            'stamina',
                            'iv_percent'])
            for item in inventory_items:
                try:
                    reduce(dict.__getitem__, ["inventory_item_data", "pokemon_data"], item)
                except KeyError:
                    pass
                else:
                    try:
                        pokemon = item['inventory_item_data']['pokemon_data']
    
                        pid = pokemon['id']
                        num = int(pokemon['pokemon_id'])
                        name = pokemon_list[str(num)]
    
                        attack = pokemon.get('individual_attack', 0)
                        defense = pokemon.get('individual_defense', 0)
                        stamina = pokemon.get('individual_stamina', 0)
                        iv_percent = (float(attack + defense + stamina) / 45.0) * 100.0
    
                        nickname = pokemon.get('nickname', 'NONE')
                        combat_power = pokemon.get('cp', 0)
    
                        pokemons.append({
                            'id': pid,
                            'name': name,
                            'nickname': nickname,
                            'num': num,
                            'cp': combat_power,
                            'attack': attack,
                            'defense': defense,
                            'stamina': stamina,
                            'iv_percent': iv_percent,
                        })
                        cw.writerow([unicode(pid).encode("utf-8"),
                            unicode(name).encode("utf-8"),
                            unicode(nickname).encode("utf-8"),
                            unicode(num).encode("utf-8"),
                            unicode(combat_power).encode("utf-8"),
                            unicode(attack).encode("utf-8"),
                            unicode(defense).encode("utf-8"),
                            unicode(stamina).encode("utf-8"),
                            unicode(iv_percent).encode("utf-8")])
                    except KeyError:
                        pass            
                
            
            
            output = make_response(si.getvalue())
            output.headers["Content-Disposition"] = "attachment; filename=export.csv"
            output.headers["Content-type"] = "text/csv"
            return output
#            contents=pokemons
#            return render_template('results.html', contents=contents)
    return render_template('index.html')