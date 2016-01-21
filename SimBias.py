#!/usr/bin/env python

"""A simple script to check for possible bias in the selection of simulated models."""

from ValueWithError import valueWithError

# A bit dumb, but I need a helper function
def pullInOverflow(hist):
    """Pull the overflow into the final histogram bin."""

    nbins = hist.GetNbinsX()

    lastbin  = valueWithError(hist.GetBinContent(nbins  ),hist.GetBinError(nbins ))
    lastbin += valueWithError(hist.GetBinContent(nbins+1),hist.GetBinError(nbins+1))

    hist.SetBinContent(nbins,lastbin.value)
    hist.SetBinError(nbins,lastbin.error)

    return
    
# Import & set up ATLAS style
import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.gROOT.LoadMacro("AtlasStyle.C")
ROOT.SetAtlasStyle()
ROOT.gROOT.LoadMacro("AtlasUtils.C") 

# Open the two ROOT files I want to compare
simfile = ROOT.TFile.Open('Data_Yields/SummaryNtuple_STA_sim.root')
simtree = simfile.Get('susy')

nosimfile = ROOT.TFile.Open('Data_Yields/SummaryNtuple_STA_nosim.root')
nosimtree = nosimfile.Get('susy')

# Set up the output file
pdfname = 'Data_Yields/SimSkim.pdf'
canvas = ROOT.TCanvas('can','can',800,600)
canvas.Print(pdfname+'[')

# Loop over all branches
branchlist = simtree.GetListOfBranches()

for branchname in branchlist:

    # Adjust variable purely for my convenience
    branchname = branchname.GetName()

    # I cannot get automatic ranging to work, so let's do it by hand
    if branchname.startswith('BF_'):
        binstr = '(101,0,1.01)'
    elif branchname.startswith('Cross_section'):
        binstr = '(100,0,5)'
    elif branchname.startswith('EW_Cat'):
        binstr = '(6,-1.5,4.5)'
    elif branchname.startswith('EW_Expected'):
        binstr = '(110,-1,10)'
    elif branchname.startswith('EW_r_'):
        binstr = '(150,-1,2)'
    else:
        binstr = ''

    # Draw the two histograms, making sure they have the same binning
    nosimtree.Draw(branchname+'>>hnosim'+branchname+binstr)
    nosimhist = ROOT.gDirectory.Get('hnosim'+branchname)

    simtree.Draw(branchname+'>>hsim'+branchname+binstr)
    simhist = ROOT.gDirectory.Get('hsim'+branchname)

    # Pull overflow into the histogram
    pullInOverflow(simhist)
    pullInOverflow(nosimhist)

    if not nosimhist.Integral(): continue

    # Set up style and normalisation
    nosimhist.SetLineColor(ROOT.kBlue)
    nosimhist.Scale(1./nosimhist.Integral())

    if simhist.Integral():
        simhist.Sumw2()
        simhist.Scale(1./simhist.Integral())

    # Sort which plot is bigger so they both fit on the canvas
    if simhist.GetMaximum() > nosimhist.GetMaximum():
        nosimhist.SetMaximum(1.1*simhist.GetMaximum())

    # Draw!
    nosimhist.Draw('hist')
    simhist.Draw('esame')

    # Add a title so I know what the plot is, and save!
    ROOT.myText(0.2, 0.95, ROOT.kBlack, branchname)
    canvas.Print(pdfname)

# Close the pdf file
canvas.Print(pdfname+']')

simfile.Close()
nosimfile.Close()
