"""
Parser for files produced by objdump.
"""
import pandas as pd

from collections import defaultdict
from .riscv import RISCVInstruction


def parse_instruction(line):
    chunks = line.split()
    addr, raw, insn = chunks[:3]

    args = [] if len(chunks) <= 3 else chunks[3].split(",")

    return RISCVInstruction(int(addr[:-1], 16), int(raw, 16), insn, args)


def parse_objdump(f):
    """
    Take an objdump file as input, produce a dictionary from function names
    to lists of instructions.
    """
    result = defaultdict(list)
    table = []

    current_function = None

    for i, line in enumerate(f.readlines()):
        #         print(i)
        if i <= 5:
            # part of the header
            continue

        if line.startswith("  "):
            # an instruction line
            assert current_function is not None
            insn = parse_instruction(line)
            result[current_function].append(insn)
            table.append([insn.pc, 1])
        elif line[0].isdigit():
            # start of a function
            # looks like `0...0 <function_name>:`
            current_function = line.strip()[:-2].split("<")[-1]
    #             print(current_function)

    df = pd.DataFrame(table, columns=["addr", "times"]).set_index("addr")

    return result, df
