import numpy as np

from astropy.coordinates import SkyCoord
from astropy import units as u

from MulensModel.utils import Utils
from MulensModel.satelliteskycoord import SatelliteSkyCoord

#data_list and ephemerides_file must have the same time standard.
#To implement: mjd2hjd = T/F
#usecols
class MulensData(object):
    """
    A set of photometric measurements for a microlensing event.

    Attributes :

        time - the dates of the observations
        mag - the brightness in magnitudes
        err_mag - the errors on the magnitudes
        flux - the brightness in flux
        err_flux - the errors on the fluxes
        bad - a logical array/list of the same length as time where
            TRUE means the datapoint should be excluded.

    """

    def __init__(self, data_list=None, file_name=None,
                 phot_fmt="mag", coords=None, ra=None, dec=None, 
                 ephemerides_file=None, add_2450000=False,
                 add_2460000=False, bandpass=None, bad=None, **kwargs):
        """
        Create a MulensData object from a set of photometric measurements.

        Keywords:
           data_list - a list or array with columns: Date, Magnitude/Flux, Err
           file_name - The path to a file with columns: Date,
               Magnitude/Flux, Err
           *Either data_list or file_name is required.*

           phot_fmt - accepts either 'mag' or 'flux'. Default =
              'mag'. Specifies whether the photometry is in Magnitudes
              or Flux units.

           coords - [optional] sky coordinates of the event
           ra, dec - [optional] sky coordinates of the event
          
           ephemerides_file - [optional] specify the ephemerides of the
               satellite over the period when the data were taken. Will be
               interpolated as necessary to model the satellite parallax 
               effect.

           add_2450000 - Adds 2450000. to the input dates. Useful if
               the dates are supplied as HJD-2450000.
           add_2460000 - Adds 2460000. to the input dates.

           **kwargs - if file_name is provided, uses np.loadtxt to
               load file, and therefore this function accpets loadtxt
               keywords.
        """
        #Initialize some variables
        self._n_epochs = None  
        self._horizons = None
        self._satellite_skycoord = None

        self._init_keys = {'add245':add_2450000, 'add246':add_2460000}
        self._limb_darkening_weights = None
        self.bandpass = bandpass

        #Set the coords (if applicable)...
        coords_msg = 'Must specify both or neither of ra and dec'
        self._coords = None
        #...using coords keyword
        if coords is not None:
            if isinstance(coords, SkyCoord):
                self._coords = coords
            else:
                self._coords = SkyCoord(coords, unit=(u.hourangle, u.deg))
        #...using ra, dec keywords
        if ra is not None:
            if dec is not None:
                self._coords = SkyCoord(ra, dec, unit=(u.hourangle, u.deg))
            else:
                raise AttributeError(coords_msg)
        else:
            if ra is not None:
                raise AttributeError(coords_msg)

        #Import the photometry...
        if data_list is not None and file_name is not None:
            m = 'MulensData cannot be initialized with data_list and file_name'
            raise ValueError(m)
        elif data_list is not None:
            #...from an array
            (vector_1, vector_2, vector_3) = list(data_list) 
            self._initialize(phot_fmt, time=vector_1, 
                             brightness=vector_2, err_brightness=vector_3,
                             coords=self._coords)
        elif file_name is not None:
            #...from a file
            (vector_1, vector_2, vector_3) = np.loadtxt(
                fname=file_name, unpack=True, usecols=(0,1,2), **kwargs)
            self._initialize(phot_fmt, time=vector_1, 
                             brightness=vector_2, err_brightness=vector_3,
                             coords=self._coords)

        if bad is not None:
            self.bad = bad
        
        #Set up satellite properties (if applicable)
        self.ephemerides_file = ephemerides_file

    def _initialize(self, phot_fmt, time=None, brightness=None, 
                    err_brightness=None, coords=None):
        """
        internal function to package photometric data using a few numpy arrays

        Keywords:
            phot_fmt - Specifies type of photometry. Either 'flux' or 'mag'. 
            time - Date vector of the data
            brightness - vector of the photometric measurements
            err_brightness - vector of the errors in the phot measurements.
            coords - Sky coordinates of the event
        """
        if self._init_keys['add245'] and self._init_keys['add246']:
            raise ValueError('You cannot initilize MulensData with both ' + 
                            'add_2450000 and add_2460000 being True')
        #Adjust the time vector as necessary.
        if self._init_keys['add245']:
            time += 2450000.
        elif self._init_keys['add246']:
            time += 2460000.

        #Store the time vector
        self._time = time
        self._n_epochs = len(time)

        #Check that the number of epochs equals the number of observations
        if ((len(brightness) != self._n_epochs) 
            or (len(err_brightness) != self._n_epochs)):
            raise ValueError('input data in MulesData have different lengths')

        #Store the photometry
        self._brightness_input = brightness
        self._brightness_input_err = err_brightness        
        self.input_fmt = phot_fmt

        #Create the complementary photometry (mag --> flux, flux --> mag)
        if phot_fmt == "mag":
            self.mag = self._brightness_input
            self.err_mag = self._brightness_input_err
            (self.flux, self.err_flux) = Utils.get_flux_and_err_from_mag(
                                          mag=self.mag, err_mag=self.err_mag)
        elif phot_fmt == "flux":
            self.flux = self._brightness_input
            self.err_flux = self._brightness_input_err
            (self.mag, self.err_mag) = Utils.get_mag_and_err_from_flux(
                                        flux=self.flux, err_flux=self.err_flux)
        else:
            msg = 'unknown brightness format in MulensData'
            raise ValueError(msg)

        #Create an array to flag bad epochs
        self.bad = self.n_epochs * [False]

    @property
    def n_epochs(self):
        """give number of epochs"""
        return self._n_epochs

    @property
    def time(self):
        """short version of time vector"""
        return self._time

    @property
    def coords(self):
        """
        Sky coordinates (RA,Dec)
        """
        return self._coords

    @coords.setter
    def coords(self, new_value):
        if isinstance(new_value, SkyCoord):
            self._coords = new_value
        else:
            self._coords = SkyCoord(new_value, unit=(u.hourangle, u.deg))

    @property
    def ra(self):
        """
        Right Ascension
        """
        return self._coords.ra

    @ra.setter
    def ra(self, new_value):
        try:
            self._coords.ra = new_value
        except AttributeError:
            if self._coords is None:
                self._coords = SkyCoord(
                    new_value, 0.0, unit=(u.hourangle, u.deg))
            else:
                self._coords = SkyCoord(
                    new_value, self._coords.dec, unit=(u.hourangle, u.deg)) 

    @property
    def dec(self):
        """
        Declination
        """
        return self._coords.dec

    @dec.setter
    def dec(self, new_value):
        try:
            self._coords.dec = new_value
        except AttributeError:
            if self._coords is None:
                self._coords = SkyCoord(
                    0.0, new_value, unit=(u.hourangle, u.deg))
            else:
                self._coords = SkyCoord(
                    self._coords.ra, new_value, unit=(u.hourangle, u.deg))

    @property
    def satellite_skycoord(self):
        """return Astropy SkyCoord of satellite for epochs covered by
        the dataset"""
        if self.ephemerides_file is None:
            raise ValueError('ephemerides_file is not defined.')

        if self._satellite_skycoord is None:
            satellite_skycoord = SatelliteSkyCoord(
                ephemerides_file=self.ephemerides_file)
            self._satellite_skycoord = satellite_skycoord.get_satellite_coords(
                self._time)

        return self._satellite_skycoord

    @property
    def bandpass(self):
        """bandpass of given dataset (primary usage is limb darkening)"""
        return self._bandpass
        
    @bandpass.setter
    def bandpass(self, value):
        if self._limb_darkening_weights is not None:
            raise ValueError("Limb darkening weights were already set - you" +
                                "cannot bandpass now.")
        self._bandpass = value

    def set_limb_darkening_weights(self, weights):
        """save a dictionary weights that will be used to evaluate l
        imb darkening coefficient
        
        e.g. weights = {'I': 1.5, 'V': 1.} if I-band gamma limb-darkening 
        coefficient is 1.5-times larger than V-band"""
        if self.bandpass is not None:
            raise ValueError("Don't try to run " + 
                                "MulensData.set_limb_darkening_weights() " + 
                                "after bandpass was provided")
        if not isinstance(weights, dict):
            raise TypeError("MulensData.set_limb_darkening_weights() " + 
                    "parameter has to be dict, not {:}".format(type(weights)))
        
        self._limb_darkening_weights = weights
        
