import subprocess, sys, os, os.path
import xlate_core
import pickle
from grabCircuit import __grab_Circuit
from grabCircuit import __write_Target
from grabCircuit import __convert_Output
from grabCircuit import __collect_Multiout

execfile("utilities.py")

def __get_DFF_Logic(infile, outfile, dfflist):

    print infile

    expr = '{'
    fin = open(infile, 'r')
    try:
        for line in fin:
            expr = expr + line
    except IOError:
        print "Error in file " + infile
        sys.exit(1)
    finally:
        fin.close()

    expr = expr + '}'

    dfflogicDict = eval(expr)
    dffLogic = []

    for dff in dfflist:

        modulename = dff[0][:-2]

        dffname = (modulename, dff[1])

        dffname = xlate_core.post2pre(dffname)

        try:
            logic = dfflogicDict[dffname[0]]
        except KeyError:
# Need to modified when all the synthesized netlists are avaliable
            print dff[1] + " does not exist!"
            logic = "0"
#            sys.exit(1)

#        dffLogic.append((int(float(logic)) >> (dffname[1])) & 1)
#        print logic
        dffLogic.append(logic[max(len(logic) - dffname[1] - 1, 0)])

    fout = open(outfile, 'w')
    for i in range(0, len(dffLogic)):
#        print dfflist[i]
        fout.write(dfflist[i][2] + " " + str(dffLogic[i]) + "\n")
    fout.close() 

    return

'''
API for the circuit level simulation -- construct subcircuit from the netlist and get the
logic value for each input DFF, circuit level fault injection simulation and output file conversion.

The inputs to the problem includes:
        netInFile: circuit netlist
        inputFile: dumped file that contains all the logic value for DFFs
        target: DFF to inject fault
        instanceFile: DFFs in the circuit
'''


def __cal_SER(inputFile, regName, regPos, instanceFile, initFile, outDir, postsynDir, LOG_FILE, __NAME2INDEX, __GATE2INDEX, __DFF2NETLIST, __NODELIST):

    if not os.path.isdir(outDir):
        os_mkdir(outDir)
    
    netFile = outDir + "/netlist.sp"
    inputSimFile = outDir + "/input.txt"
    outSetFile = outDir + "/impactSet.txt"
    outProbFile = outDir + "/impactProb.txt"
    targetFile = outDir + "/target.txt"

    ignoreList = ["se", "sehold"]

    print "Initialize directory for name translation"

    print instanceFile
    print initFile

    xlate_core.init(instanceFile, initFile)

    print "Subcircuit Construction"

    dffList = __grab_Circuit(regName, regPos, netFile, ignoreList, postsynDir, __GATE2INDEX, __NODELIST, __NAME2INDEX, __DFF2NETLIST)
    if (dffList == []):
        print "cannot find target"
        return [0, 0]

    print "Grab input logic for subcircuit"

    __get_DFF_Logic(inputFile, inputSimFile, dffList)

    print "Creating file for target DFF"

    __write_Target(targetFile, regName, regPos, __GATE2INDEX, __NODELIST)

    command = "../SEU_simulator " + netFile + " " + inputSimFile + " " + targetFile + " " + outSetFile + " " + outProbFile + " |& tee log"
    subprocess.call(command, shell = True)

    __convert_Output(outDir + "/impactOutput.txt", outSetFile)

    return __collect_Multiout(outDir + "/impactOutput.txt", outProbFile)

#    subprocess.call("rm " + netFile, shell = True)
#    subprocess.call("rm " + inputSimFile, shell = True)
#    subprocess.call("rm " + targetFile, shell = True)
#    subprocess.call("rm " + outSetFile, shell = True)
#    subprocess.call("rm log", shell = True)

if __name__ == "__main__":
    netInFile = "cmp_top.iop.sparc0.exu.v"
    inputFile = "../tgt.tcheck"
    initFile = "../xlate_name/tgt.sizes"
    regName = "cmp_top.iop.sparc0.exu.div.d_dff.q"
    regPos = 0
    instanceFile = "../xlate_name/postsyn/instances.txt"
    __cal_SER(inputFile, regName, regPos, instanceFile, initFile, ".", "log")

