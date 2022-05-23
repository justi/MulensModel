# Some Notes About Refactoring Model, MagnificationCurve, etc. into subClasses

## Trajectory is fundamental

- Most of the arguments passed to MagnificationCurve are actually properties of
a Trajectory:
  -  yes: times, parameters, parallax=None, coords=None, satellite_skycoord=None,
  -  no: gamma=0.
  Hence, a MagnificationCurve could be uniquely specified by only two
  arguments: a Trajectory + gamma.

- FitData could be simplified by making the argument of model.get_magnification()
a Trajectory object. Then, all the properties of the dataset would be contained in
the Trajectory. The only problem is for generating magnifications of the model
at arbitrary times, in the absence of data. In that case, "times" would be
passed to get_magnification() and this could be used to generate a Trajectory
object with the properties of the model.

- Satellite_skycoord is only meaningful in the context of a Trajectory and the
only thing needed to calculate it is a set of times and coords. Thus,
get_satellite_skycoord should be a method of Trajectory, not MulensData.