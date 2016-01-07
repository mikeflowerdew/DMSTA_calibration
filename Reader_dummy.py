#!/usr/bin/env python

from glob import glob
from DataObject import SignalRegion

class DummyReader:

    def __init__(self, suffix='.txt', directory='dummydata'):

        self.__suffix = suffix
        self.__directory = directory

    def ReadFiles(self):
        """Returns a list of SignalRegion objects,as required by the CorrelationPlotter.
        """

        # This is what we want to return
        result = []

        infiles = glob(self.__directory+'/*'+self.__suffix)
        
        for fname in infiles:
            
            basename = fname.replace(self.__directory+'/','').replace(self.__suffix,'')
            
            # Allow for underscores in the analysis name
            analysisname = '_'.join(basename.split('_')[:-1])
            modelname = basename.split('_')[-1]
            
            f = open(fname)
            for line in f:

                if line.startswith('#'): continue
                if not line.split(): continue

                splitline = line.split(',')
                try:
                    analysisSR = '_'.join([analysisname,splitline[0]])
                    SRyield = float(splitline[1])
                    SRCLsb = float(splitline[2])
                except:
                    print 'WARNING: Malformed line in %s: %s'%(fname,line)
                    # Carry on, hopefully we can just analyse the other results
                    continue

                # Add in this data point
                # First, try to find the existing data item
                obj = next((x for x in result if x.name == analysisSR), None)
                if obj is None:
                    # First time we've looked at this analysisSR
                    obj = SignalRegion(analysisSR, ['CLsb'])
                    result.append(obj)

                # Next, create the empty data item
                datum = obj.AddData(modelname)
                datum['yield'] = SRyield
                datum['CLsb'] = SRCLsb

        return result
    
class DummyRandomReader:
    """Produce randomly-generated yields and CL values for a configurable number of toy "analyses".
    The CL values have some arbitrary relationship to the yield.
    """

    def __init__(self, nmodels=50, nanalyses=5, nSRs=4):
        """Allows configuration of the number of models, number of analyses, and number of SRs per analysis.
        """

        # TODO: Add option to randomly drop some results, for testing
        self.__nmodels = nmodels
        self.__nanalyses = nanalyses
        self.__nSRs = nSRs

    def ReadFiles(self):
        """Returns a dictionary, structured in the way required by the CorrelationPlotter.
        """

        import ROOT
        result = {}

        # Quick alias to our random number generator
        # Don't care about seeding etc, this is just for testing
        yieldfunc = lambda cap: ROOT.gRandom.Uniform(cap)
        CLfunc = lambda nevt,scale: (scale/nevt)*ROOT.gRandom.Gaus(1,0.1)

        # Set up some initial data
        for analysis in range(self.__nanalyses):

            for iSR in range(self.__nSRs):

                analysisSR = 'Analysis%i_SR%i'%(analysis,iSR)

                result[analysisSR] = {}

                # Let's pick what parameters to use for this SR
                evtcap = ROOT.gRandom.Gaus(15,3)
                effectiveness = ROOT.gRandom.Uniform(1,10)

                for imodel in range(self.__nmodels):

                    nevt = yieldfunc(evtcap)
                    result[analysisSR][imodel] = (nevt, CLfunc(nevt,effectiveness))

        return result
