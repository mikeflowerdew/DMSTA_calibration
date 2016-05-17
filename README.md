# DMSTA_calibration
Package for the calibration of CL values vs yield for the ATLAS dark matter STA project

A secondary goal of this repository is to learn a little more about how git works. Eventually the code will probably need to move to the ATLAS SVN area, as the real data cannot be placed on github.

The main script in this package is CorrelationPlotter.py. This holds the infrastructure to plot the correlations between CL values and the truth yield. As the input file format is not yet known, the plotting code is kept separate from the read-in code. At the moment, only dummy read-in classes are available.

To run the main analysis, just try
```bash
$ ./CorrelationPlotter.py
```
To combine the end results (ie apply the CLs calibration to truth-level events) do
```bash
$ ./CombineCLs.py
```
Various other scripts exist, look for the executable files and try `-h`.

# Complete workflow

## Prerequisites

First, check out the repo
```bash
$ git clone https://github.com/mikeflowerdew/DMSTA_calibration
$ cd DMSTA_calibration/
```

On top of the git repository, you also need to have a directory called `Data_Yields` (located within `DMSTA_calibration`). The contents are large, so personally I make this a soft link to a data-file area. It needs to contain:
1. D3PDs.txt, with one simulated dataset per line.
2. SummaryNtuple_STA_all_version4.root (or change the name in `SkimYieldFile.py` if yours is different).

## Step 1: Process the summary ntuple

First, the summary ntuple is to be split and drastically reduced in size (else later processing steps will be _very_ slow). The command to do this is
```bash
$ ./SkimYieldFile.py
```
This creates three skimmed files in `Data_Yields/`:
1. SummaryNtuple_STA_sim.root, with just the 500 simulated models (deduced from `D3PDs.txt`).
2. SummaryNtuple_STA_evgen.root, with the ~460k models with evgen (deduced from the ntuple itself).
3. SummaryNtuple_STA_noevgen.root, containing all models not in SummaryNtuple_STA_evgen.root.
This script has no command-line options: in principle it is a "do once and forget" script.

## Step 2: Run HistFitter to calculate the calibration curves

## Step 3: Perform the CLs calibration

Now, the CLs values in the `Data_*` directories are calibrated against the truth yields in SummaryNtuple_STA_sim.root. This is very fast.
```bash
$ ./CorrelationPlotter.py
```
This creates a directory called `plots_officialMC` with lots of plots that can be copied straight over to the support note.

The behaviour of `CorrelationPlotter.py` can be altered using command-line options (use `-h` to see them all). The most important ones are:
1. To use the original evgen instead of the official MC for the truth yields:
```bash
$ ./CorrelationPlotter.py --truthlevel
```
In this case, the output is in `plots_privateMC`.
2. To compare the real combined CLs values with those from various combinations of the per-SR CLs values, try
```bash
$ ./CorrelationPlotter.py --productcheck
```
This uses the files in `Data_*_combination`, and produces results in `productcheck/`.

## Step 4: Apply the calibration and compute the final results

