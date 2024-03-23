"""Contains basic filtering and smoothing logic.
"""

import numpy as np
import logging
from scipy.ndimage import gaussian_filter
from configs import SIGMA
from plotconfigs import SCALAR_PARAMS, VECTOR_PARAMS, FILTER_SPECS

def eval_binary(op1, oper, op2, val):
    import operator
    ops = {
        '>': operator.gt,
        '>=': operator.ge,
        '<': operator.lt,
        '<=': operator.le
    }
    return np.where(ops[oper](op1, op2), val, np.nan)

def _execute_filtering(data):
    """
    Helper function to perform the filtering of a particular parameter based on any number
    of additional parameters.

    If a bad parameter is passed (i.e. one that's not specified in the config file or
    misstyped, etc.), no actions are performed on the data dictionary.

    Parameters:
    -----------
    data: list of dictionaries
        A list of dictionaries, with each entry corresponding to a model time step or
        forecast hour, containing the data to be filtered and smoothed

    Returns:
    --------
    data: list of dictionaries
        Filtered and smoothed data. Same form as input.

    """
    for t in range(len(data)):
        v = list(data[t].keys())
        for parm_to_filter in FILTER_SPECS.keys():
            idx = [i for i, s in enumerate(v) if parm_to_filter in s]
            if len(idx) > 0:
                filter_rules = FILTER_SPECS[parm_to_filter]

                # Loop through the filtering rules and apply each sequentially.
                for parm, operand in filter_rules.items():
                    idx_2 = [i for i, s in enumerate(v) if parm in s]

                    # Filter parameter is a vector. Convert to magnitude
                    if len(idx_2) == 2:
                        magnitude = np.sqrt(data[t][v[idx_2[0]]]**2 + \
                                            data[t][v[idx_2[1]]]**2)
                        data[t][v[idx[0]]] = eval_binary(magnitude, operand[0],
                                                         operand[1], data[t][v[idx[0]]])
                        if len(idx) == 2:
                            data[t][v[idx[1]]] = eval_binary(magnitude, operand[0],
                                                             operand[1],
                                                             data[t][v[idx[1]]])

                    # Scalar value
                    elif len(idx_2) == 1:
                        data[t][v[idx[0]]] = eval_binary(data[t][v[idx_2[0]]], operand[0],
                                                         operand[1], data[t][v[idx[0]]])
                        if len(idx) == 2:
                            data[t][v[idx[1]]] = eval_binary(data[t][v[idx_2[0]]],
                                                             operand[0], operand[1],
                                                             data[t][v[idx[1]]])
                    # Undefined/misstyped in the config file
                    else:
                        logging.warning('filtering variable %s not defined' % (parm))
            else:
                logging.warning('Parameter %s not in data dictionary' % (parm_to_filter))
    return data

def filter(data):
    """
    Perform smoothing and data filtering

    Parameters:
    -----------
    data: list of dictionaries
        A list of dictionaries, with each entry corresponding to a model time step or
        forecast hour, containing the data to be filtered and smoothed

    Returns:
    --------
    data: list of dictionaries
        Filtered and smoothed data. Same form as input.
    """
    for t in range(len(data)):
        vars_ = list(data[t].keys())

        # Smooth the scalar parameter fields. SIGMA specified in the configs.py file.
        for v in vars_:
            if v in SCALAR_PARAMS.keys():
                data[t][v] = gaussian_filter(data[t][v], sigma=SIGMA, mode='nearest')

    data = _execute_filtering(data)
    return data
