#!/usr/bin/env python

"""A simple script to skim out the useful info from the 26GB(!) input yield file"""

import ROOT
ROOT.gROOT.SetBatch(True)

# ########################################################
# Load up the input tree
# ########################################################

infile = ROOT.TFile.Open('Data_Yields/SummaryNtuple_STA_all_version4.root')
intree = infile.Get('susy')

# Turn every branch off, except the model ID
intree.SetBranchStatus('*', 0)
intree.SetBranchStatus('modelName', 1)

# Turn analysis branches on
intree.SetBranchStatus('*EwkFourLepton*', 1)
intree.SetBranchStatus('*EwkThreeLepton*', 1)
intree.SetBranchStatus('*EwkTwoLepton*', 1)
intree.SetBranchStatus('*EwkTwoTau*', 1)
intree.SetBranchStatus('*DisappearingTrack*', 1)
intree.SetBranchStatus('EW_Events_truth',1)

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
intree.SetBranchStatus('EWOffTruthAcc_*', 0)

# ########################################################
# Create the three output trees
# The second and third trees contain all models, with none in common
# ########################################################

# First, a tree with just the 500 simulated models
outfile_sim = ROOT.TFile.Open('Data_Yields/SummaryNtuple_STA_sim.root', 'RECREATE')
outtree_sim = intree.CloneTree(0)

# Second, a tree for all models with evgen
outfile_evgen = ROOT.TFile.Open('Data_Yields/SummaryNtuple_STA_evgen.root', 'RECREATE')
outtree_evgen = intree.CloneTree(0)

# Third, a tree for all models *without* evgen
outfile_noevgen = ROOT.TFile.Open('Data_Yields/SummaryNtuple_STA_noevgen.root', 'RECREATE')
outtree_noevgen = intree.CloneTree(0)

# ########################################################
# Make a list of simulated samples
# ########################################################

# Open the file with the list of simulated samples
f = open('Data_Yields/D3PDs.txt')

# Create a python list that will hold just the model IDs
modellist = []

# Loop over the simulated models
for line in f:

    line = line.rstrip() # Remove carriage returns etc
    if not line: # Empty line
        continue
            
    # The line is not empty, so should have a dataset name!
    # Split up the dataset into components
    splitline = line.split('.')

    # In case the line is malformed, try to catch errors
    try:
        # Extract the dataset ID and the model ID
        # The DSID is mainly to help check that this is a valid dataset name
        DSID = int(splitline[1])
        modelID = int(splitline[2].split('_')[5])
    except IndexError:
        # Badly formed line - print out a warning
        print 'WARNING: failed to read line in D3PDs.txt'
        print repr(line)
        print splitline
        raise # Because I want to see what this is and fix it

    # Everything OK, add this model to the list
    modellist.append(modelID)

# ########################################################
# Loop over the input tree and fill the output trees
# ########################################################

print 'Looping over',intree.GetEntries(),'entries'
nsimulated = 0 # Double-check the number of simulated samples

for entry in intree:

    # Very slight optimisation for speed
    modelName = entry.modelName
    if modelName % 1000 == 0:
        # The models actually don't print out in order any more,
        # but it's still useful to get some sense of progress
        print 'On model %6i, written %3i so far'%(modelName,nsimulated)

    # Check if the truth analysis actually ran
    HaveTruthAcc = entry.EW_Events_truth != -1

    if HaveTruthAcc:
        # We have evgen, write to the "evgen" tree!
        outtree_evgen.Fill()

        # Check to see if this model was simulated
        if modelName in modellist:
            outtree_sim.Fill()
            nsimulated += 1
    else:
        # Model was not generated, write to the "noevgen" tree
        outtree_noevgen.Fill()

    # if nsimulated == 5: break # Just for testing

print 'Looped over',intree.GetEntries(),'entries'
print 'Simulated',nsimulated,'entries'

# ########################################################
# Save the results
# ########################################################

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

