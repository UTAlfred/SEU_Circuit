from pyparsing import *
#from run_circuit.py import __NAME2INDEX, __GATE2INDEX, __DFF2NETLIST, __NODELIST
#import run_circuit.py
import xlate_core
import time
import sys

###
# Global variables
###

__GATELIST = []
__CIRCUITOUT = dict()

__POSTSYN_DIR = None

__IGNORE_MODULE = ['irf']

class Node(object):
    def __init__(self, name, gatename, fanin, fanout, isDFF):
        self.name = name
        self.gatename = gatename
        self.fanin = fanin
        self.fanout = fanout
        self.isDFF = isDFF


def __build_Graph(filename, __NAME2INDEX, __GATE2INDEX, __DFF2NETLIST, __NODELIST):

    name2index = dict()
    gate2index = dict()
    nodelist = []

    scheme_chars = ('abcdefghijklmnopqrstuvwxyz'
                    		'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                    		'0123456789'
            				'_[].')

    expr = Word(scheme_chars) + Word(scheme_chars) + Suppress('(') + OneOrMore(Suppress(Word(scheme_chars)) + Suppress('(') + Word(scheme_chars) + Suppress(')') + Suppress(Optional(Word(',')))) + Suppress(');')


    compNum = 0
		
    try:
        fin = open(__POSTSYN_DIR + "/" + filename, 'r')
    except IOError, err:
        print "file " + __POSTSYN_DIR + "/" + filename + " not found!"
        return
#        sys.exit(1)

    for line in fin:
        try:
            element = expr.parseString(line)
        except ParseException, err:
#            print "error in the line:"
#            print err.line
            continue
								
        name = element[len(element) - 1]
        gatename = element[1]
        isDFF = False
        if name2index.has_key(element[len(element) - 1]):
            index = name2index[element[len(element) - 1]]
            nodelist[index].gatename = gatename
            gate2index[gatename] = index
            if (element[0].lower().find("dff") != -1):
                nodelist[index].isDFF = True
                isDFF = True
        else:
            name2index[name] = compNum
            gate2index[gatename] = compNum
            compNum = compNum + 1
            if (element[0].lower().find("dff") != -1):
                isDFF = True
            node = Node(name, gatename, [], [], isDFF)
            nodelist.append(node)

        indexOut = name2index[element[len(element)-1]]
        for iPin in range(2, len(element) - 1):
            if isDFF == True and iPin == 3:
                continue
            if element[iPin] != "rclk":
                if name2index.has_key(element[iPin]):
                    indexIn = name2index[element[iPin]]
                    nodelist[indexIn].fanout.append(indexOut)
                    nodelist[indexOut].fanin.append(indexIn)
                else:
                    nodelist[indexOut].fanin.append(compNum)
                    name2index[element[iPin]] = compNum
#                    gate2index[element[iPin]] = compNum
                    name = element[iPin]
                    node = Node(name, "", [], [indexOut], False)
                    nodelist.append(node)
                    compNum = compNum + 1

        __DFF2NETLIST[gatename] = line
    fin.close()

    __NAME2INDEX[filename] = name2index
    __GATE2INDEX[filename] = gate2index
    __NODELIST[filename] = nodelist
    return


def __node_Match_BK(node, nodefinal, newdff, ignoreList, filename, inputList, __NODELIST):

    global __GATELIST

    try:
        nodeTemp = __NODELIST[filename][node]
    except KeyError:
        print "file " + filename + " not found!"
        return

    if (nodeTemp.isDFF):
#        __GATELIST.append(nodeTemp.gatename)
        if (node not in nodefinal):
            newdff.append([filename, nodeTemp.gatename, nodeTemp.name])
            nodefinal.append(node)
        return
    else:
        fanin = nodeTemp.fanin
        if (node not in nodefinal):
            nodefinal.append(node)
        else:
            return
        if (nodeTemp.gatename not in __GATELIST):
            __GATELIST.append(nodeTemp.gatename)
#            print "node", nodeTemp.name
#            print "gatename", nodeTemp.gatename
        if (len(fanin) == 0 and nodeTemp.name not in ignoreList):
            inputList.append(nodeTemp.name)
            return
        for i in range(0, len(fanin)):
            if (fanin[i] not in ignoreList):
                __node_Match_BK(fanin[i], nodefinal, newdff, ignoreList, filename, inputList, __NODELIST)
        return


