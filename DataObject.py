#!/usr/bin/env python

class SignalRegion:
    """
    Class for holding CL values and fit functions for a single signal region.
    """

    # Dictionary to help display CL names properly when plotting.
    # Keys should be free of weird characters, as they could be used in file names etc.
    # Values can use ROOT's TLatex format.
    CLnames = {
        'CL'     : 'CL',
        'CLs'    : 'CL_{s}',
        'CLb'    : 'CL_{b}',
        'CLsb'   : 'CL_{s+b}',
        'CLObs'  : 'Observed CL',
        'CLsObs' : 'Observed CL_{s}',
        'CLbObs' : 'Observed CL_{b}',
        'CLsbObs': 'Observed CL_{s+b}',
        'CLExp'  : 'Expected CL',
        'CLsExp' : 'Expected CL_{s}',
        'CLbExp' : 'Expected CL_{b}',
        'CLsbExp': 'Expected CL_{s+b}',

        'LogCLs' : 'log_{10}(CL_{s})',
        }
    
    def __init__(self, name, infolist=None):
        """Initialise the object with a name and (optionally) a list of which CL info will be provided.

        Name would usually encode the analysis and SR names.

        The infolist describes which CL-like quantities will be supplied.
        The values of the list should match keys of SignalRegion.CLnames, see also the comment there.
        If something really non-standard is needed, just modify the CLnames member of your instance.
        By default, it is assumed that CLs, CLb and CLsb will be provided.

        Every data entry will have "yield" in addition to the infolist items.
        The object also defines a "fitfunctions" dictionary, with the same keys as infolist.
        These can be populated with strings and/or TF1 objects in the reader class,
        to decide how the functions are to be fitted.
        """
        
        self.name = name

        if infolist is None: self.__infolist = ['CLs','CLb','CLsb']
        else:                self.__infolist = infolist

        # Data (CL values) and fit functions will be filled later
        # The structure of data is a dictionary of dictionaries like this:
        # { modelID : {'yield': yield, 'CLs': CLs, ... }, ... }
        # It should be filled by an appropriate Reader class, eg Reader_DMSTA
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
    
    def CheckData(self):
        """Checks for missing data and (by default) removes models where no yield and/or CL information is found.
        """

        # Find models with incomplete data
        # Simple implementation with one loop over the models - hopefully the amount of missing data will be small

        # Classify missing info as follows (mutually exclusive categories):
        emptymodels = [] # No data at all
        yieldlessmodels = [] # No yield, but at least one CL value
        CLlessmodels = [] # Has yield, but no CL values
        incompletemodels = [] # Has yield, as well as some (but not all) CL values - only this is OK for plotting

        # Find out how many results we _should_ have
        targetCLnumber = len(self.__infolist)
        
        # Loop over the data
        for modelID,datum in self.data.iteritems():

            try:
                # Make sure we have a yield
                hasYield = datum['yield'] is not None
            except TypeError:
                # Implies that datum has no "yield" key
                # This should not happen, bail out if it does
                print 'Urgh:',modelID,datum
                raise

            # Find out how many CL-like numbers are filled (ie not None)
            numCLs = len([prop for prop in self.__infolist if datum[prop] is not None])

            if hasYield:
                # Maybe OK, let's check the CL values
                if numCLs == targetCLnumber:
                    # Perfect, we have all the CL values
                    continue
                elif not numCLs:
                    # No CL values at all, ie no meaningful results
                    CLlessmodels.append(modelID)
                else:
                    # Some, but not all, CL values are filled
                    incompletemodels.append(modelID)
            else:
                # No evgen yields, this is a problem
                if not numCLs:
                    # No CL values either, ie completely empty
                    emptymodels.append(modelID)
                else:
                    # At least one CL value is filled
                    yieldlessmodels.append(modelID)
        
        def __PrintWarning(modellist, message, removeduds=True):
            """Helper function to process possible warnings.
            Bad models (in modellist) are removed from self.data unless removeduds is False.
            """

            # If the (bad) modellist is empty, everything is OK
            if not modellist:
                print 'INFO: Checked %s for %s. OK'%(self.name,message)
                return

            # If we get here, something is wrong
            print 'WARNING: %s for %i/%s models in %s'%(message,len(modellist),len(self.data),self.name)
            print '\t',modellist,'\n'

            # Remove bad models now, if requested
            if removeduds:
                for m in modellist: self.data.pop(m)

        __PrintWarning(emptymodels, 'empty data')
        __PrintWarning(yieldlessmodels, 'empty yields')
        __PrintWarning(CLlessmodels, 'empty CL data')
        __PrintWarning(incompletemodels, 'incomplete CL data', False) # Hope for the best and do not remove here

