#!/bin/env python

import ROOT, math

class PaperResults:

    __slots__ = {
        'SR': '',
        'Nbkg': None, # Could be a ValueWithError?
        'NbkgErr': None, # Absolute error
        'Ndata': None,
        'Limit': None, # Model independent limit, to start the Nsig scan
        }

    def __init__(self):
        
        for k,v in self.__slots__.items():
            setattr(self,k,v)

    def isOK(self):
        """Not a complete test, but a start"""

        # Background systematic should be reasonable
        try:
            assert(self.NbkgErr/self.Nbkg < 1)
        except: # Almost any error indicates a poor result
            return False
        
        # SR string should not have spaces
        try:
            assert(' ' not in self.SR)
        except: # Almost any error indicates a poor result
            return False

        # Data events should be an integer (dumb way to test, I know)
        try:
            assert(self.Ndata % 1 == 0)
        except: # Almost any error indicates a poor result
            return False

        return self.SR and self.Nbkg and self.NbkgErr and self.Ndata

# I want to run HistFitter within a subdirectory for safety
from contextlib import contextmanager
import os

@contextmanager
def cd(newdir):
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)

def RunOneSearch(config, Nsig):
    """config should be a PaperResults object,
    which has all the info I need to set up a simple HistFitter 1-bin fit.
    The procedure here follows one of the tutorial examples in HistFitter.
    It's therefore a little bit convoluted...
    """

    if not config.isOK(): return

    testdir = config.SR
    import os,shutil
    if os.path.exists(testdir):
        # Remove it, so we have a clean directory
        shutil.rmtree(testdir)
    os.makedirs(testdir)

    # Use the context manager to handle the changing of directory
    with cd(testdir):

        # Warning: the internal logic of this is a bit hairy
        # Be careful if you edit!

        # ########################
        # Step 0: Make sure we have everything we need

        import shutil
        shutil.copy('../HistFactorySchema.dtd', '.')

        # ########################
        # Step 1: Create an input file

        modelfile = ROOT.TFile.Open('modelfile_%s.root'%(config.SR),'recreate')
    
        signalhist = ROOT.TH1F('signal','',1,0,1)
        signalhist.Fill(0.5,Nsig)
        signalhist.Write()
    
        backgroundhist = ROOT.TH1F('background','',1,0,1)
        backgroundhist.Fill(0.5,config.Nbkg)
        backgroundhist.Write()
    
        datahist = ROOT.TH1F('data','',1,0,1)
        datahist.Fill(0.5,config.Ndata)
        datahist.Write()
    
        modelfile.Close()
    
        # ########################
        # Step 2: Create a couple of xml files
        
        # I was going to use ElementTree, but as writing the header
        # is non-trivial and the files are short I'll just do this long-handed.

        masterfile = open('master.xml', 'w')
        masterfile.write('<!DOCTYPE Combination  SYSTEM "HistFactorySchema.dtd">\n')
        masterfile.write('<Combination OutputFilePrefix="simple">\n')
        masterfile.write('<Input>channel.xml</Input>\n')
        masterfile.write('<Measurement Name="%s" Lumi="1." LumiRelErr="0.028" BinLow="0" BinHigh="2" >\n'%(config.SR))
        masterfile.write('<POI>SigXsecOverSM</POI>\n')
        masterfile.write('</Measurement>\n')
        masterfile.write('</Combination>\n')
        masterfile.close()

        channelfile = open('channel.xml', 'w')
        channelfile.write('<!DOCTYPE Channel  SYSTEM \'HistFactorySchema.dtd\'>\n')
        channelfile.write('<Channel Name="channel1" InputFile="modelfile_%s.root" HistoName="" >\n'%(config.SR))
        channelfile.write('<Data HistoName="data" HistoPath="" />\n')
        channelfile.write('<Sample Name="signal" HistoPath="" HistoName="signal">\n')
        channelfile.write('<NormFactor Name="SigXsecOverSM" Val="1" Low="0." High="5." Const="True" />\n')
        channelfile.write('</Sample>\n')
        channelfile.write('<Sample Name="background" HistoPath="" NormalizeByTheory="True" HistoName="background">\n')
        channelfile.write('<OverallSys Name="syst2" Low="%.3f" High="%.3f"/>\n'%(1.-config.NbkgErr/config.Nbkg,1+config.NbkgErr/config.Nbkg))
        channelfile.write('</Sample>\n')
        channelfile.write('</Channel>\n')
        channelfile.close()

        # ########################
        # Step 3: Create a workspace

        ROOT.gSystem.Exec('hist2workspace master.xml')

        # ########################
        # Step 4: Open the workspace and run the fit

        fitfile = ROOT.TFile.Open('simple_channel1_%s_model.root'%(config.SR))
        workspace = fitfile.Get('channel1')
        workspace.var('Lumi').setConstant()

        # 0 = CPU clock
        # 1 helps get reproducible results
        ROOT.RooRandom.randomGenerator().SetSeed(1)

        # Even though this (without the RooStats scope) is the WRONG function,
        # It appears I need to acknowledge it before I can see the other one.
        # Weird...
        ROOT.get_Pvalue

        # Leave alone except for:
        # Third arg = number of toys
        # Fourth arg = calculator type. 0=toys, 2=asymptotic
        result = ROOT.RooStats.get_Pvalue(workspace, True, 5000, 2, 3)
        result.Summary()

        fitfile.Close()

    try:
        return result.GetCLs()
    except:
        return None

