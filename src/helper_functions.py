# -*- coding: utf-8 -*-

from typing import Iterable
from copy import deepcopy

####################################

def add_dict(base_dict, dict_to_add):
    """
    Take a base dictionary and add the values 
    from another dictionary to it.

    Contrary to standard dict update methods,
    this function does not overwrite values in the
    base dictionary. Instead, it is meant to add
    the values of the second dictionary to the values
    in the base dictionary. The dictionary is modified in-place.

    For example:

    >> base = {"A" : 1, "B" : {"c" : 2, "d" : 3}, "C" : [1, 2, 3]}
    >> add = {"A" : 1, "B" : {"c" : 1, "e" : 1}, "C" : [4], "D" : 2}
    >> add_dict(base, add)

    will create a base dictionary:
    
    >> base
    {'A': 2, 'B': {'c': 3, 'd': 3, 'e': 1}, 'C': [1, 2, 3, 4], 'D': 2}

    The function can handle different types of nested structures.
    - Integers and float values are summed up.
    - Lists are appended
    - Sets are added (set union)
    - Dictionaries are added recursively
    For other value types, the base dictionary is left unchanged.

    Input: Base dictionary and dictionary to be added.
    Output: Base dictionary.
    """

    #For each key in second dict
    for key, val in dict_to_add.items():

        #It is already in the base dict
        if key in base_dict:

            #It has an integer or float value
            if isinstance(val, (int, float)) \
                and isinstance(base_dict[key], (int, float)):

                #Increment value in base dict
                base_dict[key] += val

            #It has an iterable as value
            elif isinstance(val, Iterable) \
                and isinstance(base_dict[key], Iterable):

                #List
                if isinstance(val, list) \
                    and isinstance(base_dict[key], list):
                    #Append
                    base_dict[key].extend(val)
                
                #Set
                elif isinstance(val, set) \
                    and isinstance(base_dict[key], set):
                    #Set union
                    base_dict[key].update(val)

                #Dict
                elif isinstance(val, dict) \
                    and isinstance(base_dict[key], dict):
                    #Recursively repeat
                    add_dict(base_dict[key], val)
                
                #Something else
                else:
                    #Do nothing
                    pass

            #It has something else as value
            else:
                #Do nothing           
                pass

        #It is not in the base dict
        else:
            #Insert values from second dict into base
            base_dict[key] = deepcopy(val)

    return base_dict

###################################
