#!/usr/bin/env python

class CLs:
    """Small data class"""

    def __init__(self, value):
        self.value = value
        self.valid = True
        self.ratio = 1. # ratio to minimum CLs value

class Combiner:

    def __init__(self, yieldfilename, calibfilename):
        """Inputs are the ROOT files with the truth-level ntuple
        and the CL/yield calibration."""

        self.__yieldfilename = yieldfilename

        self.ReadCalibrations(calibfilename)

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
            resultkey = min(results, key=results.get)
            result = results[resultkey]

            if not result.valid:
                print 'Invalid result: %s has CLs = %6e below the min of %6e'%(resultkey,result.value,self.CalibCurves[resultkey].xmin)

        else:
            # Absolutely no sensitive SR
            resultkey = None
            result = CLs(1.)
            result.valid = False        
        
        return result,resultkey

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
                
            CLresult,SR = self.__AnalyseModel(entry)

            outfile.write('%i,%6e\n'%(modelName,CLresult.value))
            CLsplot.Fill(CLresult.value)
            LogCLsplot.Fill(math.log10(CLresult.value))
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

        # Add some useful printout too
        Ninvalid = CLsplot.Integral() - CLsplot_valid.Integral()
        print 'Number of invalid models :',Ninvalid
        Nexcluded = CLsplot.Integral(0,CLsplot.GetXaxis().FindBin(0.049))
        print 'Number of excluded models:',Nexcluded
        
if __name__ == '__main__':

    import ROOT
    ROOT.gROOT.SetBatch(True)
    ROOT.gROOT.LoadMacro("AtlasStyle.C")
    ROOT.SetAtlasStyle()
    ROOT.gROOT.LoadMacro("AtlasUtils.C") 
    ROOT.gROOT.LoadMacro("AtlasLabels.C") 

    obj = Combiner('Data_Yields/SummaryNtuple_STA_evgen.root',
                   'plots/calibration.root')
    # obj.ReadNtuple('results')
    obj.PlotSummary('results')
