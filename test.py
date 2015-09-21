import xlate_core

def __combine_bitvector(postsyn_dict):
    output_dict = dict()
    for (postsyn_name, value) in postsyn_dict.iteritems():
        presyn_name = xlate_core.post2pre(postsyn_name)
        reg_name, bit_pos = presyn_name
        if reg_name not in output_dict:
            output_dict[reg_name] = long(value) << bit_pos
        else:
            output_dict[reg_name] = output_dict[reg_name] ^ \
                ((-value ^ output_dict[reg_name]) & (1 << bit_pos))
    return { k: format(v, 'b') for k, v in output_dict.items() }



#### tests ####

if __name__ == "__main__":
    xlate_core.init("postsyn/instances.txt", "tgt.sizes")

    test_dict = { \
        ('cmp_top.iop.sparc0.exu', 'div_yreg_dff_yreg_thr0_q_reg[0]'): 1, \
        ('cmp_top.iop.sparc0.exu', 'div_yreg_dff_yreg_thr0_q_reg[3]'): 1, \
        ('cmp_top.iop.sparc0.exu', 'div_yreg_dff_yreg_thr0_q_reg[1]'): 1, \
        ('cmp_top.iop.sparc0.exu', 'div_yreg_dff_yreg_thr0_q_reg[7]'): 1, \
        ('cmp_top.iop.sparc0.exu', 'div_yreg_dff_yreg_thr1_q_reg[31]'): 1, \
        ('cmp_top.iop.sparc0.exu', 'div_yreg_dff_yreg_thr1_q_reg[30]'): 1, \
        ('cmp_top.iop.sparc0.exu', 'div_yreg_dff_yreg_thr1_q_reg[0]'): 1, \
    }

    print __combine_bitvector(test_dict)
