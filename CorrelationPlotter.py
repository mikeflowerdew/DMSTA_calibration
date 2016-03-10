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

        # Fit result cache, for monitoring
        self.__fitresults = None # Dict of name:TFitResultPtr

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
        self.__fitresults = {}

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
                    
                    # Little hack to set the x-axis title correctly
                    # Using graph.GetXaxis().SetTitle(...) now is pointless,
                    # because the underlying histogram axes have not yet been made.
                    # So I'll augment the python object to store the information for later.
                    try:
                        graph.xtitle = dataobj.CLnames[CLtype]
                    except KeyError:
                        print 'WARNING in CorrelationPlotter: No CLname info provided for %s in %s'%(CLtype,dataobj.name)
                        graph.xtitle = 'CL'
                    self.__correlations[graphkey] = graph

                # Fill the graph with data
                for model,info in dataobj.data.iteritems():

                    # Add the new point
                    if info[CLtype] is not None and info['yield']:
                        pointNumber = graph.GetN()
                        graph.SetPoint(pointNumber, info[CLtype], info['yield'])

                        # Check to see if we have an error on the yield
                        try:
                            graph.SetPointError(pointNumber, 0, info['yield'].error)
                        except AttributeError:
                            # Absolutely OK, we just don't have errors
                            pass

                # Finally, attempt to fit the graph
                if graph.GetN():
                    # Give a warning if this was already fitted (shouldn't happen?)
                    if self.__fitresults.has_key(graphkey):
                        print 'WARNING: Graph %s has already been fitted'%(graphkey)
                    # Overwrite previous fit result, if any
                    self.__fitresults[graphkey] = self.FitGraph(graph, dataobj.fitfunctions[CLtype])

                    # Cache for later if this is a good fit or not
                    graph.goodfit = (not self.__fitresults[graphkey].Status()) and dataobj.GoodFit(graph)
                    
    def SaveData(self, dirname):
        """Saves the graphs in a TFile called results.root,
        and a separate summary of the good fit results in calibration.root"""

        if self.__correlations is None:
            print 'ERROR: Cannot save graph output, as it has not been created yet!'
            return

        outfile = ROOT.TFile.Open('/'.join([dirname,'results.root']),'RECREATE')

        for analysisSR in sorted(self.__correlations.keys()):
            self.__correlations[analysisSR].Write()

        outfile.Close()

        outfile = ROOT.TFile.Open('/'.join([dirname,'calibration.root']),'RECREATE')

        for analysisSR in sorted(self.__correlations.keys()):

            graph = self.__correlations[analysisSR]

            # Use the result we cached in MakeCorrelations to decide if we store this one
            if not graph.goodfit:
                continue
            
            funclist = graph.GetListOfFunctions()
            if len(funclist) != 1:
                print 'WARNING in SaveData: %i fit functions found for %s'%(len(funclist),analysiSR)
            if not funclist:
                continue

            # Regardless, just write out one function (should be good enough)
            func = funclist[0]
            func.SetName(analysisSR)
            
            # Set the function minimum to the first observed point
            xmin = min([graph.GetX()[i] for i in range(graph.GetN())])
            func.SetRange(xmin,func.GetXmax())
            
            func.Write()

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
            graph.GetYaxis().SetTitle('Yield')
            try:
                graph.GetXaxis().SetTitle(graph.xtitle) # Using the augmentation provided in self.MakeCorrelations()
            except AttributeError:
                # Should not happen, this is just in case
                print 'WARNING in CorrelationPlotter: python-level augmentation of %s graph did not work'%(graph.GetName())

            graph.GetYaxis().SetRangeUser(0,graph.GetYaxis().GetXmax())
            # Check if the x-axis goes negative (ie log(CLs) vs CLs)
            if graph.GetXaxis().GetXmin() >= 0:
                # Linear CL scale
                graph.GetXaxis().SetLimits(0,graph.GetXaxis().GetXmax())
                doLogX = True
            else:
                # Log(CL) scale
                assert(graph.GetXaxis().GetXmax() <= 0)
                graph.GetXaxis().SetLimits(graph.GetXaxis().GetXmin(),0)
                doLogX = False

            # Draw again (this is the pretty one!)
            graph.Draw('ap')

            ROOT.myText(0.2, 0.95, ROOT.kBlack, graph.GetTitle())
            ROOT.ATLASLabel(0.6,0.9,"Internal")

            self.__canvas.Print('/'.join([outdir,analysisSR+'.pdf(']))

            # Try some variations with log scales
            if doLogX:
                self.__canvas.SetLogx()
                self.__canvas.SetLogy()
                self.__canvas.Print('/'.join([outdir,analysisSR+'.pdf']))

            self.__canvas.SetLogx(0)
            self.__canvas.SetLogy()
            self.__canvas.Print('/'.join([outdir,analysisSR+'.pdf']))

            if doLogX:
                self.__canvas.SetLogx()
                self.__canvas.SetLogy(0)
                self.__canvas.Print('/'.join([outdir,analysisSR+'.pdf']))

            # Close the file
            self.__canvas.Print('/'.join([outdir,analysisSR+'.pdf]']))

            # Reset to linear scale
            self.__canvas.SetLogx(0)
            self.__canvas.SetLogy(0)

        # Now plot some summary fit results
        chi2plot = ROOT.TH1D('chi2plot',';;#chi^{2}/Ndof',
                             len(self.__fitresults),-0.5,len(self.__fitresults)-0.5)
        probplot = chi2plot.Clone('probplot')
        probplot.GetYaxis().SetTitle('Fit probability')
        paramplots = [chi2plot.Clone('param%iplot'%(i)) for i in range(self.__fitresults.values()[0].NPar())]
        for iplot in range(len(paramplots)):
            paramplots[iplot].GetYaxis().SetTitle('Parameter %i'%(iplot))
        
        for ibin,analysisSR in enumerate(sorted(self.__fitresults.keys())):

            chi2plot.GetXaxis().SetBinLabel(ibin+1, analysisSR)
            probplot.GetXaxis().SetBinLabel(ibin+1, analysisSR)
            for iplot in range(len(paramplots)):
                paramplots[iplot].GetXaxis().SetBinLabel(ibin+1, analysisSR)


            if self.__fitresults[analysisSR].Ndf():
                chi2plot.SetBinContent(ibin+1, self.__fitresults[analysisSR].Chi2()/self.__fitresults[analysisSR].Ndf())
                
            probplot.SetBinContent(ibin+1, self.__fitresults[analysisSR].Prob())

            for iplot in range(len(paramplots)):
                paramplots[iplot].SetBinContent(ibin+1, abs(self.__fitresults[analysisSR].Value(iplot)))
                paramplots[iplot].SetBinError(ibin+1, self.__fitresults[analysisSR].Error(iplot))

        # Make sure the labels can be read, and adjust the canvas margin to fit
        chi2plot.GetXaxis().LabelsOption('v')
        chi2plot.GetXaxis().SetLabelSize(0.03)
        
        probplot.GetXaxis().LabelsOption('v')
        probplot.GetXaxis().SetLabelSize(0.03)
        
        for iplot in range(len(paramplots)):
            paramplots[iplot].GetXaxis().LabelsOption('v')
            paramplots[iplot].GetXaxis().SetLabelSize(0.03)

        oldmargin = self.__canvas.GetBottomMargin()
        self.__canvas.SetBottomMargin(0.3)

        chi2plot.SetMinimum(0)
        chi2plot.Draw()
        ROOT.ATLASLabel(0.5,0.85,"Internal")
        self.__canvas.Print('/'.join([outdir,'chi2.pdf']))

        probplot.SetMinimum(0)
        probplot.Draw()
        ROOT.ATLASLabel(0.5,0.85,"Internal")
        self.__canvas.Print('/'.join([outdir,'prob.pdf']))

        for iplot in range(len(paramplots)):
            paramplots[iplot].Draw()
            ROOT.ATLASLabel(0.2,0.95,"Internal")
            self.__canvas.SetLogy()
            self.__canvas.Print('/'.join([outdir,'param%i.pdf'%(iplot)]))

        # Reset the canvas
        self.__canvas.SetBottomMargin(oldmargin)

        print
        print '======= Final summary printout'

        keylength = max([len(x) for x in self.__fitresults.keys()])
        keyfmtstring = '%%%is'%(keylength) # Yay, formatting the format string!

        for key,fitresult in sorted(self.__fitresults.items()):

            key = keyfmtstring%(key)
            if fitresult.NPar() == 0:
                print '%s: No free parameters'%(key)
            elif fitresult.NPar() == 1:
                print '%s: %.4f +- %.2f %%'%(key,fitresult.Value(0),100.*fitresult.Error(0)/fitresult.Value(0))
            else:
                print '%s:'%(key)
                for i in range(fitresult.NPar()):
                    print '  Par %i: %.4f +- %.2f %%'%(i,fitresult.Value(i),100.*fitresult.Error(i)/fitresult.Value(i))

    def FitGraph(self, graph, fitfunc):
        """Function for fitting the CL calibration data.
        If called before the graph is plotted and/or saved, the results are included in those steps."""

        # If no fitting function is supplied, just bail
        if fitfunc is None: return

        # Options to try: (see https://root.cern.ch/doc/master/classTGraph.html#aa978c8ee0162e661eae795f6f3a35589)
        # Q: Quiet mode (if too many SRs)
        # E: Better error estimate
        # M: Improve fit results
        # S: Returns full fit result
        print
        print 'INFO: Fitting',graph.GetName()
        fitresult = graph.Fit(fitfunc, "SRB")

        # A nonzero fit status indicates an error
        if fitresult.Status():
            print 'ERROR: Error code %i in fit for %s'%(fitresult.Status(),graph.GetName())
            # What to do? Remove the function?

        # Example extraction of results, see link above.
        # chi2 = fitresult.Chi2()
        # parameters = [fitresult.Value(i) for i in range(fitresult.NPar())]
        # errors = [fitresult.Error(i) for i in range(fitresult.NPar())]
        
        return fitresult
            
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
    parser.add_argument(
        "--productcheck",
        action = "store_true",
        dest = "productcheck",
        help = "Run a consistency check on the 4L data")

    return parser.parse_args()

if __name__ == '__main__':

    cmdlinearguments = PassArguments()

    import ROOT
    ROOT.gROOT.SetBatch(True)
    ROOT.gROOT.LoadMacro("AtlasStyle.C")
    ROOT.SetAtlasStyle()
    ROOT.gROOT.LoadMacro("AtlasUtils.C") 
    ROOT.gROOT.LoadMacro("AtlasLabels.C") 

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
        
    elif cmdlinearguments.productcheck:

        # Special run mode: a specific study
        from ProductCheck import ProductCheck
        checker = ProductCheck()
        checker.RunAnalysis('4L')
        checker.RunAnalysis('3L')

    else:
        
        # Default operation: do the real anaylsis
        from Reader_DMSTA import DMSTAReader

        reader = DMSTAReader()
        data = reader.ReadFiles()
        plotdir = 'plots'

    if 'data' in dir():
        plotter = CorrelationPlotter(data)
        plotter.MakeCorrelations()
        plotter.PlotData(plotdir)
        plotter.SaveData(plotdir)

