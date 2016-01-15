#!/usr/bin/env python

from glob import glob
from DataObject import SignalRegion

class DummyReader:

    def __init__(self, suffix='.txt', directory='dummydata'):

        self.__suffix = suffix
        self.__directory = directory

    def ReadFiles(self):
        """Returns a list of SignalRegion objects, as required by the CorrelationPlotter.
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
        """Returns a list of SignalRegion objects, as required by the CorrelationPlotter.
        """

        import ROOT
        result = []

        # Functions for randomised truth yields and CL values.
        # Don't care about seeding etc, this is just for proof-of-principle testing.

        # Truth yield for a model: just a uniform distribution between 0 and some maximum value.
        yieldfunc = lambda cap: ROOT.gRandom.Uniform(cap)

        # Extremely naive CL model: inversely proportional to the number of selected events.
        # "scale" sets the absolute normalisation of the CL values (ie the SR sensitivity).
        # The CL values are randomly smeared by 10%.
        CLfunc = lambda nevt,scale: (scale/nevt)*ROOT.gRandom.Gaus(1,0.1)

        # Set up some initial data
        for analysis in range(self.__nanalyses):

            for iSR in range(self.__nSRs):

                analysisSR = 'Analysis%i_SR%i'%(analysis,iSR)

                obj = SignalRegion(analysisSR, ['CLs','CLsb']) # Test out some new functionality, woo!
                result.append(obj)

                # Let's pick what parameters to use for this SR.
                # Cap the number of events somewhere near 15.
                evtcap = ROOT.gRandom.Gaus(15,3)
                # Assign a random sensitivity parameter (less sensitive SRs could have higher backgrounds etc).
                effectiveness = ROOT.gRandom.Uniform(1,10)

                for imodel in range(self.__nmodels):

                    # Cache the number of events
                    nevt = yieldfunc(evtcap)

                    datum = obj.AddData(imodel)
                    datum['yield'] = nevt
                    datum['CLsb']  = CLfunc(nevt,effectiveness)
                    datum['CLs']   = CLfunc(nevt,effectiveness) # Lazy - in reality there would be some relationship between CLs and CLsb

                # Fit functions. I know the correct form, so this is cheating
                # Constructors take the x-axis range, while the parameter must be initialised to something.
                # It apparently doesn't matter if the functions have unique names or not.

                obj.fitfunctions['CLs'] = ROOT.TF1('fitfunc','[0]/x',0,evtcap)
                obj.fitfunctions['CLs'].SetParameter(0,5.) # dumb but seems to work

                obj.fitfunctions['CLsb'] = ROOT.TF1('fitfunc','[0]/x',0,evtcap)
                obj.fitfunctions['CLs'].SetParameter(0,5.) # dumb but seems to work

        return result
