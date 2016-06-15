#!/usr/bin/env python

import sys
import logging
import csv
import random
import pickle

sys.path.append('/mnt/usmp-data3/scratch/Labs/Kristofor/python/mhpbb')
import milhouseBAM as mh

from pbcommand.models import FileTypes
from pbcommand.cli import registry_builder, registry_runner
from pbcore.io import openDataSet

import plotly
from plotly.graph_objs import *
from plotly.offline import download_plotlyjs, plot


log = logging.getLogger(__name__)

NAMESPACE = "pbsmrtpipe_examples"

# the 'Driver' exe needs to be in your path. The first arg will be the path
# to the resolved tool contract.
#
# Note, When the tool contract is emitted, the 'run-rtc'
# will automatically be added to the driver.
#
# When this commandline tool is invoked, it will be of the form:
# comparative_plots.py run-rtc /path/to/resolved-tool-contract.py
registry = registry_builder(
    NAMESPACE, "interact_with_multiple_mapped_ssets.py")


def _get_dset_paths(input_file):
    dset_paths = []
    log.info("Attempting to open input CSV")
    with open(input_file, 'rb') as csvfile:
        reader = csv.reader(csvfile)
        for mapped_sset in reader:
            # check for a commented line (like a header)
            if mapped_sset[0][0] is not '#':
                absolute_filename = mapped_sset[0]
                dset_paths.append(absolute_filename)
    return dset_paths


def _subsample_alignments(mapped_subreadset, num=1000):
    ss = random.sample(mapped_subreadset, num)
    return ss


def _getKPIs(mapped_sset, subsampled_mapped_sset):
    """
    Retrieve the KPIs for a single mapped sset in a dictionary structure.
    """
    log.info("Retrieving metrics from aligned subread set")
    data = {}
    data['holenumber'] = []
    data['readlength'] = []
    data['templatespan'] = []
    data['insertions'] = []
    data['deletions'] = []
    data['mismatches'] = []
    data['accuracy'] = []
    data['IPD'] = []

    for aln in subsampled_mapped_sset:
        data['holenumber'].append(aln.HoleNumber)
        data['readlength'].append(float(aln.readEnd - aln.readStart))
        data['templatespan'].append(
            float(aln.referenceEnd - aln.referenceStart))
        data['insertions'].append(float(aln.nIns) / data['readlength'][-1])
        data['deletions'].append(float(aln.nDel) / data['readlength'][-1])
        data['mismatches'].append(float(aln.nMM) / data['readlength'][-1])
        error_rate = (aln.nIns + aln.nDel + aln.nMM) / data['readlength'][-1]
        data['accuracy'].append(1 - error_rate)
        data['IPD'].append(aln.IPD())

    data['total nreads'] = len(mapped_sset)

    return data


def _example_main(input_file, output_file, **kwargs):
    """
    This func should be imported from your python package.

    This should have *no* dependency on the pbcommand IO, such as the RTC/TC models.
    """

    # This is just for test purposes
    log.info("Running example main with {i} {o} kw:{k}".format(i=input_file,
                                                               o=output_file,
                                                               k=kwargs))

    # Open input CSV. Store absolute path of each alignment set.
    dset_paths = _get_dset_paths(input_file)

    dsets_kpis = {}
    for f in dset_paths:
        dset = openDataSet(f)
        subsampled_dset = _subsample_alignments(dset)
        dsets_kpis[f] = _getKPIs(dset, subsampled_dset)

    pickle.dump(dsets_kpis, open(output_file, 'wb'))

    # save a simple plot
    traces = []; titles = []; max_rl = 0
    for key in dsets_kpis.keys():
        rl = dsets_kpis[key]['readlength']
        acc = dsets_kpis[key]['accuracy']
        if max(rl) > max_rl:
            max_rl = max(rl)
        trace = Scatter(
                x = rl,
                y = acc,
                mode='markers'
        )
        traces.append( trace )
        titles.append( str(key) )
    rows = len( traces )
    fig = plotly.tools.make_subplots(rows=rows, cols=1,
                                     subplot_titles=tuple(titles))
    for row,trace in enumerate(traces):
        fig.append_trace(trace, row+1, 1) # convert from zero-based to one-based indexing
        fig['layout']['xaxis'+str(row+1)]['tickfont'].update(size=16)
        fig['layout']['yaxis'+str(row+1)]['tickfont'].update(size=16)
        fig['layout']['xaxis'+str(row+1)].update(range=[0,max_rl])

    fig['layout']['yaxis'+str(rows/2+1)].update(title='accuracy')
    fig['layout']['xaxis'+str(rows)].update(title='readlength (bases)')
    fig['layout']['font']['size'] = 20

    plot(fig, filename='test-plot.html')

    return 0


@registry("dev_interact_with_multiple_mapped_ssets", "0.2.2", (FileTypes.CSV, ), (FileTypes.PICKLE, ), nproc=1, options=dict(alpha=1234))
def run_rtc(rtc):
    """
    Example Task for grabbing data from multiple mapped ssets. Single input CSV contains path to each mapped sset.
    Takes a mapped SubreadSet XML file as input and writes a csv file with mock data.
    """
    # The above docstring will be used as the Task/ToolContract Description

    log.info("Got RTC task options {t}".format(t=rtc.task.options))
    log.info("Got nproc {n}".format(n=rtc.task.nproc))

    # The Task options are now accessible via global identifier
    alpha = rtc.task.options['pbsmrtpipe_examples.task_options.alpha']
    return _example_main(rtc.task.input_files[0], rtc.task.output_files[0], nproc=rtc.task.nproc, alpha=alpha)


if __name__ == '__main__':
    sys.exit(registry_runner(registry, sys.argv[1:]))
