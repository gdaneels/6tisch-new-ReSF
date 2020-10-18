import sys
import os
import re

def validate(exp_dir):
    """ Validate the experiment to be really successful."""
    error_log = '%s/error.log' % exp_dir # should be empty
    runSim_log = '%s/runSim.log' % exp_dir # should be there, should not be empty
    output_data = '%s/output_cpu0.dat' % exp_dir # should be there, should not be empty
    id_pattern = '*.id.txt' # should only be one file with this id_pattern

    import os
    if not os.path.exists(error_log) or os.path.getsize(error_log) > 0:
        # print exp_dir
        return exp_dir
        # raise 'Error log not there or not zero.'
    if not os.path.exists(runSim_log) or os.path.getsize(runSim_log) == 0:
        # print exp_dir
        return exp_dir
        # raise 'No runSim log or runSim log is empty.'
    if not os.path.exists(output_data) or os.path.getsize(output_data) == 0:
        # print exp_dir
        return exp_dir
        # raise 'No output data or output data is zero.'
    import fnmatch
    count_workers = fnmatch.filter(os.listdir(exp_dir), id_pattern)
    if len(count_workers) > 1:
        # print exp_dir
        # raise 'Multiple workers worked on this.'
        return exp_dir

def get_set_rgx(exp, rgx = ''):
    candidates = set()
    regex_result = re.search(rgx, exp, re.IGNORECASE)
    if regex_result is not None:
        candidates.add(regex_result.group(1))
    else:
        raise 'No %s indicator in experiment dir.' % rgx
    return candidates

if __name__ == '__main__':
    dataDir = str(sys.argv[1])
    failedSeeds = []
    for ix in range(2, len(sys.argv)):
        cmd = "find {0} -ipath *{1}*/output_cpu0.dat".format(dataDir, sys.argv[ix])
        listFiles = os.popen(cmd).read().split("\n")[:-1] # for some reason, there is a trailing whitespace in the list, remove it
        # print "Processing %d file(s) in %s." % (len(listFiles), str(dataDir))
        failed = []
        for datafile in listFiles:
            f = validate(os.path.dirname(datafile))
            if f is not None:
                failed.append(f)

        for fail in failed:
            # print fail
            rgx = '[_\/]+%s_([A-Za-z0-9]+)_' % 'seed'
            candidates = get_set_rgx(fail, rgx)
            failedSeeds += candidates

        # print failedSeeds

    # make it unique
    failedSeeds = list(set(failedSeeds))

    countToRename = 0
    filesToRename = []
    for ix in range(2, len(sys.argv)):
        for s in failedSeeds:
            s = '_%s_' % s
            cmd = "find {0} -ipath *{1}*{2}*/output_cpu0.dat".format(dataDir, sys.argv[ix], s)
            listFiles = os.popen(cmd).read().split("\n")[:-1]
            countToRename += len(listFiles)
            filesToRename += listFiles
            # print listFiles

    for f in filesToRename:
        newName = f.replace('output_cpu0.dat', 'failed_cpu0.dat')
        # print newName
        print f
        os.rename(f, newName)

    print 'Removing all experiments (%d experiments) with following seeds: %s' % (countToRename, str(failedSeeds))