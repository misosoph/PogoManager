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
import pprint
import re
import collections
import datetime

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
# import Pokemon Go API lib
from pgoapi import pgoapi
from pgoapi import utilities as util

log = logging.getLogger(__name__)

# route for handling the login page logic
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        pokemon_list = json.load(open('app/pokemon.json'))
        pokemon_data = json.load(open('app/pogodata.json'))
        pokemon_map = {pokemon_list[str(int(re.match(r"V([0-9]+).*",x['Pokemon']['UniqueId']).group(1)))] : x['Pokemon'] for x in pokemon_data['Items'] if 'Pokemon' in x}
        pokemon_evo_map = {pokemon_list[str(int(re.match(r"V([0-9]+).*",x['Pokemon']['ParentId']).group(1)))] : pokemon_list[str(int(re.match(r"V([0-9]+).*",x['Pokemon']['UniqueId']).group(1)))] for x in pokemon_data['Items'] if 'Pokemon' in x and 'ParentId' in x['Pokemon']}

        if request.form['type'] == "Show Raw Game Data":
            def my_safe_repr(object, context, maxlevels, level):
                typ = pprint._type(object)
                if typ is unicode:
                    object = str(unicode(object).encode("utf-8"))
                return pprint._safe_repr(object, context, maxlevels, level)

            printer = pprint.PrettyPrinter(indent=2)
            printer.format = my_safe_repr
            contents = ('StaticData: \n\r{}'.format(printer.pformat(sorted([x.items()[0] for x in pokemon_data['Items']], key=lambda x:x[0]))))    
            return render_template('results.html', contents=contents)
        # instantiate pgoapi
        api = pgoapi.PGoApi()

    # parse position
        position = util.get_pos_by_name('New York, NY')
        if not position:
            error = 'Your given location could not be found by name'
            return render_template('results.html', contents=error)
    
        # set player position on the earth
        api.set_position(*position)
    
        if not api.login(request.form['auth'], request.form['username'], request.form['password'], app_simulation = True):
            error = 'Login failed for '+request.form['username']
            return render_template('results.html', contents=error)
        else:
            # get player profile + inventory call (thread-safe/chaining example)
            # ----------------------
            req = api.create_request()
            #req.get_player()
            req.get_inventory()
            response_dict = req.call()
            #print(contents)
            
            pokemons = []
            inventory_items = response_dict['responses'] \
                                           ['GET_INVENTORY'] \
                                           ['inventory_delta'] \
                                           ['inventory_items']

            
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
                        iv_percent = (float(attack + defense + stamina) / 45) * 100.0
                        
                        cp_mult = pokemon.get('cp_multiplier', 0)
                        addtl_cp_mult = pokemon.get('additional_cp_multiplier', 0)
    
                        nickname = pokemon.get('nickname', 'NONE')
                        combat_power = pokemon.get('cp', 0)
                        
                        base_attack = pokemon_map[name]['Stats']['BaseAttack']
                        base_defense = pokemon_map[name]['Stats']['BaseDefense']
                        base_stamina = pokemon_map[name]['Stats']['BaseStamina']
                        
                        cap_time = datetime.datetime.fromtimestamp(int(pokemon.get('creation_time_ms', 0)/1000))

                        max_cp_mult = 0.7903001
                        
                        
                        def compute_cp(base_attack, attack, base_defense, defense, base_stamina, stamina, cp_mult, addtl_cp_mult):
                            return ((base_attack + attack) * 
                                        pow(base_defense + defense, .5) * 
                                        pow(base_stamina + stamina, .5) *
                                        pow(cp_mult + addtl_cp_mult, 2))/10
                        
                        computed_cp = compute_cp(base_attack, attack, base_defense, defense, base_stamina, stamina, cp_mult, addtl_cp_mult)
                                        
                        min_final_cp = compute_cp(base_attack, 0, base_defense, 0, base_stamina, 0, max_cp_mult, 0)
                        this_final_cp = compute_cp(base_attack, attack, base_defense, defense, base_stamina, stamina, max_cp_mult, 0)
                        max_final_cp = compute_cp(base_attack, 15, base_defense, 15, base_stamina, 15, max_cp_mult, 0)
                        
                        next_evo = pokemon_evo_map.get(name, '')
                        if next_evo != '':
                            next_evo = pokemon_evo_map.get(next_evo, next_evo)
                        next_evo_stats = pokemon_map.get(next_evo, {}).get('Stats', {})
                        next_evo_cp=''
                        next_evo_sf=''
                        if next_evo != '':
                            next_evo_cp = round(compute_cp(next_evo_stats['BaseAttack'], attack, next_evo_stats['BaseDefense'], defense, next_evo_stats['BaseStamina'], stamina, cp_mult, addtl_cp_mult),2)
                            final_evo_max_cp = compute_cp(next_evo_stats['BaseAttack'], 15, next_evo_stats['BaseDefense'], 15, next_evo_stats['BaseStamina'], 15, cp_mult, addtl_cp_mult)
                            next_evo_sf = round(100 * (1-next_evo_cp/final_evo_max_cp), 2)
                        
                        newRow = collections.OrderedDict([
                            ('name', name),
                            ('cp', combat_power),
                            ('nickname', nickname),
                            ('num', num),
                            ('cap_date', cap_time.strftime('%x')),
                            ('cap_time', cap_time.strftime('%X')),
                            ('attack', attack),
                            ('defense', defense),
                            ('stamina', stamina),
                            ('iv_percent', round(iv_percent,2)),
                            ('cp_mult', round(cp_mult,2)),
                            ('adtl_cp_mult', round(addtl_cp_mult,2)),
                            ('min_final_cp', round(min_final_cp,2)),
                            ('max_final_cp', round(max_final_cp,2)),
                            ('ths_final_cp', round(this_final_cp,2)),
                            ('max_iv_imp', round((max_final_cp/min_final_cp - 1.0)*100,2)),
                            ('this_iv_imp', round((this_final_cp/min_final_cp - 1.0)*100,2)),
                            ('iv_max_sf', round(((max_final_cp-this_final_cp)/min_final_cp)*100,2)),
                            ('final_evo', next_evo),
                            ('final_evo_cp', next_evo_cp),
                            ('final_evo_sf', next_evo_sf)
                            ])
                        pokemons.append(newRow)
                    except KeyError:
                        pass        
            pokemons.sort(key = lambda x:x['cp'], reverse=True)
            if request.form['type'] == "Show My Poke":
                contents = 'Player Pokemon\n\n'
                for key in pokemons[1].keys():
                    contents += '%-10s\t' % key
                for row in pokemons:
                    contents += "\n"
                    for key,value in row.items():
                        contents += '%-10s\t' % (unicode(value).encode("utf-8"))
                return render_template('results.html', contents=contents.decode('utf-8'))
            elif request.form['type'] == "Show My Raw Data":
                contents = ('Response dictionary (get_player + get_inventory): \n\r{}'.format(pprint.PrettyPrinter(indent=2).pformat(sorted([x['inventory_item_data'] for x in inventory_items], key=lambda x:x.keys()[0]))))    
                return render_template('results.html', contents=contents)
            else:
                
                si = StringIO.StringIO()
                cw = csv.writer(si)
                cw.writerow(pokemons[1].keys())
                for row in pokemons:
                    cw.writerow([unicode(x).encode("utf-8") for x in row.values()])
                output = make_response(si.getvalue())
                output.headers["Content-Disposition"] = "attachment; filename=pokemon.csv"
                output.headers["Content-type"] = "text/csv"
                return output
            
    return render_template('index.html')