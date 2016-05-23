#!/usr/bin/env python

import pickle,math

class CLs:
    """Small data class"""

    def __init__(self, value):
        try:
            # Maybe "value" is actually a CLs object
            self.value = value.value
            self.valid = value.valid
            self.ratio = value.ratio
        except AttributeError:
            # Or maybe "value" is really just a value
            # If "value" is negative, then it must be the log of a CLs value
            if value > 0:
                self.value = value
            else:
                self.value = math.pow(10,value)
            self.valid = True
            self.ratio = 1. # ratio to minimum CLs value

    def __float__(self):
        return float(self.value)

    def __cmp__(self, other):
        if self.value < float(other):
            return -1
        elif self.value > float(other):
            return 1
        else:
            return 0

    def __mul__(self, other):
        # A bit tricky to define, but let's go

        result = CLs(self.value*other.value)
        result.valid = self.valid and other.valid
        result.ratio = min([self.ratio,other.ratio])
        # Explanation: the ratio is used to determine if the
        # result was extrapolated. Therefore we want to
        # record the worst case, ie the smallest.

        return result

    def __str__(self):

        valuestr = '%.3f'%(self.value) if self.value > 0.01 else '%.2e'%(self.value)
        if self.valid:
            return valuestr
        else:
            return 'INVALID CLs value of %s'%valuestr

class DoNotProcessError(Exception):
    """Signals that there is something really wrong with the model,
    and it should not be processed by the STAs.
    """
    pass
#     def __init__(self, value):
#         self.value = value
#     def __str__(self):
#         return repr(self.value)

