from pyparsing import *
import string

module_name = "fpu"

scheme_chars2 = ('abcdefghijklmnopqrstuvwxyz'
                    		'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                    		'0123456789'
            				'_[].')

expr = Word(scheme_chars2) + Word(scheme_chars2) + Suppress('(') + OneOrMore(Suppress(Word(scheme_chars2)) + Suppress('(') + Word(scheme_chars2) + Suppress(')') + Suppress(Optional(Word(',')))) + Suppress(Optional(Word(')'))) + Suppress(';')

fin = open('cmp_top.iop.' + module_name + ".v", 'r')
fout = open('cmp_top.iop.' + module_name + ".modified.v", 'w')

for line in fin:
        try:
                element = expr.parseString(line)
        except ParseException:
                fout.write(line)
                continue
        for i in range(2, len(element)):
                if element[i][0] == 'n' and element[i][1:].isdigit():
                        element[i] = module_name + "_" + element[i]
        if "DFFPOSX1" in line or "DFFSR" in line or "LATCH" in line:
                fout.write(element[0] + " " + element[1] + "(.D(" + element[2] + "), .CLK(" + element[3] + "), .Q(" + element[4] + "));\n")
        elif len(element) == 4:
                fout.write(element[0] + " " + element[1] + "(.A(" + element[2] + "), .Y(" + element[3] + "));\n")
        else:
                fout.write(element[0] + " " + element[1] + "(.A(" + element[2] + "), .B(" + element[3] + "), .Y(" + element[4] + "));\n")

fout.close()
fin.close()
