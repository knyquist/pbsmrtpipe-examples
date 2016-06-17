#!/usr/bin/env python

import os
import sys
import logging
import csv
import random
import pickle

import accuracy_plots

from pbcommand.models import FileTypes
from pbcommand.models.report import Report, PlotGroup, Plot
from pbcommand.cli import registry_builder, registry_runner
from pbcore.io import openDataSet

import plotly
from plotly.graph_objs import *
from plotly.offline import download_plotlyjs, plot

from selenium import webdriver
phantomjs_driver = webdriver.PhantomJS(executable_path='/home/knyquist/local/phantomjs-2.1.1-linux-x86_64/bin/phantomjs')



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
    NAMESPACE, "mh_toy.py")


def _get_dset_paths(file):
    dset_paths = []
    log.info("Attempting to open dset paths CSV")
    with open(file, 'rb') as csvfile:
        reader = csv.reader(csvfile)
        for mapped_sset in reader:
            # check for a commented line (like a header)
            if mapped_sset[0][0] is not '#':
                absolute_filename = mapped_sset[0]
                dset_paths.append(absolute_filename)
    return dset_paths

def _get_plots_to_generate(file):
    plots_to_generate = []
    log.info("Attempting to open plots CSV")
    with open(file, 'rb') as csvfile:
        reader = csv.reader(csvfile)
        for plot_name in reader:
            if plot_name[0][0] is not '#':
                if int(plot_name[1]) == 1:
                    name = plot_name[0]
                    plots_to_generate.append(name)
    return plots_to_generate

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

    # Open dset CSV. Store absolute path of each alignment set.
    dset_paths = _get_dset_paths(input_file[0])

    # Open plots CSV. Store names of plots to produce.
    plots_to_generate = _get_plots_to_generate(input_file[1])

    dsets_kpis = {}
    for f in dset_paths:
        dset = openDataSet(f)
        subsampled_dset = _subsample_alignments(dset)
        dsets_kpis[f] = _getKPIs(dset, subsampled_dset)

    figures = []
    if 'accuracy_vs_readlength' in plots_to_generate:
        # figure tuple has form (plot_group_id, plot_id, figure)
        figures.append(('accuracy', 'accuracy_vs_readlength', accuracy_plots._plot_accuracy_vs_readlength(dsets_kpis)))
    if 'accuracy' in plots_to_generate:
        figures.append(('accuracy', 'accuracy', accuracy_plots._plot_accuracy_distribution(dsets_kpis)))
    if 'accuracy_boxplot' in plots_to_generate:
        figures.append(('accuracy', 'accuracy_boxplot', accuracy_plots._plot_accuracy_boxplots(dsets_kpis)))

    all_plots = {} # dictionary of plots. keys are groups
    for plot_group, plot_id, fig in figures:
        if plot_group not in all_plots.keys():
            all_plots[plot_group] = []
        plot(fig, filename='{i}.html'.format(i=plot_id), show_link=False, auto_open=False)
        phantomjs_driver.set_window_size(1920, 1080)
        phantomjs_driver.get('{i}.html'.format(i=plot_id))
        phantomjs_driver.save_screenshot('{i}.png'.format(i=plot_id))
        phantomjs_driver.get('{i}.html'.format(i=plot_id))
        phantomjs_driver.save_screenshot('{i}_thumb.png'.format(i=plot_id))
        os.remove('{i}.html'.format(i=plot_id))
        plot_path = '{i}.png'.format(i=plot_id)
        thumb_path = '{i}_thumb.png'.format(i=plot_id)
        all_plots[plot_group].append(Plot(plot_id, plot_path, thumbnail=thumb_path))

    plot_groups = []
    for plot_group_title in all_plots.keys():
        plot_group = PlotGroup( plot_group_title, plots=all_plots[plot_group_title])
        plot_groups.append(plot_group) 

    report = Report('mh_toy', tables=(), plotgroups=plot_groups, attributes=())
    report.write_json( output_file )

    return 0


@registry("dev_mh_toy", "0.2.2", (FileTypes.CSV, FileTypes.CSV), (FileTypes.REPORT, ), nproc=1, options=dict(alpha=1234))
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
    return _example_main(rtc.task.input_files, rtc.task.output_files[0], nproc=rtc.task.nproc, alpha=alpha)


if __name__ == '__main__':
    sys.exit(registry_runner(registry, sys.argv[1:]))
