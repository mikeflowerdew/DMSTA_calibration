#!/usr/bin/env python

import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.gROOT.LoadMacro("AtlasStyle.C")
ROOT.SetAtlasStyle()
ROOT.gROOT.LoadMacro("AtlasUtils.C") 

class CorrelationPlotter:

    def __init__(self, data):
        """Data should be a list of SignalRegion objects, with names corresponding to "analysis_SR".
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

        for dataobj in self.__data:

            dataobj.CheckData() # Checks and removes the duds

            # Collect the model list after cleaning
            modelset |= set(dataobj.data.keys())

        print 'Found %i models and %i SRs'%(len(modelset),len(self.__data))
        print 'SR list:\t','\n\t\t'.join([x.name for x in self.__data])
        print

        # Second loop, to check if any analyses have missing models
        
        for dataobj in self.__data:

            if modelset != set(dataobj.data.keys()):
                print 'WARNING in CorrelationPlotter: missing models for',dataobj.name
                print '\t','\n\t'.join(sorted(modelset - set(dataobj.data.keys()))),'\n'

    def MakeCorrelations(self):
        """Makes a TGraph object for each SR
        where we have both a truth-level yield and a CLs value.
        """
        
        self.CheckData()

        # Clear the correlation data
        self.__correlations = {}

        for dataobj in self.__data:

            for model,info in dataobj.data.iteritems():

                # Create the new TGraph
                try:
                    graph = self.__correlations[dataobj.name]
                except KeyError:
                    graph = ROOT.TGraph()
                    graph.SetName('Corr_%s'%(dataobj.name))
                    graph.SetTitle(dataobj.name.replace('_',' '))
                    self.__correlations[dataobj.name] = graph

                # Add the new point
                graph.SetPoint(graph.GetN(), info['yield'], info[dataobj.InfoList()[-1]])

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
            graph.GetXaxis().SetLimits(0,graph.GetXaxis().GetXmax())
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

    def FitData(self):
        """Function for fitting the CL calibration data."""

        # Things to be defined:
        # * How to know what function to use (string in Fit? more complex function).
        #   Maybe have an input from the Reader class?
        # * How to perform the fit, including error-handling.
        # * How to record the fit results. Best store the complete result, for flexibility.
        
        pass
            
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
    parser.add_argument(
        "--fourleppaper",
        action = "store_true",
        dest = "fourleppaper",
        help = "Read input from 4L signature paper (for testing)")

    return parser.parse_args()

if __name__ == '__main__':

    cmdlinearguments = PassArguments()

    plotdir = 'plots'
    
    # Read the input files
    if cmdlinearguments.dummy:

        from Reader_dummy import DummyReader

        reader = DummyReader()
        data = reader.ReadFiles()
        # Example to corrupt part of the data
        # data[0].data['model1']['CLsb'] = None
        plotdir = 'dummyplots'
        
    elif cmdlinearguments.dummyrandom:

        from Reader_dummy import DummyRandomReader

        reader = DummyRandomReader()
        data = reader.ReadFiles()
        plotdir = 'dummyplots'

    elif cmdlinearguments.fourleppaper:

        from Reader_FourLepPaper import FourLepPaperReader

        reader = FourLepPaperReader()
        data = reader.ReadFiles()
        plotdir = 'fourleppaperplots'
        
    else:
        
        print 'ERROR: The script only operates in dummy mode.'
        exit(1)

        pass

    plotter = CorrelationPlotter(data)
    plotter.MakeCorrelations()
    plotter.PlotData(plotdir)
    plotter.SaveData('/'.join([plotdir,'results.root']))

    
