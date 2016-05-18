#!/bin/env python

# This is a simple script to run one fit using HistFitterLoop.py
# It is meant for testing purposes

import ROOT
from HistFitterLoop import RunOneSearch,PaperResults

# Set up all of the libraries etc that we need
ROOT.gROOT.SetBatch(True)
ROOT.gROOT.LoadMacro("AtlasStyle.C")
ROOT.SetAtlasStyle()
ROOT.gROOT.LoadMacro("AtlasUtils.C") 
ROOT.gROOT.LoadMacro("AtlasLabels.C") 
ROOT.gSystem.Load('libSusyFitter.so')

# Create the (made-up) input
config = PaperResults()
config.SR = 'SR1'
config.Ndata = 10
config.Nbkg = 8.7
config.NbkgErr = 3.0
config.Limit = 4.0

# Decide on some arbitrary test signal
Nsig = 5.0

# Run the fit!
CLs = RunOneSearch(config, Nsig)

print 'The CLs result is',CLs
