#!/usr/bin/env python

class SignalRegion:
    """
    Class for holding CL values and fit functions for a single signal region.
    """

    def __init__(self, name, infolist=None):
        """Initialise the object with a name and (optionally) a list of which CL info will be provided.
        Name would usually encode the analysis and SR names.
        The infolist describes which CL-like quantities will be supplied.
        If not specified, it will be assumed that CL_s, CL_b and CL_s+b will all be required.
        These are encoded as "CLs", "CLb" and "CLsb", respectively (this will help the plotter to understand what to show).
        In any case, the infolist items should not include unusual characters (_, {}, etc) as they may
        be used in output file names etc.
        Every data entry will have "yield" in addition to the infolist items.
        """
        
        self.name = name

        if infolist is None: self.__infolist = ['CLs','CLb','CLsb']
        else:                self.__infolist = infolist

        # Data (CL values) and fit functions will be filled later
        self.data = {}
        self.fitfunctions = dict.fromkeys(self.__infolist) # Values default to None

    def InfoList(self):
        return self.__infolist
    
    def AddData(self, modelID):
        """Creates a new entry in self.data, if needed, and return the entry.
        Existing data is not overwritten.
        """

        if self.data.has_key(modelID): return self.data[modelID]
        return self.ResetData(modelID)

    def ResetData(self, modelID):
        """Resets the data for the given model, creating a new record if required.
        The data entry is returned.
        """

        self.data[modelID] = dict.fromkeys(['yield']+self.__infolist)
        return self.data[modelID]
    
    def CheckData(self, removeduds=True):
        """Checks for missing data and (by default) removes models where no yield and/or CL information is found.
        """

        # Find models with incomplete data
        # Simple implementation with one loop over the models - hopefully the amount of missing data will be small

        # Classify missing info as follows (mutually exclusive categories):
        emptymodels = [] # No data at all
        yieldlessmodels = [] # No yield, but at least one CL value
        CLlessmodels = [] # Has yield, but no CL values
        incompletemodels = [] # Has yield, as well as some (but not all) CL values - only this is OK for plotting

        targetCLnumber = len(self.__infolist)
        
        for modelID,datum in self.data.iteritems():

            hasYield = datum['yield'] is not None
            numCLs = len([prop for prop in self.__infolist if datum[prop] is not None])

            if hasYield:
                # Maybe OK, let's check the CL values
                if numCLs == targetCLnumber: continue # OK!
                elif not numCLs: CLlessmodels.append(modelID)
                else: incompletemodels.append(modelID)
            else:
                # Oh dear, this means we cannot plot the data
                if not numCLs: emptymodels.append(modelID)
                else: yieldlessmodels.append(modelID)
        
        def __PrintWarning(modellist, message, removeduds=True):

            if not modellist: return # We're OK!

            print 'WARNING: %s for %i models in %s'%(message,len(modellist),self.name)
            print '\t',modellist,'\n'
            if removeduds:
                for m in modellist: self.data.pop(m)

        __PrintWarning(emptymodels, 'empty data')
        __PrintWarning(yieldlessmodels, 'empty yields')
        __PrintWarning(CLlessmodels, 'empty CL data')
        __PrintWarning(incompletemodels, 'incomplete CL data', False)
