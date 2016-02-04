#!/usr/bin/env python

class Combiner:

    def __init__(self, yieldfilename, calibfilename):
        """Inputs are the ROOT files with the truth-level ntuple
        and the CL/yield calibration."""

        self.__yieldfilename = yieldfilename

        self.ReadCalibrations(calibfilename)

    def ReadCalibrations(self, calibfilename):
        """Reads all TF1 objects and stores them."""

        self.CalibCurves = {}

        calibfile = ROOT.TFile.Open(calibfilename)

        for keyname in calibfile.GetListOfKeys():

            thing = calibfile.Get(keyname)

            if not thing.InheritsFrom('TF1'):
                continue

            # Copy the graph to memory
            thing.SetDirectory(0)

            # Retrieve the x-axis minimum, extend the range back down to zero
            thing.xmin = thing.GetXmin()
            thing.SetRange(0,thing.GetXmax())
            
            # The graph names come with the CL type
            # separated from the analysis/SR by an underscore
            analysisSR = '_'.join(keyname.split('_')[:-1])
            
            self.CalibCurves[analysisSR] = thing

            return

if __name__ == '__main__':

    import ROOT
    ROOT.gROOT.SetBatch(True)
    ROOT.gROOT.LoadMacro("AtlasStyle.C")
    ROOT.SetAtlasStyle()
    ROOT.gROOT.LoadMacro("AtlasUtils.C") 

    obj = Combiner('Data_Yields/SummaryNtuple_STA_nosim.root',
                   'plots/calibration.root')
