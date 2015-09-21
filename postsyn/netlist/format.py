fin = open('cmp_top.iop.sparc0.exu.v', 'r')

fout = open('cmp_top.iop.sparc0.exu.modified.v', 'w')

gate = ['DFFPOSX1', 'AND2X1', 'INVX1', 'XNOR2X1', 'OR2X1', 'XOR2X1', 'NAND2X1', 'NOR2X1', 'BUFX1', 'AND2X2', 'OR2X2', 'BUFX2', 'INVX2', 'DFFNEGX1', 'DFFSR']
flag = 0
gateNum = 0

for line in fin:
        element = line.split()
#        print element
        if (len(element) == 0):
                flag = 0
                continue
        if flag == 1:
                fout.write(" ".join(line.split()))
                if ';' in line:
                        fout.write('\n')
                        flag = 0
        elif (element[0] in gate):
                if ';' in line:
                        fout.write(" ".join(element))
                        fout.write('\n')
                        flag = 0
                else:
#                        element.remove('\n')
                        fout.write(" ".join(element))
                        flag = 1
        else:
                fout.write(line)
                flag = 0
fin.close()
fout.close()

fin = open('cmp_top.iop.sparc0.exu.modified.v', 'r')

for line in fin:
        element = line.split()
        if (len(element) == 0):
                continue
        elif (element[0] in gate):
                gateNum = gateNum + 1
                if ';' not in line:
                        print line
#                        exit(0)

print 'gate number:'
print gateNum

fin.close()