def __node_Match_FW(node, nodefinal, newdff, ignoreList, filename, outputList, __NODELIST):

    global __GATELIST

    try:
        nodeTemp = __NODELIST[filename][node]
    except KeyError:
        print "file " + filename + " not found!"
        return

    if (nodeTemp.isDFF):
        if node not in nodefinal:
#            __GATELIST.append(nodeTemp.gatename)
            newdff.append([filename, nodeTemp.gatename, nodeTemp.name])
            nodefinal.append(node)
            fanout = nodeTemp.fanout
            for i in range(0, len(fanout)):
                if (fanout[i] not in nodefinal and not __NODELIST[filename][fanout[i]].isDFF):
                    __node_Match_FW(fanout[i], nodefinal, newdff, ignoreList, filename, outputList, __NODELIST)
    else:
        fanout = nodeTemp.fanout
        if (node not in nodefinal):
            nodefinal.append(node)
        else:
            return
        if (len(fanout) == 0 and nodeTemp.name not in ignoreList):
            outputList.append(nodeTemp.name)
        for i in range(0, len(fanout)):
            if (fanout[i] not in nodefinal and not __NODELIST[filename][fanout[i]].isDFF):
                __node_Match_FW(fanout[i], nodefinal, newdff, ignoreList, filename, outputList, __NODELIST)
        if nodeTemp.gatename not in __GATELIST:
            __GATELIST.append(nodeTemp.gatename)
	return


def __build_Netlist(outfile, __DFF2NETLIST):

    global __GATELIST

    fout = open(outfile, 'a')

    for ele in __GATELIST:
        if ele == "":
            continue
        line = __DFF2NETLIST[ele]
        fout.write(line)

    fout.close()
    return

def __write_Target(targetFile, regName, regPos, __GATE2INDEX, __NODELIST):

    fout = open(targetFile, 'w')

    gate = xlate_core.pre2post((regName, regPos))
    filename = gate[0] + ".v"
    try:
        index = __GATE2INDEX[filename][gate[1]]
    except KeyError:
        print "target " + gate[1] + " not found"
        sys.exit(1)
    fout.write(__NODELIST[filename][__NODELIST[filename][index].fanin[0]].name + "\n")

#    for ele in target:
#        gate = xlate_core.pre2post(ele)
#        try:
#            index = __GATE2INDEX[filename][gate[1]]
#        except KeyError:
#            print "target " + gate[1] + " not found"
#            sys.exit(1)
#        fout.write(__NODELIST[filename][__NODELIST[filename][index].fanin[0]].name + "\n")

    fout.close()
    return

def __classify_Input(innode, filelist):
    for node in innode:
        loc = node.find("_")
        infile = "cmp_top.iop.sparc0." + node[:loc] + ".v"
#        if infile == "cmp_top.iop.sparc0.ecl.v" or infile == "cmp_top.iop.sparc0.mux.v":
#            print node
        if infile in filelist:
            filelist[infile].append(node)
        else:
            filelist[infile] = [node]
    return

def __classify_Output(outnode, filelist):
    for node in outnode:
        loc1 = node.find("_")
        loc2 = node.find("_", loc1 + 1)
        outfile = "cmp_top.iop.sparc0." + node[loc1+1 : loc2] + ".v"
#        if outfile == "cmp_top.iop.sparc0.ecl.v" or outfile == "cmp_top.iop.sparc0.mux.v":
#            print node
        if outfile in filelist:
            filelist[outfile].append(node)
        else:
            filelist[outfile] = [node]
    return

