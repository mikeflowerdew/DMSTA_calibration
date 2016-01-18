#!/usr/bin/env python

"""A simple script to skim out the useful info from the 26GB(!) input yield file"""

import ROOT
ROOT.gROOT.SetBatch(True)

infile = ROOT.TFile.Open('Data_Yields/SummaryNtuple_STA_all.root')
intree = infile.Get('susy')

intree.SetBranchStatus('*', 0)
intree.SetBranchStatus('modelName', 1)
intree.SetBranchStatus('*EwkFourLepton*', 1)
intree.SetBranchStatus('*EwkThreeLepton*', 1)
intree.SetBranchStatus('*EwkTwoLepton*', 1)
intree.SetBranchStatus('*EwkTwoTau*', 1)

outfile = ROOT.TFile.Open('Data_Yields/SummaryNtuple_STA_skim.root', 'RECREATE')
outtree = intree.CloneTree(0)
# outtree.CopyEntries(intree) # This copies every event

# First-level optimisation: write output only for simulated samples
f = open('Data_Yields/D3PDs.txt')
modellist = []
for line in f:

    line = line.rstrip()
    if not line:
        continue
            
    # The line should be empty or a dataset name
    splitline = line.split('.')

    try:
        DSID = int(splitline[1])
        modelID = int(splitline[2].split('_')[5])
    except IndexError:
        print 'WARNING: failed to read line in D3PDs.txt'
        print repr(line)
        print splitline
        raise # Because I want to see what this is and fix it

    modellist.append(modelID)

nwritten = 0
for entry in intree:
    if entry.modelName in modellist:
        outtree.Fill()
        nwritten += 1

print 'Looped over',intree.GetEntries(),'entries'
print 'Selected',nwritten,'entries'

# The open command puts us in the correct directory
outtree.Write()
outfile.Close()

infile.Close()

