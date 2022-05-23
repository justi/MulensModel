class PointLensMagnificationCurve(object):

    def __init__(self, trajectory=None, parameters=None):
        self.trajectory = trajectory
        if parameters is None:
            self.parameters = {'t_0': None, 'u_0': None, 't_E': None}
        else:
            self._check_parameters(parameters)
            self.parameters = parameters

        self.magnification = None
        self.d_A_d_params = None

    def _check_parameters(self, parameters):
        pass

    def get_magnification(self):
        self.magnification = point_lens_magnification
        return self.magnification

    def get_d_A_d_params(self):
        return self.d_A_d_params


class FiniteSourceGould94MagnificationCurve(PointLensMagnificationCurve):

    def __init__(self, **kwargs):
        PointLensMagnificationCurve.__init__(**kwargs)
        self.pspl_magnification = None
        self.B_0 = None

    def _check_parameters(self, parameters):
        PointLensMagnificationCurve._check_parameters(parameters)
        # Check for rho

    def get_pspl_magnification(self):
        self.pspl_magnification = PointLensMagnificationCurve.get_magnification()
        return self.pspl_magnification

    def get_B_0(self):
        return self.B_0

    def get_magnification(self):
        if self.pspl_magnification is None:
            self.get_pspl_magnification()

        if self.B_0 is None:
            self.get_B_0()

        self.magnification = self.pspl_magnification * self.B_0
        return self.magnification

    def get_d_A_d_params(self):
        PointLensMagnificationCurve.get_d_A_d_params()
        # Modifications for FSPL
        return self.d_A_d_params


class FiniteSourceYoo04MagnificationCurve(FiniteSourceGould94MagnificationCurve):

    def __init__(self, gamma=None, **kwargs):
        FiniteSourceGould94MagnificationCurve.__init__(**kwargs)
        self.B_1 = None
        self.gamma = gamma

    def _check_parameters(self, parameters):
        FiniteSourceGould94MagnificationCurve._check_parameters(parameters)
        # Check for gamma

    def get_B_1(self):
        return self.B_1

    def get_magnification(self):
        if self.B_1 is None:
            self.get_B_1()

        FiniteSourceGould94MagnificationCurve.get_magnification()
        self.magnification += self.gamma * self.B_1
        return self.magnification

    def get_d_A_d_params(self):
        FiniteSourceGould94MagnificationCurve.get_d_A_d_params()
        # Modifications for B_1 term
        return self.d_A_d_params

class FiniteSourceUniformLee09():

    def __init__(self, **kwargs):
        raise NotImplementedError

class FiniteSourceLDLee09():

    def __init__(self, gamma=None, **kwargs):
        raise NotImplementedError