#!/usr/bin/env python

import ROOT

class CLsData:
    """Simple class to keep all of the CLs values together"""

    def __init__(self, CombinationCLs):

        self.CombCLs = CombinationCLs
        self.ProductCLs = 1.
        self.SRCLs = {} # SR: CLs

    def ComputeProduct(self, testfunc=1.):
        """testfunc could be a function or a float.
        If a function, it defines how to calculate self.ProductCLs from self.SRCLs.
        If a float, it sets a simple upper threshold on what CLs values will be included.
        """
        
        try:
            testfunc + 1 # Dumb numerical value test
            self.ProductCLs = reduce(lambda x,y: x*y if y <= testfunc else x, self.SRCLs.values(), 1)
        except:
            self.ProductCLs = testfunc(self.SRCLs)

class ProductCheck:
    """Single-use class, isolated from the rest of the code, for studying the 
    efficacy of taking the product of CLs values."""

    def __init__(self):
        """Placeholder, in case I need it later"""
        pass

    def RunAnalysis(self, analysis):

        self.__ReadData(analysis)
        self.__DebugPrintout(analysis)

        self.__MainAnalysis(analysis)

    def __ReadData(self, analysis):
        """Read in all the relevant data and sort it.
        The combined CLs values are read in, together with the CLs
        values for each individual signal region.
        These are stored in the usual SignalRegion object, which is
        not especially convenient, so the data is then sorted.
        Each combined value is associated directly with the relevant SR data.
        self.__CLsCorrelation is a dictionary with keys corresponding to
        the combinations (eg aaaZ or bbbZ), while the values are lists of
        CLsData objects.
        """

        from Reader_DMSTA import DMSTAReader

        # Analyse the data
        perSRreader = DMSTAReader()
        perSRreader.analysisdict = {
            analysis: DMSTAReader.analysisdict[analysis],
            }
        self.__perSRdata = perSRreader.ReadFiles()
        # Cache the order of the SRs
        self.__SRorder = [thing.name for thing in self.__perSRdata]

        # Read the combined data
        # There's no point in reading the yields!
        combinationReader = DMSTAReader(
            yieldfile = None,
            DSlist = None,
            )
        combinationReader.analysisdict = {
            analysis+'_combination': DMSTAReader.analysisdict[analysis],
            }
        self.__combinationData = combinationReader.ReadFiles()
        # Cache the order of the combinations
        self.__CombOrder = [thing.name for thing in self.__combinationData]

        # Now sort out the real mapping between these results
        self.__CLsCorrelation = {}
        for CombData in self.__combinationData:

            SRindices = []
            if 'aaa' in CombData.name:
                name = 'aaaZ'
                allowedSRs = ['EwkFourLepton_SR0noZa',
                              'EwkFourLepton_SR0Z',
                              'EwkFourLepton_SR1noZa',
                              'EwkFourLepton_SR1Z',
                              'EwkFourLepton_SR2noZa',
                              'EwkFourLepton_SR2Z']
            elif 'bbb' in CombData.name:
                name = 'bbbZ'
                allowedSRs = ['EwkFourLepton_SR0noZb',
                              'EwkFourLepton_SR0Z',
                              'EwkFourLepton_SR1noZb',
                              'EwkFourLepton_SR1Z',
                              'EwkFourLepton_SR2noZb',
                              'EwkFourLepton_SR2Z']
            elif '3L' in CombData.name:
                name = '3L'
                allowedSRs = ['EwkThreeLepton_3L_SR0a_%i'%i for i in range(1,21)]
                allowedSRs.extend(['EwkThreeLepton_3L_SR0b','EwkThreeLepton_3L_SR1SS'])
            else:
                print 'ERROR in ProductCheck: Unknown combination',CombData.name
                continue

            # Cache the indices for use in a moment
            SRindices = [idx for idx,SR in enumerate(self.__SRorder) if SR in allowedSRs]

            data = []
            
            for modelID,info in CombData.data.items():

                result = CLsData(info['CLs'])

                for index in SRindices:
                    try:
                        SRdata = self.__perSRdata[index]
                        CLs = SRdata.data[modelID]['CLs']
                        result.SRCLs[SRdata.name] = CLs
                    except KeyError:
                        # May have no results in that model for that SR
                        pass

                result.ComputeProduct()
                data.append(result)

            self.__CLsCorrelation[name] = data
            
        return

    def __DebugPrintout(self, analysis):

        print self.__SRorder
        print self.__combinationData[0].name

        for info in self.__CLsCorrelation.values()[0][:10]:

            print info.CombCLs,info.ProductCLs,info.SRCLs
            print info.ProductCLs/info.CombCLs if info.CombCLs else 0.0

    def __CLsMatchPlot(self, combination='aaaZ', CLsThreshold=1., adjustCLs=lambda comb,prod: (comb,prod)):
        """Returns a tuple of TGraph objects.
        The first graph shows the ratio Pi(CLs_SR)/CLs_comb vs number of contributing regions.
        The second graph shows the same ratio versus the combined CLs.
        The third graph shows the same ratio versus the product CLs.
        The adjustCLs function allows the user to adjust the CLs value(s) (eg to round up)
        and/or to reject them altogether by returning None for at least one of the values.
        It must have the same signature as the default argument."""

        indata = self.__CLsCorrelation[combination]
        
        result = tuple([ROOT.TGraph() for i in range(3)])
        result[0].SetName('RatioVsNSR_%s_%s'%(combination,CLsThreshold))
        result[1].SetName('RatioVsComb_%s_%s'%(combination,CLsThreshold))
        result[2].SetName('RatioVsProd_%s_%s'%(combination,CLsThreshold))

        for info in indata:

            info.ComputeProduct(CLsThreshold)

            combCLs,prodCLs = adjustCLs(info.CombCLs,info.ProductCLs)

            if combCLs and prodCLs and combCLs < 0.5:
                CLsRatio = prodCLs/combCLs
                result[0].SetPoint(result[0].GetN(),len(info.SRCLs),CLsRatio)
                result[1].SetPoint(result[1].GetN(),combCLs,CLsRatio)
                result[2].SetPoint(result[2].GetN(),prodCLs,CLsRatio)

                if CLsRatio > 1e5: #1e8: # Wow!
                    print 'Extreme point found for',combination,CLsThreshold
                    print 'Combined = %.4e, estimate = %.4e for %i SRs'%(combCLs,prodCLs,len(info.SRCLs))
                    print sorted(info.SRCLs.values())

                # FIXME
