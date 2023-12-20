import unittest
from os.path import join
import numpy as np
from numpy.testing import assert_allclose
from test_FitData import create_0939_parallax_model

import MulensModel as mm

dir_1 = join(mm.DATA_PATH, 'photometry_files', 'OB140939')
dir_2 = join(mm.DATA_PATH, 'unit_test_files')
dir_3 = join(mm.DATA_PATH, 'ephemeris_files')
dir_4 = join(dir_2, 'fspl_derivs')

SAMPLE_FILE_02 = join(dir_1, 'ob140939_OGLE.dat')  # HJD'
SAMPLE_FILE_03 = join(dir_1, 'ob140939_Spitzer.dat')  # HJD'
SAMPLE_FILE_03_EPH = join(dir_3, 'Spitzer_ephemeris_01.dat')  # UTC
SAMPLE_FILE_03_REF = join(dir_2, 'ob140939_Spitzer_ref_v1.dat')  # HJD'
SAMPLE_FILE_FSPL_51 = join(dir_4, 'fort.51')
SAMPLE_FILE_FSPL_61 = join(dir_4, 'fort.61')

def test_get_d_u_d_params():
    """
    Test that calculating derivatives with an ephemeris file is different from
    without an ephemeris file.
    """
    parameters = ['pi_E_N', 'pi_E_E']
    model_with_par = create_0939_parallax_model()

    data_ephm = mm.MulensData(
        file_name=SAMPLE_FILE_03, ephemerides_file=SAMPLE_FILE_03_EPH)
    fit_ephm = mm.FitData(dataset=data_ephm, model=model_with_par)
    derivs_ephm = fit_ephm._get_d_u_d_params(parameters)

    data_no_ephm = mm.MulensData(file_name=SAMPLE_FILE_03)
    fit_no_ephm = mm.FitData(dataset=data_no_ephm, model=model_with_par)
    derivs_no_ephm = fit_no_ephm.magnification_curve.get_d_u_d_params(
        parameters)

    for param in parameters:
        ratio = derivs_ephm[param] / derivs_no_ephm[param]
        assert (np.abs(ratio - 1.) > 0.001).all()


class TestGradient(unittest.TestCase):
    def test_no_gradient_for_xallarap(self):
        """
        Make sure that gradient for xallarap models in not implemented.
        """
        data = mm.MulensData(file_name=SAMPLE_FILE_02)
        model = mm.Model({
            't_0': 2456836.22, 'u_0': 0.922, 't_E': 22.87,
            'xi_period': 100., 'xi_semimajor_axis': 0.5, 'xi_Omega_node': 90.,
            'xi_inclination': 90., 'xi_argument_of_latitude_reference': 90.})
        fit = mm.FitData(model, data)

        with self.assertRaises(NotImplementedError):
            fit.get_chi2_gradient(['t_0', 'u_0', 't_E'])


class FortranSFitFile(object):
    """
    Class to parse the comparison file generated by
    the Fortran version of sfit.
    """
    def __init__(self, filename):
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


