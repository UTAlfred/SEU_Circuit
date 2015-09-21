import sys, os, os.path, re

'''
Translates between pre-synthesis Verilog register names and post-synthesis
netlist names.

Pre-synthesis Verilog register name is a tuple of the register name with full
RTL hierarchy, and an integer of the bit position.
('cmp_top.iop.sparc0.exu.div.yreg.dff_yreg_thr0.q', 0)

Post-synthesis netlist name is a tuple of two strings representing the
instance name and the name of the DFF inside the synthesized module,
respectively, such as
('cmp_top.iop.sparc0.exu', 'div_yreg_dff_yreg_thr0_q_reg[0]')

Author: Yi Yuan <yi.yuan@utexas.edu>
Copyright (C) 2015 Yi Yuan for the Regents of the University of Texas.
'''

####
# Global variables
####


####
# Static (private) variables
####
# mapping of DFF list names to module instance names
__INSTANCES = dict()

# mapping of DFF list names to DFFs in that module
__POSTSYN_DFFS = dict()

# mapping of DFF list names to RTL register names (module name truncated) in
# that module
__PRESYN_DFFS = dict()

# file name supplied for instances file
__INSTANCES_FILENAME = ''


####
# Public functions
####

# Finds the post-synthesis netlist name corresponding to the given pre-
# synthesis Verilog name.
# Returns post-synthesis netlist name, or None if no match found.
def pre2post(presyn_name):
    if not isinstance(presyn_name, tuple):
        raise TypeError("pre-synthesis name must be of type 'tuple'")
    if len(presyn_name) != 2:
        raise IndexError("pre-synthesis name does not have two elements")

    rtl_reg_name, bit_pos = presyn_name

    # find module instance name and the DFF list for it
    instance = __find_instance(rtl_reg_name)
    if instance is None:
        return None
    (instance_name, dff_list) = instance

    # strip module name and the "." between module name and register name
    module_reg_name = rtl_reg_name[len(instance_name)+1:]

    # find DFF name inside module
    dff_name = __find_postsyn_reg(dff_list, module_reg_name, bit_pos)
    if dff_name is None:
        return None
    else:
        return (instance_name, dff_name)


# Finds the pre-synthesis Verilog name corresponding to the given post-
# synthesis netlist name.
# Returns pre-synthesis Verilog name, or None if no match found.
def post2pre(postsyn_name):
    if not isinstance(postsyn_name, tuple):
        raise TypeError("post-synthesis name must be of type 'tuple'")
    if len(postsyn_name) != 2:
        raise IndexError("post-synthesis name does not have two elements")

    instance_name, dff_name = postsyn_name

    dff_list = __find_dff_list(instance_name)
    module_presyn_reg = __find_presyn_reg(dff_list, dff_name)

    if module_presyn_reg is None:
        return None
    else:
        module_reg_name, bit_pos = module_presyn_reg
        rtl_reg_name = instance_name + "." + module_reg_name
        return (rtl_reg_name, bit_pos)


# Initialize this translator by providing:
# 1) name of file containing information for all synthesized modules and their
#    instances in the design (i.e. "instances file"),
# 2) name of file containing all Verilog register names.
# In addition, files containing lists of post-synthesis flip-flop names are
# expected to be in the same directory as the instances file.
def init(instances_filename, verilog_reg_filename):
    __read_instances_file(instances_filename)
    __read_dff_files()

    rtl_reg_dict = __read_rtl_reg_file(verilog_reg_filename)
    __populate_rtl_reg(rtl_reg_dict)



####
# Private functions
####

# Reads instances file and populates __INSTANCES dictionary.
def __read_instances_file(instances_filename):
    global __INSTANCES, __INSTANCES_FILENAME

    __INSTANCES_FILENAME = instances_filename

    if not os.path.isfile(instances_filename):
        print "ERROR: cannot find instances file '%s'" % instances_filename
        raise IOError("cannot find file '%s'" % instances_filename)

    infile = open(instances_filename)
    expr = ''
    try:
        for line in infile:
            expr = expr + line
        __INSTANCES = eval(expr)
    except IOError:
        print "ERROR: cannot read instances file '%s'" % instances_filename
        raise
    finally:
        infile.close()


