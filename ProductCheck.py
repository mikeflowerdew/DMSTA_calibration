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

    def RunAnalysis(self):

        self.__ReadData()
        self.__DebugPrintout()

        self.__MainAnalysis()

    def __ReadData(self):
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

        # Analyse just the 4L data
        perSRreader = DMSTAReader()
        perSRreader.analysisdict = {
            '4L': DMSTAReader.analysisdict['4L'],
            }
        self.__perSRdata = perSRreader.ReadFiles()
        # Cache the order of the SRs
        self.__SRorder = [thing.name for thing in self.__perSRdata]

        # Read the combined 4L data
        # There's no point in reading the yields!
        combinationReader = DMSTAReader(
            yieldfile = None,
            DSlist = None,
            )
        combinationReader.analysisdict = {
            '4L_combination': DMSTAReader.analysisdict['4L'],
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
                allowedSRs = ['SR0noZa','SR0Z','SR1noZa','SR1Z','SR2noZa','SR2Z']
                SRindices = [idx for idx,SR in enumerate(self.__SRorder) if 'noZb' not in SR]
            elif 'bbb' in CombData.name:
                name = 'bbbZ'
                allowedSRs = ['SR0noZb','SR0Z','SR1noZb','SR1Z','SR2noZb','SR2Z']
                SRindices = [idx for idx,SR in enumerate(self.__SRorder) if 'noZa' not in SR]
            else:
                print 'ERROR in ProductCheck: Unknown combination',CombData.name
                continue

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

    def __DebugPrintout(self):

        print self.__SRorder
        print self.__combinationData[0].name

        for info in self.__CLsCorrelation['aaaZ'][:10]:

            print info.CombCLs,info.ProductCLs,info.SRCLs
            print info.ProductCLs/info.CombCLs if info.CombCLs else 0.0

    def __CLsMatchPlot(self, combination='aaaZ', CLsThreshold=1.):
        """Returns a graph of the ratio Pi(CLs_SR)/CLs_comb vs number of contributing regions."""

        indata = self.__CLsCorrelation[combination]
        
        result = ROOT.TGraph()
        result.SetName('CLsRatio_%s_%s'%(combination,CLsThreshold))

        for info in indata:

            info.ComputeProduct(CLsThreshold)

            if info.CombCLs and info.CombCLs < 0.5:
                result.SetPoint(result.GetN(),len(info.SRCLs),info.ProductCLs/info.CombCLs)

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

        result = [ROOT.TH1D(graph.GetName()+'_%i'%(i),'',200,0,2.0) for i in range(1,7)]

        for ipoint in range(graph.GetN()):

            NSRs = int(1.01*graph.GetX()[ipoint]) # Add 1% to avoid floating point errors
            CLsRatio = graph.GetY()[ipoint]

            result[NSRs-1].Fill(CLsRatio)

        return result

    def __MainAnalysis(self):

        outdir = 'productcheck'
        
        import os
        if not os.path.exists(outdir):
            os.makedirs(outdir)

        can = ROOT.TCanvas('can','can',800,800)

        # loop over possible CLs thresholds
        for threshold in [100,95,90,85,80,75]:
            
            # Create the output file and input data
            fname = '/'.join([outdir,'threshold_%i.pdf'%(threshold)])
            graph_aaa = self.__CLsMatchPlot('aaaZ',threshold/100.)
            graph_bbb = self.__CLsMatchPlot('bbbZ',threshold/100.)
            self.__PlotGraph(can, graph_aaa, graph_bbb, fname)

        # Try an experimental function
        def twosmallest(indict):
            mylist = sorted(indict.values())[:2]
            return reduce(lambda x,y: x*y, mylist, 1)

        # Create the output file and input data
        fname = '/'.join([outdir,'twosmallest.pdf'])
        graph_aaa = self.__CLsMatchPlot('aaaZ',twosmallest)
        graph_bbb = self.__CLsMatchPlot('bbbZ',twosmallest)
        self.__PlotGraph(can, graph_aaa, graph_bbb, fname)

        # Another experiment
        def twotimestwosmallest(indict):
            mylist = sorted(indict.values())[:2]
            return len(mylist)*reduce(lambda x,y: x*y, mylist, 1)

        # Create the output file and input data
        fname = '/'.join([outdir,'twotimestwosmallest.pdf'])
        graph_aaa = self.__CLsMatchPlot('aaaZ',twotimestwosmallest)
        graph_bbb = self.__CLsMatchPlot('bbbZ',twotimestwosmallest)
        self.__PlotGraph(can, graph_aaa, graph_bbb, fname)

        # And another
        def smallest(indict):
            return min(indict.values()) if indict else 1.

        # Create the output file and input data
        fname = '/'.join([outdir,'smallest.pdf'])
        graph_aaa = self.__CLsMatchPlot('aaaZ',smallest)
        graph_bbb = self.__CLsMatchPlot('bbbZ',smallest)
        self.__PlotGraph(can, graph_aaa, graph_bbb, fname)

    def __PlotGraph(self, canvas, graph_aaa, graph_bbb, fname):
        """Plot two graphs, together with their 1D projections"""
        
        canvas.Print(fname+'[')
    
        # plot the plots
        graph_aaa.SetMarkerSize(0.4)
        graph_aaa.Draw('ap')
        ROOT.myText(0.2, 0.95, ROOT.kBlack, 'aaaZ combination')
        canvas.Print(fname)
    
        # Plot the 1D projections
        histograms_aaa = self.__1Dprojections(graph_aaa)
        canvas.Clear()
        canvas.Divide(3,2)
        for i,h in enumerate(histograms_aaa):
            canvas.cd(i+1)
            # Make some space for the legend
            if h.GetMaximum() < 10:
                h.SetMaximum(1.5*h.GetMaximum())
            h.Draw()
            ROOT.myText(0.2, 0.95, ROOT.kBlack, 'aaaZ %i SRs'%(i+1))
            ROOT.myText(0.2, 0.9, ROOT.kBlack, 'Mean ratio = %.2f'%(h.GetMean()))
            ROOT.myText(0.2, 0.85, ROOT.kBlack, 'Entries: %i'%(h.GetEntries()))
            ROOT.myText(0.2, 0.8, ROOT.kBlack, 'Ratio < 0.7: %i'%(h.Integral(0,h.GetXaxis().FindBin(0.699))))
            ROOT.myText(0.2, 0.75, ROOT.kBlack, 'Ratio > 1.4: %i'%(h.Integral(h.GetXaxis().FindBin(1.401),h.GetNbinsX()+1)))
        canvas.Print(fname)
        canvas.Clear()

        # plot the plots
        graph_bbb.SetMarkerSize(0.4)
        graph_bbb.Draw('ap')
        ROOT.myText(0.2, 0.95, ROOT.kBlack, 'bbbZ combination')
        canvas.Print(fname)
    
        # Plot the 1D projections
        histograms_bbb = self.__1Dprojections(graph_bbb)
        canvas.Clear()
        canvas.Divide(3,2)
        for i,h in enumerate(histograms_bbb):
            canvas.cd(i+1)
            # Make some space for the legend
            if h.GetMaximum() < 10:
                h.SetMaximum(1.5*h.GetMaximum())
            h.Draw()
            ROOT.myText(0.2, 0.95, ROOT.kBlack, 'bbbZ %i SRs'%(i+1))
            ROOT.myText(0.2, 0.9, ROOT.kBlack, 'Mean ratio = %.2f'%(h.GetMean()))
            ROOT.myText(0.2, 0.85, ROOT.kBlack, 'Entries: %i'%(h.GetEntries()))
            ROOT.myText(0.2, 0.8, ROOT.kBlack, 'Ratio < 0.7: %i'%(h.Integral(0,h.GetXaxis().FindBin(0.699))))
            ROOT.myText(0.2, 0.75, ROOT.kBlack, 'Ratio > 1.4: %i'%(h.Integral(h.GetXaxis().FindBin(1.401),h.GetNbinsX()+1)))
        canvas.Print(fname)
        canvas.Clear()
    
        # Close the file, on to the next
        canvas.Print(fname+']')
