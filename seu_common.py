'''
Common classes for SEU fault injection simulations.

Copyright (C) 2014-2015 Yi Yuan for the Regents of the University of Texas.
'''

# support for enums
# from http://stackoverflow.com/a/1695250
def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    reverse = dict((value, key) for key, value in enums.iteritems())
    enums['reverse_mapping'] = reverse
    return type('Enum', (), enums)


# constants for checkpoint comparison and simulation results
RESULT = enum(
    # checkpoint comparison results
    'CMP_FULL_MATCH',       # all registers and DRAM match [OBSOLETE]
    'CMP_NONARCH_MATCH',    # non-SW-visible registers match [OBSOLETE]
    'CMP_MISMATCH',         # no match [OBSOLETE]
    'CMP_UNDETERMINED',     # fault outcome cannot be determined yet
    # simulation results
    'SIM_MASKED',           # fault masked
    'SIM_MEM_MATCH',        # DRAM match, but registers do not, possibly masked
    'SIM_SDC',              # silent data corruption
    'SIM_RAISE_ABS',        # raise abstraction to ISA level
    'SIM_INF_LOOP',         # program runtime limit exceeded
    'SIM_DETECTED',         # error detected (bad trap, crash, etc.)
    # other
    'ERROR',                # error when trying to do comparison (but not fatal)
    'NONE',                 # no result (did not compare)
)


# fault specification class
# specifies the faulty value in a register using one of:
# - faulty bit position (integer of bit position, 1 bit-flip only)
# - faulty mask (bit string mask of bits that are flipped)
# - new value (bit string of new value, replacing existing register value)
class FaultSpec:
    def __init__(self, fault_bit_pos=None, fault_mask=None, new_val=None):
        if fault_bit_pos is not None:
            if fault_mask is not None or new_val is not None:
                raise TypeError("FaultSpec: only one of fault_bit_pos, " \
                    "fault_mask, and new_val can be specified.")
            if not isinstance(fault_bit_pos, (int, long)):
                raise TypeError("FaultSpec: fault_bit_pos must be an int.")
            mask = '1' + '0' * fault_bit_pos
        if fault_mask is not None:
            if fault_bit_pos is not None or new_val is not None:
                raise TypeError("FaultSpec: only one of fault_bit_pos, " \
                    "fault_mask, and new_val can be specified.")
            if not isinstance(fault_mask, basestring):
                raise TypeError("FaultSpec: fault_mask must be a bit string.")
            mask = fault_mask
        if new_val is not None:
            if fault_bit_pos is not None or fault_mask is not None:
                raise TypeError("FaultSpec: only one of fault_bit_pos, " \
                   "fault_mask, and new_val can be specified.")
            if not isinstance(new_val, basestring):
                raise TypeError("FaultSpec: new_val must be a bit string.")
        if fault_bit_pos is None and fault_mask is None and new_val is None:
            mask = '0'          # no fault

        self.fault_mask = mask
        self.new_val = new_val

    def __str__(self):
        if self.fault_mask is not None:
            return "bf:" + self.fault_mask
        else:
            return "nv:" + self.new_val

    def __repr__(self):
        if self.fault_mask is not None:
            return "FaultSpec(fault_mask=%s)" % repr(self.fault_mask)
        else:
            return "FaultSpec(new_val=%s)" % repr(self.new_val)

    # returns the type of fault specification: "bf" for bit flip, "nv" for
    # new value
    def get_spec_type(self):
        if self.fault_mask is not None:
            return "bf"
        else:
            return "nv"

    # returns the bit string for this fault spec (can be bit flip mask or
    # new value)
    def get_fault_string(self):
        if self.fault_mask is not None:
            return self.fault_mask
        else:
            return self.new_val