def __grab_Circuit(targetName, targetPos, netlistFile, ignoreList, postsynDir, __GATE2INDEX, __NODELIST, __NAME2INDEX, __DFF2NETLIST):

    global __POSTSYN_DIR

    __init_Grab()

    print __GATELIST

    __POSTSYN_DIR = postsynDir

    print "netlist directory: " + postsynDir

    netList = []
    nodeFinal = []
    newDFF = []
    DFFList = []
    targetList = []

    targetGate = xlate_core.pre2post((targetName, targetPos))
    try:
        filename = targetGate[0] + ".v"
    except TypeError:
        print "target gate cannot be found!"
        return []

    t1 = time.time()

    __build_Graph(filename, __NAME2INDEX, __GATE2INDEX, __DFF2NETLIST, __NODELIST)

    t2 = time.time()

    nodelist = __NODELIST[filename]

    index = __GATE2INDEX[filename][targetGate[1]]
    targetList.append(nodelist[index].fanin[0])
    __CIRCUITOUT[nodelist[nodelist[index].fanin[0]].name] = (filename, nodelist[index].gatename)
    DFFList.append([filename, targetGate[1], nodelist[index].name])

    inNode = []
    while (targetList != []):
        __node_Match_BK(targetList.pop(), nodeFinal, newDFF, ignoreList, filename, inNode, __NODELIST)

    while (inNode != []):
        inNodeFileList = {}
        __classify_Input(inNode, inNodeFileList)
        inNode = []
        for file in inNodeFileList:
            if file not in __NODELIST:
                __build_Graph(file, __NAME2INDEX, __GATE2INDEX, __DFF2NETLIST, __NODELIST)
            nodeList = inNodeFileList[file]
            while (nodeList != []):
                node = nodeList.pop()
                try:
                    node_index = __NAME2INDEX[file][node]
                except KeyError:
                    print file + " not found!"
                    print node
                    continue
                __node_Match_BK(node_index, nodeFinal, newDFF, ignoreList, file, inNode, __NODELIST)

    t3 = time.time()
    print "time for backward traversal of the whole netlist is " + str(t3 - t2)

    targetDict = dict()
    for ele in newDFF:
        if ele not in DFFList:
            DFFList.append(ele)
        index = __GATE2INDEX[ele[0]][ele[1]]
        if ele[0] in targetDict:
            targetDict[ele[0]].append(index)
        else:
            targetDict[ele[0]] = [index]

    newDFF = []
    nodeFinal = []
    outNode = []
    for file in targetDict:
        targetList = targetDict[file]
        if file not in __NODELIST:
            __build_Graph(file, __NAME2INDEX, __GATE2INDEX, __DFF2NETLIST, __NODELIST)
        while(targetList != []):
            __node_Match_FW(targetList.pop(), nodeFinal, newDFF, ignoreList, file, outNode, __NODELIST)

    while outNode != []:
        outNodeFileList = {}
        __classify_Output(outNode, outNodeFileList)
        outNode = []
        for file in outNodeFileList:
            if file not in __NODELIST:
                __build_Graph(file, __NAME2INDEX, __GATE2INDEX, __DFF2NETLIST, __NODELIST)
            nodeList = outNodeFileList[file]
            while nodeList != []:
                node = nodeList.pop()
                try:
                    node_index = __NAME2INDEX[file][node]
                except KeyError:
                    print file + " not found!"
                    print node
                    continue
                __node_Match_FW(node_index, nodeFinal, newDFF, ignoreList, file, outNode, __NODELIST)


    t4 = time.time()
    print "time for forward traversal of the whole netlist is " + str(t4 - t3)

    targetDict = dict()
    for ele in newDFF:
        if ele not in DFFList:
            DFFList.append(ele)
            print "element " + str(ele[1])
