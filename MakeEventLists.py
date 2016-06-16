#!/usr/bin/env python

import ROOT

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

eventlists = {}

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
