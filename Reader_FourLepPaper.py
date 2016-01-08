#!/usr/bin/env python

from glob import glob
from DataObject import SignalRegion

class FourLepPaperReader:
    """Similar to the dummy reader, but reads HepData-like tables from the 4L search paper."""
    
    def __init__(self, suffix='.txt', directory='fourleppaperdata', analysisname='4L'):
        """
        Set up to read input files from a named directory.
        Once the directory and the suffix are removed, the remaining filename indicates the SR.
        The input files should be semicolon-separated (like HepData), with columns like this:
            param1; param2; --; cross-section [pb]; acceptance; --; --; CL obs; CL exp; [filter efficiency];
        The first two columns will be appended to the model name to make each point unique.
        Columns with '--' are irrelevant and will be ignored.
        The last column is optional, and allows the cross-section to be corrected
        for the evgen filter efficiency if it was not already included.
        Lines beginning with a # are regarded as comments and ignored.
        A line before the data (usually the first) should be formatted like this:
            Model: SomeName
        The SomeName will be used to label the model in question.
        """
        
        self.__suffix = suffix
        self.__directory = directory
        self.__analysis = analysisname
        
    def ReadFiles(self):
        """Returns a list of SignalRegion objects, as required by the CorrelationPlotter.
        """

        # This is what we want to return
        result = []

        infiles = glob(self.__directory+'/*'+self.__suffix)
        
        for fname in infiles:
            
            SRname = fname.replace(self.__directory+'/','').replace(self.__suffix,'')

            analysisSR = '_'.join([self.__analysis,SRname])

            modelname = 'Model' # Dummy value, should be overwritten later
            
            f = open(fname)
            for line in f:

                # Skip comments and empty lines
                if line.startswith('#'): continue
                if not line.split(): continue

                if line.startswith('Model:'):
                    try: modelname = line.split()[1]
                    except IndexError: print 'WARNING: Could not read model name in %s: %s'%(fname,line)
                    
                    # In either case, skip the next section, as the formatting doesn't match
                    continue
                
                splitline = line.split(';')
                try:
                    # Find all the input data first
                    params = splitline[0:2]
                    Xsec = float(splitline[3])
                    Acc = float(splitline[4])
                    # Optional correction for the evgen filter efficiency
                    if len(splitline) > 9 and splitline[9] and not splitline[9].isspace():
                        Xsec *= float(splitline[9])

                    # CL values are sometimes " < (some small value)"
                    # while others are equal to 1000000
                    
                    CLobs = splitline[7]
                    if '<' in CLobs or '1000000' in CLobs: CLobs = None
                    else: CLobs = float(CLobs)

                    CLexp = splitline[8]
                    if '<' in CLexp or '1000000' in CLexp: CLexp = None
                    else: CLexp = float(CLexp)
                except:
                    print 'WARNING: Malformed line in %s: %s'%(fname,line)
                    # Carry on, hopefully we can just analyse the other results
                    continue

                # Construct the complete model name
                modelpoint = '_'.join([modelname]+params)

                # Now find the truth-level yield
                # Hard-coded lumi, this isn't going to change now :)
                truthyield = 20.3e3 * Xsec * Acc

                if not CLobs and CLobs is not None:
                    print 'WARNING: CLobs is zero in %s, model %s'%(fname,modelpoint)
                if not CLexp and CLexp is not None:
                    print 'WARNING: CLexp is zero in %s, model %s'%(fname,modelpoint)
                # Finally, check that CLobs was read OK
                # Not done earlier because eventually I might want to look at CLexp too
                if CLobs is None: continue

                # Add in this data point
                # First, try to find the existing data item
                obj = next((x for x in result if x.name == analysisSR), None)
                if obj is None:
                    # First time we've looked at this analysisSR
                    obj = SignalRegion(analysisSR, ['CLs'])
                    result.append(obj)

                datum = obj.AddData(modelpoint)
                datum['yield'] = truthyield
                datum['CLs']   = CLobs

        return result
