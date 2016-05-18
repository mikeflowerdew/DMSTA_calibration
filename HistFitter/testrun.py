#!/bin/env python

# This is a simple script to run one fit using HistFitterLoop.py
# It is meant for testing purposes

import ROOT
from HistFitterLoop import RunOneSearch_RooStats,RunOneSearch_HistFitter,PaperResults

# Set up all of the libraries etc that we need
ROOT.gROOT.SetBatch(True)
ROOT.gROOT.LoadMacro("AtlasStyle.C")
ROOT.SetAtlasStyle()
ROOT.gROOT.LoadMacro("AtlasUtils.C") 
ROOT.gROOT.LoadMacro("AtlasLabels.C") 
ROOT.gSystem.Load('libSusyFitter.so')
ROOT.gROOT.ProcessLine('#include "/ptmp/mpp/flowerde/HistFitter/src/Utils.h"')

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
CLs_RS = RunOneSearch_RooStats(config, Nsig)

# Run a second fit with HistFitter
# I need to change the SR name so the first test directory doesn't get overwritten
config.SR = 'SR1a'
LLH_HF = RunOneSearch_HistFitter(config, Nsig)

print 'The CLs result from RooStats is',CLs_RS
print 'The negative LLH result from HistFitter is',LLH_HF
