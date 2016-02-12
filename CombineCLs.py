#!/usr/bin/env python

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
            self.value = value
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

class Combiner:

    def __init__(self, yieldfilename, calibfilename):
        """Inputs are the ROOT files with the truth-level ntuple
        and the CL/yield calibration."""

        self.__yieldfilename = yieldfilename

        self.ReadCalibrations(calibfilename)

        # Some other configurable options
        self.strategy = 'smallest'
        self.truncate = False

    def ReadCalibrations(self, calibfilename):
        """Reads all TF1 objects and stores them."""

        self.CalibCurves = {}

        calibfile = ROOT.TFile.Open(calibfilename)

        for keyname in calibfile.GetListOfKeys():

            # Let's just make this easier
            keyname = keyname.GetName()
            
            thing = calibfile.Get(keyname)

            if not thing.InheritsFrom('TF1'):
                continue

            # Retrieve the x-axis minimum, extend the range back down to zero
            thing.xmin = thing.GetXmin()
            thing.SetRange(0,thing.GetXmax())
            
            # The graph names come with the CL type
            # separated from the analysis/SR by an underscore
            analysisSR = '_'.join(keyname.split('_')[:-1])
            
            self.CalibCurves[analysisSR] = thing

        calibfile.Close()

        return

    def __AnalyseModel(self, entry):
        """Analyse a single entry in the ntuple."""

        results = {}

        for analysisSR,graph in self.CalibCurves.items():

            # slow, slow, slow, but I guess OK for now
            truthyield = getattr(entry, graph.branchname)
            # trutherror = getattr(entry, '_'.join(['EW_ExpectedError',analysisSR]))

            number = CLs(graph.GetX(truthyield))

            if number.value >= 0.999*graph.GetXmax():
                # Too high
                continue

            results[analysisSR] = number
            
            # Compare the CLs to our self-imposed minimum
            if number.value < graph.xmin:
                # This message prints out A LOT
                # print 'WARNING in CombineCLs: %s has CLs = %f below the min of %s'%(analysisSR,CLs,graph.xmin)
                
                number.valid = False
                number.ratio = number.value/graph.xmin

        if results:
            resultkey = min(results, key=results.get) # keep a record of the best SR no matter what
            # FIXME: Use results[resultkey] to find if CLs < 0.05

            # What we do next depends on the CLs combination strategy
            if self.strategy == 'smallest':
                # Copy the smallest result, in case we truncate it later
                result = CLs(results[resultkey])
            elif self.strategy == 'twosmallest':
                sortedkeys = sorted(results, key=results.get)[:2]
                mylist = [results[k] for k in sortedkeys]
                result = reduce(lambda x,y: x*y, mylist, CLs(1.))
                if len(mylist) > 1:
                    assert(result.value == mylist[0].value*mylist[1].value)

            if self.truncate and result.value < 1e-6:
                result.value = 1e-6

            if not result.valid:
                print 'Invalid result: %s has CLs = %6e below the min of %6e'%(resultkey,result.value,self.CalibCurves[resultkey].xmin)

        else:
            # Absolutely no sensitive SR
            resultkey = None
            result = CLs(1.)
            result.valid = False        
        
        return result,resultkey,len(results)

    def ReadNtuple(self, outdirname):
        """Read all truth yields, record the estimated CLs values."""

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
        SRcount = {}
        
        CLsplot = ROOT.TH1I('CLsplot',';CL_{s};Number of models',100,0,1)
        CLsplot.SetDirectory(0)
        LogCLsplot = ROOT.TH1I('LogCLsplot',';log(CL_{s});Number of models',120,-6,0)
        LogCLsplot.SetDirectory(0)
        
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

        import math

        print 'Looping over %i events'%(tree.GetEntries())

        for entry in tree:

            modelName = entry.modelName
            if modelName % 1000 == 0:
                print 'On model %6i'%(modelName)

            # FIXME: Just for testing
            # if modelName > 3e4: break
                
            CLresult,SR,NSRs = self.__AnalyseModel(entry)

            outfile.write('%i,%6e\n'%(modelName,CLresult.value))
            CLsplot.Fill(CLresult.value)
            LogCLsplot.Fill(math.log10(CLresult.value))
            NSRplot.Fill(NSRs)
            if CLresult.value < 1.: # This would be zero by default
                NSRplots[int(CLresult.value/0.05)].Fill(NSRs)
            if CLresult.valid:
                CLsplot_valid.Fill(CLresult.value)
                LogCLsplot_valid.Fill(math.log10(CLresult.value))
                
            try:
                SRcount[SR] += 1
            except KeyError:
                SRcount[SR] = 1

        outfile.close()
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
    cmdlinearguments = parser.parse_args()

    import ROOT
    ROOT.gROOT.SetBatch(True)
    ROOT.gROOT.LoadMacro("AtlasStyle.C")
    ROOT.SetAtlasStyle()
    ROOT.gROOT.LoadMacro("AtlasUtils.C") 
    ROOT.gROOT.LoadMacro("AtlasLabels.C") 

    obj = Combiner('Data_Yields/SummaryNtuple_STA_evgen.root',
                   'plots/calibration.root')
    if cmdlinearguments.all:
        obj.strategy = cmdlinearguments.strategy
        obj.truncate = cmdlinearguments.truncate
        obj.ReadNtuple('results')
    obj.PlotSummary('results')
