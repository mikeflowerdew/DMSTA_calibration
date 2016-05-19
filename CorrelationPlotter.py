#!/usr/bin/env python

# ########################################################
# Main helper class for calibration
# ########################################################

class CorrelationPlotter:
    """A class to store and plot the correlation between two variables (eg signal yield and CLs) for an arbitrary number of SRs.

    The data format is ultimately defined by the SignalRegion class (in DataObject.py),
    which is read in by one of the Reader classes (Reader_DMSTA.py by now being the only relevant one).
    More or less everything else (eg where output plots are written) is configurable.
    """

    def __init__(self, data):
        """Initialise the object, storing a reference to the data.
        data should be a list of SignalRegion objects, with names corresponding to "analysis_SR".
        """

        # Cache the input data
        self.__data = data
        
        # This will be a dictionary containing the TGraph objects used in the calibration
        # The keys will be based on the analysis name, SR name and the type of thing that is plotted (eg log(CLs))
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
        # Second purpose: look for incomplete data ie missing yield and/or CLs values

        for dataobj in self.__data:

            dataobj.CheckData() # Checks and removes the duds

            # Collect the model list after cleaning
            modelset |= set(dataobj.data.keys())

        print
        print 'Found %i models and %i SRs'%(len(modelset),len(self.__data))
        print 'SR list:\t','\n\t\t'.join([x.name for x in self.__data])
        print

        # Second loop, to check if any analyses have missing models
        # Just for information, no action is taken
        
        for dataobj in self.__data:

            if modelset != set(dataobj.data.keys()):
                print 'WARNING in CorrelationPlotter: missing %i/%i models for %s'%(len(modelset) - len(dataobj.data.keys()),len(modelset),dataobj.name)
                print '\t','\n\t'.join(map(str, sorted(modelset - set(dataobj.data.keys())))),'\n'

    def MakeCorrelations(self):
        """Makes a TGraph object for each SR where we have both a truth-level yield and a CLs value.
        """
        
        # First check and clean the data
        self.CheckData()

        # Clear the correlation data
        self.__correlations = {}
        self.__fitresults = {}

        # Loop over each SR
        # Recall that dataobj is a SignalRegion object
        for dataobj in self.__data:

            # Loop over the different CL values (one plot per CL type)
            for CLtype in dataobj.InfoList():

                # Work out what to call this graph
                graphkey = '_'.join( [dataobj.name, CLtype] )

                # See if it already exists
                try:
                    graph = self.__correlations[graphkey]
                except KeyError:
                    # Graph does not exist, we need to make it
                    graph = ROOT.TGraphErrors()
                    graph.SetName('Corr_%s'%(graphkey))
                    graph.SetTitle(dataobj.name.replace('_',' ')) # Helps when plotting
                    
                    # Little hack to set the x-axis title correctly
                    # Using graph.GetXaxis().SetTitle(...) now is pointless,
                    # because the underlying histogram axes have not yet been made.
                    # So I'll augment the python object to store the information for later.
                    try:
                        graph.xtitle = dataobj.CLnames[CLtype]
                    except KeyError:
                        print 'WARNING in CorrelationPlotter: No CLname info provided for %s in %s'%(CLtype,dataobj.name)
                        graph.xtitle = 'CL'

                    # Store the graph for future use
                    self.__correlations[graphkey] = graph

                # Loop over each model to extract yield and CL values
                for model,info in dataobj.data.iteritems():

                    # Check if we have the necessary x- and y-axis values
                    if info[CLtype] is not None and info['yield']:

                        # Add a new point to the TGraph
                        pointNumber = graph.GetN()
                        graph.SetPoint(pointNumber, info[CLtype], info['yield'])

                        # Check to see if we have an error on the yield
                        try:
                            # The next line only works if info['yield'] is a valueWithError object
                            graph.SetPointError(pointNumber, 0, info['yield'].error)
                        except AttributeError:
                            # Absolutely OK, we just don't have errors on the yield
                            pass

                # Finally, attempt to fit the graph for this SR + CL type combination
                # Only try this if it's non-empty
                if graph.GetN():

                    # Give a warning if this was already fitted (shouldn't happen?)
                    if self.__fitresults.has_key(graphkey):
                        print 'WARNING: Graph %s has already been fitted'%(graphkey)

                    # Overwrite previous fit result, if any
                    # The fit function is defined by the SignalRegion object itself
                    self.__fitresults[graphkey] = self.FitGraph(graph, dataobj.fitfunctions[CLtype])

                    # The fit is good if
                    # a) the fit result exists
                    # b) the fit status is zero (nonzero implies an error)
                    # c) the SignalRegion object's GoodFit function is satisfied
                    graph.goodfit = self.__fitresults[graphkey] and (not self.__fitresults[graphkey].Status()) and dataobj.GoodFit(graph)

                    # Compute and store the error on the fit
                    graph.fiterrorgraph = dataobj.FitErrorGraph(graph)

                # End of loop over different CL types
                pass

            # End of loop over models
            pass

    def SaveData(self, dirname):
        """Save graphs in self.__correlations in a TFile called results.root,
        and a separate summary of the good fit results in calibration.root.
        The latter file only records SRs with a good fit, and can therefore be used
        safely by downstream code, without further checks.
        """

        if self.__correlations is None:
            print 'ERROR: Cannot save graph output, as it has not been created yet!'
            return

        # First write the correlation graphs (scatter plots)
        # Note that any fitted TF1s are still associated with them,
        # and therefore also saved.
        outfile = ROOT.TFile.Open('/'.join([dirname,'results.root']),'RECREATE')

        for analysisSR in sorted(self.__correlations.keys()):
            # Save all graphs, for reference
            # These elements are just TGraph objects
            self.__correlations[analysisSR].Write()

        outfile.Close()

        # Now write the fitted functions to a separate file, for easier downstream access
        outfile = ROOT.TFile.Open('/'.join([dirname,'calibration.root']),'RECREATE')

        # Loop again over the correlation dictionary
        for analysisSR in sorted(self.__correlations.keys()):

            # Get the graph
            graph = self.__correlations[analysisSR]

            # Use the result we cached in MakeCorrelations to decide if we want to keep it
            if not graph.goodfit:
                print 'INFO in SaveData: %s rejected'%(analysisSR)
                continue

            # Now we extract the fitted TF1 associated with the graph
            funclist = graph.GetListOfFunctions()

            # There _should_ be only one function
            if len(funclist) != 1:
                print 'WARNING in SaveData: %i fit functions found for %s'%(len(funclist),analysiSR)

            # If we have no function, there's nothing to store...
            if not funclist:
                continue

            # At this point, there _might_ be more than one function (though there shouldn't be)
            # Regardless, just write out the first (should be good enough)
            func = funclist[0].Clone()
            func.SetName(analysisSR)
            
            # Set the function minimum to the first observed point
            # This is needed by downstream code, and is only accessible via the original TGraph scatter plot
            xmin = min([graph.GetX()[i] for i in range(graph.GetN())])

            # For the log-scale version, I have to set the maximum to zero now,
            # or else it's not saved

            # Use a trick to tell if this is a linear or log-scale CL value
            if xmin >=0:
                # Linear
                func.SetRange(xmin,func.GetXmax())
            else:
                # Logarithmic
                func.SetRange(max([xmin,-6]),0)
            
            func.Write()

        outfile.Close()

    def PlotData(self, outdir):
        """Makes scatter plots with the fitted functions in the specified directory."""

        if self.__correlations is None:
            print 'ERROR: Cannot plot graph output, as it has not been created yet!'
            return

        # Create the output directory if it does not already exist
        import os
        if not os.path.exists(outdir):
            os.makedirs(outdir)

        # Make a canvas (this could be done more elegantly)
        self.__canvas = ROOT.TCanvas('can','can',800,800)

        # ###########################################
        # Per-SR scatter plots

        # Loop over the correlation graphs
        for analysisSR,graph in self.__correlations.items():

            graph.SetMarkerSize(1)
            graph.SetMarkerStyle(ROOT.kFullCircle)

            # Let's make the best fit line red
            funclist = graph.GetListOfFunctions()
            for f in funclist:
                f.SetLineColor(ROOT.kRed)

            # First draw, needed in order to access the axis labels etc
            graph.Draw('ap')
            graph.GetYaxis().SetTitle('Yield')
            try:
                graph.GetXaxis().SetTitle(graph.xtitle) # Using the augmentation provided in self.MakeCorrelations()
            except AttributeError:
                # Should not happen, this is just in case
                print 'WARNING in CorrelationPlotter: python-level augmentation of %s graph did not work'%(graph.GetName())

            # Set the minimum of the y-axis to zero
            graph.GetYaxis().SetRangeUser(0,graph.GetYaxis().GetXmax())

            # Check if the x-axis goes negative (ie log(CLs) vs CLs)
            if graph.GetXaxis().GetXmin() >= 0:
                # Linear CL scale

                # Set x-axis minimum to zero
                graph.GetXaxis().SetLimits(0,graph.GetXaxis().GetXmax())

                # If the x-axis is linear, then we want to also plot a log(x) version of the plot
                doLogX = True
            else:
                # Log(CL) scale
                # Sanity check
                assert(graph.GetXaxis().GetXmax() <= 0)

                # Zoom out to a consistent range if needed
                # ie always plot down to -6, or the graph minimum if this is smaller
                xmin = min([graph.GetXaxis().GetXmin(), -6])
                graph.GetXaxis().SetLimits(xmin,0)

                # If the x-axis is logarithmic, there is no point trying a log(log(x)) plot
                doLogX = False

            # Draw again (this is the pretty one!)
            graph.Draw('ap')

            # Draw the fit function error band next, if it exists
            if graph.fiterrorgraph:
                graph.fiterrorgraph.SetMarkerSize(0)
                graph.fiterrorgraph.SetFillColorAlpha(ROOT.kYellow, 0.35)
                graph.fiterrorgraph.Draw('same3')

            # The fit function itself should go on top
            for f in funclist:

                f.Draw('same')

                # Put the fit parameters on the plot, for convenience
                printy = 0.9 # Start position for listing the fit parameters
                for ipar in range(f.GetNpar()):
                    printy -= 0.05
                    ROOT.myText(0.6,printy, ROOT.kBlack, 'p%i: %5.2f #pm %5.2f'%(ipar,f.GetParameter(ipar),f.GetParError(ipar)))

            # Add the graph title, so you can see which SR this is
            ROOT.myText(0.2, 0.95, ROOT.kBlack, graph.GetTitle())

            # And an ATLAS label!
            ROOT.ATLASLabel(0.6,0.9,"Internal")

            # Open a multi-page pdf file
            # This adds the current canvas, ie completely "natural" x and y axes
            self.__canvas.Print('/'.join([outdir,analysisSR+'.pdf(']))

            # If the x-axis is linear, plot a log(x) vs log(y) version
            if doLogX:
                self.__canvas.SetLogx()
                self.__canvas.SetLogy()
                self.__canvas.Print('/'.join([outdir,analysisSR+'.pdf']))

            # "Natural" x-axis, log(y)
            self.__canvas.SetLogx(0)
            self.__canvas.SetLogy()
            self.__canvas.Print('/'.join([outdir,analysisSR+'.pdf']))

            if doLogX:
                # log(x) vs linear y
                self.__canvas.SetLogx()
                self.__canvas.SetLogy(0)
                self.__canvas.Print('/'.join([outdir,analysisSR+'.pdf']))

            # Close the file
            self.__canvas.Print('/'.join([outdir,analysisSR+'.pdf]']))

            # Reset to linear scale
            self.__canvas.SetLogx(0)
            self.__canvas.SetLogy(0)

            # If I don't delete the graphs now, the job ends with a seg fault
            # Strange, but true!
            graph.Delete()

            # End of loop over per-SR correlation graphs (scatter plots)
            pass

        # ###########################################
        # Summary plots

        # Fit chi^2 summary
        chi2plot = ROOT.TH1D('chi2plot',';;#chi^{2}/Ndof',
                             len(self.__fitresults),-0.5,len(self.__fitresults)-0.5)

        # Fit probability summary
        probplot = chi2plot.Clone('probplot')
        probplot.GetYaxis().SetTitle('Fit probability')

        # Plots of the fit parameter(s)
        paramplots = [chi2plot.Clone('param%iplot'%(i)) for i in range(self.__fitresults.values()[0].NPar())]
        for iplot in range(len(paramplots)):
            paramplots[iplot].GetYaxis().SetTitle('Parameter %i'%(iplot))
        
        # Loop over the fit results and fill the summary graphs
        for ibin,analysisSR in enumerate(sorted(self.__fitresults.keys())):

            # Use the analysis/SR name as a bin label
            chi2plot.GetXaxis().SetBinLabel(ibin+1, analysisSR)
            probplot.GetXaxis().SetBinLabel(ibin+1, analysisSR)
            for iplot in range(len(paramplots)):
                paramplots[iplot].GetXaxis().SetBinLabel(ibin+1, analysisSR)

            # Check if we have any data at all
            if self.__fitresults[analysisSR] is None:
                continue

            # Fill the three plots
            if self.__fitresults[analysisSR].Ndf():
                chi2plot.SetBinContent(ibin+1, self.__fitresults[analysisSR].Chi2()/self.__fitresults[analysisSR].Ndf())
                
            probplot.SetBinContent(ibin+1, self.__fitresults[analysisSR].Prob())

            for iplot in range(len(paramplots)):
                paramplots[iplot].SetBinContent(ibin+1, abs(self.__fitresults[analysisSR].Value(iplot)))
                paramplots[iplot].SetBinError(ibin+1, self.__fitresults[analysisSR].Error(iplot))

            # End of loop over fit results

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

        # Draw the chi^2 plot
        chi2plot.SetMinimum(0)
        chi2plot.Draw()
        ROOT.ATLASLabel(0.5,0.85,"Internal")
        self.__canvas.Print('/'.join([outdir,'chi2.pdf']))

        # Draw the fit probability plot
        probplot.SetMinimum(0)
        probplot.Draw()
        ROOT.ATLASLabel(0.5,0.85,"Internal")
        self.__canvas.Print('/'.join([outdir,'prob.pdf']))

        # Draw the fit parameter plots
        for iplot in range(len(paramplots)):
            paramplots[iplot].SetMaximum(2.)
            paramplots[iplot].Draw()
            ROOT.ATLASLabel(0.2,0.95,"Internal")
            self.__canvas.Print('/'.join([outdir,'param%i.pdf('%(iplot)]))
            self.__canvas.SetLogy()
            self.__canvas.Print('/'.join([outdir,'param%i.pdf)'%(iplot)]))

        # Reset the canvas in case the method is extended (or the canvas reused)
        self.__canvas.SetBottomMargin(oldmargin)

        # ###########################################
        # Screen printout

        print
        print '======= Final summary printout'

        # Work out the longest analysis/SR name, to help formatting the output
        keylength = max([len(x) for x in self.__fitresults.keys()])
        keyfmtstring = '%%%is'%(keylength) # Yay, formatting the format string!

        for key,fitresult in sorted(self.__fitresults.items()):

            key = keyfmtstring%(key)
            if fitresult is None:
                print '%s: No fit result'%(key)
            elif fitresult.NPar() == 0:
                print '%s: No free parameters'%(key)
            elif fitresult.NPar() == 1:
                print '%s: %.4f +- %.2f %%'%(key,fitresult.Value(0),100.*fitresult.Error(0)/fitresult.Value(0))
            else:
                print '%s:'%(key)
                for i in range(fitresult.NPar()):
                    print '  Par %i: %.4f +- %.2f %%'%(i,fitresult.Value(i),100.*fitresult.Error(i)/fitresult.Value(i))

    def FitGraph(self, graph, fitfunc):
        """Function for fitting the CL calibration data.
        If called before the graph is plotted and/or saved, the results are included in those steps.
        Returns None if the fit results do not exist at all.
        """

        # If no fitting function is supplied, just bail
        if fitfunc is None: return

        # Options to try: (see https://root.cern.ch/doc/master/classTGraph.html#aa978c8ee0162e661eae795f6f3a35589)
        # Q: Quiet mode (if too many SRs)
        # E: Better error estimate
        # M: Improve fit results
        # S: Returns full fit result
        print
        print 'INFO: Fitting',graph.GetName()

        # The next bit was all part of a desperate attempt to get
        # the range -0.5 < log(CLs) < 0.0 saved properly.
        # With the function clone a few lines down, I'm not sure
        # it's really needed any more.
        funcmin = fitfunc.GetXmin()
        funcmax = fitfunc.GetXmax()
        try:
            xmin = fitfunc.xmin
        except AttributeError:
            xmin = fitfunc.GetXmin()
        try:
            xmax = fitfunc.xmax
        except AttributeError:
            xmax = fitfunc.GetXmax()

        fitresult = graph.Fit(fitfunc, "SRB", '', xmin, xmax)
        finalfunc = graph.GetFunction(fitfunc.GetName())
        if finalfunc:

            # The only way I can find to properly store the region
            # -0.5 < log(CLs) < 0.0 is to clone the original function.
            # It really seems as if this part of the function is lost during the fit...?
            newfunc = fitfunc.Clone()
            for iparam in range(newfunc.GetNpar()):
                newfunc.SetParameter(iparam, finalfunc.GetParameter(iparam))
                newfunc.SetParError(iparam, finalfunc.GetParError(iparam))
            graph.GetListOfFunctions().Clear()
            # finalfunc.SetName(finalfunc.GetName()+'_old')
            graph.GetListOfFunctions().AddFirst(newfunc)
            assert len(graph.GetListOfFunctions()) == 1
            # finalfunc.SetRange(funcmin,funcmax)

        # Some failures (eg no data) return a null object
        if not fitresult.Get():
            print 'ERROR: No fit object returned for %s'%(graph.GetName())
            return None

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
        help = "Run a consistency check on the 3L and 4L data")
    parser.add_argument(
        "--truthlevel",
        action = "store_true",
        dest = "truthlevel",
        help = "Get yields from evgen rather than official MC")

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
        data = reader.ReadFiles(not cmdlinearguments.truthlevel)
        if cmdlinearguments.truthlevel:
            plotdir = 'plots_privateMC'
        else:
            plotdir = 'plots_officialMC'

    if 'data' in dir():
        plotter = CorrelationPlotter(data)
        plotter.MakeCorrelations()
        plotter.SaveData(plotdir)
        plotter.PlotData(plotdir)

