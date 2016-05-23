#!/usr/bin/env python

from glob import glob
import math
from DataObject import SignalRegion
from ValueWithError import valueWithError
import ROOT
ROOT.gROOT.SetBatch(True)

class DMSTAReader:
    """Similar to the dummy reader, but reads truth yields from an ntuple and CL values from text files."""

    # Dictionary that serves two purposes
    # 1) the keys control what analyses will be included
    # 2) the values are associated strings used in the ntuple branch names
    analysisdict = {
        '3L': 'EwkThreeLepton_3L',
        '4L': 'EwkFourLepton',
        '2L': 'EwkTwoLepton',
        # '2T': 'EwkTwoTau',
        }

    # Veto reading certain model/SR combinations
    # This should be used VERY sparingly, but seems to be the only
    # way to get some SR calibrations to look remotely sensible
    # analysis/SR strings are the keys, and the lists are the DSIDs to skip for that SR
    vetodata = {
        'EwkFourLepton_SR0Z': [255054,254844],
        }
    
    # Gah, way too many arguments - could fix with slots if I have time
    def __init__(self, yieldfile='Data_Yields/SummaryNtuple_STA_sim.root',
                 dirprefix='Data_', fileprefix='pMSSM_STA_table_EWK_', filesuffix='.dat',
                 DSlist='Data_Yields/D3PDs.txt', HFfile='HistFitter/CLsFunctions_logCLs.root'):
        """
        Set up to read input files from several directories.
        The yield ntuple path is stated explicitly, as is the DS list (for mapping the model ID to the DS ID).
        The CL values are assumed to be in dirprefix+analysis/fileprefix+analysis+'_'+SR+filesuffix
        The analysis names are taken from self.analysisdict.keys(), and the SR names are deduced from the file names.
        The ntuple is in the format described in https://twiki.cern.ch/twiki/bin/view/AtlasProtected/SUSYRun1pMSSMSummaryNtuple
        The file format column-based with whitespace separation and should look like
        Dataset   CL_b    CL_b_up   CL_b_down   CL_s+b   CL_s+b_up   CL_s+b_down   CL_s_expected
        Lines beginning with a # are regarded as comments and ignored.
        The dataset will be used to label the model.
        Lines with non-numeric data will be ignored.

        If no files of the above pattern are found for a particular directory, but files ending .yaml are found,
        Then the reader assumes a format like
        SR: [yield,CLs_obs,CLs_exp]
        At the time of writing, this is used by the 2L search.

        The HFfile describes where the HistFitter calibration functions are to be found.
        If set to None, '', etc, then no fit function will be associated with the objects.
        """
        
        self.__yieldfile = yieldfile
        self.__dirprefix = dirprefix
        self.__fileprefix = fileprefix
        self.__filesuffix = filesuffix
        self.__dslist = DSlist
        self.__hffile = HFfile
        self.__DSIDdict = {} # Formed from the DSlist in a bit
        
    def ReadFiles(self, officialMC=True):
        """Returns a list of SignalRegion objects, as required by the CorrelationPlotter.
        The flag sets whether the truth yields are taken from the official MC (default)
        or the original private evgen.
        """

        # This is what we want to return
        result = []

        # First map model IDs to DSIDs
        self.__ReadDSIDs()

        # Because the input is split between different formats,
        # I need to break the reading down into two steps.

        # The CL values are more refined and can give me the SR names for free,
        # so start with those
        for analysis in self.analysisdict.keys():
            result = self.ReadCLValues(result, analysis)

        # Then add the yields
        result = self.ReadYields(result, officialMC)

        # Keep warning/info messages from different sources separate
        print

        return result

    def __ReadDSIDs(self):
        """Map the model number to the ATLAS dataset ID.
        The information from self.__dslist is stored in self.__DSIDdict
        """
        
        if not self.__dslist:
            return
            
        # First open the DSlist to find which models we need
        f = open(self.__dslist)
        
        for line in f:

            line = line.rstrip()
            if not line:
                continue
            
            # The line should be empty or a dataset name
            splitline = line.split('.')

            try:
                # In both cases I need a string, but want to check that it's a valid int
                DSID = int(splitline[1])
                modelID = int(splitline[2].split('_')[5])
            except IndexError:
                print 'WARNING in Reader_DMSTA: failed to read line'
                print repr(line)
                print splitline
                raise # Because I want to see what this is and fix it

            self.__DSIDdict[modelID] = DSID

        f.close()

        return

    def ReadYields(self, data, officialMC=True):
        """Reads the model yields from the given ntuple file.
        The data argument should be an already-populated list of SignalRegion instances.
        """

        if not self.__yieldfile:
            return data
            
        # Keep warning/info messages from different sources separate
        print
            
        # Open up the ROOT ntuple with the yields and iterate over the entries
        # looking for relevant models
        yieldfile = ROOT.TFile.Open(self.__yieldfile)

        if not yieldfile:
            print 'ERROR: ROOT file %s not found'%(self.__yieldfile)
            # If I were doing this properly, I'd probably raise an exception
            return result
        
        tree = yieldfile.Get('susy')

        branchprefix = 'EWOff' if officialMC else 'EW'

        # Quick & dirty optimisation of what to read, as the tree is big
        tree.SetBranchStatus('*', 0)
        tree.SetBranchStatus('modelName', 1)
        for analysis in self.analysisdict.values():
            tree.SetBranchStatus('*%s*'%(analysis), 1)

        print 'INFO: Reader_DMSTA looping over %s entries'%(tree.GetEntries())
        filledYields = 0
        
        for entry in tree:

            modelID = int(entry.modelName)

            try:
                DSID = self.__DSIDdict[modelID]
            except KeyError:
                continue # Not interested (yet)

            # Loop over known analyses/SRs and look for the truth yield
            for datum in data:

                analysisSR = datum.name

                # See if we should skip this entry
                # Killing the yield info is enough: we don't need to remove the CL values
                try:
                    veto = DSID in self.vetodata[analysisSR]
                    if veto:
                        continue
                except KeyError:
                    # analysisSR not in vetolist: we're OK to go on
                    pass

                # Get the yield from the official samples
                truthyield = getattr(entry, '_'.join([branchprefix,'ExpectedEvents',datum.branchname]))
                trutherror = getattr(entry, '_'.join([branchprefix,'ExpectedError',datum.branchname]))

                try:
                    datum.data[DSID]['yield'] = valueWithError(truthyield,trutherror)
                    filledYields += 1

                except KeyError:
                    # FIXME: Should check if the model is in DSIDdict and the yield is high and print a warning if it's not in data
                    pass

        print 'Filled %i entries with yields'%(filledYields)
        return data
    
    def ReadCLValues(self, data, analysis):
        """For the given analysis, add the CL values to the data.
        """

        # Find the input files
        # Try the traditional pMSSM paper format first
        firstbit = self.__dirprefix+analysis+'/'+self.__fileprefix+analysis+'_'
        searchstring = firstbit+'*'+self.__filesuffix
        infiles = glob(searchstring)

        if infiles:
            
            print 'INFO: Reader_DMSTA found %i matches to %s'%(len(infiles),searchstring)
            for fname in infiles:
                SRname = self.NtupleSRname(fname.replace(firstbit,'').replace(self.__filesuffix,''), analysis)
                data = self.__ReadPmssmFiles(data, analysis, fname, SRname)

        else:

            # Oh dear, maybe these are YAML files
            firstbit = self.__dirprefix+analysis
            searchstring = '/'.join([firstbit,'*.yaml'])
            infiles = glob(searchstring)

            print 'INFO: Reader_DMSTA found %i matches to %s'%(len(infiles),searchstring)
            for fname in infiles:
                modelname = int(fname.split('/')[-1].split('.')[0])
                DSID = self.__DSIDdict[modelname]
                data = self.__ReadYamlFiles(data, analysis, fname, DSID)

        return data

    def __ReadYamlFiles(self, data, analysis, fname, modelname):
        """Homebrewed reading of YAML files. The assumed format is
        SRname: [DSID,CLs_obs,CLs_exp]
        """

        f = open(fname)

        for line in f:

            splitline = line.split()

            # Skip empty lines
            if not splitline: continue

            # Apply some basic formatting to the SR name
            SRname = self.NtupleSRname(splitline[0].rstrip(':').replace('-','_'),analysis)

            analysisSR = '_'.join([self.analysisdict[analysis],SRname])

            # Try to find the existing data item
            obj = next((x for x in data if x.name == analysisSR), None)
            if obj is None:
                # First time we've looked at this analysisSR
                obj = SignalRegion(analysisSR, ['LogCLsObs','LogCLsExp'])
                data.append(obj)

                # Store the equivalent ntuple branch name for convenience later
                obj.branchname = '_'.join([self.analysisdict[analysis],self.NtupleSRname(SRname,analysis)])

                self.__SetupFitFunc(obj)

            # The data is stored as a list, use ast to read it
            import ast
            numericdata = ast.literal_eval(''.join(splitline[1:]))

            try:
                CLsObs = float(numericdata[1])
                CLsExp = float(numericdata[2])
            except IndexError:
                print 'WARNING: Incomplete data in %s, %s'%(fname,SRname)
                print line
                continue
            except:
                print 'WARNING: Invalid CLs values %s and %s in %s, %s'%(numericdata[1],numericdata[2],fname,SRname)
                continue

            try:
                datum = obj.data[modelname]
                print 'WARNING: Entry for model %i already exists for %s'%(modelname,analysisSR)
            except KeyError:
                datum = obj.AddData(modelname)

            if CLsObs and CLsObs > 0:
                datum['LogCLsObs'] = math.log10(CLsObs)
            if CLsExp and CLsExp > 0:
                datum['LogCLsExp'] = math.log10(CLsExp)
                
        f.close() # Let's be tidy

        return data

    def __ReadPmssmFiles(self, data, analysis, fname, SRname):
        """Homebrewed reading of tab-separated data files. The assumed format is:
        Dataset   CL_b    CL_b_up   CL_b_down   CL_s+b   CL_s+b_up   CL_s+b_down   CL_s_expected
        """

        analysisSR = '_'.join([self.analysisdict[analysis],SRname])

        # Try to find the existing data item
        obj = next((x for x in data if x.name == analysisSR), None)
        if obj is None:
            # First time we've looked at this analysisSR
            obj = SignalRegion(analysisSR, ['LogCLsObs','LogCLsExp'])
            data.append(obj)

            # Store the equivalent ntuple branch name for convenience later
            obj.branchname = '_'.join([self.analysisdict[analysis],self.NtupleSRname(SRname,analysis)])
        else:
            print 'WARNING in Reader_DMSTA: already read-in file for %s'%(analysisSR)
            return data

        self.__SetupFitFunc(obj)

        f = open(fname)
        for line in f:

            splitline = line.split()

            # Skip comments and empty lines
            if not splitline: continue
            if splitline[0].startswith('#'): continue
            try:
                modelpoint = int(splitline[0])
            except ValueError:
                continue # Line of text
            
            try:
                # Find all the input data first
                CLbObs  = float(splitline[1])
                CLsbObs = float(splitline[4])
                CLsExp  = float(splitline[7])
            except:
                print 'WARNING: Malformed line in %s: %s'%(fname,line)
                # Carry on, hopefully we can just analyse the other results
                continue

            # Check that either CLsb or CLb were read OK
            if CLbObs is None and CLsbObs is None and CLsExp is None: continue

            if not CLbObs and CLbObs is not None:
                print 'WARNING: CLbObs is zero in %s, model %s'%(fname,modelpoint)
            if not CLsbObs and CLsbObs is not None:
                print 'WARNING: CLsbObs is zero in %s, model %s'%(fname,modelpoint)
            if not CLsExp and CLsExp is not None:
                print 'WARNING: CLsExp is zero in %s, model %s'%(fname,modelpoint)

            try:
                datum = obj.data[modelpoint]
                print 'WARNING: Entry for model %i already exists for %s'%(modelpoint,analysisSR)
            except KeyError:
                datum = obj.AddData(modelpoint)

            if CLbObs and CLsbObs:
                datum['LogCLsObs'] = math.log10(CLsbObs/CLbObs)
            if CLsExp and CLsExp > 0:
                datum['LogCLsExp'] = math.log10(CLsExp)

        f.close() # Let's be tidy
        
        return data
    
    def NtupleSRname(self, SRname, analysis):
        """Convert the SR name used in the CL files to that used in the yield ntuple.
        """

        if analysis == '3L':
            # Fix for 3L SR0a
            SRname = SRname.replace('BIN0','_')
            SRname = SRname.replace('BIN','_')
    
            # Fix for a couple of other 3L SRs
            SRname = SRname.replace('SR0tb','SR0b')
            SRname = SRname.replace('SR1t','SR1SS')

        return SRname
    
    def __SetupFitFunc(self, SRobj):
        """Sets up fitting functions, to avoid duplication in the
        YAML and pMSSM file-reading methods.
        Could be extended to SR-specific configs using SRobj.name
        """

        def GoodFit(graph):
            """Tells the upstream code if a fit is good or bad, potentially
            in an SR-dependent way."""

            print 'MJF: checking fit for',graph.GetName()
    
            fitfunc = graph.GetFunction('fitfunc')
            if not fitfunc:
                return False
    
            # Compare the error of the log coefficient to its value
            normcoeff = valueWithError(fitfunc.GetParameter(0),fitfunc.GetParError(0))
            if abs(normcoeff.error) > 0.2*abs(normcoeff.value):
                return False

            print 'Success!'
            # Leave space for additional criteria if I need them
            return True

        def FitErrorGraph(graph):
            """Extracts the function fitted to the graph,
            and creates a TGraphErrors object to represent the +-1 sigma band of the fit.
            Whoever calls this function should give the graph a sensible name.
            If no fit function can be found, the method returns None."""

            fitfunc = graph.GetFunction('fitfunc')
            if not fitfunc:
                return None

            result = ROOT.TGraphErrors()

            # I haven't found a generic way to do this,
            # so I'll use the knowledge that this is really a one-parameter function
            normfactor = fitfunc.GetParameter(0)
            if not normfactor:
                return

            # Store the fractional error for convenience later
            normerror = fitfunc.GetParError(0)/normfactor

            # Loop over the function range in regular steps
            xmin = fitfunc.GetXmin()
            xmax = fitfunc.GetXmax()
            npx  = fitfunc.GetNpx()
            stepsize = (xmax-xmin)/(npx-1)

            for ipoint in range(npx):

                xval = xmin + ipoint*stepsize
                yval = fitfunc.Eval(xval)
                yerr = normerror*yval

                result.SetPoint(ipoint, xval, yval)
                result.SetPointError(ipoint, 0, yerr)

            return result

        # Check first if we have anything to configure
        if not self.__hffile:
            return
        # Extract HistFitter curves from the root file
        funcfile = ROOT.TFile.Open(self.__hffile)

        if funcfile and not funcfile.IsZombie():

            # Extracting the TF1 objects directly doesn't seem to work,
            # as the normalisation parameter becomes fixed.
            # So, extract the graph objects instead and recreate the TF1.
            # The real SR name is from "SR" to the end.
            shortSRname = SRobj.name[SRobj.name.index('SR'):]
            graphObs = funcfile.Get(shortSRname+'_graphObs')
            graphExp = funcfile.Get(shortSRname+'_graphExp')

            # FIXME: hard-coded -6...
            SRobj.fitfunctions['LogCLsObs'] = ROOT.TF1('fitfunc', lambda x,p: graphObs.Eval(x[0])/p[0], -6, 0, 1)
            SRobj.fitfunctions['LogCLsExp'] = ROOT.TF1('fitfunc', lambda x,p: graphExp.Eval(x[0])/p[0], -6, 0, 1)

            # Extract the TF1 object - does not work.
            # SRobj.fitfunctions['LogCLsObs'] = funcfile.Get(shortSRname)
            # SRobj.fitfunctions['LogCLsObs'].SetName('fitfunc') # for later convenience
            SRobj.fitfunctions['LogCLsObs'].SetParameter(0,1.)
            SRobj.fitfunctions['LogCLsExp'].SetParameter(0,1.)

            # Restrict the fit range to small CLs values
            # SRobj.fitfunctions['LogCLsObs'].SetRange(-6, -0.5)
            SRobj.fitfunctions['LogCLsObs'].xmin = -6.
            SRobj.fitfunctions['LogCLsObs'].xmax = -0.5
            SRobj.fitfunctions['LogCLsExp'].xmin = -6.
            SRobj.fitfunctions['LogCLsExp'].xmax = -0.5

            # Special case(s)
            if 'SR0Z' in SRobj.name:
                # SRobj.fitfunctions['LogCLsObs'].SetRange(-6, -0.6)
                SRobj.fitfunctions['LogCLsObs'].xmax = -0.6
                SRobj.fitfunctions['LogCLsExp'].xmax = -0.6

            SRobj.GoodFit = GoodFit
            SRobj.FitErrorGraph = FitErrorGraph

        else:

            print 'ERROR in Reader_DMSTA: could not open HistFitter file'
