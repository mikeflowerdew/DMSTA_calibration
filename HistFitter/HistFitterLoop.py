#!/bin/env python

import ROOT, math

# ########################################################
# Storage class for inputs
# ########################################################

class PaperResults:
    """Class to hold SR yield information for one signal region.
    """

    # The slots show which data this class holds
    __slots__ = {
        'SR'     : '',   # SR name
        'Nbkg'   : None, # Number of background events. Could be a valueWithError?
        'NbkgErr': None, # Absolute error on the number of bkg events
        'Ndata'  : None, # Number of events in data
        'Limit'  : None, # Model independent limit. Used only to start the Nsig scan, so does not need to be precise
        }

    def __init__(self):
        """Set all properties to their default values, from self.__slots__
        """

        for k,v in self.__slots__.items():
            setattr(self,k,v)

    def isOK(self):
        """Simple sanity check that the stored information is valid.
        Not a complete test, but a start.
        """

        # Background systematic should be reasonable
        try:
            assert(self.NbkgErr/self.Nbkg < 1)
        except: # Almost any exception indicates a poor result
            return False
        
        # SR string should not have spaces
        try:
            assert(' ' not in self.SR)
        except:
            return False

        # Data events should be an integer (dumb way to test, I know)
        # This is now checked again later
        try:
            assert(self.Ndata % 1 == 0)
        except:
            return False

        # SR, Nbkg and NbkgErr should be non-null values
        # Caution: Ndata _can_ be zero!
        return self.SR and self.Nbkg and self.NbkgErr and isinstance(self.Ndata,int)

# ########################################################
# RooStats interface
# ########################################################

# I want to run each fit within a subdirectory for safety
# Neat trick: use a context manager to handle this
from contextlib import contextmanager
import os

@contextmanager
def cd(newdir):

    # Record the current directory
    prevdir = os.getcwd()
    # Change to the new directory
    os.chdir(os.path.expanduser(newdir))

    try:
        # Pass control back to the caller
        yield
    finally:
        # At the end, change back to the original directory
        os.chdir(prevdir)

def RunOneSearch_RooStats(config, Nsig):
    """Runs the simplechannel example from the HistFitter page, once.
    It is a one-bin fit, with once main background systematic.
    This does not, in fact, use HistFitter, rather the underlying RooStats classes,
    but the effect should be the same.

    config should be a PaperResults object, which has all the info I need to set up a simple 1-bin fit,
    while Nsig is the expected number of signal events.
    The method returns a CLs value, or None if a problem occurred.
    """

    # Check if the input is OK
    if not config.isOK(): return None

    # Work in a subdirectory named the same as the SR
    testdir = config.SR
    import os,shutil
    # Remove the directory if it already exists, so we have a clean start
    if os.path.exists(testdir):
        shutil.rmtree(testdir)
    # Make the directory(ies)
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
        signalhist.Fill(0.5, Nsig)
        signalhist.Write()
    
        backgroundhist = ROOT.TH1F('background','',1,0,1)
        backgroundhist.Fill(0.5, config.Nbkg)
        backgroundhist.Write()
    
        datahist = ROOT.TH1F('data','',1,0,1)
        datahist.Fill(0.5, config.Ndata)
        datahist.Write()
    
        modelfile.Close()
    
        # ########################
        # Step 2: Create a couple of xml files
        
        # I was going to use ElementTree to make the xml writing more flexible,
        # but as writing the header is non-trivial and the files are short I'll just do this long-handed.

        # See the HistFitter tutorial(s) for what all of this means

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
        workspace.var('Lumi').setConstant() # Oh, I guess this means I turned it off :)

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
    
    # At the end of the "with:" block, the context manager returns us to the original directory
    
    try:
        # Return the CLs value
        return result.GetCLs()
    except:
        # result does not exist, return None to indicate an error
        return None

# ########################################################
# HistFitter interface
# ########################################################