class Combiner:

    def __init__(self, yieldfilename, calibfilename):
        """Inputs are the ROOT files with the truth-level ntuple
        and the CL/yield calibration."""

        self.__yieldfilename = yieldfilename

        self.ReadCalibrations(calibfilename)

        # Some other configurable options
        self.strategy = 'smallest'
        self.truncate = False
        self.useexpected = False

    @classmethod
    def __FixXrange(cls, graph):
        """Fixes the x-axis range for a calibration graph.
        The range is [0,1] for a linear scale, and [-6,0] for a log scale.
        In the case of a log scale, the original minimum is stored under graph.xmin
        """

        # Retrieve the x-axis minimum, extend the range back down to zero
        graph.xmin = graph.GetXmin()
        # Test for linear or log x-axis scale
        if graph.xmin >= 0:
            # Linear
            graph.SetRange(0,graph.GetXmax())
        else:
            # Logarithmic
            graph.SetRange(-6,0)
            graph.xmin = math.pow(10,graph.xmin) # Convert back to linear scale

        # Nothing more to do
        return

    def ReadCalibrations(self, calibfilename):
        """Reads all TF1 objects and stores them in self.CalibCurves.
        This is a dictionary, with entries either like {SRname: CL_graph}.
        Another dictionary, self.CalibCurvesExp, stores the expected fit results,
        if they are found in the file.
        """

        self.CalibCurves = {}
        self.CalibCurvesExp = {}

        calibfile = ROOT.TFile.Open(calibfilename)

        for keyname in calibfile.GetListOfKeys():

            # Let's just make this easier
            keyname = keyname.GetName()
            
            thing = calibfile.Get(keyname)

            if not thing.InheritsFrom('TF1'):
                continue

            # This is a graph we want!

            # Fix its x-axis range
            self.__FixXrange(thing)
            
            # The graph names come with the CL type
            # separated from the analysis/SR by an underscore
            analysisSR = '_'.join(keyname.split('_')[:-1])

            # Work out if this is an expected or an observed result
            if 'Exp' in keyname:
                self.CalibCurvesExp[analysisSR] = thing
            else:
                self.CalibCurves[analysisSR] = thing

        calibfile.Close()

        return

    def __AnalyseModel(self, entry):
        """Analyse a single entry in the ntuple.
        This can raise a DoNotProcessError if the truth yields are not present."""

        results = {}
        resultsExp = {}
        negativeYieldList = []

        def GetCLs(graph, truthyield):
            """Small helper function to extract a valid CLs from a TGraph.
            If the number is out of the valid range, then None is returned.
            """

            result = CLs(graph.GetX(truthyield))

            # If on a linear scale, check if the CLs value is within the valid range
            if graph.GetXmin() >= 0 and result.value >= 0.999*graph.GetXmax():
                # Too high
                return None
            # Similar range check for a log scale
            if graph.GetXmin() < 0 and math.log10(result.value) >= graph.GetXmax():
                return None

            # Compare the CLs to our self-imposed minimum
            if result.value < graph.xmin:
                # This message prints out A LOT
                # print 'WARNING in CombineCLs: %s has CLs = %f below the min of %s'%(analysisSR,CLs,graph.xmin)

                result.valid = False
                result.ratio = result.value/graph.xmin

            return result

        # Start the event loop
        for analysisSR,graph in self.CalibCurves.items():

            # slow, slow, slow, but I guess OK for now
            truthyield = getattr(entry, graph.branchname)
            # trutherror = getattr(entry, '_'.join(['EW_ExpectedError',analysisSR]))
            if truthyield < 0:
                negativeYieldList.append(analysisSR)
                continue

            # Get the main result
            number = GetCLs(graph, truthyield)
            if number is None:
                continue

            if self.useexpected:
                # See if we have the corresponding expected result
                try:
                    graphExp = self.CalibCurvesExp[analysisSR]
                except KeyError:
                    # Only write the results out if we have the expected results
                    continue

                numberExp = GetCLs(graphExp, truthyield)
                if numberExp is None:
                    continue

                # We have both expected+observed results, so this is looking OK
                results[analysisSR] = number
                resultsExp[analysisSR] = numberExp

            else:
                # self.useexpected == False
                results[analysisSR] = number

            # print '%40s: %.3f events, CLs = %s, log(CLs) = %.2f'%(analysisSR,truthyield,number,math.log10(number.value))
            # if number.value < 1e-3:
            #     print number.value,graph.xmin,number.ratio

        if negativeYieldList:

            # Oh dear, we may have a problem, where a model with generated events
            # has no recorded yield for one or more SRs

            if len(negativeYieldList) == len(self.CalibCurves):

                # Perfectly straightforward, no evgen yields were found, the model is completely broken
                raise DoNotProcessError

            else:

                # There is a known issue with some 2tau yields
                # If this is the only issue, the result I get should still be OK
                # I also found one model with missing 3L results
                onlyTau = True
                only3L = True
                for analysisSR in negativeYieldList:
                    if 'TwoTau' not in analysisSR:
                        onlyTau = False
                    if 'ThreeLepton' not in analysisSR:
                        only3L = False

                if only3L:
                    # We can't really drop the strongest search, so let's drop the model
                    raise DoNotProcessError

                if not onlyTau:
                    # A bit clumsy, but I had this code already and it does the job
                    try:
                        assert len(negativeYieldList) == len(self.CalibCurves)
                    except AssertionError:
                        print '================ Oh dear, some SRs have yields and others don\'t!'
                        print len(negativeYieldList),len(self.CalibCurves)
                        for analysisSR,graph in self.CalibCurves.items():
                            truthyield = getattr(entry, graph.branchname)
                            print '%30s: %6.2f'%(analysisSR,truthyield)
                        raise
                # If only 2tau results were affected, carry on!
                pass

        if results:

            # Find the best SR
            if self.useexpected:
                resultkey = min(resultsExp, key=results.get)
            else:
                resultkey = min(results, key=results.get)
            # FIXME: Use results[resultkey] to find if CLs < 0.05

            # What we do next depends on the CLs combination strategy
            if self.strategy == 'smallest':
                # Take only the best result
                # This is a copy constructor, as result might be truncated later
                result = CLs(results[resultkey])

            elif self.strategy == 'twosmallest':
                # Now we need to sort the whole list
                if self.useexpected:
                    sortedkeys = sorted(resultsExp, key=results.get)[:2]
                else:
                    sortedkeys = sorted(results, key=results.get)[:2]
                # Find the observed CLs from the two best results
                mylist = [results[k] for k in sortedkeys]
                result = reduce(lambda x,y: x*y, mylist, CLs(1.))

            # However we got the result, truncate it now if necessary
            if self.truncate and result.value < 1e-6:
                result.value = 1e-6

            if not result.valid:
                print 'Invalid result: %s has CLs = %6e below the min of %6e'%(resultkey,result.value,self.CalibCurves[resultkey].xmin)

        else:
            # Absolutely no sensitive SR
            resultkey = None
            result = CLs(1.)
            result.valid = False        
        
        return result,resultkey,results

    def ReadNtuple(self, outdirname, Nmodels=None):
        """Read all truth yields, record the estimated CLs values.
        Use Nmodels to reduce the number of analysed models, for testing."""

        import os
        if not os.path.exists(outdirname):
            os.makedirs(outdirname)

        yieldfile = ROOT.TFile.Open(self.__yieldfilename)

        tree = yieldfile.Get('susy')
        tree.SetBranchStatus('*', 0)
        tree.SetBranchStatus('modelName', 1)
        tree.SetBranchStatus('*ExpectedEvents*', 1)

        for analysisSR,graph in self.CalibCurves.items():
            graph.branchname = '_'.join(['EW_ExpectedEvents',analysisSR])
            graph.yieldbranch = tree.GetBranch(graph.branchname)
            graph.yieldvalue = getattr(tree, graph.branchname)
            # I can't find out how to actually use this :(

        # Some stuff for record-keeping

        # SR:count - the key SR was the best SR in count models
        SRcount = {}
        # Same thing, but only if CLs < 5% (best SR not required)
        ExclusionCount = {}

        # Plots of the CLs values for all models
        CLsplot = ROOT.TH1I('CLsplot',';CL_{s};Number of models',100,0,1)
        CLsplot.SetDirectory(0)
        LogCLsplot = ROOT.TH1I('LogCLsplot',';log(CL_{s});Number of models',120,-6,0)
        LogCLsplot.SetDirectory(0)
        
        # Plots of the CLs values for "valid" models (ie within the calibration function range)
        CLsplot_valid = ROOT.TH1I('CLsplot_valid',';CL_{s};Number of models',100,0,1)
        CLsplot_valid.SetDirectory(0)
        LogCLsplot_valid = ROOT.TH1I('LogCLsplot_valid',';log(CL_{s});Number of models',120,-6,0)
        LogCLsplot_valid.SetDirectory(0)

        # How many SRs were used? Absolute maximum of 42 :D
        NSRplot = ROOT.TH1I('NSRplot',';Number of active SRs;Number of models',43,-0.5,42.5)
        NSRplot.SetDirectory(0)
        # More refined information, in 20 bins of CLs
        NSRplots = [NSRplot.Clone('NSRplot_%i'%(i)) for i in range(20)]
        for p in NSRplots:
            p.SetDirectory(0)

        # Output text file for the STAs
        outfile = open('/'.join([outdirname,'STAresults.csv']), 'w')
        badmodelfile = open('/'.join([outdirname,'DoNotProcess.txt']), 'w')

        print '%i models found in tree'%(tree.GetEntries())
        imodel = 0 # Counter

        for entry in tree:

            modelName = entry.modelName
            if modelName % 1000 == 0:
                print 'On model %6i'%(modelName)

            if Nmodels is not None:
                if imodel >= Nmodels: break
                imodel += 1

            if Nmodels is not None:
                # Debug mode, essentially
                print '============== Model',modelName

            try:
                CLresult,bestSR,CLresults = self.__AnalyseModel(entry)
            except DoNotProcessError:
                badmodelfile.write('%i\n'%(modelName))
                continue

            outfile.write('%i,%6e\n'%(modelName,CLresult.value))

            CLsplot.Fill(CLresult.value)
            LogCLsplot.Fill(math.log10(CLresult.value))
            NSRplot.Fill(len(CLresults))
            if CLresult.value < 1.: # This would be zero by default
                NSRplots[int(CLresult.value/0.05)].Fill(len(CLresults))
            if CLresult.valid:
                CLsplot_valid.Fill(CLresult.value)
                LogCLsplot_valid.Fill(math.log10(CLresult.value))

            bestSRkey = bestSR if bestSR else ''
            try:
                SRcount[bestSRkey] += 1
            except KeyError:
                SRcount[bestSRkey] = 1

            for k,v in CLresults.items():
                if v.valid and v.value < 0.05:
                    try:
                        ExclusionCount[k] += 1
                    except KeyError:
                        ExclusionCount[k] = 1

        outfile.close()
        badmodelfile.close()
        yieldfile.Close()

        # Save the results
        outfile = ROOT.TFile.Open('/'.join([outdirname,'CLresults.root']),'RECREATE')
        CLsplot.Write()
        LogCLsplot.Write()
        CLsplot_valid.Write()
        LogCLsplot_valid.Write()
        NSRplot.Write()
        for p in NSRplots:
            p.Write()
        outfile.Close()

        from pprint import pprint
        pprint(SRcount)

        # Pickle the SR count results, to make a nice table later
        SRcountFile = open('/'.join([outdirname,'SRcount.pickle']), 'w')
        pickle.dump(SRcount,SRcountFile)
        SRcountFile.close()

        # And again for the exclusion counts
        ExclusionCountFile = open('/'.join([outdirname,'ExclusionCount.pickle']), 'w')
        pickle.dump(ExclusionCount,ExclusionCountFile)
        ExclusionCountFile.close()

    def PlotSummary(self, dirname):
        """Makes some pdf plots.
        Separated from the event loop, as that's so slow."""

        canvas = ROOT.TCanvas('can','can',800,600)
        infile = ROOT.TFile.Open('/'.join([dirname,'CLresults.root']))

        CLsplot = infile.Get('CLsplot')
        CLsplot_valid = infile.Get('CLsplot_valid')
        
        CLsplot_valid.SetFillColor(ROOT.kBlue)
        CLsplot_valid.SetLineWidth(0)
        CLsplot_valid.Draw()
        CLsplot.Draw('same')
        
        ROOT.ATLASLabel(0.3,0.85,"Internal")
        ROOT.myBoxText(0.3,0.8,0.02,ROOT.kWhite,'All models')
        ROOT.myBoxText(0.3,0.75,0.02,CLsplot_valid.GetFillColor(),'Non-extrapolated models')

        canvas.Print('/'.join([dirname,'CLsplot.pdf']))
        
        LogCLsplot = infile.Get('LogCLsplot')
        LogCLsplot_valid = infile.Get('LogCLsplot_valid')
        
        LogCLsplot_valid.SetFillColor(ROOT.kBlue)
        LogCLsplot_valid.SetLineWidth(0)
        LogCLsplot_valid.Draw()
        LogCLsplot.Draw('same')
        
        ROOT.ATLASLabel(0.3,0.85,"Internal")
        ROOT.myBoxText(0.3,0.8,0.02,ROOT.kWhite,'All models')
        ROOT.myBoxText(0.3,0.75,0.02,CLsplot_valid.GetFillColor(),'Non-extrapolated models')

        canvas.SetLogy()
        canvas.Print('/'.join([dirname,'LogCLsplot.pdf']))
        canvas.SetLogy(0)

        NSRname = '/'.join([dirname,'NSRplot.pdf'])
        NSRplot = infile.Get('NSRplot')
        NSRplot.Draw()
        canvas.Print(NSRname+'(')
        for ibin in range(20):
            NSRplot = infile.Get('NSRplot_%i'%(ibin))
            NSRplot.Draw()
            ROOT.myText(0.2,0.95,ROOT.kBlack,'Bin %i: %i%% < CLs < %i%%'%(ibin,5*ibin,5*(ibin+1)))
            canvas.Print(NSRname)
        canvas.Print(NSRname+']')

        # Add some useful printout too
        Ninvalid = CLsplot.Integral() - CLsplot_valid.Integral()
        print 'Number of invalid models :',Ninvalid
        Nexcluded = CLsplot.Integral(0,CLsplot.GetXaxis().FindBin(0.049))
        print 'Number of excluded models:',Nexcluded

    def LatexSummary(self, dirname):
        """Makes some LaTeX tables to put directly into the support note (maybe also the paper)."""

        # First grab the SR count information
        SRcountFile = open('/'.join([dirname,'SRcount.pickle']))
        SRcount = pickle.load(SRcountFile)
        SRcountFile.close()
        blah = []
        for SR in SRcount.keys():
            if 'SR' in SR:
                blah.append(SR)

        # And the same for the exclusion counts
        ExclusionCountFile = open('/'.join([dirname,'ExclusionCount.pickle']))
        ExclusionCount = pickle.load(ExclusionCountFile)
        ExclusionCountFile.close()

        # A combined table of all results
        latexfile = open('/'.join([dirname,'SRcountTable.tex']), 'w')
        latexfile.write('\\begin{tabular}{lrr}\n')
        latexfile.write('\\toprule\n')
        latexfile.write('Signal region & Number of models & Excluded models\\\\ \n')
        latexfile.write('\\midrule\n')

        def writeLine(latexname,SR):
            """Little helper function for writing one line of the table."""
            if ExclusionCount.has_key(SR):
                latexfile.write('%s & \\num{%i} & \\num{%i} \\\\ \n'%(latexname,SRcount[SR],ExclusionCount[SR]))
            else:
                latexfile.write('%s & \\num{%i} & 0 \\\\ \n'%(latexname,SRcount[SR]))

        # Now add in the SR results
        # Start with the 2L SRWW results
        mySRs = [SR for SR in SRcount.keys() if 'SR_WW' in SR]
        for SR in sorted(mySRs):
            # It's either SR_WWa, b, or c
            whichone = SR.split('_')[2][-1]
            writeLine('2$\\ell$ SR-\\Wboson{}\\Wboson{}'+whichone, SR)

        # Now on to the 2L Zjets SR
        mySRs = [SR for SR in SRcount.keys() if 'Zjets' in SR]
        for SR in sorted(mySRs):
            # There should be only one...
            writeLine('2$\\ell$ SR-\\Zboson{}jets', SR)

        # Next, the 2L mT2 SRs
        mySRs = [SR for SR in SRcount.keys() if 'SR_mT2' in SR]
        for SR in sorted(mySRs):
            # It's either SR_mT2a, b, or c
            whichone = SR.split('_')[2][-1]
            # But we don't call them a,b,c in the note...
            whichone = {'a':90, 'b':120, 'c':150}[whichone]
            writeLine('2$\\ell$ SR-$\\mttwo^{%i}$'%(whichone), SR)

        # Have a break
        latexfile.write('\\midrule\n')

        # Next, 3L SR0a
        mySRs = [SR for SR in SRcount.keys() if 'SR0a' in SR]
        for ibin in range(1,21):
            # See if we have a result for this bin
            theSRs = [SR for SR in mySRs if SR.endswith('_%i'%(ibin))]
            if len(theSRs) > 1:
                print 'WARNING in WriteLatex: found %i SRs for SR0a bin %i'%(len(theSRs),ibin)
                print theSRs
            if theSRs:
                SR = theSRs[0]
                writeLine('3$\\ell$ SR0$\\tau$a bin %i'%(ibin), SR)

        # Now the other 3L regions, if we have them
        mySRs = [SR for SR in SRcount.keys() if 'SR0b' in SR]
        for SR in sorted(mySRs):
            # There should be only one...
            writeLine('3$\\ell$ SR0$\\tau$b', SR)
        mySRs = [SR for SR in SRcount.keys() if 'SR1SS' in SR]
        for SR in sorted(mySRs):
            # There should be only one...
            writeLine('3$\\ell$ SR1$\\tau$', SR)

        # Have a break
        latexfile.write('\\midrule\n')

        # Now the 4L regions
        mySRs = [SR for SR in SRcount.keys() if 'FourLepton' in SR]
        for SR in sorted(mySRs):
            whichone = SR.split('_')[1]
            writeLine('4$\\ell$ '+whichone, SR)


        # Now the 2tau regions
        mySRs = [SR for SR in SRcount.keys() if 'TwoTau' in SR]
        # Have a break, _if_ we have any 2tau SRs
        if mySRs:
            latexfile.write('\\midrule\n')

        for SR in sorted(mySRs):
            # Let's just hard-code this
            if 'C1C1' in SR:
                latexSR = 'SR-C1C1'
            elif 'C1N2' in SR:
                latexSR = 'SR-C1N2'
            elif 'highMT2' in SR:
                latexSR = 'SR-DS-highMass'
            elif 'lowMT2' in SR:
                latexSR = 'SR-DS-lowMass'
            writeLine('2$\\tau$ '+latexSR, SR)

        # Finish the file off
        latexfile.write('\\bottomrule\n')
        latexfile.write('\\end{tabular}\n')
        latexfile.close()
        