#                 try:
#                     # FIXME - debug only
#                     if info.CombCLs and abs(info.ProductCLs/info.CombCLs - 1.) < 0.05 and len(info.SRCLs) > 3:
#                         print info.CombCLs,info.ProductCLs,info.SRCLs
#                     if abs(CLsThreshold-0.75) < 0.01 and info.ProductCLs/info.CombCLs < 0.5:
#                         print info.CombCLs,info.ProductCLs,info.SRCLs
#                 except:
#                     pass
            
        return result

    def __1Dprojections(self, graph):
        """Turns a TGraph returned by self.__CLsMatchPlot into 6 histograms
        corresponding to the slices in the number of SRs."""

        # The x-axis min/max values should be integers,
        # although it seems they go from 0.5 to NSRs+0.5?
        # Just add a little protection about float rounding errors
        minimum = int(graph.GetXaxis().GetXmin() + 1.005)
        maximum = int(graph.GetXaxis().GetXmax() + 1.005)

        result = [ROOT.TH1D(graph.GetName()+'_%i'%(i),'',200,0,2.0) for i in range(minimum,maximum)]

        for ipoint in range(graph.GetN()):

            NSRs = int(graph.GetX()[ipoint] + 0.005) # Add 0.005 to avoid floating point errors
            CLsRatio = graph.GetY()[ipoint]

            result[NSRs-minimum].Fill(CLsRatio)

        return result

    def __MainAnalysis(self, analysis):

        outdir = 'productcheck/'+analysis
        
        import os
        if not os.path.exists(outdir):
            os.makedirs(outdir)

        can = ROOT.TCanvas('can','can',800,800)

        # loop over possible CLs thresholds
        for threshold in [100,90,80,70]:
            # Create the output file and input data
            fname = '/'.join([outdir,'threshold_%i.pdf'%(threshold)])
            graphs = [self.__CLsMatchPlot(name,threshold/100.) for name in sorted(self.__CLsCorrelation.keys())]
            self.__PlotGraph(can, graphs, fname)

        # Try an experimental function
        def twosmallest(indict):
            mylist = sorted(indict.values())[:2]
            return reduce(lambda x,y: x*y, mylist, 1)
        # Create the output file and input data
        fname = '/'.join([outdir,'twosmallest.pdf'])
        graphs = [self.__CLsMatchPlot(name,twosmallest) for name in sorted(self.__CLsCorrelation.keys())]
        self.__PlotGraph(can, graphs, fname)

        # Another experiment
        def twotimestwosmallest(indict):
            mylist = sorted(indict.values())[:2]
            return len(mylist)*reduce(lambda x,y: x*y, mylist, 1)
        # Create the output file and input data
        fname = '/'.join([outdir,'twotimestwosmallest.pdf'])
        graphs = [self.__CLsMatchPlot(name,twotimestwosmallest) for name in sorted(self.__CLsCorrelation.keys())]
        self.__PlotGraph(can, graphs, fname)

        # And another
        def smallest(indict):
            return min(indict.values()) if indict else 1.
        # Create the output file and input data
        fname = '/'.join([outdir,'smallest.pdf'])
        graphs = [self.__CLsMatchPlot(name,smallest) for name in sorted(self.__CLsCorrelation.keys())]
        self.__PlotGraph(can, graphs, fname)

        # Try chopping out very low CL values
        def chopLow_1em6(combCLs,prodCLs):
            if combCLs < 1e-6: combCLs = None
            if prodCLs < 1e-6: prodCLs = None
            return combCLs,prodCLs
        # Try chopping with different CLs product procedures
        # 1: Default
        fname = '/'.join([outdir,'threshold_100_chop_1em6.pdf'])
        graphs = [self.__CLsMatchPlot(name,1.,chopLow_1em6) for name in sorted(self.__CLsCorrelation.keys())]
        self.__PlotGraph(can, graphs, fname)
        # 2: Smallest
        fname = '/'.join([outdir,'smallest_chop_1em6.pdf'])
        graphs = [self.__CLsMatchPlot(name,smallest,chopLow_1em6) for name in sorted(self.__CLsCorrelation.keys())]
        self.__PlotGraph(can, graphs, fname)
        # 3: Two smallest
        fname = '/'.join([outdir,'twosmallest_chop_1em6.pdf'])
        graphs = [self.__CLsMatchPlot(name,twosmallest,chopLow_1em6) for name in sorted(self.__CLsCorrelation.keys())]
        self.__PlotGraph(can, graphs, fname)

        # Try rounding up very low CL values
        def roundUp_1em6(combCLs,prodCLs):
            if combCLs < 1e-6: combCLs = 1e-6
            if prodCLs < 1e-6: prodCLs = 1e-6
            return combCLs,prodCLs
        # Try chopping with different CLs product procedures
        # 1: Default
        fname = '/'.join([outdir,'threshold_100_round_1em6.pdf'])
        graphs = [self.__CLsMatchPlot(name,1.,roundUp_1em6) for name in sorted(self.__CLsCorrelation.keys())]
        self.__PlotGraph(can, graphs, fname)
        # 2: Smallest
        fname = '/'.join([outdir,'smallest_round_1em6.pdf'])
        graphs = [self.__CLsMatchPlot(name,smallest,roundUp_1em6) for name in sorted(self.__CLsCorrelation.keys())]
        self.__PlotGraph(can, graphs, fname)
        # 3: Two smallest
        fname = '/'.join([outdir,'twosmallest_round_1em6.pdf'])
        graphs = [self.__CLsMatchPlot(name,twosmallest,roundUp_1em6) for name in sorted(self.__CLsCorrelation.keys())]
        self.__PlotGraph(can, graphs, fname)

    def __PlotGraph(self, canvas, graphs, fname):
        """Plot a list of graphs (each element an output of self.__CLsMatchPlot), together with their 1D projections"""

        if not graphs: return
        
        canvas.Print(fname+'[')

        for graphtuple in graphs:

            # ##########################################
            # First plot the CLs ratio vs number of SRs
            NSRgraph = graphtuple[0]
            # Ugh, a bit nasty but should be safe
            label = NSRgraph.GetName().split('_')[1]

            # plot the plots
            NSRgraph.SetMarkerSize(0.8)
            NSRgraph.Draw('ap')
            NSRgraph.GetXaxis().SetTitle('Number of active SRs')
            NSRgraph.GetYaxis().SetTitle('Estimated CLs / Combined CLs')
            ROOT.myText(0.2, 0.96, ROOT.kBlack, label+' combination')
            ROOT.ATLASLabel(0.6,0.9,'Internal')

            # Find the dynamic range of the graph,
            # only use a linear scale if this is small enough
            dynamicRange = NSRgraph.GetYaxis().GetXmax()/NSRgraph.GetYaxis().GetXmin() if NSRgraph.GetYaxis().GetXmin() else 1000.
            if dynamicRange < 6.:
                NSRgraph.SetMinimum(0)
            else:
                canvas.SetLogy()
                NSRgraph.SetMaximum(2*NSRgraph.GetYaxis().GetXmax()) # Leave space for the ATLAS label!
            canvas.Print(fname)
            canvas.SetLogy(0)

            # ##########################################
            # Now plot the second graph: CLs ratio vs combined CLs
            CLsgraph = graphtuple[1]
            # The label should be the same as before...

            # plot the plots
            CLsgraph.SetMarkerSize(0.8)
            CLsgraph.Draw('ap')
            CLsgraph.GetXaxis().SetTitle('Combined CLs')
            CLsgraph.GetYaxis().SetTitle('Estimated CLs / Combined CLs')
            ROOT.myText(0.2, 0.96, ROOT.kBlack, label+' combination')
            ROOT.ATLASLabel(0.6,0.9,'Internal')

            # This one will always need a logarithmic x-axis
            canvas.SetLogx()
            # The y-axis dynamic range should also be the same as before
            if dynamicRange < 6.:
                CLsgraph.SetMinimum(0)
            else:
                canvas.SetLogy()
                CLsgraph.SetMaximum(2*CLsgraph.GetYaxis().GetXmax()) # Leave space for the ATLAS label!
            canvas.Print(fname)
            canvas.SetLogx(0)
            canvas.SetLogy(0)

            # ##########################################
            # Now plot the third graph: CLs ratio vs product CLs
            CLsgraph = graphtuple[2]
            # The label should be the same as before...

            # plot the plots
            CLsgraph.SetMarkerSize(0.8)
            CLsgraph.Draw('ap')
            CLsgraph.GetXaxis().SetTitle('Estimated CLs')
            CLsgraph.GetYaxis().SetTitle('Estimated CLs / Combined CLs')
            ROOT.myText(0.2, 0.96, ROOT.kBlack, label+' combination')
            ROOT.ATLASLabel(0.6,0.9,'Internal')

            # This one will always need a logarithmic x-axis
            canvas.SetLogx()
            # The y-axis dynamic range should also be the same as before
            if dynamicRange < 6.:
                CLsgraph.SetMinimum(0)
            else:
                canvas.SetLogy()
                CLsgraph.SetMaximum(2*CLsgraph.GetYaxis().GetXmax()) # Leave space for the ATLAS label!
            canvas.Print(fname)
            canvas.SetLogx(0)
            canvas.SetLogy(0)

            # ##########################################
            # Plot the 1D projections of NSRgraph
            histograms = self.__1Dprojections(NSRgraph)
            canvas.Clear()
            canvas.Divide(3,2) # Nicely fits on one page
            # Round up the number of pages I need
            npages = (len(histograms)+5)/6

            for ipage in range(npages):
                for i,h in enumerate(histograms[6*ipage:6*(ipage+1)]):
                    canvas.cd(i+1)
                    # Make some space for the legend
                    if h.GetMaximum() < 10:
                        h.SetMaximum(1.5*h.GetMaximum())
                    h.GetXaxis().SetTitle('Estimated CLs / Combined CLs')
                    h.Draw()
                    ROOT.myText(0.2, 0.96, ROOT.kBlack, label+': %s active SRs'%(h.GetName().split('_')[-1]))
                    ROOT.myText(0.2, 0.9, ROOT.kBlack, 'Mean ratio = %.2f'%(h.GetMean()))
                    ROOT.myText(0.2, 0.85, ROOT.kBlack, 'Entries: %i'%(h.GetEntries()))
                    ROOT.myText(0.2, 0.8, ROOT.kBlack, 'Ratio < 0.7: %i models'%(h.Integral(0,h.GetXaxis().FindBin(0.699))))
                    ROOT.myText(0.2, 0.75, ROOT.kBlack, 'Ratio > 1.4: %i models'%(h.Integral(h.GetXaxis().FindBin(1.401),h.GetNbinsX()+1)))
                    ROOT.ATLASLabel(0.6,0.9,"Internal")
                canvas.Print(fname)
                canvas.Clear('D') # Keep the pads

            canvas.Clear()

        # Close the file, on to the next
        canvas.Print(fname+']')
