import os, os.path, sys, re, argparse, time
from circuitSEU import __cal_SER

execfile("utilities.py")

from seu_common import enum, InjectionPointSingle, Checkpoint, \
    FatalSimulationError

'''
Front-end script for doing circuit-level simulation.
'''

#### Global constants ####

# file containing info on saved checkpoints
# must match name used by RTL simulation scripts
CHECKPOINT_LIST_FILE = "checkpoint_list"

# regex to match run ID
RUN_ID_REGEX = re.compile(r'run_(\d+)-0_')

#### Global variables used to save the netlist
#### Modified by Meng Li 28/06/2015
#global __NAME2INDEX, __GATE2INDEX, __DFF2NETLIST, __NODELIST
__NAME2INDEX = dict()
__GATE2INDEX = dict()
__DFF2NETLIST = dict()
__NODELIST = dict()
__MULTI_ERROR = []


#### Command line args ####

# name of test
TEST_NAME = "none"

# injection points file used to do pre-circuit simulation
INJ_PT_FILE = None

# directory where pre-circuit checkpoints are saved
PRE_CIRCUIT_DIR = None

# post-synthesis instances file used for translation
XLATE_INSTANCES_FILE = None

# pre-synthesis register name file used for translation
XLATE_PRESYN_NAME_FILE = None

# directory to put circuit simulation output files
OUTPUT_DIR = None

# log file to save information
LOG_FILE = None

# doing dry run?
IS_DRY_RUN = False

# modified by Meng Li (07/14/2015)
# directory to save post-synthesized netlist
POSTSYN_NETLIST_DIR = None



#### Calls to backend script ####

# Performs experiment for one run.
def __perform_experiment(run_id, inj_pt, golden_ckpt_path):
    print "Golden checkpoint file:", golden_ckpt_path

    output_test_dir = os.path.join(OUTPUT_DIR, TEST_NAME, "run_%d" % run_id)
    print "Output file dir:", output_test_dir

    if IS_DRY_RUN:
        return

    # **** Meng: add call to your script here ****

    # register checkpoint at start of cycle: golden_ckpt_path

    # injection register: inj_pt.reg_name
    # injection bit position: inj_pt.bit_pos
    # pre-syn register name: (inj_pt.reg_name, inj_pt.bit_pos)

    # output directory (for possibility and probability files): output_test_dir

    # translation name file for pre-syn registers: XLATE_PRESYN_NAME_FILE
    # translation instances file: XLATE_INSTANCES_FILE

    # file to save any logs: LOG_FILE

    # modified by Meng Li (14/07/2015)

    [single_bit_error, multi_bit_error] = __cal_SER(golden_ckpt_path, inj_pt.reg_name, inj_pt.bit_pos, XLATE_INSTANCES_FILE, XLATE_PRESYN_NAME_FILE, output_test_dir, POSTSYN_NETLIST_DIR, LOG_FILE, __NAME2INDEX, __GATE2INDEX, __DFF2NETLIST, __NODELIST)
    
    print single_bit_error
    print multi_bit_error

    __MULTI_ERROR.append(single_bit_error)
    __MULTI_ERROR.append(multi_bit_error)

    return


#### Setup for experiment ####

# Reads injection points file.
# Returns a list of InjectionPointSingle objects.
def __read_injection_points(inj_pt_file):
    inj_points = list()
    f = open(inj_pt_file)
    lineno = 1
    try:
        for line in f:
            if line.strip() == "":
                # line is empty, do nothing
                continue
            tokens = line.strip().split()
            if tokens[0].startswith('#') or tokens[0].startswith('/'):
                # comment line, do nothing
                continue
            elif len(tokens) is 3:
                # recognized line, add injection point
                cycle = int(tokens[0])
                register = tokens[1]
                position = int(tokens[2])
                inj_pt = InjectionPointSingle(cycle, register, position)
                inj_points.append(inj_pt)
                print "Read injection point: %s[%d] @ cycle %d" % \
                    (register, position, cycle)
            else:
                # unrecognized line, skip
                print "WARNING: Could not read line", lineno, \
                    "in injection points file", infile, ". Skipping"
            lineno = lineno + 1
    except IOError:
        print "ERROR: Cannot read injection points file", infile
        sys.exit(1)
    finally:
        f.close()

    return inj_points


