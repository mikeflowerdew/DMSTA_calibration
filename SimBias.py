#!/usr/bin/env python

"""A simple script to check for possible bias in the selection of simulated models."""

from ValueWithError import valueWithError

# A bit dumb, but I need a helper function
def pullInOverflow(hist):
    """Pull the overflow into the final histogram bin."""

    if not hist: return

    nbins = hist.GetNbinsX()

    lastbin  = valueWithError(hist.GetBinContent(nbins  ),hist.GetBinError(nbins ))
    lastbin += valueWithError(hist.GetBinContent(nbins+1),hist.GetBinError(nbins+1))

    hist.SetBinContent(nbins,lastbin.value)
    hist.SetBinError(nbins,lastbin.error)

    return
    
def drawHistos(hname1,hname2,title,pdfname,hname3=''):
    """Draw two plots on the same canvas,
    both with overflows pulled in and normalised to unit area.
    It is assumed that both histograms exist in ROOT.gDirectory.
    """

    # Draw the two histograms, making sure they have the same binning
    hist1 = ROOT.gDirectory.Get(hname1)
    hist2 = ROOT.gDirectory.Get(hname2)
    hist3 = ROOT.gDirectory.Get(hname3) if hname3 else None

    # Pull overflow into the histogram
    pullInOverflow(hist1)
    pullInOverflow(hist2)
    pullInOverflow(hist3)

    if not hist1.Integral(): return False

    # Set up style and normalisation
    hist1.SetLineColor(ROOT.kBlue)
    hist1.Scale(1./hist1.Integral())

    if hist2.Integral():
        hist2.Sumw2()
        hist2.Scale(1./hist2.Integral())

    if hist3 and hist3.Integral():
        hist3.SetMarkerColor(ROOT.kRed)
        hist3.SetLineColor(ROOT.kRed)
        hist3.Sumw2()
        hist3.Scale(1./hist3.Integral())

    # Sort which plot is bigger so they both fit on the canvas
    if hist2.GetMaximum() > hist1.GetMaximum():
        hist1.SetMaximum(1.1*hist2.GetMaximum())
    if hist3 and hist3.GetMaximum() > hist1.GetMaximum():
        hist1.SetMaximum(1.1*hist3.GetMaximum())

    # Draw!
    hist1.Draw('hist')
    hist2.Draw('esame')
    if hist3: hist3.Draw('esame')

    # Add a title so I know what the plot is, and save!
    ROOT.myText(0.2, 0.95, ROOT.kBlack, title)
    canvas.Print(pdfname)

    return [hist1,hist2,hist3] if hist3 else [hist1,hist2]

# Import & set up ATLAS style
import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.gROOT.LoadMacro("AtlasStyle.C")
ROOT.SetAtlasStyle()
ROOT.gROOT.LoadMacro("AtlasUtils.C") 

# Open the two ROOT files I want to compare
simfile = ROOT.TFile.Open('Data_Yields/SummaryNtuple_STA_sim.root')
simtree = simfile.Get('susy')

evgenfile = ROOT.TFile.Open('Data_Yields/SummaryNtuple_STA_evgen.root')
evgentree = evgenfile.Get('susy')

# Observed xsec limits from the paper, converted to events
# Note that there is no SR0
obslimits = [0,35.7,20.7,12.6,8.9]
passdistrk = '||'.join(['EW_ExpectedEvents_DisappearingTrack_SR%i > %.1f'%(SR,obslimits[SR]) for SR in range(1,5)])

# Set up the output file
pdfname = 'Data_Yields/SimSkim.pdf'
canvas = ROOT.TCanvas('can','can',800,600)
canvas.Print(pdfname+'[')

# Some way to store the output
histolist = []

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
    evgentree.Draw(branchname+'>>hevgen'+branchname+binstr)
    simtree.Draw(branchname+'>>hsim'+branchname+binstr)
    evgentree.Draw(branchname+'>>hdistrk'+branchname+binstr,
                   passdistrk)

    histolist.extend(drawHistos('hevgen'+branchname,'hsim'+branchname,
                                branchname, pdfname, 'hdistrk'+branchname))

# Close the pdf file
canvas.Print(pdfname+']')

# Save the plots!
outfile = ROOT.TFile.Open('Data_Yields/histograms.root','RECREATE')
for h in histolist:
    h.Write()
outfile.Close()

# I need more info about the disappearing track analysis

evgenentries = evgentree.GetEntries()
for SR in range(1,5):
    passlimit = 'EW_ExpectedEvents_DisappearingTrack_SR%i > %.1f'%(SR,obslimits[SR])
    ewkexclude = '(EW_Cat_EwkTwoLepton > 1 || EW_Cat_EwkThreeLepton > 1 || EW_Cat_EwkFourLepton > 1 || EW_Cat_EwkTwoTau > 1)'
    evgenmodels = evgentree.GetEntries(passlimit)
    evgenmodels_excluded = evgentree.GetEntries(passlimit+'&&'+ewkexclude)
    print
    print 'Studying DisTrk SR%i'%(SR)
    print '%i of %i non-simulated models above limit'%(evgenmodels,evgenentries)
    print 'Of these, %i might be excluded by EWK searches'%(evgenmodels_excluded)

print
print 'A total of %i models are excluded by the DisTrk analysis'%(evgentree.GetEntries(passdistrk))

simfile.Close()
evgenfile.Close()
