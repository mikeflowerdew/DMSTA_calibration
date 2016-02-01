#!/usr/bin/env python

import ROOT

class ProductCheck:
    """Single-use class, isolated from the rest of the code, for studying the 
    efficacy of taking the product of CLs values."""

    def __init__(self):
        """Placeholder, in case I need it later"""
        pass

    def RunAnalysis(self):

        self.__ReadData()
        self.__DebugPrintout()

        graph = self.__CLsMatchPlot(CLsThreshold=None)

        can = ROOT.TCanvas('can','can',800,800)
        graph.SetMarkerSize(0.4)
        graph.Draw('ap')
        can.Print('blah.pdf')


    def __ReadData(self):

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

    def __DebugPrintout(self):

        # FIXME: Experimental while I think about how to do this
        print self.__SRorder
        print self.__combinationData[0].name
        indices = [0,2,3,5,6,8] if 'aaa' in self.__combinationData[0].name else [1,2,4,5,7,8] # FIXME
        for modelID,info in self.__combinationData[0].data.items()[:10]:
            
            combinedCLs = info['CLs']

            separateCLs = []
            for index in indices:
                try:
                    separateCLs.append(self.__perSRdata[index].data[modelID]['CLs'])
                except KeyError:
                    # May have no results in that model for that SR
                    pass
            from operator import mul
            productCLs = reduce(mul, separateCLs, 1)
            print modelID,combinedCLs,productCLs,separateCLs
            print productCLs/combinedCLs if combinedCLs else 0.0

    def __CLsMatchPlot(self, combination='aaaZ', CLsThreshold=None):
        """Returns a graph of the ratio Pi(CLs_SR)/CLs_comb vs number of contributing regions."""

        whichComb = self.__CombOrder.index('4L_combination_'+combination)
        indices = []
        for idx,SR in enumerate(self.__SRorder):
            if 'noZ' in SR:
                if 'aaa' in combination and 'noZa' in SR:
                    indices.append(idx)
                elif 'bbb' in combination and 'noZb' in SR:
                    indices.append(idx)
            else:
                # Z region, always add
                indices.append(idx)
        
        result = ROOT.TGraph()
        result.SetName('CLsRatio_%s_%s'%(combination,CLsThreshold))

        for modelID,info in self.__combinationData[whichComb].data.items():
            
            combinedCLs = info['CLs']

            separateCLs = []
            for index in indices:
                try:
                    CLs = self.__perSRdata[index].data[modelID]['CLs']
                    separateCLs.append(CLs)
                except KeyError:
                    # May have no results in that model for that SR
                    pass
            from operator import mul
            productCLs = reduce(lambda x,y: x*y if CLsThreshold is None or y <= CLsThreshold else x, separateCLs, 1)
        
            if combinedCLs:
                result.SetPoint(result.GetN(),len(separateCLs),productCLs/combinedCLs)

        return result