def NSigStrategy(existingResults, SRobj, granularity=0.02):
    """Returns a list of signal yield values to try,
    given a list of (Nsig,CLs) tuples.
    SRobj is a PaperResults object.
    The granularity argument is the desired CLs separation
    - if larger gaps are found, yield values should be suggested to fill
    in the gap.
    May return an empty list in case of error or no more samples needed.
    """

    if not existingResults:
        # Start with a simple list based on the model-independent limit
        # Start with "high priority" runs close to exclusion.
        return [scale*SRobj.Limit for scale in [1.0,0.5,2.0,0.25]]
        
    # Look through pairs of results for CLs values less than some threshold
    # Neat trick from itertools!
    from itertools import tee, izip
    def pairwise(iterable):
        "s -> (s0,s1), (s1,s2), (s2, s3), ..."
        a, b = tee(iterable)
        next(b, None)
        return izip(a, b)

    existingResults.sort()
    # Special case to make sure we get to high values
    if existingResults[0][1] < 0.999:
        existingResults.append( (0,1) )

    for result0,result1 in pairwise(existingResults):

        # How does the CLs difference compare to our desired tolerance?
        CLsDiff = abs(result1[1] - result0[1])
        if CLsDiff < granularity:
            # OK, move on
            continue

        # Break up the truth yield difference into sections,
        # by comparing the CLsDiff to the requested granularity.
        # Pretty dumb approach, should be conservative?
        NsigDiff = abs(result1[0] - result0[0])
        # How many segments do we need?
        Nsteps = math.ceil(CLsDiff/granularity)
        StepSize = NsigDiff/Nsteps
        
        # result0 *should* have the smallest Nsig value, but just in case...
        try: assert(result1[0] > result0[0])
        except AssertionError:
            from pprint import pprint
            pprint(existingResults)
            raise

        MinNsig = result0[0]

        # Now, return our list of suggestions
        # Of course MinNsig+Nsteps*StepSize is intentially not included ;)
        return [MinNsig+i*StepSize for i in range(1,int(Nsteps))]

    # If we get here, I guess we're done!
    return []

if __name__=='__main__':

    ROOT.gROOT.SetBatch(True)
    ROOT.gROOT.LoadMacro("AtlasStyle.C")
    ROOT.SetAtlasStyle()
    ROOT.gROOT.LoadMacro("AtlasUtils.C") 
    ROOT.gROOT.LoadMacro("AtlasLabels.C") 
    ROOT.gSystem.Load('libSusyFitter.so')

    # For now, run just one analysis
    config = PaperResults()
    config.SR = 'SR0noZa'
    config.Ndata = 3
    config.Nbkg = 1.6
    config.NbkgErr = 0.5
    config.Limit = 5.9

    YieldValues = NSigStrategy([], config) # First list of variables
    results = []

    while YieldValues:

        # Pick up the first yield value
        Nsig = YieldValues.pop(0)

        CLs = RunOneSearch(config, Nsig)
        results.append( (Nsig,CLs) )

        # If we're out of values, give a chance to replenish them
        if not YieldValues:
            YieldValues = NSigStrategy(results, config)

    from pprint import pprint
    pprint(results)

    graph = ROOT.TGraph()
    graph.SetName(config.SR+'_graph')
    results.sort() # Just in case
    for Nsig,CLs in results:
        graph.SetPoint(graph.GetN(),CLs,Nsig)

    # Amazingly this works!
    function = ROOT.TF1(config.SR, lambda x,p: p[0]*graph.Eval(x[0]), 0, 1, 1)
    function.SetParameter(0,1) # Default "normalisation"
    
    # Store TGraphs in an output file
    outfile = ROOT.TFile.Open('CLsFunctions.root','RECREATE')
    graph.Write()
    function.Write()
    outfile.Close()
