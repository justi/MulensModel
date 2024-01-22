"""
Classes for handling comparison files generated by the Fortran version of sfit.
"""
import os.path
import numpy as np


class FortranSFitFile51(object):
    """
    Class to parse the fort.51 comparison file generated by
    the Fortran version of sfit.
    """
    def __init__(self, filename='fort.51', dir=None):
        if dir is not None:
            filename = os.path.join(dir, filename)

        with open(filename, 'r') as input_file:
            key = None
            for line in input_file.readlines():
                words = line.split()
                if words[0] == '#':
                    key = words[-1]
                    continue
                elif len(words) == 1:
                    value = float(words[0])
                else:
                    value = np.array([float(item) for item in words])

                self.__setattr__(key, value)

        self.source_fluxes = [fs for fs in self.a[9::3]]


class FortranSFitFile61(object):
    """
    Class to parse the fort.61 comparison file generated by
    the Fortran version of sfit.
    """

    def __init__(self, filename='fort.61', dir=None):
        if dir is not None:
            filename = os.path.join(dir, filename)

        self.data = np.genfromtxt(
            filename, dtype=None, encoding='utf-8',
            names=['nob', 'k', 't', 'dfdrho', 'mag', 'db0', 'db1'])
        for name in self.data.dtype.names:
            self.__setattr__(name, self.data[name])

        self.sfit_nob_indices = self._set_nob_indices()

    def _set_nob_indices(self):
        nobs = np.unique(self.data['nob'])
        nob_indices = []
        for nob in np.sort(nobs):
            sfit_index = (self.data['nob'] == nob)
            nob_indices.append(sfit_index)

        return nob_indices


class FortranSFitFile62(FortranSFitFile61):
    """
    Class to parse the fort.62 comparison file generated by
    the Fortran version of sfit.
    """

    def __init__(self, filename='fort.62', dir=None):
        if dir is not None:
            filename = os.path.join(dir, filename)

        self.data = np.genfromtxt(
            filename, dtype=None, encoding='utf-8',
            names=['nob', 'k', 't', 'dfdt0', 'dfdu0', 'dfdtE', 'dfdrho',
                   'dAdu', 'df', 'res', 'sig2'])
        for name in self.data.dtype.names:
            self.__setattr__(name, self.data[name])

        self.sfit_nob_indices = self._set_nob_indices()


class FortranSFitFile63(FortranSFitFile61):
    """
    Class to parse the fort.63 comparison file generated by
    the Fortran version of sfit.
    """

    def __init__(self, filename='fort.63', dir=None):
        if dir is not None:
            filename = os.path.join(dir, filename)

        self.data = np.genfromtxt(
            filename, dtype=None, encoding='utf-8',
            names=['nob', 'k', 't', 'x', 'x2', 'amp', 'b0', 'b1'])
        for name in self.data.dtype.names:
            self.__setattr__(name, self.data[name])

        self.sfit_nob_indices = self._set_nob_indices()


def read_sfit_files(dir):
    try:
        fort51 = FortranSFitFile51(dir=dir)
    except OSError:
        fort51 = None

    try:
        fort61 = FortranSFitFile61(dir=dir)
    except OSError:
        fort61 = None

    try:
        fort62 = FortranSFitFile62(dir=dir)
    except OSError:
        fort62 = None

    try:
        fort63 = FortranSFitFile63(dir=dir)
    except OSError:
        fort63 = None

    return {'51': fort51, '61': fort61, '62': fort62, '63': fort63}