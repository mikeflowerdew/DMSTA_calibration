#!/usr/bin/env python

"""
Create special-purpose event lists of the models with event generation.
There are two groups of event lists:
A) Models excluded by a particular SR (for making plots of excluded models)
B) A random separation of the 500 models into two groups. One is for making new calibration curves (=> output in the format of D3PDs.txt), and the other is for applying this modified calibration as a consistency check (=> output as a TEventList).
"""

import ROOT
ROOT.gRandom.SetSeed(1)

from glob import glob
SRfilenames = glob('results/smallest_officialMC_bestExpected/perSRresults/*.txt')
modeldict = {}
for fname in SRfilenames:
    SRname = fname.split('/')[-1].replace('.txt','')
    modeldict[SRname] = set()
    SRfile = open(fname)
    for line in SRfile:
        modeldict[SRname].add(int(line))
    SRfile.close()

infile = ROOT.TFile.Open('Data_Yields/SummaryNtuple_STA_evgen.root')
intree = infile.Get('susy')
intree.SetBranchStatus('*',0)
intree.SetBranchStatus('modelName',1)

eventlists = {
    }

for ientry,entry in enumerate(intree):

    if ientry%10000 == 0:
        print 'Model',ientry
    modelName = entry.modelName
    for SRname,modellist in modeldict.items():
        if modelName in modellist:
            try:
                eventlists[SRname].Enter(ientry)
            except KeyError:
                eventlists[SRname] = ROOT.TEventList('elist_'+SRname)
                eventlists[SRname].Enter(ientry)
            continue

outfile = ROOT.TFile.Open('Data_Yields/EventLists_evgen.root', 'RECREATE')
for elist in eventlists.values():
    elist.Write()
outfile.Close()

infile.Close()

infile = ROOT.TFile.Open('Data_Yields/SummaryNtuple_STA_sim.root')
intree = infile.Get('susy')
intree.SetBranchStatus('*',0)
intree.SetBranchStatus('modelName',1)

eventlists = {
    'TestCalib': ROOT.TEventList('elist_TestCalib'), # Just for checking
    'TestSample': ROOT.TEventList('elist_TestSample'),
    }
TestCalibModels = [] # Used later to create a text file of dataset names
TestSampleModels = []

for ientry,entry in enumerate(intree):

    if ientry%10000 == 0:
        print 'Model',ientry
    modelName = entry.modelName
    if ROOT.gRandom.Rndm() > 0.5:
        eventlists['TestCalib'].Enter(ientry)
        TestCalibModels.append(modelName)
    else:
        eventlists['TestSample'].Enter(ientry)
        TestSampleModels.append(modelName)

print 'Selected %i models for calibration'%(len(TestCalibModels))

# Now I need to convert eventlists['TestCalib'] into a text file
calibtxtfile = open('Data_Yields/D3PDs_calibsubset.txt', 'w')
sampletxtfile = open('Data_Yields/D3PDs_testsubset.txt', 'w')
inputtxtfile = open('Data_Yields/D3PDs.txt')
for line in inputtxtfile:

    if not line.rstrip():
        continue
    splitline = line.split('.')
    
    try:
        modelID = int(splitline[2].split('_')[5])
    except:
        print 'WARNING: failed to read line in D3PDs.txt'
        print repr(line)
        print splitline
        raise # Because I want to see what this is and fix it
    
    if modelID in TestCalibModels:
        calibtxtfile.write(line)
    elif modelID in TestSampleModels:
        sampletxtfile.write(line)
calibtxtfile.close()
sampletxtfile.close()
inputtxtfile.close()

outfile = ROOT.TFile.Open('Data_Yields/EventLists_sim.root', 'RECREATE')
for elist in eventlists.values():
    elist.Write()
outfile.Close()

infile.Close()