def RunOneSearch_HistFitter(config, Nsig):
    """Runs the MyUserAnalysis example from the HistFitter page, once.
    It is a one-bin fit, with once main background systematic.

    config should be a PaperResults object, which has all the info I need to set up a simple 1-bin fit,
    while Nsig is the expected number of signal events.
    The method returns a negative log-likelihood value, or None if a problem occurred.
    """

    # Check if the input is OK
    if not config.isOK(): return None

    # Work in a subdirectory named the same as the SR
    testdir = config.SR
    import os,shutil
    # Remove the directory if it already exists, so we have a clean start
    if os.path.exists(testdir):
        shutil.rmtree(testdir)
    # Make the directory(ies)
    os.makedirs(testdir)

    # Use the context manager to handle the changing of directory
    with cd(testdir):

        # Warning: the internal logic of this is a bit hairy
        # Be careful if you edit!

        # ########################
        # FIXME FIXME FIXME
        # NEEDS TO BE UPDATED TO ACTUALLY RUN HISTFITTER!
        # ########################

        # HistFitter.py -fwp -F excl <config>.py
        # Util::GeneratePlots("results/MyUserAnalysis/SplusB_combined_NormalMeasurement_model.root", "MyUserAnalysis", 0, 0, 0, 0, 1, 0, "", 0, "", 0);
        # (run by Sarah as root -l -b -q 'extractLikelihood.C()')
        # Then the results directory contains can_NLL__RooExpandedFitResult_afterFit_mu_Sig.root
        # Which has a RooCurve called nll_mu_Sig
        # nll_mu_Sig.Eval(1.) gets the mu=1 LLH

        # ########################
        # Step 0: Make sure we have everything we need

        # # Does not appear to be necessary
        # import shutil
        # shutil.copy('../HistFactorySchema.dtd', '.')

        # ########################
        # Step 1: Create the HistFitter config file

        configfile = open('HistFitterConfig.py', 'w')
        configfile.write('ndata     =  7.\n')
        configfile.write('nbkg      =  5.\n')
        configfile.write('nsig      =  3.\n')
        configfile.write('nbkgErr   =  1.\n')
        configfile.write('nsigErr   =  0.01\n')

        with open('../HistFitterConfig.py') as genericfile: configfile.write(genericfile.read())
        configfile.close()

        # ########################
        # Step 2: Run HistFitter

        ROOT.gSystem.Exec('HistFitter.py -fwp -F excl HistFitterConfig.py')

        # ########################
        # Step 3: Generate the LLH plot

        ROOT.Util.GeneratePlots('results/MyUserAnalysis/SplusB_combined_NormalMeasurement_model.root', 'MyUserAnalysis', 0, 0, 0, 0, 1, 0, "", 0, "", 0)

        # ########################
        # Step 4: Extract the results
        
        NLLfile = ROOT.TFile.Open('results/MyUserAnalysis/can_NLL__RooExpandedFitResult_afterFit_mu_Sig.root')
        
        NLLfunc = NLLfile.Get('nll_mu_Sig')

        print NLLfunc
        NLLfile.ls()
        
        # For now, just take the NLL wrt the best fit mu value
        NLLvalue = NLLfunc.Eval(1.)
    
    return NLLvalue

# ########################################################
# Signal yield scanning strategy
# ########################################################

