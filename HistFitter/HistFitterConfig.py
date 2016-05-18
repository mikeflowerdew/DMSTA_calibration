"""
This is a deliberately incomplete HistFitter config file.
The intention is to prepend the key information, like this:

ndata     =  7. 	# Number of events observed in data
nbkg      =  5.	 	# Number of predicted bkg events
nsig      =  3.  	# Number of predicted signal events
nbkgErr   =  1.  	# (Absolute) Statistical error on bkg estimate
nsigErr   =  0.01  	# (Absolute) Statistical error on signal estimate
# SRname    = "SR1"       # Signal region name

"""

# Keep the lumi error fixed
lumiError = 0.028 	# Relative luminosity uncertainty

# Initial imports

from configManager import configMgr
from ROOT import kBlack,kWhite,kGray,kRed,kPink,kMagenta,kViolet,kBlue,kAzure,kCyan,kTeal,kGreen,kSpring,kYellow,kOrange
from configWriter import fitConfig,Measurement,Channel,Sample
from systematic import Systematic
from math import sqrt

import os

# Setup for ATLAS plotting
from ROOT import gROOT
import ROOT

##########################

# Set observed and expected number of events in counting experiment

# Set uncorrelated systematics for bkg and signal (1 +- relative uncertainties)
ucb = Systematic("ucb", configMgr.weights, 1.+nbkgErr/nbkg, 1-nbkgErr/nbkg, "user","userOverallSys")
# ucs = Systematic("ucs", configMgr.weights, 1.1,0.9, "user","userOverallSys")

# correlated systematic between background and signal (1 +- relative uncertainties)
# corb = Systematic("cor",configMgr.weights, [1.1],[0.9], "user","userHistoSys")
# cors = Systematic("cor",configMgr.weights, [1.15],[0.85], "user","userHistoSys")

##########################

# Setting the parameters of the hypothesis test
configMgr.doExclusion=True # True=exclusion, False=discovery
#configMgr.nTOYs=5000
configMgr.calculatorType=2 # 2=asymptotic calculator, 0=frequentist calculator (ie toys)
configMgr.testStatType=3   # 3=one-sided profile likelihood test statistic (LHC default)
configMgr.nPoints=20       # number of values scanned of signal-strength for upper-limit determination of signal strength.

# configMgr.writeXML = True

##########################

# Give the analysis a name
configMgr.analysisName = "MyUserAnalysis"
configMgr.outputFileName = "%s_Output.root"%configMgr.analysisName

# Define cuts
configMgr.cutsDict["UserRegion"] = "1."

# Define weights
configMgr.weights = "1."

# Define samples
bkgSample = Sample("Bkg",kGreen-9)
bkgSample.setStatConfig(True)
bkgSample.buildHisto([nbkg],"UserRegion","cuts",0.5)
# bkgSample.buildStatErrors([nbkgErr],"UserRegion","cuts")
# bkgSample.addSystematic(corb)
bkgSample.addSystematic(ucb)


dataSample = Sample("Data",kBlack)
dataSample.setData()
dataSample.buildHisto([ndata],"UserRegion","cuts",0.5)

# Define top-level
ana = configMgr.addFitConfig("B")
ana.addSamples([bkgSample,dataSample])
# ana.setSignalSample(sigSample)

# Define measurement
meas = ana.addMeasurement(name="NormalMeasurement",lumi=1.0,lumiErr=lumiError)
meas.addPOI("mu_Sig")
#meas.addParamSetting("Lumi",True,1)

# Add the channel
chan = ana.addChannel("cuts",["UserRegion"],1,0.5,1.5)
ana.setSignalChannels([chan])

myTopLvl = configMgr.addFitConfigClone(ana,"SplusB")

sigSample = Sample("Sig",kPink)
sigSample.setNormFactor("mu_Sig",1.,0.,100.)
sigSample.setStatConfig(True)
sigSample.setNormByTheory()
sigSample.buildHisto([nsig],"UserRegion","cuts",0.5)
sigSample.buildStatErrors([nsigErr],"UserRegion","cuts")
# sigSample.addSystematic(cors)
# sigSample.addSystematic(ucs)

myTopLvl.addSamples(sigSample)
myTopLvl.setSignalSample(sigSample)
myTopLvl.setSignalChannels([chan])


# These lines are needed for the user analysis to run
# Make sure file is re-made when executing HistFactory
if configMgr.executeHistFactory:
    if os.path.isfile("data/%s.root"%configMgr.analysisName):
        os.remove("data/%s.root"%configMgr.analysisName) 
