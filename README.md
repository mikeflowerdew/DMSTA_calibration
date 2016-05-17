# DMSTA_calibration
Package for the calibration of CL values vs yield for the ATLAS dark matter STA project

A secondary goal of this repository is to learn a little more about how git works.

There are a number of python scripts in this package. Some are executable, and these are the ones documented below. The non-executable python files contain classes that are used by the executable scripts. You'll need to refer to the code itself (and associated comments) to see which classes are used where.

# Complete workflow

## Prerequisites

First, check out the repo
```bash
$ git clone https://github.com/mikeflowerdew/DMSTA_calibration
$ cd DMSTA_calibration/
```

On top of the git repository, you also need to have a directory called `Data_Yields` (located within `DMSTA_calibration`). The contents are large, so personally I make this a soft link to a data-file area. It needs to contain:

1. `D3PDs.txt`, with one simulated dataset per line.
2. `SummaryNtuple_STA_all_version4.root` (or change the name in `SkimYieldFile.py` if yours is different).

## Step 1: Process the summary ntuple

First, the summary ntuple is to be split and drastically reduced in size (else later processing steps will be _very_ slow). The command to do this is
```bash
$ ./SkimYieldFile.py
```
This creates three skimmed files in `Data_Yields/`:

1. `SummaryNtuple_STA_sim.root`, with just the 500 simulated models (deduced from `D3PDs.txt`).
2. `SummaryNtuple_STA_evgen.root`, with the ~460k models with evgen (deduced from the ntuple itself).
3. `SummaryNtuple_STA_noevgen.root`, containing all models not in SummaryNtuple_STA_evgen.root.

This script has no command-line options: in principle it is a "do once and forget" script. It's possible to make some plots to compare the three files using `./SimBias.py`, however there are some unsolved problems with the histogram binning, making the interpretation rather difficult.

## Step 2: Run HistFitter to calculate the calibration curves

For obscure reasons (I do not have HistFitter on my office desktop), this is performed in a separate directory:
```bash
$ cd HistFitter/
$ ./HistFitterLoop.py
```
This uses the information in `HistFitter/PaperSRData.dat` (all numbers taken/inferred from the published papers) to produce the CLs calibration curves. There are no command line options. The fit setup is really just the [HistFitter tutorial](https://twiki.cern.ch/twiki/bin/view/AtlasProtected/HistFitterTutorial#Setting_up_a_simple_cut_and_coun), with a slightly complicated procedure to scan the full CLs range efficiently (given that the CLs is a result, not an input).

Processing this step takes something like 6 hours. The output is stored in `HistFitter/CLsFunctions_logCLs.root`, while the _last_ fit for each SR is in `HistFitter/SR*/`. Don't forget to
```bash
$ cd ../
```
before continuing.

## Step 3: Perform the CLs calibration

Now, the CLs values in the `Data_*` directories are calibrated against the truth yields in `SummaryNtuple_STA_sim.root`. This is very fast.
```bash
$ ./CorrelationPlotter.py
```
This creates a directory called `plots_officialMC/` with lots of plots that can be copied straight over to the support note.

The behaviour of `CorrelationPlotter.py` can be altered using command-line options (use `-h` to see them all). The most important ones are:

1. To use the original evgen instead of the official MC for the truth yields, with output in `plots_privateMC/`:
  - `$ ./CorrelationPlotter.py --truthlevel`
2. To compare the real combined CLs values with those from various combinations of the per-SR CLs values, using input from `Data_*_combination` and with output in `productcheck/`:
  - `$ ./CorrelationPlotter.py --productcheck`

## Step 4: Apply the calibration and compute the final results

This applies the calibration performed in the previous step to the `SummaryNtuple_STA_evgen.root` ntuple produced in step 1. To run the code, just do
```bash
$ ./CombineCLs.py --all
```
The output of this script goes into a new directory called `results/`. You'll notice it actually creates a subdirectory, by default called `smallest_officialMC/` - this allows different setups to be tried without them all overwriting each other (more on this later). The files created in this directory are:

* Inputs for the STAs: `STAresults.csv` and `DoNotProcess.txt`. The STAs need **both** files - the latter contains models which have insufficient truth info to process correctly.
* Plots for the support note: `CLsplot.pdf`, `LogCLsplot.pdf`, `NSRplot.pdf`, and `CLresults.root`.
* A LaTeX summary of the main results: `SRcountTable.tex`, which can be directly copied to `SupportNote/Tables/` in the SVN area.
* Some summary information in pickled format: `SRcount.pickle` and `ExclusionCount.pickle`.

The pickle files are a cache of the main results, so that simple changes to the other outputs can be made without rerunning the event loop (ie in seconds rather than minutes). To skip the event loop, simply remove the `--all` argument when you run the script.

Some command line options control exactly how the CLs is computed:

* `-n 10` can be used for testing the event loop, where you only want to run over a few models.
* `--truthlevel` will use the input from `plots_privateMC/` instead of `plots_officialMC` (assuming you already created it!).
* `--strategy twosmallest` will multiply the two smallest CLs values together, instead of just using the smallest (which is the default). Other strategies could be added by making changes to `Combiner.__AnalyseModel` in `CombineCLs.py`.
* `--truncate` replaces all CLs values less than 1e-6 with a value of 1e-6 (after the "strategy" has been applied).
