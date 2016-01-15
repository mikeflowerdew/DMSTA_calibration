#!/usr/bin/env python

from glob import glob
from DataObject import SignalRegion
import ROOT

class DMSTAReader:
    """Similar to the dummy reader, but reads truth yields from an ntuple and CL values from text files."""

    # Dictionary that serves two purposes
    # 1) the keys control what analyses will be included
    # 2) the values are associated strings used in the ntuple branch names
    analysisdict = {
        '3L': 'EwkThreeLepton_3L',
        '4L': 'EwkFourLepton',
        # '2L': 'EwkTwoLepton_SR',
        # '2T': 'EwkTwoTau_SR',
        }
    
    # Gah, way too many arguments - could fix with slots if I have time
    def __init__(self, yieldfile='Data_Yields/SummaryNtuple_STA_all.root',
                 dirprefix='Data_', fileprefix='pMSSM_SRA_table_EWK_', filesuffix='.dat',
                 DSlist='Data_Yields/D3PDs.txt'):
        """
        Set up to read input files from several directories.
        The yield ntuple path is stated explicitly, as is the DS list (for mapping the model ID to the DS ID).
        The CL values are assumed to be in dirprefix+analysis/fileprefix+analysis+'_'+SR+filesuffix
        The analysis names are taken from self.analysisdict.keys(), and the SR names are deduced from the file names.
        The ntuple is in the format described in https://twiki.cern.ch/twiki/bin/view/AtlasProtected/SUSYRun1pMSSMSummaryNtuple
        The file format column-based with whitespace separation and should look like
        Dataset   CL_b    CL_b_up   CL_b_down   CL_s+b   CL_s+b_up   CL_s+b_down
        Lines beginning with a # are regarded as comments and ignored.
        The dataset will be used to label the model.
        Lines with non-numeric data will be ignored.
        """
        
        self.__yieldfile = yieldfile
        self.__dirprefix = dirprefix
        self.__fileprefix = fileprefix
        self.__filesuffix = filesuffix
        self.__dslist = DSlist
        
    def ReadFiles(self):
        """Returns a list of SignalRegion objects, as required by the CorrelationPlotter.
        """

        # This is what we want to return
        result = []

        # Because the input is split between different formats,
        # I need to break the reading down into two steps.

        # The CL values are more refined and can give me the SR names for free,
        # so start with those
        for analysis in self.analysisdict.keys():
            result = self.ReadCLValues(result, analysis)

        # Then add the yields
        result = self.ReadYields(result)

        return result

    def ReadYields(self, data):
        """Reads the model yields from the given ntuple file.
        The data argument should be an already-populated list of SignalRegion instances.
        """

        # First open the DSlist to find which models we need
        f = open(self.__dslist)
        DSIDdict = {} # modelID : DSID for easy lookup later
        
        for line in f:

            line = line.rstrip()
            if not line:
                continue
            
            # The line should be empty or a dataset name
            splitline = line.split('.')

            try:
                DSID = int(splitline[1])
                modelID = int(splitline[2].split('_')[5])
            except IndexError:
                print 'WARNING in Reader_DMSTA: failed to read line'
                print repr(line)
                print splitline
                raise # Because I want to see what this is and fix it

            DSIDdict[modelID] = DSID

        f.close()
            
        # Now open up the ROOT ntuple and iterate over the entries
        # looking for relevant models
        yieldfile = ROOT.TFile.Open(self.__yieldfile)

        if not yieldfile:
            print 'ERROR: ROOT file %s not found'%(self.__yieldfile)
            # If I were doing this properly, I'd probably raise an exception
            return result
        
        tree = yieldfile.Get('susy')

        # Quick & dirty optimisation of what to read, as the tree is big
        tree.SetBranchStatus('*', 0)
        tree.SetBranchStatus('modelName', 1)
        for analysis in self.analysisdict.values():
            tree.SetBranchStatus('*%s*'%(analysis), 1)

        print 'WARNING: Looping over %s entries'%(tree.GetEntries())
        
        for entry in tree:

            modelID = entry.modelName

            # I believe the models are in order
            if not modelID % 1000:
                print 'On model',modelID
            
            try:
                DSID = DSIDdict[modelID]
            except KeyError:
                continue # Not interested (yet)

            # Loop over known analyses/SRs and look for the truth yield
            for datum in data:

                analysisSR = datum.name

                # Special case for 3L analysis SR0a
                analysisSR = analysisSR.replace('BIN','_')

                truthyield = getattr(entry, '_'.join(['EW_ExpectedEvents',datum.branchname]))

                try:
                    datum.data['yield'] = truthyield
                except KeyError:
                    # FIXME: Should check if the model is in DSIDdict and the yield is high and print a warning if it's not in data
                    pass
        
        return data
    
    def ReadCLValues(self, data, analysis):
        """For the given analysis, add the CL values to the data.
        """

        # Find the input files
        firstbit = self.__dirprefix+analysis+'/'+self.__fileprefix+analysis
        infiles = glob(firstbit+'_*'+self.__filesuffix)
        
        for fname in infiles:
            
            SRname = fname.replace(firstbit,'').replace(self.__filesuffix,'')

            analysisSR = '_'.join([analysis,SRname])

            # Try to find the existing data item
            obj = next((x for x in data if x.name == analysisSR), None)
            if obj is None:
                # First time we've looked at this analysisSR
                obj = SignalRegion(analysisSR, ['CLs','CLsb'])
                data.append(obj)

                # Store the equivalent ntuple branch name for convenience later
                obj.branchname = '_'.join([self.analysisdict[SRname],self.NtupleSRname(SRname,analysis)])
            else:
                print 'ERROR in Reader_DMSTA: already read-in model %s for %s'%(modelpoint,analysisSR)
                continue

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
                    CLb = float(splitline[1])
                    CLsb = float(splitline[4])
                except:
                    print 'WARNING: Malformed line in %s: %s'%(fname,line)
                    # Carry on, hopefully we can just analyse the other results
                    continue

                # Check that either CLsb or CLb were read OK
                if CLs is None and CLsb is None: continue

                if not CLb and CLb is not None:
                    print 'WARNING: CLb is zero in %s, model %s'%(fname,modelpoint)
                if not CLsb and CLsb is not None:
                    print 'WARNING: CLsb is zero in %s, model %s'%(fname,modelpoint)

                datum = obj.data[modelpoint] # Is it possible for this to fail?
                datum['CLs']   = CLs
                datum['CLsb']   = CLsb

        return data

    def NtupleSRname(self, SRname, analysis):
        """Convert the SR name used in the CL files to that used in the yield ntuple.
        """

        # Fix for 3L SR0a
        SRname = SRname.replace('BIN','_')

        return SRname
    