# Returns a dictionary of checkpoint file names, keyed by run ID.
def __find_precircuit_ckpts(precircuit_dir, test_name):
    print "Finding pre-circuit golden checkpoints..."

    precircuit_ckpts = dict()
    precircuit_test_dir = os.path.join(precircuit_dir, test_name)
    run_dirs = os.listdir(precircuit_test_dir)

    for run_dir in run_dirs:
        run_dir_path = os.path.join(precircuit_test_dir, run_dir)
        if not os.path.isdir(run_dir_path):
            continue

        run_id_match = RUN_ID_REGEX.match(run_dir)
        if run_id_match is None:
            print "Info: skipping pre-circuit test dir '%s'" % run_dir_path
            continue

        # get run _ID
        run_id = int(run_id_match.group(1))

        # read checkpoint list file in run dir
        ckpt_info_file = os.path.join(run_dir_path, CHECKPOINT_LIST_FILE)
        ckpt_info = read_checkpoint_list(ckpt_info_file)

        if ckpt_info is None:
            print "ERROR: checkpoint list file corrupt: '%s'" % ckpt_info_file
            raise FatalSimulationError("checkpoint list corrupt")

        if len(ckpt_info) < 3:
            print "ERROR: checkpoint list file '%s' does not contain at " \
                "least 3 checkpoints" % ckpt_info_file
            raise FatalSimulationError("too few checkpoints in pre-circuit run")

        # get the golden pre-circuit checkpoint path
        # always the 2nd checkpoint in list, because the 1st one is the
        # checkpoint at which VCS restarted
        golden_ckpt = ckpt_info[1]
        golden_ckpt_path = get_tgt_ckpt_path(run_dir_path, \
            golden_ckpt.ckpt_id, golden_ckpt.num)[0]

        if not os.path.isfile(golden_ckpt_path):
            print "ERROR: checkpoint file '%s' for %s (specified in %s) " \
                "does not exist" % \
                (golden_ckpt_path, golden_ckpt, ckpt_info_file)
            raise FatalSimulationError("cannot find checkpoint file")

        # save this run and checkpoint
        print "Found checkpoint for run %d" % run_id
        precircuit_ckpts[run_id] = golden_ckpt_path

    return precircuit_ckpts


#### Misc print functions ####

def __print_run_header(run_id, inj_pt):
    print
    print "==========================================="
    print "Run ID: %d" % run_id
    print "==========================================="
    if IS_DRY_RUN:
        print "This is a dry run"
    print "Starting circuit simulation:"
    print "Injection into: %s [%d]" % (inj_pt.reg_name, inj_pt.bit_pos)


# Prints out current time
def print_time():
    time_str = time.strftime('%Y-%m-%d %H:%M:%S')
    print "Current time is: %s (%d)" % (time_str, time.time())



#### Command line argument parsing and checking ####

# Parse command line arguments
def __parse_arguments():
    parser = argparse.ArgumentParser(description="Runs circuit-level fault " \
        "simulations.")
    parser.add_argument('test_name', help="name of test (directory under " \
        "target_checkpoints or dmtcp_checkpoints)")
    parser.add_argument('injection_pt_file', help="fault injection points file")
    parser.add_argument('-d', '--ckpt_dir', default="./precircuit_test", \
        help="directory of checkpoints saved from pre-circuit simulation " \
        "(default ./precircuit_test)")
    parser.add_argument('--instances', default="../postsyn/instances.txt", \
        metavar="FILE", help="instances file for name translation (default " \
        "../postsyn/instances.txt)")
    parser.add_argument('--presyn-names', default="../tgt.sizes", \
        metavar="FILE", help="pre-synthesis register names file (default " \
        "tgt.sizes)")

    # modified by Meng Li (07/14/2015) 
    parser.add_argument('--postsyn-netlist', default="../postsyn/netlist", \
        help="directory of post-synthesized netlist (default ../postsyn/netlist)")

    parser.add_argument('-o', '--out_dir', default="./postcircuit_test", \
        help="directory to save fault outcome files (default " \
        "./postcircuit_test")
    parser.add_argument('-l', '--log', default="circuit_sim.log", \
        help="simulation log file (default circuit_sim.log)")
    parser.add_argument('--dry-run', action="store_true", \
        help="perform dry run instead of actually running circuit simulator")
    return parser.parse_args()


