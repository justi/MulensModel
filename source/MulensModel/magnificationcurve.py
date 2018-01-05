import numpy as np
import warnings

from scipy.special import ellipe
# This is incomplete elliptic integral of the second kind.

from scipy import integrate

from MulensModel.trajectory import Trajectory
from MulensModel.binarylens import BinaryLens
from MulensModel.modelparameters import ModelParameters


class MagnificationCurve(object):
    """
    The magnification curve calculated from the model light curve.

    The key function is :py:func:`set_magnification_methods`, which
    specifies the method used to calculate the finite source
    magnification and when to use it..

    Arguments :
        times: iterable of *floats*
            the times at which to generate the magnification curve

        parameters: :py:class:`~MulensModel.modelparameters.ModelParameters`
            specifies the microlensing parameters

        parallax: *dict*, optional
            dictionary specifying what parallax effects should be
            used, e.g., ``{'earth_orbital': True, 'satellite': False,
            'topocentric': False}``

        coords: :py:class:`MulensModel.coordinates.Coordinates`, optional
            sky coordinates of the event

        satellite_skycoord: *Astropy.coordinates.SkyCoord*, optional
            sky coordinates of the satellite specified by the
            ephemrides file. see
            :py:obj:`MulensModel.mulensdata.MulensData.satellite_skycoord.`

        gamma: *float*, optional
            limb darkening coefficient in gamma convention; defaults to 0

    """
    def __init__(self, times, parameters, parallax=None,
                 coords=None, satellite_skycoord=None, gamma=0.):
        # Set times
        if isinstance(times, (list, tuple, np.ndarray)):
            self.times = times
        else:
            self.times = np.array(times)

        # Check for ModelParameters and set.
        if isinstance(parameters, ModelParameters):
            self.parameters = parameters
        else:
            raise ValueError(
                'parameters is a required and must be a ' +
                'ModelParameters object')

        # Calculate the source trajectory (i.e. u(t))
        self.trajectory = Trajectory(
            self.times, parameters=parameters, parallax=parallax,
            coords=coords, satellite_skycoord=satellite_skycoord)

        # Initialize the magnification vector
        self._magnification = None

        # Set methods' variables:
        self._methods_epochs = None
        self._methods_names = None
        self._default_magnification_method = None
        self._methods_parameters = None

        self._gamma = gamma

    def set_magnification_methods(self, methods, default_method):
        """
        Sets methods used for magnification calculation.

        For available methods, see:
            :py:func:`get_point_lens_magnification`

            :py:func:`get_binary_lens_magnification`

        Parameters :
            methods: *list*
                List that specifies which methods (*str*) should be
                used when (*float* values for Julian dates). Given
                method will be used for times between the times
                between which it is on the list, e.g.,

                ``methods = [2455746., 'Quadrupole', 2455746.6,
                'Hexadecapole', 2455746.7, 'VBBL', 2455747.,
                'Hexadecapole', 2455747.15, 'Quadrupole', 2455748.]``

            default_method: *str*
                Name of the method to be used for epochs outside the ranges
                specified in *methods*.

        For point-lens with finite source, the methods named
        ``finite_source_uniform_Gould94`` and ``finite_source_LD_Gould94``
        implement the algorithms presented by `Gould 1994 ApJ, 421L, 71
        <http://adsabs.harvard.edu/abs/1994ApJ...421L..71G>`_ and
        `Yoo et al. 2004 ApJ, 603, 139
        <http://adsabs.harvard.edu/abs/2004ApJ...603..139Y>`_.
        """
        self._default_method = default_method
        if methods is None:
            self._methods_epochs = None
            self._methods_names = None
            return

        if not isinstance(methods, list):
            msg = ('MagnificationCurve.set_magnification_methods() requires' +
                   'list as a parameter')
            raise TypeError(msg)
        epochs = methods[0::2]
        names = methods[1::2]

        for epoch in epochs:
            if not isinstance(epoch, float):
                raise TypeError('Wrong epoch: {:}'.format(epoch))
        for method in names:
            if not isinstance(method, str):
                raise TypeError('Wrong method: {:}'.format(method))
        for (e_beg, e_end) in zip(epochs[::2], epochs[1::2]):
            if e_beg >= e_end:
                msg = ('Incorrect epochs provided: {:} and {:} (first should' +
                       'be earlier)')
                raise ValueError(msg.format(e_beg, e_end))

        self._methods_epochs = np.array(epochs)
        self._methods_names = names
        self._default_method = default_method

    def set_magnification_methods_parameters(self, methods_parameters):
        """
        Set additional parameters for magnification calculation methods.

        Parameters :
            methods_parameters: *dict*
                Dictionary that for method names (keys) returns dictionary
                in the form of ``**kwargs`` that are passed to given method,
                e.g., ``{'VBBL': {'accuracy': 0.005}}``.

        """
        self._methods_parameters = methods_parameters

    @property
    def magnification(self):
        """
        *np.ndarray*

        provide vector of magnifications

        """
        return self.get_magnification()
        #  THIS HAS TO BE REWRITTEN - USE LAZY LOADING! (here or in model.py)

    def get_magnification(self):
        """
        Calculate magnification.

        Returns :
            magnification: *np.ndarray*
                Vector of magnifications.

        """
        if self.parameters.rho is not None:
            self._check_for_finite_source_method()

        if self.parameters.n_lenses == 1:
            magnification = self.get_point_lens_magnification()
        elif self.parameters.n_lenses == 2:
            magnification = self.get_binary_lens_magnification()
        else:
            raise NotImplementedError(
                "magnification for more than 2 lenses not handled yet")
        self._magnification = magnification
        return self._magnification

    def _check_for_finite_source_method(self):
        """
        check if there is method defined that uses finite source
        calculations and warn if not
        """
        if self._methods_epochs is None:
            warnings.warn('No finite-source method is set')
            return
        methods = self._methods_names + [self._default_magnification_method]
        if set(methods) == set(['point_source']):
            warnings.warn('no finite-source method is set')
            return

    def get_point_lens_magnification(self):
        """
        Calculate the Point Lens magnification.

        Magnification Methods :
            point_source:
                standard Pczynski equation for a point source/point lens.

            finite_source_uniform_Gould94:
                Uses the Gould (1994) prescription assuming a
                *uniform* (and circular) source.

            finite_source_LD_Gould94:
                Uses the Gould (1994) prescription for a circular source
                *including limb-darkening.*

        Returns :
            magnification: *np.ndarray*
                Vector of magnifications.

        Gould A. 1994 ApJ 421L, 71 "Proper motions of MACHOs"
        http://adsabs.harvard.edu/abs/1994ApJ...421L..71G

        """

        u2 = (self.trajectory.x**2 + self.trajectory.y**2)
        #  This is Paczynski equation, i.e., point-source/point-lens (PSPL)
        #  magnification:
        pspl_magnification = (u2 + 2.) / np.sqrt(u2 * (u2 + 4.))
        if self._methods_epochs is None:
            return pspl_magnification

        magnification = pspl_magnification
        u_all = np.sqrt(u2)
        methods = np.array(self._methods_for_epochs())

        for method in set(methods):
            kwargs = {}
            if self._methods_parameters is not None:
                if method in self._methods_parameters.keys():
                    kwargs = self._methods_parameters[method]
                if kwargs != {}:
                    raise ValueError(
                        'Methods parameters passed, but currently ' +
                        'no point lens method accepts the parameters')

            if method.lower() == 'point_source':
                pass  # This cases are already taken care of.
            elif method.lower() == 'finite_source_uniform_Gould94'.lower():
                selection = (methods == method)
                magnification[selection] = (
                    self._get_point_lens_finite_source_magnification(
                        rho=self.parameters.rho, u=u_all[selection],
                        pspl_magnification=pspl_magnification[selection]))
            elif method.lower() == 'finite_source_LD_Gould94'.lower():
                selection = (methods == method)
                magnification[selection] = (
                    self._get_point_lens_limb_darkening_magnification(
                        rho=self.parameters.rho, u=u_all[selection],
                        pspl_magnification=pspl_magnification[selection]))
            else:
                msg = 'Unknown method specified for single lens: {:}'
                raise ValueError(msg.format(method))

        return magnification

    def _B_0_function(self, z):
        """
        calculate B_0(z) function defined in:

        Gould A. 1994 ApJ 421L, 71 "Proper motions of MACHOs"
        http://adsabs.harvard.edu/abs/1994ApJ...421L..71G

        Yoo J. et al. 2004 ApJ 603, 139 "OGLE-2003-BLG-262: Finite-Source
        Effects from a Point-Mass Lens"
        http://adsabs.harvard.edu/abs/2004ApJ...603..139Y

        """
        out = 4. * z / np.pi
        function = lambda x: (1.-value**2*np.sin(x)**2)**.5

        for (i, value) in enumerate(z):
            if value < 1.:
                out[i] *= ellipe(value*value)
            else:
                out[i] *= integrate.quad(function, 0., np.arcsin(1./value))[0]
        return out

    def _B_1_function(self, z, B_0=None):
        """
        calculate B_1(z) function defined in:

        Gould A. 1994 ApJ 421L, 71 "Proper motions of MACHOs"
        http://adsabs.harvard.edu/abs/1994ApJ...421L..71G

        Yoo J. et al. 2004 ApJ 603, 139 "OGLE-2003-BLG-262: Finite-Source
        Effects from a Point-Mass Lens"
        http://adsabs.harvard.edu/abs/2004ApJ...603..139Y

        """
        if B_0 is None:
            B_0 = self._B_0_function(z)

        function = (lambda r, theta: r * np.sqrt(1.-r**2) /
                    self.parameters.rho /
                    np.sqrt(r**2+zz**2-2.*r*zz*np.cos(theta)))
        lim_0 = lambda x: 0
        lim_1 = lambda x: 1
        W_1 = 0. * z
        for (i, zz) in enumerate(z):
            W_1[i] = integrate.dblquad(function, 0., 2.*np.pi, lim_0, lim_1)[0]

        W_1 /= np.pi
        return B_0 - 1.5 * z * self.parameters.rho * W_1

    def _get_point_lens_finite_source_magnification(
                self, rho, u, pspl_magnification):
        """
        calculate magnification for point lens and finite source.
        The approximation was proposed by:

        Gould A. 1994 ApJ 421L, 71 "Proper motions of MACHOs"
        http://adsabs.harvard.edu/abs/1994ApJ...421L..71G

        and later the integral calculation was simplified by:

        Yoo J. et al. 2004 ApJ 603, 139 "OGLE-2003-BLG-262: Finite-Source
        Effects from a Point-Mass Lens"
        http://adsabs.harvard.edu/abs/2004ApJ...603..139Y

        """
        z = u / rho

        magnification = pspl_magnification * self._B_0_function(z)
        # More accurate calculations can be performed - see Yoo+04 eq. 11 & 12.
        return magnification

    def _get_point_lens_limb_darkening_magnification(
                self, rho, u, pspl_magnification):
        """
        calculate magnification for point lens and finite source with
        limb darkening. The approximation was proposed by:

        Gould A. 1994 ApJ 421L, 71 "Proper motions of MACHOs"
        http://adsabs.harvard.edu/abs/1994ApJ...421L..71G

        and later the integral calculation was simplified by:

        Yoo J. et al. 2004 ApJ 603, 139 "OGLE-2003-BLG-262: Finite-Source
        Effects from a Point-Mass Lens"
        http://adsabs.harvard.edu/abs/2004ApJ...603..139Y

        """
        z = u / rho
        B_0 = self._B_0_function(z)
        B_1 = self._B_1_function(z, B_0=B_0)
        magnification = pspl_magnification * (B_0 - self._gamma * B_1)
        return magnification

    def get_binary_lens_magnification(self):
        """
        Calculate the binary lens magnification.

        Magnification Methods :
            point_source:
                standard PSPL magnification calculation.

            quadrupole/hexadecapole:
                From Gould 20008. See
                :py:func:`MulensModel.binarylens.BinaryLens.hexadecapole_magnification()`

            vbbl:
                Uses VBBinaryLensing (a Stokes theorem/contour
                integration code) by Valerio Bozza. See
                :py:func:`MulensModel.binarylens.BinaryLens.vbbl_magnification()`

            adaptivecontouring:
                Uses AdaptiveContouring (a Stokes theorem/contour
                integration code) by Martin Dominik.  See
                :py:func:`MulensModel.binarylens.BinaryLens.adaptive_contouring_magnification()`

        Returns :
            magnification: *np.ndarray*
                Vector of magnifications.

        """
        # Set up the binary lens system
        q = self.parameters.q
        m_1 = 1. / (1. + q)
        m_2 = q / (1. + q)
        binary_lens = BinaryLens(
            mass_1=m_1, mass_2=m_2, separation=self.parameters.s)
        methods = self._methods_for_epochs()

        # Calculate the magnification
        magnification = []
        for index in range(len(self.times)):
            x = self.trajectory.x[index]
            y = self.trajectory.y[index]
            method = methods[index].lower()

            kwargs = {}
            if self._methods_parameters is not None:
                if method in self._methods_parameters.keys():
                    kwargs = self._methods_parameters[method]
                    if method not in ['vbbl', 'adaptivecontouring']:
                        msg = ('Methods parameters passed for method {:}' +
                               ' which does not accept any parameters')
                        raise ValueError(msg.format(method))

            if method == 'point_source':
                m = binary_lens.point_source_magnification(x, y)
            elif method == 'quadrupole':
                m = binary_lens.hexadecapole_magnification(
                    x, y, rho=self.parameters.rho, quadrupole=True,
                    gamma=self._gamma)
            elif method == 'hexadecapole':
                m = binary_lens.hexadecapole_magnification(
                    x, y, rho=self.parameters.rho, gamma=self._gamma)
            elif method == 'vbbl':
                m = binary_lens.vbbl_magnification(
                    x, y, rho=self.parameters.rho, gamma=self._gamma, **kwargs)
            elif method == 'adaptivecontouring':
                m = binary_lens.adaptive_contouring_magnification(
                    x, y, rho=self.parameters.rho, gamma=self._gamma, **kwargs)
            else:
                msg = 'Unknown method specified for binary lens: {:}'
                raise ValueError(msg.format(method))

            magnification.append(m)

        return np.array(magnification)

    def _methods_for_epochs(self):
        """
        for given epochs, decide which methods should be used to
        calculate magnification, but don't run the calculations
        """
        out = [self._default_method] * len(self.times)
        if self._methods_epochs is None:
            return out

        brackets = np.searchsorted(self._methods_epochs, self.times)
        n_max = len(self._methods_epochs)

        out = [self._methods_names[value - 1]
               if (value > 0 and value < n_max) else self._default_method
               for value in brackets]
        return out
