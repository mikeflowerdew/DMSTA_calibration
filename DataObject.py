#!/usr/bin/env python

class SignalRegion:
    """
    Class for holding CL values and fit functions for a single signal region.
    """

    def __init__(self, name, infolist=None):
        """Initialise the object with a name and (optionally) a list of which CL info will be provided.
        If not specified, it will be assumed that CL_s, CL_b and CL_s+b will all be required.
        """
        
        self.name = name

        if infolist is None: self.infolist = ['CLs','CLb','CLsb']
        else:                self.infolist = infolist

        # Data (CL values) and fit functions will be filled later
        self.data = {}
        self.fitfunctions = dict.fromkeys(self.infolist) # Values default to None

    
