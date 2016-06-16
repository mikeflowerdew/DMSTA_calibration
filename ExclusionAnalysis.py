#!/usr/bin/env python

class SRresult:

    plotlist = ['mu','M_1','M_2','tanb'] \
        + ['mu:M_1'] \
        + ['M_2:M_1'] \
        + ['mu:M_2'] \
        + ['m_chi_10:m_chi_1p'] \
        + ['m_chi_20:m_chi_1p'] \
        + ['m_chi_30:m_chi_20'] \
        + ['m_chi_30:m_chi_2p'] \
        + ['m_chi_%i0'%i for i in range(1,5)] \
        + ['m_chi_%ip'%i for i in range(1,3)] \
        + ['N_1%i'%i for i in range(1,5)] \
        + ['N_2%i'%i for i in range(1,5)] \
        + ['N_3%i'%i for i in range(1,5)] \
        + ['N_4%i'%i for i in range(1,5)] \
        + ['Cross_section_nn1%i'%i for i in range(1,9)] \
        + ['Cross_section_nn2%i'%i for i in range(2,9)] \
        + ['Cross_section_nn3%i'%i for i in range(3,9)] \
        + ['Cross_section_nn4%i'%i for i in range(4,9)] \
        + ['Cross_section_nn5%i'%i for i in range(7,9)] \
        + ['Cross_section_nn6%i'%i for i in range(7,9)] \
        + ['BF_chi_20_to_chi_10%s'%s for s in ['','_Z','_h']] \
        + ['BF_chi_20_to_chi_1p%s'%s for s in ['','_W']] \
        + ['BF_chi_20_to_chi_2p%s'%s for s in ['','_W']] \
        + ['BF_chi_20_other'] \
        + ['BF_chi_30_to_chi_10%s'%s for s in ['','_Z','_h']] \
        + ['BF_chi_30_to_chi_20%s'%s for s in ['','_Z','_h']] \
        + ['BF_chi_30_to_chi_1p%s'%s for s in ['','_W']] \
        + ['BF_chi_30_to_chi_2p%s'%s for s in ['','_W']] \
        + ['BF_chi_30_other'] \
        + ['BF_chi_40_to_chi_10%s'%s for s in ['','_Z','_h']] \
        + ['BF_chi_40_to_chi_20%s'%s for s in ['','_Z','_h']] \
        + ['BF_chi_40_to_chi_30%s'%s for s in ['','_Z','_h']] \
        + ['BF_chi_40_to_chi_1p%s'%s for s in ['','_W']] \
        + ['BF_chi_40_to_chi_2p%s'%s for s in ['','_W']] \
        + ['BF_chi_40_other'] \
        + ['BF_chi_1p_to_chi_%i0'%i for i in range(1,4)] \
        + ['BF_chi_1p_other'] \
        + ['BF_chi_2p_to_chi_%i0'%i for i in range(1,4)] \
        + ['BF_chi_2p_to_chi_1p%s'%s for s in ['','_Z','_h']] \
        + ['BF_chi_2p_other']

    cutranges = {
        'All': {
            'm_chi_20': 'abs(m_chi_20) < 1000',
            'm_chi_30': 'abs(m_chi_30) < 1000',
            },
        'TwoLep': {
            'mu': 'abs(mu) < 500',
            'M_1': 'abs(M_1) < 200',
            # 'mu:M_1': 'abs(mu) < 500 && abs(M_1) < 200',
            'm_chi_30': 'abs(m_chi_30) < 500',
            },
        'ThreeLep': {
            'mu': 'abs(mu) < 500',
            'M_1': 'abs(M_1) < 200',
            'M_2': 'abs(M_2) < 1000',
            # 'mu:M_1': 'abs(mu) < 500 && abs(M_1) < 200',
            'm_chi_30': 'abs(m_chi_30) < 500',
            'm_chi_40': 'abs(m_chi_40) < 1000',
            },
        }

    def __init__(self, eventlist=None):
        
        self.eventlist = eventlist
        self.histograms = {}

    def getplots(self, tree, name='', templates=None):

        tree.SetEventList(self.eventlist)

        for branchname in self.plotlist:

            histname = '_'.join([branchname.replace(':','_'),name]) if name else branchname

            joinstr = '>>'
            if templates and templates.has_key(branchname):
                joinstr = '>>+'
                self.histograms[branchname] = templates[branchname].Clone(histname)
                self.histograms[branchname].Reset()

            try:
                tree.Draw(branchname+joinstr+histname, self.cutranges[name][branchname])
            except KeyError:
                tree.Draw(branchname+joinstr+histname)
            if not self.histograms.has_key(branchname):
                self.histograms[branchname] = ROOT.gDirectory.Get(histname)

            self.histograms[branchname].SetDirectory(0)
            if ':' in branchname:
                # 2D plot
                axisnames = branchname.split(':')
                # Yes, these labels are the correct way around!
                self.histograms[branchname].GetXaxis().SetTitle(axisnames[1])
                self.histograms[branchname].GetYaxis().SetTitle(axisnames[0])
            else:
                # 1D plot
                self.histograms[branchname].GetXaxis().SetTitle(branchname)