# Reads DFF files for every synthesized netlist in __INSTANCES.
def __read_dff_files():
    if not isinstance(__INSTANCES, dict):
        print "ERROR: instances file did not produce a dictionary"
        raise TypeError("instance file does not contain a dictionary")

    for dff_file in __INSTANCES.keys():
        __read_dff_file(dff_file)


# Reads a DFF file for one synthesized module.
# DFF file should be found in the same directory as the instances file.
def __read_dff_file(filename):
    global __POSTSYN_DFFS

    base_dir = os.path.dirname(__INSTANCES_FILENAME)
    dff_path = os.path.join(base_dir, filename)

    if not os.path.isfile(dff_path):
        print "ERROR: cannot find DFF file '%s' listed in instances file" % \
            filename
        print "       ensure path is correct: '%s'" % dff_path
        raise IOError("cannot find file '%s'" % dff_path)

    __POSTSYN_DFFS[filename] = set()
    infile = open(dff_path)
    try:
        for line in infile:
            dff_name = line.strip()
            if dff_name != "" and not dff_name.startswith("#") and \
                not dff_name.startswith("/"):
                __POSTSYN_DFFS[filename].add(dff_name)
    except IOError:
        print "ERROR: cannot read DFF file '%s'" % dff_path
        raise
    finally:
        infile.close()


# Reads the file containing RTL register names (i.e. "tgt.sizes"), and
# returns a list of all RTL registers.
def __read_rtl_reg_file(filename):
    if not os.path.isfile(filename):
        print "ERROR: cannot find RTL register file '%s'" % filename
        raise IOError("cannot find file '%s'" % filename)

    infile = open(filename)
    expr = '{'
    try:
        for line in infile:
            expr = expr + line
    except IOError:
        print "ERROR: cannot read RTL register file '%s'" % filename
        raise
    finally:
        infile.close()

    expr = expr + '}'
    return eval(expr)


# Populates __PRESYN_DFFS based on register dictionary read from file.
def __populate_rtl_reg(rtl_reg_dict):
    global __PRESYN_DFFS

    if not isinstance(rtl_reg_dict, dict):
        raise TypeError("RTL register file does not contain a dictionary")

    for rtl_reg_name in rtl_reg_dict.iterkeys():
        # find instance and module (DFF list) of given register
        instance = __find_instance(rtl_reg_name)
        if instance is None:
            key = None
            module_reg_name = rtl_reg_name
        else:
            key = instance[1]
            module_reg_name = rtl_reg_name[len(instance[0])+1:]

        # insert into list of registers for module
        if key not in __PRESYN_DFFS:
            __PRESYN_DFFS[key] = set()
        __PRESYN_DFFS[key].add(module_reg_name)


# Finds the name of the most specific synthesized module that contains the
# given pre-synthesis RTL register name, and the name of the DFF list for that
# module.
# Returns a tuple of (name of instance, name of DFF list), or None if no
# synthesized modules contain the given register.
def __find_instance(rtl_reg_name):
    chosen_dff = ""
    chosen_instance = ""

    for (dff_list, instance_list) in __INSTANCES.iteritems():
        for instance_name in instance_list:
            if rtl_reg_name.startswith(instance_name):
                if len(chosen_instance) < len(instance_name):
                    chosen_instance = instance_name
                    chosen_dff = dff_list

    if chosen_instance == "":
        return None
    else:
        return (chosen_instance, chosen_dff)

# Finds the DFF list for the given module instance name.
def __find_dff_list(instance_name):
    for (dff_list, instance_list) in __INSTANCES.iteritems():
        if instance_name in instance_list:
            return dff_list
    return None


# Finds the name of the flip-flop in the given post-synthesis DFF netlist
# that matches the given register name and bit position.
# Returns name of flip-flop in post-synthesis netlist, or None if no matches
# found.
def __find_postsyn_reg(dff_list, module_reg_name, bit_pos):
    module_dffs = __POSTSYN_DFFS[dff_list]

    # add bit position to register name
    match_name1 = "%s[%d]" % (module_reg_name, bit_pos)

    # look for exact match
    if match_name1 in module_dffs:
        return match_name1

    # change all "." to "_" and look for match
    match_name2 = match_name1.replace(".", "_")
    if match_name2 in module_dffs:
        return match_name2

    # add "_reg" to name and look for match
    # note, "_reg" is added before the bit position, e.g. "xyz_reg[123]"
    # TODO: handle multi-dimensional arrays
    parts = match_name2.partition("[")
    match_name3 = parts[0] + "_reg" + parts[1] + parts[2]
    if match_name3 in module_dffs:
        return match_name3

    # give up
    return None


