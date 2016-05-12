#!/bin/env python

import ROOT
from HistFitterLoop import RunOneSearch,PaperResults

ROOT.gROOT.SetBatch(True)
ROOT.gROOT.LoadMacro("AtlasStyle.C")
ROOT.SetAtlasStyle()
ROOT.gROOT.LoadMacro("AtlasUtils.C") 
ROOT.gROOT.LoadMacro("AtlasLabels.C") 
ROOT.gSystem.Load('libSusyFitter.so')

config = PaperResults()

config.SR = 'SR1'
config.Ndata = 10
config.Nbkg = 8.7
config.NbkgErr = 3.0
config.Limit = 4.0

Nsig = 5.0

CLs = RunOneSearch(config, Nsig)

print 'The CLs result is',CLs
