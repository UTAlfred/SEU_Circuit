from pyparsing import *
import string, subprocess

#module_name = ["exu", "ffu", "ifu", "lsu", "mul", "tlu"]
module_name = ["fpu"]

scheme_chars2 = ('abcdefghijklmnopqrstuvwxyz'
                    		'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                    		'0123456789'
            				'_[].')

expr = Word(scheme_chars2) + Word(scheme_chars2) + Suppress('(') + OneOrMore(Suppress(Word(scheme_chars2)) + Suppress('(') + Word(scheme_chars2) + Suppress(')') + Suppress(Optional(Word(',')))) + Suppress(Optional(Word(')'))) + Suppress(';')

for module in module_name:

        fileIn = "cmp_top.iop." + module + ".v"
        fileOut = "cmp_top.iop." + module + ".modified.v"

        fin = open(fileIn, 'r')
        fout = open(fileOut, 'w')
        
        for line in fin:
                try:
                        element = expr.parseString(line)
                except ParseException:
                        fout.write(line)
                        continue
                if "DFFPOSX1" in line or "DFFSR" in line or "LATCH" in line or "DFFNEGX1" in line:
                        fout.write(element[0] + " " + element[1] + "(.D(" + element[2] + "), .CLK(" + element[3] + "), .Q(" + element[4] + "));\n")
                elif len(element) == 4:
                        element[1] = module + "_" + element[1]
                        fout.write(element[0] + " " + element[1] + "(.A(" + element[2] + "), .Y(" + element[3] + "));\n")
                else:
                        element[1] = module + "_" + element[1]
                        fout.write(element[0] + " " + element[1] + "(.A(" + element[2] + "), .B(" + element[3] + "), .Y(" + element[4] + "));\n")
        
        fout.close()
        fin.close()

        command = "mv " + fileOut + " " + fileIn

        print command

        subprocess.call(command, shell=True)