def NSigStrategy(existingResults, SRobj, granularity=0.05, logCLs=True, logMin=-6):
    """Returns a list of signal yield values to try, given a list of (Nsig,CLs) tuples.
    The function tries to space the points more or less evenly in log(CLs) by default,
    between logMin and zero.

    SRobj is a PaperResults object.
    The granularity argument is the desired CLs separation - if larger
    gaps are found then the function returns a list of yield values
    to try and fill the gaps.
    May return an empty list in case of error or no more samples needed.
    The logic is written so that, whatever happens, eventually an empty
    list should be returned, terminating the loop.

    The default is to populate log10(CLs) evenly between logMin and 0
    (10^[logMin] < CLs < 1). If logCLs is False, then the function attempts
    to populate CLs evenly between 0 and 1.
    In both cases, the granularity sets the desired maximum separation between
    neighbouring points.
    Remember that the final TF1 has 100 points by default, so log granularities
    much below 100/abs(logMin) and linear granularities much below 0.01 are pointless.
    """

    if not existingResults:
        # This is the first go.
        # Start with a simple list based on the model-independent limit
        # Start with "high priority" runs close to exclusion.
        return [ scale*SRobj.Limit for scale in [1.0, 0.5, 2.0, 0.25] ]
        
    # Make sure that the existing results are sorted!
    # Note this will sort low to high Nsig, ie high to low CLs
    existingResults.sort()

    # Special case to make sure we get to high values
    if existingResults[0][1] < 0.999:
        # Add a point corresponding to Yield=0 and CLs=1
        existingResults.insert(0, (0,1) )

    # Let's make sure we go low enough too
    # First tackle the case of a log scale
    if logCLs and math.log10(existingResults[-1][1]) > logMin:
        # I don't want to overshoot logMin by too much,
        # as this can be very wasteful.

        # If we're a long way from the end, just double the yield
        if math.log10(existingResults[-1][1])/logMin < 0.5:
            return [ 2.0*existingResults[-1][0] ]

        # If we're not so far off, try a more sophisticated extrapolation

        # Assume that the gradient in Yield vs log10(CLs) is constant,
        # and guesstimate the Yield I need from that.
        # There should be no danger of existingResults having <2 elements.
        DeltaCLs = math.log10( existingResults[-2][1] / existingResults[-1][1] )
        DeltaYield = existingResults[-1][0] - existingResults[-2][0]
        CLsDistance = math.log10(existingResults[-1][1]) - (1.01*logMin) # Allow a little safety margin

        # Linear extrapolation
        YieldEstimate = existingResults[-1][0] + CLsDistance*DeltaYield/DeltaCLs

        # The above estimate can sometimes overshoot.
        # If the extrapolation is very big, just double the yield
        YieldEstimate = min([YieldEstimate, 2.0*existingResults[-1][0]])

        return [ YieldEstimate ]

    # In the non-log case, we just need to make sure we have a point with CLs < granularity
    if not logCLs and existingResults[-1][1] > granularity:
        # Just increase by a factor of 2
        # This might give a stupidly low CLs value,
        # but on a linear scale this doesn't really matter too much
        return [2.0*existingResults[-1][0]]

    # If we get here, then the upper and lower ends of the CLs range are OK.
    # This means it's time to fill out the middle!
    from pprint import pprint
    print 'HistFitterLoop: Results so far...'
    pprint(existingResults)

    # Look through pairs of results for CLs values less than some threshold
    # Neat trick from itertools!
    from itertools import tee, izip
    def pairwise(iterable):
        "s -> (s0,s1), (s1,s2), (s2, s3), ..."
        a, b = tee(iterable)
        next(b, None)
        return izip(a, b)

    for result0,result1 in pairwise(existingResults):

        # How does the CLs difference (or its log) compare to our desired tolerance?
        CLsDiff = abs(math.log10(result1[1]/result0[1])) if logCLs else abs(result1[1] - result0[1])
        if CLsDiff < granularity:
            # OK, move on
            continue

        # We need to add some points
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
            pprint(existingResults)
            raise

        MinNsig = result0[0]

        # Now, return our list of suggestions
        # Of course MinNsig+Nsteps*StepSize is intentially not included ;)
        return [ MinNsig+i*StepSize for i in range(1,int(Nsteps)) ]

    # If we get here, I guess we're done!
    return []

# ########################################################
# Execution starts here
# ########################################################