# Finds the name of the RTL register and bit position in the given module
# that matches the given DFF name.
# Returns RTL register name in the module and bit position, or None if no
# matches found.
def __find_presyn_reg(dff_list, dff_name):
    module_regs = __PRESYN_DFFS[dff_list]

    # split the name between register name and bit position
    # TODO: handle multi-dimensional arrays
    match_bit_pos = re.match(r'(.*)\[(\d+)]', dff_name)
    if match_bit_pos is None:
        bit_pos = 0
        dff_noindex_name = dff_name
    else:
        bit_pos = int(match_bit_pos.group(2))
        dff_noindex_name = match_bit_pos.group(1)

    # look for exact match
    if dff_noindex_name in module_regs:
        return (dff_noindex_name, bit_pos)

    # change all "." to "_" and look for match
    for module_reg_name in module_regs:
        match_name1 = module_reg_name.replace(".", "_")
        if match_name1 == dff_noindex_name:
            return (module_reg_name, bit_pos)

    # add "_reg" in name and look for match
    for module_reg_name in module_regs:
        match_name1 = module_reg_name.replace(".", "_")
        match_name2 = match_name1 + "_reg"
        if match_name2 == dff_noindex_name:
            return (module_reg_name, bit_pos)

    # give up
    return None


# checks built-in tests when running as script
def __check_test(test_case, actual, expected):
    print test_case, "=>", actual
    if actual != expected:
        print "FAILED, expected", expected
    else:
        print "PASSED"


# main - test cases
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print "Usage: python xlate_core.py [instances file] [RTL reg file]"
        sys.exit(1)

    instance_file = sys.argv[1]
    verilog_reg_file = sys.argv[2]

    init(instance_file, verilog_reg_file)

    print __INSTANCES_FILENAME
    print __INSTANCES

    # test pre2post()
    test_case = ("cmp_top.iop.sparc0.exu.bypass.dfill_data_dff.q", 31)
    actual = pre2post(test_case)
    expected = ("cmp_top.iop.sparc0.exu", "bypass_dfill_data_dff_q_reg[31]")
    __check_test(test_case, actual, expected)

    test_case = ("cmp_top.iop.sparc0.exu.div.yreg.dff_yreg_thr0.q", 0)
    actual = pre2post(test_case)
    expected = ("cmp_top.iop.sparc0.exu", "div_yreg_dff_yreg_thr0_q_reg[0]")
    __check_test(test_case, actual, expected)

    test_case = ("cmp_top.iop.sparc0.exu.rml.rstff.q", 0)
    actual = pre2post(test_case)
    expected = ("cmp_top.iop.sparc0.exu", "rml_rstff_q_reg[0]")
    __check_test(test_case, actual, expected)

    test_case = ("cmp_top.iop.sparc0.exu.rml.rstff.q", 1)
    actual = pre2post(test_case)
    expected = None
    __check_test(test_case, actual, expected)

    # test post2pre()
    test_case = ("cmp_top.iop.sparc0.exu", "bypass_dfill_data_dff_q_reg[31]")
    actual = post2pre(test_case)
    expected = ("cmp_top.iop.sparc0.exu.bypass.dfill_data_dff.q", 31)
    __check_test(test_case, actual, expected)

    test_case = ("cmp_top.iop.sparc0.exu", "div_yreg_dff_yreg_thr0_q_reg[0]")
    actual = post2pre(test_case)
    expected = ("cmp_top.iop.sparc0.exu.div.yreg.dff_yreg_thr0.q", 0)
    __check_test(test_case, actual, expected)

    test_case = ("cmp_top.iop.sparc0.exu", "rml_rstff_q_reg[0]")
    actual = post2pre(test_case)
    expected = ("cmp_top.iop.sparc0.exu.rml.rstff.q", 0)
    __check_test(test_case, actual, expected)

    test_case = ("cmp_top.iop.sparc0.exu", "div_yreg_dff_yreg_thr4_q_reg[0]")
    actual = post2pre(test_case)
    expected = None
    __check_test(test_case, actual, expected)


