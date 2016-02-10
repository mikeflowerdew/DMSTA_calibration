#!/usr/bin/env python

"""A simple script to skim out the useful info from the 26GB(!) input yield file"""

import ROOT
ROOT.gROOT.SetBatch(True)

infile = ROOT.TFile.Open('Data_Yields/SummaryNtuple_STA_all.root')
intree = infile.Get('susy')

intree.SetBranchStatus('*', 0)
intree.SetBranchStatus('modelName', 1)

# Turn analysis branches on
intree.SetBranchStatus('*EwkFourLepton*', 1)
intree.SetBranchStatus('*EwkThreeLepton*', 1)
intree.SetBranchStatus('*EwkTwoLepton*', 1)
intree.SetBranchStatus('*EwkTwoTau*', 1)
intree.SetBranchStatus('*DisappearingTrack*', 1)

# Add some associated info about the models
intree.SetBranchStatus('BF_chi_*', 1)
intree.SetBranchStatus('Cross_section_nn*', 1)
intree.SetBranchStatus('cos_tau', 1)
intree.SetBranchStatus('m_chi_*', 1)
intree.SetBranchStatus('LLV_*', 1)
intree.SetBranchStatus('mu', 1)
intree.SetBranchStatus('tanb', 1)

# Turn some specific categories of branches off again
intree.SetBranchStatus('EWTruthAcc_*', 0)

outfile_sim = ROOT.TFile.Open('Data_Yields/SummaryNtuple_STA_sim.root', 'RECREATE')
outtree_sim = intree.CloneTree(0)
# outtree_sim.CopyEntries(intree) # This copies every event

outfile_evgen = ROOT.TFile.Open('Data_Yields/SummaryNtuple_STA_evgen.root', 'RECREATE')
outtree_evgen = intree.CloneTree(0)

# A third copy, for all the models without truth acceptance
# Mainly for validation (ie that I don't skip one by mistake)
outfile_noevgen = ROOT.TFile.Open('Data_Yields/SummaryNtuple_STA_noevgen.root', 'RECREATE')
outtree_noevgen = intree.CloneTree(0)

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

print 'Looping over',intree.GetEntries(),'entries'
nwritten = 0
for entry in intree:

    modelName = entry.modelName
    if modelName % 1000 == 0:
        print 'On model %6i, written %3i so far'%(modelName,nwritten)

    # Check if the truth analysis actually ran
    HaveTruthAcc = entry.EW_ExpectedEvents_EwkTwoLepton_SR_Zjets != -1

    if HaveTruthAcc:
        # Write all events to "evgen" tree for easier processing later
        outtree_evgen.Fill()
        if modelName in modellist:
            outtree_sim.Fill()
            nwritten += 1
    else:
        outtree_noevgen.Fill()

    # if nwritten == 5: break # Just for testing

print 'Looped over',intree.GetEntries(),'entries'
print 'Selected',nwritten,'entries'

outfile_sim.cd()
outtree_sim.Write()
outfile_sim.Close()

outfile_evgen.cd()
outtree_evgen.Write()
outfile_evgen.Close()

outfile_noevgen.cd()
outtree_noevgen.Write()
outfile_noevgen.Close()

infile.Close()

