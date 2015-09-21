import sys, os, os.path, argparse

'''
Reads post-synthesis Verilog netlist to extract a list of all the flip-flops.
'''

# list of names of flip-flop primitives in design, case sensitive
DFF_NAMES = [ 'DFFPOSX1', 'DFFSR', 'DFFNEGX1' ]

# symbols in verilog identifiers, other than alpha-numeric chars
VERILOG_IDENTIFIER = '[]_.:'

# symbols that separate verilog tokens
VERILOG_SEPARATOR = '(),; '


# reads netlist file to find flip-flops
def read_netlist(filename):
    ff_list = list()
    f = open(filename)
    try:
        for line in f:
            line = line.strip()
            if check_dff_line(line):
                tokens = tokenize_verilog(line)
                if len(tokens) >= 2 and tokens[0] in DFF_NAMES:
                    ff_list.append(tokens[1])
    except IOError:
        print "ERROR: cannot read from netlist file", filename
        sys.exit(1)
    finally:
        f.close()

    return ff_list


# tokenize one line of verilog into identifiers/keywords
def tokenize_verilog(code_line):
    tokens = list()
    text = code_line.strip()

    if text == "" or text.startswith("//"):
        return tokens

    current_token = ''
    for c in text:
        # identifier
        if c.isalnum() or c in VERILOG_IDENTIFIER:
            current_token = current_token + c
        # token separator
        elif c in VERILOG_SEPARATOR:
            if current_token != '':
                tokens.append(current_token)
            current_token = ''

    return tokens


# quickly check if line can possibly contain instantiation of flip-flop
def check_dff_line(line):
    for name in DFF_NAMES:
        if line.startswith(name):
            return True
    return False


# write list of flip-flops to file
def write_output(filename, ff_list):
    f = open(filename, 'w')
    try:
        for ff in ff_list:
            f.write(ff + '\n')
    except IOError:
        print "ERROR: cannot write to output file", filename
        sys.exit(1)
    finally:
        f.close()


# parse arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description="Generates list of " \
        "post-synthesis flip-flops.")
    parser.add_argument('netlist', \
        help='path to post-synthesis netlist file')
    parser.add_argument('output_file', \
        help='path to output file containing list of flip flops')

    return parser.parse_args()


# main
if __name__ == "__main__":
    namespace = parse_arguments()

    netlist_file = namespace.netlist
    output_file = namespace.output_file

    if not os.path.isfile(netlist_file):
        print "ERROR: cannot find specified netlist file", netlist_file
        sys.exit(1)

    print "Reading netlist file", netlist_file
    ff_list = read_netlist(netlist_file)

    print "Found %d flip-flops in netlist" % len(ff_list)

    print "Writing output file", output_file
    write_output(output_file, ff_list)
    print "Done."