#        if ele[1] not in target:
        if not (ele[1] == targetGate[1]):
            index = __NAME2INDEX[ele[0]][ele[2]]
            index = __NODELIST[ele[0]][index].fanin[0]
            if ele[0] in targetDict:
                targetDict[ele[0]].append(index)
            else:
                targetDict[ele[0]] = [index]

    newDFF = []
    nodeFinal = []
    inNode = []
    for file in targetDict:
        targetList = targetDict[file]
        if file not in __NODELIST and file not in __IGNORE_MODULE:
            __build_Graph(file, __NAME2INDEX, __GATE2INDEX, __DFF2NETLIST, __NODELIST)
        while(targetList != []):
            __node_Match_BK(targetList.pop(), nodeFinal, newDFF, ignoreList, file, inNode, __NODELIST)

    while inNode != []:
        inNodeFileList = {}
        __classify_Input(inNode, inNodeFileList)
        inNode = []
        for file in inNodeFileList:
            if file not in __NODELIST and file not in __IGNORE_MODULE:
                __build_Graph(file, __NAME2INDEX, __GATE2INDEX, __DFF2NETLIST, __NODELIST)
            nodeList = inNodeFileList[file]
            while nodeList != []:
                node = nodeList.pop()
                try:
                    node_index = __NAME2INDEX[file][node]
                except KeyError:
                    print file + " not found!"
                    print node
                    continue
                __node_Match_BK(node_index, nodeFinal, newDFF, ignoreList, file, inNode, __NODELIST)
        
    t5 = time.time()
    print "time for backward traversal of the whole netlist is " + str(t5 - t4)

    for ele in newDFF:
        if ele not in DFFList:
            DFFList.append(ele)
        index = __NAME2INDEX[ele[0]][ele[2]]
        index = __NODELIST[ele[0]][index].fanin[0]
        name = __NODELIST[ele[0]][index].name
        if name not in __CIRCUITOUT:
#            __CIRCUITOUT[name] = ele[2]
            __CIRCUITOUT[name] = (ele[0], ele[1])
#        if (index not in circuitOut):
#            circuitOut.append(__NODELIST[ele[0]][index].name)

    fout = open(netlistFile, 'w')
    fout.write("output ")
    for out in range(0, len(__CIRCUITOUT.keys())):
        fout.write(__CIRCUITOUT.keys()[out])
        if (out == len(__CIRCUITOUT.keys())-1):
            fout.write(";\n")
        elif (out % 10 == 0):
            fout.write(",\n")
        else:
            fout.write(", ")
    fout.close()

    __build_Netlist(netlistFile, __DFF2NETLIST)

    t6 = time.time()
    print "time to build the netlist is " + str(t6 - t5)

    return DFFList

def __convert_Output(outfile, infile):

    fout = open(outfile, 'w')
    fout.close()
    fout = open(outfile, 'a')
    fin = open(infile, 'r')

    nodelogic = dict()

    fout.write("[\n")
    for line in fin:
        if line.find("0") == -1 and line.find("1") == -1:
            nodelogic_temp = {k: format(v, 'b') for k, v in nodelogic.items()}
            fout.write("%r,\n" % nodelogic_temp)
            nodelogic = {}
        else:
            ele = line.split()
            dffpair = __CIRCUITOUT[ele[0]]
            dffpairt = list(dffpair)
            dffpairt[0] = dffpairt[0][:-2]
            dffpair = tuple(dffpairt)
            dffname = xlate_core.post2pre(dffpair)
            reg_name, bit_pos = dffname
            print bit_pos
            if reg_name not in nodelogic:
                nodelogic[reg_name] = long(1) << bit_pos
            else:
                nodelogic[reg_name] = nodelogic[reg_name] ^ \
                            ((-1 ^ nodelogic[reg_name]) & (1 << bit_pos))
#            if (dffpair[1].endswith("[" + str(dffname[1]) + "]")):
#                name = dffname[0] + "[" + str(dffname[1]) + "]" 
#            else:
#                name = dffname[0]
#            nodelogic[name] = ele[1]
    fout.write("]\n")
    fin.close()
    fout.close()
    return

def __collect_Multiout(infile1, infile2):

    fin1 = open(infile1, 'r')
    fin2 = open(infile2, 'r')

    single_bit_prob = 0.0
    multi_bit_prob = 0.0

    expr = ''
    for line in fin1:
        expr = expr + line
    vuln_dict_list = eval(expr)

    expr = ''
    for line in fin2:
        expr = expr + line
    prob_list = eval(expr)

    count = 0
    for vuln_dict in vuln_dict_list:
        if (len(vuln_dict) > 1):
            multi_bit_prob = prob_list[count] + multi_bit_prob
        else:
            value = vuln_dict[vuln_dict.keys()[0]]
            if (value.count('1') > 1):
                multi_bit_prob = prob_list[count] + multi_bit_prob
            else:
                single_bit_prob = prob_list[count] + single_bit_prob
        count = count + 1


    return [single_bit_prob, multi_bit_prob]


def __init_Grab():
    del __GATELIST[:]
    __CIRCUITOUT.clear()


