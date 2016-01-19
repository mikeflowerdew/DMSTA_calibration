#!/usr/bin/env python

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

        print
        print 'Found %i models and %i SRs'%(len(modelset),len(self.__data))
        print 'SR list:\t','\n\t\t'.join([x.name for x in self.__data])
        print

        # Second loop, to check if any analyses have missing models
        
        for dataobj in self.__data:

            if modelset != set(dataobj.data.keys()):
                print 'WARNING in CorrelationPlotter: missing %i/%i models for %s'%(len(modelset) - len(dataobj.data.keys()),len(modelset),dataobj.name)
                print '\t','\n\t'.join(map(str, sorted(modelset - set(dataobj.data.keys())))),'\n'

    def MakeCorrelations(self):
        """Makes a TGraph object for each SR
        where we have both a truth-level yield and a CLs value.
        """
        
        self.CheckData()

        # Clear the correlation data
        self.__correlations = {}

        for dataobj in self.__data:

            # Additional loop over the different CL values
            for CLtype in dataobj.InfoList():

                # Create the new TGraph
                graphkey = '_'.join([dataobj.name,CLtype])
                try:
                    graph = self.__correlations[graphkey]
                except KeyError:
                    graph = ROOT.TGraphErrors()
                    graph.SetName('Corr_%s'%(graphkey))
                    graph.SetTitle(dataobj.name.replace('_',' '))
                    
                    # Little hack to set the y-axis title correctly
                    # Using graph.GetYaxis().SetTitle(...) now is pointless,
                    # because the underlying histogram axes have not yet been made.
                    # So I'll augment the python object to store the information for later.
                    try:
                        graph.ytitle = dataobj.CLnames[CLtype]
                    except KeyError:
                        print 'WARNING in CorrelationPlotter: No CLname info provided for %s in %s'%(CLtype,dataobj.name)
                        graph.ytitle = 'CL'
                    self.__correlations[graphkey] = graph

                # Fill the graph with data
                for model,info in dataobj.data.iteritems():

                    # Add the new point
                    if info[CLtype] is not None:
                        pointNumber = graph.GetN()
                        graph.SetPoint(pointNumber, info['yield'], info[CLtype])

                        # Check to see if we have an error on the yield
                        try:
                            graph.SetPointError(pointNumber, info['yield'].error, 0)
                        except AttributeError:
                            # Absolutely OK, we just don't have errors
                            pass

                # Finally, attempt to fit the graph
                if graph.GetN():
                    self.FitGraph(graph, dataobj.fitfunctions[CLtype])

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
            try:
                graph.GetYaxis().SetTitle(graph.ytitle) # Using the augmentation provided in self.MakeCorrelations()
            except AttributeError:
                # Should not happen, this is just in case
                print 'WARNING in CorrelationPlotter: python-level augmentation of %s graph did not work'%(graph.GetName())
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

    def FitGraph(self, graph, fitfunc):
        """Function for fitting the CL calibration data.
        If called before the graph is plotted and/or saved, the results are included in those steps."""

        # Things to be defined:
        # * How to know what function to use (string in Fit? more complex function).
        #   Maybe have an input from the Reader class?
        # * How to perform the fit, including error-handling.
        # * How to record the fit results. Best store the complete result, for flexibility.

        # If no fitting function is supplied, just bail
        if fitfunc is None: return

        # Options to try: (see https://root.cern.ch/doc/master/classTGraph.html#aa978c8ee0162e661eae795f6f3a35589)
        # Q: Quiet mode (if too many SRs)
        # E: Better error estimate
        # M: Improve fit results
        # S: Returns full fit result
        fitresult = graph.Fit(fitfunc, "S")

        # A nonzero fit status indicates an error
        if fitresult.Status():
            print 'ERROR: Error code %i in fit for %s'%(fitresult.Status(),graph.GetName())
            # What to do? Remove the function?

        # Example extraction of results, see link above.
        # chi2 = fitresult.Chi2()
        # parameters = [fitresult.Value(i) for i in range(fitresult.NPar())]
        
        return fitresult # Dunno if I need this or not
            
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

    import ROOT
    ROOT.gROOT.SetBatch(True)
    ROOT.gROOT.LoadMacro("AtlasStyle.C")
    ROOT.SetAtlasStyle()
    ROOT.gROOT.LoadMacro("AtlasUtils.C") 

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
        
        # Default operation: do the real anaylsis
        from Reader_DMSTA import DMSTAReader

        reader = DMSTAReader()
        data = reader.ReadFiles()
        plotdir = 'plots'

    plotter = CorrelationPlotter(data)
    plotter.MakeCorrelations()
    plotter.PlotData(plotdir)
    plotter.SaveData('/'.join([plotdir,'results.root']))

    
