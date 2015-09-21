import os, os.path, subprocess, shlex

'''
Common static functions for SEU fault injection simulations.

This file should be included at the top of script, not imported as module:
execfile('utilities.py')

Copyright (C) 2014-2015 Yi Yuan for the Regents of the University of Texas.
'''

# radix of verilog dumped value (2 = binary, 16 = hexadecimal) 
VERILOG_VALUE_RADIX = 2

# run command with no input/output and return True if return code is 0,
# False otherwise
def run_command(cmdline):
    devnull = open(os.devnull, 'w')
    retcode = subprocess.call(shlex.split(cmdline), stdout=devnull,
        stderr=devnull)
    devnull.close()
    if retcode == 0:
        return True
    else:
        return False

# converts verilog bit string value into python long int
# can have Xs and Zs
def convert_verilog_value(value):
    value_lower = value.lower()
    value_nox_noz = value_lower.replace("x", "0").replace("z", "0")
    return long(value_nox_noz, VERILOG_VALUE_RADIX)

# reads the bit reg_val[bit_pos], where reg_val is verilog bit string
# returns None if bit_pos is out of range, otherwise '0', '1', 'x', or 'z'
def read_reg_bit(reg_val, bit_pos):
    if bit_pos < 0 or bit_pos >= len(reg_val):
        return None
    else:
        return reg_val[len(reg_val) - bit_pos - 1]

# extracts a bit slice of a number
def bit_slice(value, hi=None, lo=0):
    if hi is None:
        return value >> lo
    else:
        hi_mask = (1 << long(hi + 1)) - 1
        return (value & hi_mask) >> lo



#### OS file utilities ####

# does "rm -rf" on shell
def os_rm_dir(args):
    cmdline = "rm -rf " + args
    try:
        print "$", cmdline
        retcode = subprocess.call(cmdline, shell=True)
    except OSError as e:
        print "ERROR: Executing 'rm' failed:", e
        sys.exit(3)
    return 0   #retcode

# does "mv" on shell
def os_mv(args):
    cmdline = "mv " + args
    try:
        print "$", cmdline
        retcode = subprocess.call(cmdline, shell=True)
    except OSError as e:
        print "ERROR: Executing 'mv' failed:", e
        sys.exit(3)
    return 0   #retcode

# does "mkdir"
def os_mkdir(path):
    try:
        print "$ mkdir", path
        os.makedirs(path)
    except OSError as e:
        print "ERROR: Creating dir", path, ":", e
        sys.exit(3)


#### Checkpoint-related functions ####

# finds the checkpoint number corresponding to the given cycle
# returns None if no such checkpoint in the list
def find_checkpoint_num(cycle, checkpoint_list):
    for ckpt in checkpoint_list:
        if ckpt.cycle == cycle:
            return ckpt
    return None

# construct path to target checkpoint
# sample path: .../tgt_7933bc4f-40000-51f2a12d.1.tcheck
def get_tgt_ckpt_path(base_path, ckpt_id, number):
    tcheck_name = 'tgt_%s.%d.tcheck' % (ckpt_id, number)
    pmem_name = 'tgt_%s.%d.pmem' % (ckpt_id, number)
    return (os.path.join(base_path, tcheck_name),
        os.path.join(base_path, pmem_name))

# construct path to DMTCP checkpoint
# sample path: .../ckpt_7933bc4f-40000-51f2a12d_00001/ckpt_simv_7933bc4f-40000-51f2a12d.dmtcp
def get_dmtcp_ckpt_path(base_path, ckpt_id, number):
    pad_number = "%05d" % number
    dir_name = 'ckpt_%s_%s' % (ckpt_id, pad_number)
    file_name = 'ckpt_simv_%s.dmtcp' % ckpt_id
    return os.path.join(base_path, dir_name, file_name)

# read and parse the checkpoint_list file
# each line in file should be like:
# ID=73b96d4e-12819-5318b1d9 Num=2 Cyc=6000 PC=0x40100
# ID, Num, Cyc are required. PC is optional.
# returns list of Checkpoints, or None if error
def read_checkpoint_list(checkpoint_list_filename):
    ckpt_list = list()
    infile = open(checkpoint_list_filename)
    try:
        for line in infile:
            if line.strip() == "":
                continue
            tokens = line.split()
            properties = dict()
            for prop in tokens:
                (name, unused, val) = prop.partition("=")
                try:
                    val = int(val, 0)     # convert to int if possible
                except ValueError:
                    val = val.lower()     # leave as string if not possible
                properties[name.lower()] = val

            if 'id' not in properties:
                print "ERROR: checkpoint listed in '%s' is missing 'ID' " \
                    "property" % checkpoint_list_filename
                print line
                return None

            if 'num' not in properties:
                print "ERROR: checkpoint listed in '%s' is missing 'Num' " \
                    "property" % checkpoint_list_filename
                print line
                return None

            if 'cyc' not in properties:
                print "ERROR: checkpoint listed in '%s' is missing 'Cyc' " \
                    "property" % checkpoint_list_filename
                print line
                return None

            if 'pc' not in properties:
                ckpt = Checkpoint(properties['id'], properties['num'], \
                    properties['cyc'])
            else:
                ckpt = Checkpoint(properties['id'], properties['num'], \
                    properties['cyc'], properties['pc'])
            ckpt_list.append(ckpt)

        return ckpt_list
    except IOError:
        print "ERROR: cannot read checkpoint list file '%s'" % \
            checkpoint_list_filename
        return None
    finally:
        infile.close()