if __name__=='__main__':

    import ROOT
    ROOT.gROOT.SetBatch(True)
    ROOT.gROOT.LoadMacro("AtlasStyle.C")
    ROOT.SetAtlasStyle()
    ROOT.gROOT.LoadMacro("AtlasUtils.C") 
    ROOT.gROOT.LoadMacro("AtlasLabels.C")
    
    ntuplefile = ROOT.TFile.Open('Data_Yields/SummaryNtuple_STA_evgen.root')
    elistfile = ROOT.TFile.Open('Data_Yields/EventLists_evgen.root')
    
    tree = ntuplefile.Get('susy')

    # Extract TEventList objects from elistfile
    # Also, prepare some logical combinations of them
    eldict = {
        'TwoLep': ROOT.TEventList('TwoLep'),
        'ThreeLep': ROOT.TEventList('ThreeLep'),
        'FourLep': ROOT.TEventList('FourLep'),
        'Any': ROOT.TEventList('Any'),
        }

    for key in elistfile.GetListOfKeys():

        keyname = key.GetName()

        elist = elistfile.Get(keyname)

        eldict['Any'].Add(elist)
        if keyname.startswith('elist_EwkTwo'):
            eldict['TwoLep'].Add(elist)
        elif keyname.startswith('elist_EwkThree'):
            eldict['ThreeLep'].Add(elist)
        elif keyname.startswith('elist_EwkFour'):
            eldict['FourLep'].Add(elist)

        SRname = keyname.split('_')[-1]
        try:
            int(SRname)
            # Oh dear, 3L SR0a
            SRname = '_'.join(['SR0a',SRname])
        except:
            pass

        eldict[SRname] = elist

    # I want one more event list, for _non_ excluded models
    eldict['None'] = ROOT.TEventList('None')
    for ientry in range(tree.GetEntries()):
        if not eldict['Any'].Contains(ientry):
            eldict['None'].Enter(ientry)

    # Quick sanity check
    assert (eldict['Any'].GetN() + eldict['None'].GetN() == tree.GetEntries())

    resultdict = {
        'All': SRresult(),
        }
    resultdict['All'].getplots(tree)
    for keyname in ['TwoLep','ThreeLep','FourLep']:
        eldict[keyname].Print()
        resultdict[keyname] = SRresult(eldict[keyname])
        resultdict[keyname].getplots(tree, keyname)

    eldict['None'].Print()
    resultdict['None'] = SRresult(eldict['None'])
    resultdict['None'].getplots(tree, 'None', resultdict['All'].histograms)

    eldict['WWa'].Print()
    resultdict['WWa'] = SRresult(eldict['WWa'])
    resultdict['WWa'].getplots(tree, 'WWa', resultdict['TwoLep'].histograms)

    eldict['SR0a_16'].Print()
    resultdict['SR0a_16'] = SRresult(eldict['SR0a_16'])
    resultdict['SR0a_16'].getplots(tree, 'SR0a_16', resultdict['ThreeLep'].histograms)

    eldict['SR0Z'].Print()
    resultdict['SR0Z'] = SRresult(eldict['SR0Z'])
    resultdict['SR0Z'].getplots(tree, 'SR0Z', resultdict['FourLep'].histograms)

    canvas = ROOT.TCanvas('can','can',800,600)
    canvas.Divide(2,2)
    canvas.Print('ExclusionAnalysis.pdf[')

    for plotname in SRresult.plotlist:

        drawopt = 'BOX' if ':' in plotname else ''

        if plotname.startswith('N_'):
            for key in ['All','TwoLep','ThreeLep','FourLep']:
                resultdict[key].histograms[plotname].GetXaxis().SetRangeUser(-1,1)

        canvas.cd(1)
        resultdict['All'].histograms[plotname].Draw(drawopt)
        ROOT.myText(0.2,0.9,ROOT.kBlack,'All evgen')
        resultdict['None'].histograms[plotname].SetLineWidth(0)
        resultdict['None'].histograms[plotname].SetLineColor(ROOT.kRed)
        resultdict['None'].histograms[plotname].SetFillColor(ROOT.kRed)
        resultdict['None'].histograms[plotname].Draw(drawopt+'same')
        ROOT.myText(0.2,0.85,ROOT.kRed,'Not excluded')

        canvas.cd(2)
        resultdict['TwoLep'].histograms[plotname].Draw(drawopt)
        resultdict['WWa'].histograms[plotname].SetLineWidth(0)
        resultdict['WWa'].histograms[plotname].SetLineColor(ROOT.kBlue)
        resultdict['WWa'].histograms[plotname].SetFillColor(ROOT.kBlue)
        resultdict['WWa'].histograms[plotname].Draw(drawopt+'same')
        ROOT.myText(0.2,0.9,ROOT.kBlack,'2L excluded')
        ROOT.myText(0.2,0.85,ROOT.kBlue,'SR-WWa')

        canvas.cd(3)
        resultdict['ThreeLep'].histograms[plotname].Draw(drawopt)
        resultdict['SR0a_16'].histograms[plotname].SetLineWidth(0)
        resultdict['SR0a_16'].histograms[plotname].SetLineColor(ROOT.kBlue)
        resultdict['SR0a_16'].histograms[plotname].SetFillColor(ROOT.kBlue)
        resultdict['SR0a_16'].histograms[plotname].Draw(drawopt+'same')
        ROOT.myText(0.2,0.9,ROOT.kBlack,'3L excluded')
        ROOT.myText(0.2,0.85,ROOT.kBlue,'SR0#taua bin 16')

        canvas.cd(4)
        resultdict['FourLep'].histograms[plotname].Draw(drawopt)
        resultdict['SR0Z'].histograms[plotname].SetLineWidth(0)
        resultdict['SR0Z'].histograms[plotname].SetLineColor(ROOT.kBlue)
        resultdict['SR0Z'].histograms[plotname].SetFillColor(ROOT.kBlue)
        resultdict['SR0Z'].histograms[plotname].Draw(drawopt+'same')
        ROOT.myText(0.2,0.9,ROOT.kBlack,'4L excluded')
        ROOT.myText(0.2,0.85,ROOT.kBlue,'SR0Z')

        canvas.Print('ExclusionAnalysis.pdf')

    canvas.Print('ExclusionAnalysis.pdf]')
