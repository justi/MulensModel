from MulensModel.magnification_curves import PointLensMagnificationCurve


class BinaryLensPSMagnificationCurve(PointLensMagnificationCurve):

    def __init__(self, **kwargs):
        PointLensMagnificationCurve.__init__(**kwargs)

    def _check_parameters(self, parameters):
        pass

    def get_magnification(self):
        self.magnification = binary_lens_magnification
        return self.magnification

    def get_d_A_d_params(self):
        raise NotImplementedError(
            'Gradient methods NOT implemented for binary lenses.')

class BinaryLensQuadrupoleMagnificationCurve(BinaryLensPSMagnificationCurve):

    def __init__(self, **kwargs):
        BinaryLensPSMagnificationCurve.__init__(**kwargs)

    def get_magnification(self):
        self.magnification = binary_lens_magnification
        return self.magnification

class BinaryLensHexadecapoleMagnificationCurve(
    BinaryLensQuadrupoleMagnificationCurve):

    def __init__(self, **kwargs):
        BinaryLensQuadrupoleMagnificationCurve.__init__(**kwargs)

    def get_magnification(self):
        self.magnification = binary_lens_magnification
        # Hexadecapole modifications
        return self.magnification

class BinaryLensVBBLMagnificationCurve(BinaryLensPSMagnificationCurve):

    def __init__(self, **kwargs):
        BinaryLensPSMagnificationCurve.__init__(**kwargs)

    def get_magnification(self):
        self.magnification = binary_lens_magnification
        return self.magnification

class BinaryLensACMagnificationCurve(BinaryLensPSMagnificationCurve):

    def __init__(self, **kwargs):
        BinaryLensPSMagnificationCurve.__init__(**kwargs)

    def get_magnification(self):
        self.magnification = binary_lens_magnification
        return self.magnification
