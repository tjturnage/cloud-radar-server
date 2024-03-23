"""Contains a collection of vector functions.

Used to compute Bunkers right and left vectors and bulk wind shear magnitudes, for
example. 
"""

import numpy as np
from numba import njit

def componentsTo(u, v):
    return (u, v)

def add(*args):
    """From AWIPS. Perform scalar or vector addition
    """
    def scalarAddition(args):
        return reduce(np.add, args)

    def vectorAddition(args):
        uResult = np.zeros_like(args[0][0])
        vResult = np.zeros_like(args[0][0])
        for u, v in args:
            uResult += u
            vResult += v
        return componentsTo(uResult, vResult)

    if len(args)==1 and isinstance(args[0], list):
        return add(*args[0])
    elif isinstance(args[0], tuple):
        return vectorAddition(args)
    else:
        return scalarAddition(args)

def multiply(*args):
    """From AWIPS. Perform multiplication of any number of scalars or of a vector and a
    scalar.
    """
    def scalarMultiply(args):
        return reduce(multiply, args)

    def vectorMultiply(args):
        return componentsTo(scalarMultiply((args[0][0],  args[1])),
                            scalarMultiply((args[0][1],  args[1])))

    if type(args[0]) == tuple:
        return vectorMultiply(args)
    else:
        return scalarMultiply(args)

def divide(*args):
    """Modified from AWIPS. Divide a scalar by a scalar or a vector by a scalar.
    """
    divArgs = list(args)

    for i in range(1,len(divArgs)):
        divArgs[i] = np.where(divArgs[i] == 0, np.float32(np.nan), 1/divArgs[i])
    return multiply(divArgs)

@njit
def transform(uComponent, vComponent, s1, s2, s3, s4):
    """Modified from AWIPS. Rotate a vector

    Rotate vector by a number of degrees, or transform the vector with a matrix.
    The arguments after the vector need to be constants.
    """
    vector = np.array([uComponent, vComponent])
    transform = np.array([[s1, s2], [s3, s4]])
    u, v = np.dot(transform, vector)
    return (u, v)