class TestFSPLGradient(unittest.TestCase):
    """ Compares various parts of the FSPL Derivative calculations to the
    results from sfit."""

    def setUp(self):
        # Read in sfit comparison file, split by dataset
        self.filenames = ['FSPL_par_Obs_1_I.pho', 'FSPL_par_Obs_2_V.pho']
        self.sfit_derivs = np.genfromtxt(
            SAMPLE_FILE_FSPL_61, dtype=None,
            names=['nob', 'k', 't', 'dAdrho', 'mag', 'db0', 'db1'])
        self._read_sfit()
        self._create_model()
        self._set_datasets()
        self._set_fits()
        self._set_indices()

    def _read_sfit(self):
        """ read in the input parameters and output matrices from sfit"""
        self.sfit_mat = FortranSFitFile(SAMPLE_FILE_FSPL_51)
        self.sfit_mat.a[0] += 2450000.

    def _create_model(self):
        """ Initialize a model to match sfit parameters """
        parameters = ['t_0', 'u_0', 't_E', 'rho']
        self.sfit_model = mm.Model(dict(zip(parameters, self.sfit_mat.a)))
        t_star = (
            self.sfit_model.parameters.rho * self.sfit_model.parameters.t_E)
        n_t_star = 9.
        self._t_lim_1 = self.sfit_model.parameters.t_0 - n_t_star * t_star
        self._t_lim_2 = self.sfit_model.parameters.t_0 + n_t_star * t_star
        n_t_star_2 = 50.
        self._t_lim_3 = self.sfit_model.parameters.t_0 - n_t_star_2 * t_star
        self._t_lim_4 = self.sfit_model.parameters.t_0 + n_t_star_2 * t_star
        self.sfit_model.set_magnification_methods(
            [self._t_lim_3, 'finite_source_uniform_Gould94',
             self._t_lim_1, 'finite_source_LD_Yoo04',
             self._t_lim_2, 'finite_source_uniform_Gould94',
             self._t_lim_4])
        self.sfit_model.set_limb_coeff_gamma('I', self.sfit_mat.a[4])
        self.sfit_model.set_limb_coeff_gamma('V', self.sfit_mat.a[5])

    def _set_datasets(self):
        """ Read in datasets for test"""
        self.datasets = []
        for filename in self.filenames:
            bandpass = filename.split('.')[0][-1]
            mag_data = np.genfromtxt(
                join(dir_4, filename), dtype=None, encoding='utf-8',
                names=['time', 'mag', 'err'])
            (flux, err) = mm.Utils.get_flux_and_err_from_mag(
                mag_data['mag'], mag_data['err'], zeropoint=18.)
            dataset = mm.MulensData(
                [mag_data['time'], flux, err], phot_fmt='flux',
                bandpass=bandpass)
            self.datasets.append(dataset)

    def _set_fits(self):
        """ Set up fits for each individual dataset."""
        self.fits = []
        self.zs = []  # z = u / rho for each data epoch
        self.indices = []  # restrict to points affected by FS effects
        self.sfit_indices = []  # select the right parts of the sfit comparison
        # file
        for (i, dataset) in enumerate(self.datasets):
            fit = mm.FitData(
                dataset=dataset, model=self.sfit_model,
                fix_source_flux=self.sfit_mat.a[9 + i * 3],
                fix_blend_flux=self.sfit_mat.a[9 + i * 3 + 1])
            fit.fit_fluxes()
            self.fits.append(fit)

            index = ((dataset.time > self._t_lim_1) &
                     (dataset.time < self._t_lim_2))
            self.indices.append(index)

            sfit_index = np.where(self.sfit_derivs['nob'] == i + 1)
            self.sfit_indices.append(sfit_index)

            trajectory = fit.model.get_trajectory(dataset.time)
            u = np.sqrt(trajectory.x**2 + trajectory.y**2)
            z = u / self.sfit_model.parameters.rho
            self.zs.append(z)

    def _set_indices(self):
        z_break = 1.3
        zs_1_margin = 0.003
        self._indexes = []
        self._indices_not_near_1 = []
        self._indices_not_near_1_db = []
        for (zs, indices) in zip(self.zs, self.indices):
            index_large = (zs > z_break)
            index_small = (zs <= z_break)
            self._indexes.append([index_large, index_small])
            # The sfit code is not accurate near 1.0.
            near_1 = (np.abs(zs - 1.) > zs_1_margin)
            self._indices_not_near_1.append(indices & near_1)
            near_1_db = (zs < 0.88) | (zs > 1.1)
            self._indices_not_near_1_db.append(indices & near_1_db)

    ### B0B1Utils tests
    def _db0_test(self, i):
        """ Test that B0prime is calculated correctly"""
        # private function check
        sfit_db0 = self.sfit_derivs[self.sfit_indices[i]]['db0']
        kwargs_ = [{'atol': 0.0005}, {'rtol': 0.01}]
        for (condition, kwargs) in zip(self._indexes[i], kwargs_):
            index_i = condition & self._indices_not_near_1_db[i]
            z = self.zs[i][index_i]
            db0 = mm.B0B1Utils().interpolate_B0prime(z)
            assert_allclose(db0, sfit_db0[index_i], **kwargs)

    def test_db0_0(self):
        """ Check that B0prime is calculated correctly for dataset 0"""
        self._db0_test(0)

    def test_db0_1(self):
        """ Check that B0prime is calculated correctly for dataset 1"""
        self._db0_test(1)

    def _db1_test(self, i):
        """ Check that B1prime is calculated correctly"""
        # private function check
        sfit_db1 = self.sfit_derivs[self.sfit_indices[i]]['db1']
        kwargs_ = [{'atol': 0.001}, {'rtol': 0.05}]
        for (condition, kwargs) in zip(self._indexes[i], kwargs_):
            index_i = condition & self._indices_not_near_1_db[i]
            z = self.zs[i][index_i]
            db1 = mm.B0B1Utils().interpolate_B1prime(z)
            assert_allclose(db1, sfit_db1[index_i], **kwargs)

    def test_db1_0(self):
        """ Check that B1prime is calculated correctly for dataset 0"""
        self._db1_test(0)

    def test_db1_1(self):
        """ Check that B1prime is calculated correctly for dataset 1"""
        self._db1_test(1)

    ### Test Magnification Calculations
    def _mags_test(self, i):
        """ Check that magnification is calculated correctly"""
        mags = self.fits[i].get_data_magnification()
        sfit_mags = self.sfit_derivs[self.sfit_indices[i]]['mag']
        assert_allclose(mags, sfit_mags, rtol=0.005)

    def test_mags_0(self):
        """ Check that magnification is calculated correctly for dataset 0"""
        self._mags_test(0)

    def test_mags_1(self):
        """ Check that magnification is calculated correctly for dataset 1"""
        self._mags_test(1)

    ### Test magnification_curve.d_A_d_rho
    def _dA_drho_test(self, i):
        """ Check that dA / drho is calculated correctly"""
        # compare da_drho
        fs = self.fits[i].source_flux
        derivs = fs * self.fits[i].magnification_curve.d_A_d_rho
        sfit_da_drho = self.sfit_derivs[self.sfit_indices[i]]['dAdrho']
        mask = self._indices_not_near_1[i]
        assert_allclose(derivs[mask], sfit_da_drho[mask], rtol=0.015)

    def test_dAdrho_0(self):
        """ Check that dA / drho is calculated correctly for dataset 0"""
        self._dA_drho_test(0)

    def test_dAdrho_1(self):
        """ Check that dA / drho is calculated correctly for dataset 1"""
        self._dA_drho_test(1)

    ### Test Derivative Errors
    def _set_limb_coeffs(self, model):
        for band in ['I', 'V']:
            gamma = self.sfit_model.get_limb_coeff_gamma(band)
            model.set_limb_coeff_gamma(band, gamma)

    def test_FSPL_Derivatives_tstar(self):
        """ Make sure that FSPL Derivatives fails for models defined with
        tstar """
        model = mm.Model(
            {'t_0': self.sfit_model.parameters.t_0,
             'u_0': self.sfit_model.parameters.u_0,
             't_E': self.sfit_model.parameters.t_E,
             't_star': self.sfit_model.parameters.t_star})
        self._set_limb_coeffs(model)

        fit = mm.FitData(model=model, dataset=self.datasets[0])

        with self.assertRaises(KeyError):
            fit.magnification_curve.d_A_d_rho

    def test_check_FSPLDerivs_errors_1(self):
        parameters = ['t_0', 'u_0', 't_E', 'rho']
        model = mm.Model(dict(zip(parameters, self.sfit_mat.a)))
        self._set_limb_coeffs(model)

        t_star = model.parameters.rho * model.parameters.t_E
        n_t_star = 9.
        t_lim_1 = model.parameters.t_0 - n_t_star * t_star
        t_lim_2 = model.parameters.t_0 + n_t_star * t_star
        model.set_magnification_methods(
            [t_lim_1, 'finite_source_uniform_WittMao94', t_lim_2])
        fit = mm.FitData(model=model, dataset=self.datasets[0])
        with self.assertRaises(ValueError):
            fit.magnification_curve.d_A_d_rho

    ### Test Model errors for setting model_magnification_parameters
    # Doesn't really belong here.
    def test_magnification_methods_parameters(self):
        parameters = ['t_0', 'u_0', 't_E', 'rho']
        model = mm.Model(dict(zip(parameters, self.sfit_mat.a)))
        t_star = model.parameters.rho * model.parameters.t_E
        n_t_star = 9.
        t_lim_1 = model.parameters.t_0 - n_t_star * t_star
        t_lim_2 = model.parameters.t_0 + n_t_star * t_star
        model.set_magnification_methods(
            [t_lim_1, 'finite_source_uniform_Gould94', t_lim_2])
        with self.assertRaises(KeyError):
            model.set_magnification_methods_parameters(
                {'vbbl': {'accuracy': 0.005}})

        model.set_magnification_methods_parameters(
            {'finite_source_uniform_Gould94': {'accuracy': 0.005}})
        with self.assertRaises(ValueError):
            model.get_magnification(np.arange(t_lim_1, t_lim_2, 0.1))


