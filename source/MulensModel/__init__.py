from os import path

from .binarylens import BinaryLens
from .binarylenswithshear import BinaryLensWithShear
from .caustics import Caustics
from .causticspointwithshear import CausticsPointWithShear
from .causticswithshear import CausticsWithShear
from .coordinates import Coordinates
from .event import Event
from .fitdata import FitData
from .horizons import Horizons
from .limbdarkeningcoeffs import LimbDarkeningCoeffs
from .magnificationcurve import MagnificationCurve
from .model import Model
from .modelparameters import ModelParameters, which_parameters
from .mulensdata import MulensData
from .mulensobjects import Lens, Source, MulensSystem
from . import orbits
from .pointlens import PointLens, get_pspl_magnification
from .pointlenswithshear import PointLensWithShear
from .pointlensfinitesource import PointLensFiniteSource
from .satelliteskycoord import SatelliteSkyCoord
from .trajectory import Trajectory
from .uniformcausticsampling import UniformCausticSampling
from .utils import MAG_ZEROPOINT, Utils

from .version import __version__

__all__ = ['mulensobjects', 'MODULE_PATH', 'DATA_PATH']

MODULE_PATH = path.abspath(__file__)
for i in range(3):
    MODULE_PATH = path.dirname(MODULE_PATH)

path_1 = path.join(MODULE_PATH, 'data')
if path.isdir(path_1):
    DATA_PATH = path_1
else:
    DATA_PATH = path.join(path.dirname(__file__), 'data')