# Check all arguments are in order
def __check_arguments():
    has_error = False

    # check directories exist where expected
    precircuit_test_dir = os.path.join(PRE_CIRCUIT_DIR, TEST_NAME)
    if not os.path.isdir(precircuit_test_dir):
        print "ERROR: cannot find pre-circuit test dir '%s'" % \
            precircuit_test_dir
        has_error = True

    # check injection point file is there
    if not os.path.isfile(INJ_PT_FILE):
        print "ERROR: cannot find injection point file '%s'" % INJ_PT_FILE
        has_error = True

    if has_error:
        sys.exit(2)

    # create output dir if not existing
    if not os.path.isdir(OUTPUT_DIR):
        print "Info: did not find existing output dir, creating one:", \
            OUTPUT_DIR
        os_mkdir(OUTPUT_DIR)

    # if log file exists, move to <log file>.old
    if os.path.isfile(LOG_FILE):
        print "Info: found existing log file '%s', moved to '%s.old'" % \
            (LOG_FILE, LOG_FILE)
        os_mv(LOG_FILE + " " + LOG_FILE + ".old")


if __name__ == "__main__":

    
    # parse arguments
    namespace = __parse_arguments()

    TEST_NAME = namespace.test_name
    INJ_PT_FILE = namespace.injection_pt_file
    PRE_CIRCUIT_DIR = namespace.ckpt_dir
    XLATE_INSTANCES_FILE = namespace.instances
    XLATE_PRESYN_NAME_FILE = namespace.presyn_names

    # modified by Meng Li (07/24/2015)
    POSTSYN_NETLIST_DIR = namespace.postsyn_netlist

    OUTPUT_DIR = namespace.out_dir
    LOG_FILE = namespace.log
    IS_DRY_RUN = namespace.dry_run

    print "=== Running experiments ==="
    print "Test name                :", TEST_NAME
    print "Dry run only             :", IS_DRY_RUN
    print "Fault injection list     :", INJ_PT_FILE
    print "Pre-circuit checkpoints  :", PRE_CIRCUIT_DIR
    print "Xlate instances file     :", XLATE_INSTANCES_FILE
    print "Xlate pre-syn name file  :", XLATE_PRESYN_NAME_FILE
    print "Post-synthesized netlist :", POSTSYN_NETLIST_DIR
    print "Output directory         :", OUTPUT_DIR
    print "Log file                 :", LOG_FILE
    print

    __check_arguments()

    # read injection points file
    injection_pts = __read_injection_points(INJ_PT_FILE)
    print

    # go through precircuit directory and find checkpoints
    golden_ckpts = __find_precircuit_ckpts(PRE_CIRCUIT_DIR, TEST_NAME)

    if len(golden_ckpts) != len(injection_pts):
        print "WARNING: number of injection points (%d) does not match " \
            "number of golden checkpoints found (%d)" % \
            (len(injection_pts), len(golden_ckpts))
        print "WARNING: possible mismatch of checkpoints and injection point " \
            "file"

    print "==========================================="
    print
    print "Start time:",
    print_time()

    start_time = time.time()

    sys.stdout.flush()

    for (run_id, inj_pt) in enumerate(injection_pts):
        __print_run_header(run_id, inj_pt)

        if run_id not in golden_ckpts:
            print "WARNING: no golden checkpoint found for run %d, skipping" % \
                run_id
            continue

        golden_ckpt_path = golden_ckpts[run_id]

# each time only inject fault to one register?

        __perform_experiment(run_id, inj_pt, golden_ckpt_path)

    print "Portion of multi-bit error for each simulation run:"
    single_bit_total = sum(__MULTI_ERROR[0::2])
    multi_bit_total = sum(__MULTI_ERROR[1::2])
    print multi_bit_total / (single_bit_total + multi_bit_total)

    print "\n==========================================="
    print "End time:",
    print_time()

    print "Total simulation time is ", time.time() - start_time 