class TestFSPLGradient2(TestFSPLGradient):

    def setUp(self):
        fort_61 = join(dir_4, 'test_2', 'fort.61')
        fort_62 = join(dir_4, 'test_2', 'fort.62')
        fort_51 = join(dir_4, 'test_2', 'fort.51')
        self.filenames = [join('test_2', 'FSPL_Obs_1_I.pho'),
                          join('test_2', 'FSPL_Obs_2_V.pho')]

        self.sfit_derivs = np.genfromtxt(
            fort_61, dtype=None, encoding='utf-8',
            names=['nob', 'k', 't', 'dAdrho', 'mag', 'db0', 'db1'])
        self.sfit_partials = np.genfromtxt(
            fort_62, dtype=None, encoding='utf-8',
            names=['nob', 'k', 't', 'dfdt0', 'dfdu0', 'dfdtE', 'dfdrho',
                   'dAdu', 'df', 'res', 'sig2'])
        self.sfit_mat = FortranSFitFile(fort_51)
        self.sfit_mat.a[0] += 2450000.

        self._create_model()
        self._set_datasets()
        self._set_fits()
        self._set_indices()

    ### MagnificationCurve tests
    def test_dA_dparams(self):
        params = ['t_0', 'u_0', 't_E', 'rho']
        for i, fit in enumerate(self.fits):
            dA_dparam = fit.magnification_curve.get_d_A_d_params_for_point_lens_model(
                params)
            for j, param in enumerate(params):
                short_param = param.replace('_', '')
                df_dparam = fit.source_flux * dA_dparam[param]
                sfit_df_dparam = self.sfit_partials[
                    self.sfit_indices[i]]['dfd{0}'.format(short_param)]
                mask = self._indices_not_near_1[i]
                assert_allclose(
                    df_dparam[mask], sfit_df_dparam[mask], rtol=0.015)

    def test_dAdu_FSPLError(self):
        # *** JCY Is this stil not implemented? ***
        for i, fit in enumerate(self.fits):
            with self.assertRaises(NotImplementedError):
                fit.magnification_curve.d_A_d_u_for_point_lens_model()

    def test_dAdu_PSPL(self):
        params = ['t_0', 'u_0', 't_E']
        sfit_PSPL_model = mm.Model(dict(zip(params, self.sfit_mat.a)))
        for (i, dataset) in enumerate(self.datasets):
            fit = mm.FitData(
                dataset=dataset, model=sfit_PSPL_model,
                fix_source_flux=self.sfit_mat.a[9 + i * 3],
                fix_blend_flux=self.sfit_mat.a[9 + i * 3 + 1])
            fit.fit_fluxes()
            dAdu = fit.d_A_d_u_for_point_lens_model
            assert_allclose(
                dAdu, self.sfit_partials[self.sfit_indices[i]]['dAdu'],
                rtol=0.005)

    ### FitData tests
    def test_chi2_gradient(self):
        params = ['t_0', 'u_0', 't_E', 'rho']
        for i, fit in enumerate(self.fits):
            gradient = fit.get_chi2_gradient(params)
            sfit_res = self.sfit_partials[self.sfit_indices[i]]['res']

            # Test residuals from model & Errors
            res, err = fit.get_residuals(phot_fmt='flux')
            index_peak = (self.zs[i] < 15.)
            index_wings = (self.zs[i] > 15.)
            assert_allclose(res[index_peak], sfit_res[index_peak], rtol=0.01)
            assert_allclose(res[index_wings], sfit_res[index_wings], atol=0.01)
            sig2 = self.sfit_partials[self.sfit_indices[i]]['sig2']
            assert_allclose(err**2, sig2, rtol=0.01)

            # Test gradient
            for j, param in enumerate(params):
                short_param = param.replace('_', '')
                partials = self.sfit_partials[
                    self.sfit_indices[i]]['dfd{0}'.format(short_param)]
                sfit_gradient = np.sum(-2. * sfit_res * partials / sig2)
                assert_allclose(gradient[j], sfit_gradient, rtol=0.01)
