from astropy.coordinates import SkyCoord
from astropy import units as u
import matplotlib.pyplot as pl

import MulensModel 
"""
Use cases for passing RA, DEC to MulensDAta, Model, and Event.

Based on OGLE-2015-BLG-0448 from Poleski et al. 2016 ApJ 823, 63
"""

data_dir = '../../data'

#Specifying coordinates to calculate HJD from JD
data_1 = MulensModel.MulensData(
    file_name='{0}/ob140939_OGLE.dat'.format(data_dir), 
    coords='17:47:12.25 -21:22:58.2')

data_2 = MulensModel.MulensData(
    file_name='{0}/ob140939_OGLE.dat'.format(data_dir), ra='17:47:12.25', 
    dec='-21:22:58.2')

coords = SkyCoord('17:47:12.25 -21:22:58.2', unit=(u.hourangle, u.deg))
data_3 = MulensModel.MulensData(
    file_name='{0}/ob140939_OGLE.dat'.format(data_dir), coords=coords)

#Specifiying coordinates to calculate a model with parallax
t_0 = 2456836.22
u_0 = 0.922
t_E = 22.87
pi_E_N = -0.248
pi_E_E = 0.234

ground_model = MulensModel.Model()
ground_model.set_parameters(t_0=t_0, u_0=u_0, t_E=t_E, pi_E=[pi_E_N, pi_E_E])
ground_model.coords = '17:47:12.25 -21:22:58.2'
space_model = MulensModel.Model(
    t_0=t_0, u_0=u_0, t_E=t_E, pi_E=[pi_E_N, pi_E_E], 
    ra='17:47:12.25', dec='-21:22:58.2', 
    ephemerides_file='{0}/Spitzer_ephemeris_01.dat'.format(data_dir))

#Access Galactic and ecliptic coordinates:
print('l {0}'.format(ground_model.galactic_l))
print('b {0}'.format(ground_model.galactic_b))
print('ecliptic lat {0}'.format(ground_model.ecliptic_lat))
print('ecliptic lon {0}'.format(ground_model.ecliptic_lon))

pl.figure()
ground_model.plot_magnification(label='ground')
space_model.plot_magnification(label='space')
pl.title('Models with Parallax')
pl.legend()

#Sepcifying coordinates for an event
ground_data = MulensModel.MulensData(
    file_name='{0}/ob140939_OGLE.dat'.format(data_dir))
space_data = MulensModel.MulensData(
    file_name='{0}/ob140939_Spitzer.dat'.format(data_dir), 
    ephemerides_file='{0}/Spitzer_ephemeris_01.dat'.format(data_dir))

model_params = MulensModel.ModelParameters(
    t_0=t_0, u_0=u_0, t_E=t_E, pi_E_N=pi_E_N, pi_E_E=pi_E_E)
event = MulensModel.Event(datasets=[ground_data, space_data], 
                          model=MulensModel.Model(parameters=model_params), 
                          coords='17:47:12.25 -21:22:58.2')

pl.figure()
event.plot_model()
event.plot_data(label_list=['OGLE', 'Spitzer'])
(fs_ogle, fb_ogle) = event.get_ref_fluxes(data_ref=event.datasets[0])
space_model.plot_lc(f_source=fs_ogle, f_blend=fb_ogle)
pl.title('Model with Data')
pl.legend(loc='best')

pl.show()