# injection point class
class InjectionPoint:
    # cycle - cycle time of injection
    # affected_reg_list - list of (reg name, fault spec obj) tuples
    def __init__(self, cycle, affected_reg_list):
        if not isinstance(affected_reg_list, list):
            raise TypeError("InjectionPoint: affected_reg_list must be " \
                "a list.")
        if not isinstance(cycle, (int, long)):
            raise TypeError("InjectionPoint: cycle number must be int or long.")

        for item in affected_reg_list:
            if not isinstance(item, (list, tuple)):
                raise TypeError("InjectionPoint: affected_reg_list must " \
                    "contain tuples of (reg name, fault spec).")
            if len(item) != 2:
                raise TypeError("InjectionPoint: affected_reg_list must " \
                    "contain tuples of (reg name, fault spec).")
            if not isinstance(item[0], basestring):
                raise TypeError("InjectionPoint: first item of tuple in " \
                    "affected_reg_list must be string of register name.")
            if not isinstance(item[1], FaultSpec):
                raise TypeError("InjectionPoint: second item of tuple in " \
                    "affected_reg_list must be FaultSpec object.")

        self.cycle = cycle
        self.__affected_list = affected_reg_list

    def __str__(self):
        return "InjectionPoint(Cyc=%d,Regs=%s)" % \
            (self.cycle, map(lambda x: x[0], self.__affected_list))

    def __repr__(self):
        return "InjectionPoint(%d, %s)" % \
            (self.cycle, repr(self.__affected_list))

    # iterates over affected register list
    def __iter__(self):
        return iter(self.__affected_list)

    # returns number of faulty registers in this injection point
    def get_num_faults(self):
        return len(self.__affected_list)

    # gets specific faulty register and its fault spec by ID
    # returns tuple of register name and FaultSpec object
    def get_fault_by_id(self, affected_reg_id):
        return tuple(self.__affected_list[affected_reg_id])


# single bit flip injection point
class InjectionPointSingle:
    def __init__(self, cycle, reg_name, bit_pos):
        self.cycle = cycle
        self.reg_name = reg_name
        self.bit_pos = bit_pos
    def __str__(self):
        return "InjectionPointSingle(Cyc=%d,Reg=%s [%d])" % \
            (self.cycle, self.reg_name, self.bit_pos)
    def __repr__(self):
        return "InjectionPointSingle(%d, %s, %d)" % \
            (self.cycle, self.reg_name, self.bit_pos)


# checkpoint class
class Checkpoint:
    def __init__(self, ckpt_id, ckpt_num, ckpt_cycle, ckpt_pc=0):
        self.ckpt_id = ckpt_id
        self.num = ckpt_num
        self.cycle = ckpt_cycle
        self.pc = ckpt_pc
    def __str__(self):
        return "Checkpoint(ID=%s,Num=%d,Cyc=%d,PC=0x%x)" % \
            (self.ckpt_id, self.num, self.cycle, self.pc)
    def __repr__(self):
        return "Checkpoint(%s, %d, %d, %d)" % \
            (repr(self.ckpt_id), self.num, self.cycle, self.pc)


# host checkpoint (checkpoint + path) class
class HostCheckpoint:
    def __init__(self, ckpt, path):
        self.ckpt = ckpt
        self.path = path
    def __str__(self):
        return "HostCheckpoint(ID=%s,Num=%d,Cyc=%d,Path=%s)" % \
            (self.ckpt.ckpt_id, self.ckpt.num, self.ckpt.cycle, self.path)
    def __repr__(self):
        return "HostCheckpoint(%s,%s)" % \
            (repr(self.ckpt), repr(self.path))


# simulation result class
class SimulationResult:
    # run_id - run ID
    # outcome_id - one possibility of a run (always 0 if not post-low-level)
    # result_type - from RESULT enum
    # notes - string of notes from simulation
    # archive_path - path to archive dir for this run
    # perf_counters - list of "counter=N" strings
    # switch_abs - list of objects for switching abstraction
    #              1. if main RTL sim: 1st object is restart Checkpoint,
    #                 followed by raise abs info for each special bit
    #              2. if raise abs sim: names of files generated for Simics
    def __init__(self, run_id, outcome_id, result_type, notes=None, \
                 archive_path=None, perf_counters=None, switch_abs=None):
        self.run_id = run_id                    # int
        self.outcome_id = outcome_id            # int
        self.result_type = result_type          # enum
        self.notes = notes                      # string
        self.archive_path = archive_path        # string
        self.perf_counters = perf_counters      # list of strings
        self.switch_abs = switch_abs            # list of objects
    def __str__(self):
        try:
            result_type_str = RESULT.reverse_mapping[self.result_type]
        except KeyError:
            result_type_str = str(self.result_type)
        result_list = [ self.run_id, self.outcome_id, result_type_str ]
        if self.notes is not None:
            result_list.append(self.notes)
        if self.archive_path is not None:
            result_list.append("archive dir at %s" % self.archive_path)
        if self.perf_counters is not None:
            result_list.extend(self.perf_counters)
        if self.switch_abs is not None:
            result_list.extend(self.switch_abs)
        return str(result_list)
    def __repr__(self):
        return "SimulationResult(%d, %d, %d, %s, %s, %s, %s)" % \
            (self.run_id, self.outcome_id, self.result_type, repr(self.notes), \
            repr(self.archive_path), repr(self.perf_counters), \
            repr(self.switch_abs))


# fatal exception during simulation
# should cause VCS to be terminated
class FatalSimulationError(Exception):
    pass

