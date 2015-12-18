#!/usr/bin/env python

import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.gROOT.LoadMacro("AtlasStyle.C")
ROOT.SetAtlasStyle()
ROOT.gROOT.LoadMacro("AtlasUtils.C") 

class CorrelationPlotter:

    def __init__(self, data):
        """Data should be a dictionary, with keys corresponding to "analysis_SR".
        Values of this dictionary should also be dictionaries, with keys corresponding
        to models (eg integers or strings) and values of (yield, CLs+b).
        If either yield or CLs+b is not available, the entry should not be filled!
        """

        # Cache the input data
        self.__data = data
        
        # This dictionary will eventually have the same structure as 
        # the data subdictionaries, but with TGraph elements
        self.__correlations = None

        # For plotting
        self.__canvas = None

    def CheckData(self):
        """Check data integrity, eg whether all analysis+SR combinations
        have the same list of models."""

        # Element to store the complete list of all models
        modelset = set()

        # Loop over the analysis/SR list
        # First pupose: populate the complete model set
        # Second purpose: look for incomplete data ie missing yield and/or CLs+b

        for analysisSR,results in self.__data.items():

            # First check for incomplete data and remove it
            # No protection if v has no len attribute, this should in principle never fail
            incompletemodels = [k for k,v in results.items() if len(v) == 1]
            if incompletemodels:
                print 'WARNING: incomplete data for the following models in',analysisSR
                print '\t',incompletemodels
                for m in incompletemodels: results.pop(m)

            emptymodels = [k for k,v in results.items() if len(v) == 0]
            if emptymodels:
                print 'WARNING: empty data for the following models in',analysisSR
                print '\t',emptymodels
                for m in emptymodels: results.pop(m)

            # Finally, add the models to the master list
            modelset |= set(results.keys())

        print 'Found %i models and %i SRs'%(len(modelset),len(self.__data))
        print 'SR list:\t','\n\t\t'.join(self.__data.keys())

        # Second loop, to check if any analyses have missing models
        
        for analysisSR,results in self.__data.items():

            if modelset != set(results.keys()):
                print 'WARNING: missing models for',analysisSR
                print '\t','\n\t'.join(modelset - set(results.keys()))

    def MakeCorrelations(self):
        """Makes a TGraph object for each SR
        where we have both a truth-level yield and a CLs value.
        """
        
        # Clear the correlation data
        self.__correlations = {}

        for analysisSR,results in self.__data.items():

            for model,info in results.iteritems():

                if (not info) or len(info) < 2:
                    print 'WARNING: incomplete info for %s, model %s'%(analysisSR,model)
                
                # Create the new TGraph
                try:
                    graph = self.__correlations[analysisSR]
                except KeyError:
                    graph = ROOT.TGraph()
                    graph.SetName('Corr_%s'%(analysisSR))
                    graph.SetTitle(analysisSR.replace('_',' '))
                    self.__correlations[analysisSR] = graph

                # Add the new point
                graph.SetPoint(graph.GetN(), info[0], info[1])

        self.CheckData()

    def SaveData(self, fname):
        """Saves the graphs in a TFile"""

        if self.__correlations is None:
            print 'ERROR: Cannot save graph output, as it has not been created yet!'
            return

        outfile = ROOT.TFile.Open(fname,'RECREATE')

        for analysisSR in self.__correlations.keys():
            self.__correlations[analysisSR].Write()

        outfile.Close()

    def PlotData(self, outdir):
        """Makes plots in the specified directory."""

        if self.__correlations is None:
            print 'ERROR: Cannot plos graph output, as it has not been created yet!'
            return

        import os
        if not os.path.exists(outdir):
            os.makedirs(outdir)

        self.__canvas = ROOT.TCanvas('can','can',800,800)

        for analysisSR,graph in self.__correlations.items():
            
            graph.SetMarkerSize(2)
            graph.SetMarkerStyle(ROOT.kFullCircle)
            graph.Draw('ap')
            graph.GetXaxis().SetTitle('Yield')
            graph.GetYaxis().SetTitle('CL_{s+b}')
            graph.GetYaxis().SetRangeUser(0,graph.GetYaxis().GetXmax())
            graph.GetXaxis().SetRangeUser(0,graph.GetXaxis().GetXmax())
            graph.Draw('ap')

            ROOT.myText(0.2, 0.95, ROOT.kBlack, graph.GetTitle())

            self.__canvas.Print('/'.join([outdir,analysisSR+'.pdf(']))

            # Try some variations with log scales
            self.__canvas.SetLogx()
            self.__canvas.SetLogy()
            self.__canvas.Print('/'.join([outdir,analysisSR+'.pdf']))

            self.__canvas.SetLogx(0)
            self.__canvas.SetLogy()
            self.__canvas.Print('/'.join([outdir,analysisSR+'.pdf']))

            self.__canvas.SetLogx()
            self.__canvas.SetLogy(0)
            self.__canvas.Print('/'.join([outdir,analysisSR+'.pdf)']))

            # Reset to linear scale
            self.__canvas.SetLogx(0)
            self.__canvas.SetLogy(0)

def PassArguments():

    import argparse

    parser = argparse.ArgumentParser(
        description="""
           Reads input files and makes scatter plots of CLs+b vs truth-level yield.""",
        )
    parser.add_argument(
        "-v", "--version",
        action = "version",
        version = "%(prog)s 1.0",
        help = "Print version string")
    parser.add_argument(
        "-d", "--dummy",
        action = "store_true",
        dest = "dummy",
        help = "Read dummy input (for testing)")
    parser.add_argument(
        "--dummyrandom",
        action = "store_true",
        dest = "dummyrandom",
        help = "Read random dummy input (for testing)")

    return parser.parse_args()

if __name__ == '__main__':

    cmdlinearguments = PassArguments()

    # Read the input files
    if cmdlinearguments.dummy:

        from Reader_dummy import DummyReader

        reader = DummyReader()
        data = reader.ReadFiles()

    if cmdlinearguments.dummyrandom:

        from Reader_dummy import DummyRandomReader

        reader = DummyRandomReader()
        data = reader.ReadFiles()

    else:
        
        print 'ERROR: The script only operates in dummy mode.'
        exit(1)

        pass

    plotter = CorrelationPlotter(data)
    plotter.MakeCorrelations()
    plotter.PlotData('dummyplots' if (cmdlinearguments.dummy or cmdlinearguments.dummyrandom) else 'plots')
    plotter.SaveData('results.root')

    
