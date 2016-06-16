#!/usr/bin/env python

# Really stupid code
# I should be able to integrate this into the rest of it, but I can't think how

import ROOT,math
ROOT.gROOT.SetBatch(True)
ROOT.gROOT.LoadMacro("AtlasStyle.C")
ROOT.SetAtlasStyle()
ROOT.gROOT.LoadMacro("AtlasUtils.C") 
ROOT.gROOT.LoadMacro("AtlasLabels.C")

outdir = 'calibcheck'

import os
if not os.path.exists(outdir):
    os.makedirs(outdir)

# Use just the "test" models - this gives me access to the real CL values per SR
from Reader_DMSTA import DMSTAReader
reader = DMSTAReader(DSlist='Data_Yields/D3PDs_testsubset.txt')
data = reader.ReadFiles()

# Now extract my calibrated CLs values
from glob import glob
calibfilelist = glob('results/smallest_officialMC_bestExpected_subset/perSRresults/*.dat')
MyCLs = {} # SR : {model: (Obs,Exp)}
for calibfilename in calibfilelist:
    calibsetfile = open(calibfilename)
    SRname = calibfilename.split('/')[-1].replace('.dat','')
    MyCLs[SRname] = {}
    for line in calibsetfile:
        try:
            model,CLsObs,CLsExp = line.split(',')
            MyCLs[SRname][int(model)] = (float(CLsObs),float(CLsExp))
        except:
            pass

# Now try to compare the results with the real values
can = ROOT.TCanvas('can','can',800,800)

for dataobj in data:
    # Just one SR for now, will try more later
    SRname = dataobj.name
    if not MyCLs.has_key(SRname):
        continue
    # if SRname != 'EwkThreeLepton_3L_SR0a_16':
    #     continue

    outfilename = '/'.join([outdir,SRname+'.pdf'])
    can.Print(outfilename+'[')

    CLsObsGraph = ROOT.TGraph()
    CLsObsGraph.SetName(SRname+'_CLsObs')
    CLsExpGraph = ROOT.TGraph()
    CLsExpGraph.SetName(SRname+'_CLsExp')

    for modelID in MyCLs[SRname].keys():
        DSID = reader.DSIDdict[modelID]
        try:
            RealCLsObs = math.pow(10, dataobj.data[DSID]['LogCLsObs'])
            RealCLsExp = math.pow(10, dataobj.data[DSID]['LogCLsExp'])
        except KeyError:
            # I guess this SR had no result for this model
            print '====================== no result for',modelID
            continue
        except TypeError:
            # Just missing that model
            continue
        MyCLsObs,MyCLsExp = MyCLs[SRname][modelID]
        
        CLsObsGraph.SetPoint(CLsObsGraph.GetN(), RealCLsObs, MyCLsObs)
        CLsExpGraph.SetPoint(CLsExpGraph.GetN(), RealCLsExp, MyCLsExp)

    exclusionLine = ROOT.TLine()
    exclusionLine.SetLineColor(ROOT.kGray)
    exclusionLine.SetLineWidth(4)
    exclusionLine.SetLineStyle(7)
    CLsvalue = 0.05

    CLsObsGraph.Draw('ap')
    CLsObsGraph.GetXaxis().SetTitle('Observed CL_{s}')
    CLsObsGraph.GetYaxis().SetTitle('Estimated observed CL_{s}')
    exclusionLine.DrawLine(CLsvalue,CLsObsGraph.GetYaxis().GetXmin(), CLsvalue,CLsObsGraph.GetYaxis().GetXmax())
    exclusionLine.DrawLine(CLsObsGraph.GetXaxis().GetXmin(),CLsvalue, CLsObsGraph.GetXaxis().GetXmax(),CLsvalue)
    can.SetLogx()
    can.SetLogy()
    can.Print(outfilename)

    CLsExpGraph.Draw('ap')
    CLsExpGraph.GetXaxis().SetTitle('Expected CL_{s}')
    CLsExpGraph.GetYaxis().SetTitle('Estimated expected CL_{s}')
    exclusionLine.DrawLine(CLsvalue,CLsExpGraph.GetYaxis().GetXmin(), CLsvalue,CLsExpGraph.GetYaxis().GetXmax())
    exclusionLine.DrawLine(CLsExpGraph.GetXaxis().GetXmin(),CLsvalue, CLsExpGraph.GetXaxis().GetXmax(),CLsvalue)
    can.Print(outfilename)

    can.Print(outfilename+']')
