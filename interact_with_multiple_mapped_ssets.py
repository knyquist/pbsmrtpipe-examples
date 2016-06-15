#!/usr/bin/env python

import sys
import logging
import csv

from pbcommand.models import FileTypes
from pbcommand.cli import registry_builder, registry_runner
from pbcore.io import openDataSet

log = logging.getLogger(__name__)

NAMESPACE = "pbsmrtpipe_examples"

# the 'Driver' exe needs to be your your path. The first arg will be the path
# to the resolved tool contract.
#
# Note, When the tool contract is emitted, the 'run-rtc'
# will automatically be added to the driver.
#
# When this commandline tool is invoked, it will be of the form:
# comparative_plots.py run-rtc /path/to/resolved-tool-contract.py
registry = registry_builder(NAMESPACE, "interact_with_multiple_mapped_ssets.py" )


def _example_main( input_file, output_file, **kwargs ):
    """
    This func should be imported from your python package.

    This should have *no* dependency on the pbcommand IO, such as the RTC/TC models.
    """

    # This is just for test purposes
    log.info("Running example main with {i} {o} kw:{k}".format(i=input_file,
                                                               o=output_file,
                                                               k=kwargs))

    # Try to open input CSV. Iterate through mapped ssets
    dsets = []
    log.info( "Attempting to open input CSV" )
    with open( input_file, 'rb' ) as csvfile:
        reader = csv.reader( csvfile )
        for mapped_sset in reader:
            if mapped_sset[0] is not '#': # check for a commented line (like a header)
                dsets.append( mapped_sset )

    # write dset
    with open( output_file, 'wb' ) as csvfile:
        writer = csv.writer( csvfile )
        for dset in dsets:
            writer.writerow( dset )

    return 0


@registry( "dev_interact_with_multiple_mapped_ssets", "0.2.2", ( FileTypes.CSV, ), ( FileTypes.CSV, ), nproc = 1, options = dict( alpha = 1234) )
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
    return _example_main( rtc.task.input_files[0], rtc.task.output_files[0], nproc = rtc.task.nproc, alpha = alpha )


if __name__ == '__main__':
    sys.exit(registry_runner(registry, sys.argv[1:]))