if __name__ == '__main__':

    # Add some command line options
    import argparse
    parser = argparse.ArgumentParser(
        description="""
           Reads truth yields and uses the CLs calibration functions to produce the ATLAS likelihood.""",
        )
    parser.add_argument(
        "-a", "--all",
        action = "store_true",
        dest = "all",
        help = "Process the full event loop")
    parser.add_argument(
        "-s", "--strategy",
        dest = "strategy",
        choices = ['smallest','twosmallest'],
        default = 'smallest',
        help = "How to combine multiple CLs values")
    parser.add_argument(
        "-t", "--truncate",
        action = 'store_true',
        dest = "truncate",
        help = "Truncate CLs values below 1e-6")
    parser.add_argument(
        "-e", "--useexpected",
        action = 'store_true',
        dest = "useexpected",
        help = "Use expected CLs to determine the best results")
    parser.add_argument(
        "-n", "--nmodels",
        type = int,
        dest = "nmodels",
        help = "Only analyse N models (for testing)")
    parser.add_argument(
        "--truthlevel",
        action = "store_true",
        dest = "truthlevel",
        help = "Get yields from evgen rather than official MC")
    cmdlinearguments = parser.parse_args()

    import ROOT
    ROOT.gROOT.SetBatch(True)
    ROOT.gROOT.LoadMacro("AtlasStyle.C")
    ROOT.SetAtlasStyle()
    ROOT.gROOT.LoadMacro("AtlasUtils.C") 
    ROOT.gROOT.LoadMacro("AtlasLabels.C")

    # Let's create subdirectories so different runs don't overwrite each other
    subdirname = cmdlinearguments.strategy
    if cmdlinearguments.truncate:
        subdirname += 'Truncate'
    if cmdlinearguments.truthlevel:
        subdirname += '_privateMC'
    else:
        subdirname += '_officialMC'
    if cmdlinearguments.useexpected:
        subdirname += '_bestExpected'
    else:
        subdirname += '_bestObserved'
    outdirname = '/'.join(['results',subdirname])
    if cmdlinearguments.nmodels:
        outdirname += '_test'

    CLsdir = 'plots_privateMC' if cmdlinearguments.truthlevel else 'plots_officialMC'
    obj = Combiner('Data_Yields/SummaryNtuple_STA_evgen.root',
                   '/'.join([CLsdir,'calibration.root']))
    if cmdlinearguments.all:
        obj.strategy = cmdlinearguments.strategy
        obj.truncate = cmdlinearguments.truncate
        obj.useexpected = cmdlinearguments.useexpected
        obj.ReadNtuple(outdirname, cmdlinearguments.nmodels)
    obj.PlotSummary(outdirname)
    obj.LatexSummary(outdirname)