if __name__=='__main__':

    # ########################
    # Initial setup
    ROOT.gROOT.SetBatch(True)
    ROOT.gROOT.LoadMacro("AtlasStyle.C")
    ROOT.SetAtlasStyle()
    ROOT.gROOT.LoadMacro("AtlasUtils.C") 
    ROOT.gROOT.LoadMacro("AtlasLabels.C") 
    ROOT.gSystem.Load('libSusyFitter.so')
    ROOT.gROOT.ProcessLine('#include "/ptmp/mpp/flowerde/HistFitter/src/Utils.h"') # Needed to get the Utils from HistFitter working

    # Read in the analyses
    datafile = open('PaperSRData.dat')

    configlist = [] # List of PaperResults objects, not used at the moment
    thingsToWrite = [] # Keeps persistent objects in memory

    # Some settings that affect how the scan is done
    # Maybe promote these to a command line option...?
    doLogCLs = True
    logMin = -6

    # ########################
    # Loop over the signal regions
    for line in datafile:

        # Skip comments and obviously invalid lines
        if line.startswith('#'): continue
        splitline = line.split()
        if len(splitline) < 5: continue

        config = PaperResults()
        try:
            # Do the casting now, within the try block, to weed out errors
            config.SR      = splitline[0]
            config.Ndata   = int(splitline[1])
            config.Nbkg    = float(splitline[2])
            config.NbkgErr = float(splitline[3])
            config.Limit   = float(splitline[4])
        except:
            continue

        # Store the PaperResults object in case it's useful
        configlist.append(config)

        # Config looks OK - first pick a starting range of signal yields to try
        YieldValues = NSigStrategy([], config, logCLs=doLogCLs, logMin=logMin)
        
        # Keep a record in order of execution so I can see how the search progressed
        # Note this is a list of lists, ie each call to NSigStrategy is separated from the rest
        YieldOrder = []
        YieldOrder.append([v for v in YieldValues])

        # Store for the CLs results
        results = []

        # ########################
        # Loop over signal yields

        # Now we just keep going till we run out of values to try
        while YieldValues:

            # Pick up the first yield value, removing it from the list
            Nsig = YieldValues.pop(0)
            
            # Erm, I probably should have checked this earlier...?
            if not config.isOK():
                print 'CONFIG NOT OK!!!!'

            # Run the fit and record the result if it makes sense
            CLs = RunOneSearch_RooStats(config, Nsig)
            if CLs is not None:
                results.append( (Nsig,CLs) )
            
            # If we're out of values, give a chance to replenish them
            # If there's nothing left to do, NSigStrategy should return an empty list
            if not YieldValues:
                YieldValues = NSigStrategy(results, config, logCLs=doLogCLs, logMin=logMin)
                YieldOrder.append([v for v in YieldValues])

            # Crude attempt to avoid an infinite loop
            # Note this len() call counts the number of calls to NSigStrategy,
            # *not* the number of calls to RunOneSearch_RooStats.
            if len(YieldOrder) > 100:
                print 'Cutting out because I reached %i iterations'%(len(YieldOrder))
                break

        # ########################
        # Summarise results for this SR

        from pprint import pprint
        print '============= Printing results for',config.SR
        pprint(results)
        print '============= Printing the Yield search pattern for',config.SR
        pprint(YieldOrder)

        # Store the calibration curve in a TGraph, which can then be converted to TF1
        graph = ROOT.TGraph()
        graph.SetName(config.SR+'_graph')
        results.sort() # Just in case
        for Nsig,CLs in results:
            graph.SetPoint(graph.GetN(),math.log10(CLs) if doLogCLs else CLs,Nsig)

        # Amazingly this works!
        if doLogCLs:
            function = ROOT.TF1(config.SR, lambda x,p: p[0]*graph.Eval(x[0]), logMin, 0, 1)
        else:
            function = ROOT.TF1(config.SR, lambda x,p: p[0]*graph.Eval(x[0]), 0, 1, 1)
        function.SetParameter(0,1) # Default "normalisation"

        # Make sure we write both the graph and the function to the output file
        thingsToWrite.append(graph.Clone())
        thingsToWrite.append(function.Clone())

        # Store a copy now, in case later SRs fail
        outfilename = 'result_logCLs.root' if doLogCLs else 'result_linearCLs.root'
        outfile = ROOT.TFile.Open('/'.join([config.SR,outfilename]),'RECREATE')
        graph.Write()
        function.Write()
        outfile.Close()

    # ########################
    # End of the SR loop, final wrap-up

    # Store TGraphs and TF1s in an output file
    outfilename = 'CLsFunctions_logCLs.root' if doLogCLs else 'CLsFunctions_linearCLs.root'
    outfile = ROOT.TFile.Open(outfilename,'RECREATE')
    for thing in thingsToWrite:
        thing.Write()
    outfile.Close()
