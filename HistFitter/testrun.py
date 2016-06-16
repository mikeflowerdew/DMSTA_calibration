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
CLsObs_RS,CLsExp_RS = RunOneSearch_RooStats(config, Nsig)

# Run a second fit with HistFitter
# I need to change the SR name so the first test directory doesn't get overwritten
config.SR = 'SR1a'
LLH_HF = RunOneSearch_HistFitter(config, Nsig)

print 'The CLsObs result from RooStats is',CLsObs_RS
print 'The CLsExp result from RooStats is',CLsExp_RS
print 'The negative LLH result from HistFitter is',LLH_HF

# Let's do a simple test
import shutil
shutil.copy('%s/results/MyUserAnalysis/can_NLL__RooExpandedFitResult_afterFit_mu_Sig.root'%(config.SR), 'HFresult_%s.root'%(Nsig))

for Nsig in [1.0, 10.0]:
    
    LLH_HF = RunOneSearch_HistFitter(config, Nsig)
    shutil.copy('%s/results/MyUserAnalysis/can_NLL__RooExpandedFitResult_afterFit_mu_Sig.root'%(config.SR), 'HFresult_%s.root'%(Nsig))
