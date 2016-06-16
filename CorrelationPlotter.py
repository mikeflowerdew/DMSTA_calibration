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

                else:
                    # If the graph is empty, set flags to indicate a lack of fit
                    graph.goodfit = False
                    graph.fiterrorgraph = None
                    self.__fitresults[graphkey] = None

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

        # Create the output directory if it does not already exist
        import os
        if not os.path.exists(dirname):
            os.makedirs(dirname)

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

        # Make a set to keep track of which CL types we have
        CLtypes = set()
        # Also, a set for the "real" analysis/SR combinations
        SRs = set()

        # Loop over the correlation graphs
        for analysisSR,graph in self.__correlations.items():

            # Extract and record the CL type and SR name
            # This is stored at the end of the analysisSR name
            CLtype = analysisSR.split('_')[-1]
            CLtypes.add(CLtype)
            SRname = analysisSR.replace('_'+CLtype,'')
            SRs.add(SRname)

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
            isLinearCLs = graph.GetXaxis().GetXmin() >= 0
            if isLinearCLs:
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

            # Draw a guide line at CLs = 0.05
            exclusionLine = ROOT.TLine()
            exclusionLine.SetLineColor(ROOT.kGray)
            exclusionLine.SetLineWidth(4)
            exclusionLine.SetLineStyle(7) #ROOT.kDashed)
            import math
            xvalue = 0.05 if isLinearCLs else math.log10(0.05)
            ymax = graph.GetYaxis().GetXmax()
            exclusionLine.DrawLine(xvalue,0, xvalue,ymax)

            # Add some text to explain what the grey line is?
            # I can't seem to get this to look right...
            # exclusionText = ROOT.TLatex()
            # exclusionText.SetTextColor(ROOT.kGray)
            # exclusionText.SetTextAngle(90)
            # exclusionText.SetTextAlign(21) # Centre bottom adjusted
            # exclusionText.SetTextSize(0.04)
            # exclusionText.DrawLatex(xvalue, ymax*2./3, 'CLs = 0.05')

            # Draw the fit function error band next, if it exists
            if graph.fiterrorgraph:
                graph.fiterrorgraph.SetMarkerSize(0)
                graph.fiterrorgraph.SetFillColorAlpha(ROOT.kYellow, 0.35)
                graph.fiterrorgraph.Draw('same3')

            # The fit function itself should go on top
            for f in funclist:

                f.Draw('same')

                # Put the fit parameters on the plot, for convenience
                # Have one parameter as a special case
                if f.GetNpar() == 1:
                    ROOT.myText(0.58,0.85, ROOT.kBlack, '#LT#epsilon #GT = %5.2f #pm%5.2f'%(f.GetParameter(0),f.GetParError(0)))
                else:
                    printy = 0.9 # Start position for listing the fit parameters
                    for ipar in range(f.GetNpar()):
                        printy -= 0.05
                        ROOT.myText(0.6,printy, ROOT.kBlack, 'p%i: %5.2f #pm %5.2f'%(ipar,f.GetParameter(ipar),f.GetParError(ipar)))

            # Add the graph title, so you can see which SR this is
            ROOT.myText(0.2, 0.95, ROOT.kBlack, graph.GetTitle())

            # And an ATLAS label!
            ROOT.ATLASLabel(0.6,0.9,"Internal")

            # Finally, say if the fit on the plot is good or not
            if not graph.goodfit:
                ROOT.myText(0.2, 0.2, ROOT.kRed, 'Bad fit')

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

        # Let's just do a little check
        if len(self.__fitresults) != len(SRs)*len(CLtypes):
            print '========================================='
            print 'ERROR: Somehow %i SRs and %i CL types make %i combinations'%(len(SRs),len(CLtypes),len(self.__fitresults))
            print 'ERROR: The next bit of code will probably crash'
            print '========================================='

        # ###########################################
        # Summary plots

        # Make a template for all of the histograms
        plottemplate = ROOT.TH1D('template','',len(SRs),-0.5,len(SRs)-0.5)

        # Fit chi^2 summary, one for each CL type
        chi2plots = {}
        for t in CLtypes:
            plot = plottemplate.Clone('chi2plot_%s'%(t))
            plot.GetYaxis().SetTitle('#chi^{2}/Ndof')
            chi2plots[t] = plot

        # Fit probability summary, one for each CL type
        probplots = {}
        for t in CLtypes:
            plot = plottemplate.Clone('probplot_%s'%(t))
            plot.GetYaxis().SetTitle('Fit probability')
            probplots[t] = plot

        # Plots of the fit parameter(s), N for each CL type
        paramplots = {}
        for t in CLtypes:
            # In some unusual configurations, it's possible that the fitresults are not properly populated,
            # so check this now, in order to avoid a crash
            if self.__fitresults.values()[0]:
                plots = [plottemplate.Clone('param%iplot_%s'%(i,t)) for i in range(self.__fitresults.values()[0].NPar())]
                for iplot in range(len(plots)):
                    plots[iplot].GetYaxis().SetTitle('Parameter %i'%(iplot))
                paramplots[t] = plots
            else:
                paramplots[t] = []
        
        # Loop over the fit results and fill the summary graphs
        for CLtype in CLtypes:
            for ibin,analysisSR in enumerate(sorted(SRs)):

                # Reconstruct the full key for (eg) self.__fitresults
                analysisSRkey = '_'.join([analysisSR,CLtype])

                # Use the analysis/SR name as a bin label
                chi2plots[CLtype].GetXaxis().SetBinLabel(ibin+1, analysisSR)
                probplots[CLtype].GetXaxis().SetBinLabel(ibin+1, analysisSR)
                for iplot in range(len(paramplots[CLtype])):
                    paramplots[CLtype][iplot].GetXaxis().SetBinLabel(ibin+1, analysisSR)

                # Check if we have any data at all
                if self.__fitresults[analysisSRkey] is None:
                    continue

                # Fill the three plots
                if self.__fitresults[analysisSRkey].Ndf():
                    chi2plots[CLtype].SetBinContent(ibin+1, self.__fitresults[analysisSRkey].Chi2()/self.__fitresults[analysisSRkey].Ndf())
                
                probplots[CLtype].SetBinContent(ibin+1, self.__fitresults[analysisSRkey].Prob())

                for iplot in range(len(paramplots[CLtype])):
                    paramplots[CLtype][iplot].SetBinContent(ibin+1, abs(self.__fitresults[analysisSRkey].Value(iplot)))
                    paramplots[CLtype][iplot].SetBinError(ibin+1, self.__fitresults[analysisSRkey].Error(iplot))

                # End of loop over bins
            # End of loop over CL types

        # Make sure the labels can be read, and adjust the canvas margin to fit
        for plot in chi2plots.values():
            plot.GetXaxis().LabelsOption('v')
            plot.GetXaxis().SetLabelSize(0.03)

        for plot in probplots.values():
            plot.GetXaxis().LabelsOption('v')
            plot.GetXaxis().SetLabelSize(0.03)

        for plots in paramplots.values():
            for iplot in range(len(plots)):
                plots[iplot].GetXaxis().LabelsOption('v')
                plots[iplot].GetXaxis().SetLabelSize(0.03)

        oldmargin = self.__canvas.GetBottomMargin()
        self.__canvas.SetBottomMargin(0.3)

        # Draw the chi^2 plots
        for CLtype,chi2plot in chi2plots.items():
            chi2plot.SetMinimum(0)
            chi2plot.Draw()
            ROOT.ATLASLabel(0.5,0.85,"Internal")
            self.__canvas.Print('/'.join([outdir,'chi2_%s.pdf'%(CLtype)]))

        # Draw the fit probability plots
        for CLtype,probplot in probplots.items():
            probplot.SetMinimum(0)
            probplot.Draw()
            ROOT.ATLASLabel(0.5,0.85,"Internal")
            self.__canvas.Print('/'.join([outdir,'prob_%s.pdf'%(CLtype)]))

        # Draw the fit parameter plots
        for CLtype,plots in paramplots.items():
            for iplot in range(len(plots)):
                plots[iplot].SetMaximum(2.)
                plots[iplot].Draw()
                ROOT.ATLASLabel(0.2,0.95,"Internal")
                self.__canvas.Print('/'.join([outdir,'param%i_%s.pdf('%(iplot,CLtype)]))
                self.__canvas.SetLogy()
                self.__canvas.Print('/'.join([outdir,'param%i_%s.pdf)'%(iplot,CLtype)]))
                self.__canvas.SetLogy(0) # Put the scale back to linear

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
            # Even worse, the functional form is lost in a call to Clone(),
            # so reconstruct it from the original graph
            newfunc = ROOT.TF1('fitfunc', lambda x,p: fitfunc.graph.Eval(x[0])/p[0], -6, 0, 1)

            # See if we need to adjust the normalisation
            try:
                scalefact = fitfunc.SystematicFactor(graph, fitfunc)
            except AttributeError:
                scalefact = 1.0

            for iparam in range(newfunc.GetNpar()):
                newfunc.SetParameter(iparam, scalefact*finalfunc.GetParameter(iparam))
                newfunc.SetParError(iparam, scalefact*finalfunc.GetParError(iparam))
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
    parser.add_argument(
        "--systematic",
        dest = "systematic",
        choices = [None, "Lin", "Quad", "2L", "LinAll", "QuadAll"],
        help = "Do a systematic variation, for robustness checks")

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
        data = reader.ReadFiles(not cmdlinearguments.truthlevel, cmdlinearguments.systematic)
        if cmdlinearguments.truthlevel:
            plotdir = 'plots_privateMC'
        else:
            plotdir = 'plots_officialMC'
        if cmdlinearguments.systematic:
            plotdir += '_sys'+cmdlinearguments.systematic

    if 'data' in dir():
        plotter = CorrelationPlotter(data)
        plotter.MakeCorrelations()
        plotter.SaveData(plotdir)
        plotter.PlotData(plotdir)

