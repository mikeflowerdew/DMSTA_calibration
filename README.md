# DMSTA_calibration
Package for the calibration of CL values vs yield for the ATLAS dark matter STA project

A secondary goal of this repository is to learn a little more about how git works. Eventually the code will probably need to move to the ATLAS SVN area, as the real data cannot be placed on github.

The main script in this package is CorrelationPlotter.py. This holds the infrastructure to plot the correlations between CL values and the truth yield. As the input file format is not yet known, the plotting code is kept separate from the read-in code. At the moment, only dummy read-in classes are available.

To test using randomly-generated pseudodata:
$ ./CorrelationPlotter.py --dummyrandom
To test read-in of dummy text files:
$ ./CorrelationPlotter.py --dummy
Other options are not available yet.