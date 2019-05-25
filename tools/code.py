"""Code-handling tools"""
import pandas as pd


def find_basic_blocks(program):
    """Program as produced by objdump.parse_objdump, i.e. a dictionary of lists of `RISCVInstruction`s"""

    block = []

    for function in program.values():
        for instruction in function:
            if instruction.is_control_flow():
                if len(block) > 0:
                    yield block
                    block = []
            else:
                block.append(instruction)

        if len(block) > 0:
            yield block
            block = []


def load_histogram(f):
    histogram = f.readlines()

    parse = True
    for line in histogram:
        if line.startswith("PC Histogram"):
            parse = False
            break

    table = []

    for line in histogram:
        line = line.strip()

        if line.startswith("PC Histogram"):
            parse = True
            continue

        if not parse:
            continue

        if len(line) == 0:
            continue

        if (
            line.startswith("DYNAMIC")
            or line.startswith("ZERO")
            or line.startswith("ONE")
        ):
            continue

        if parse:
            try:
                pc, count = line.split()
            except:
                print(line)
                continue
            pc = int(pc, 16)
            count = int(count)

            table.append([pc, count])

    return pd.DataFrame(table, columns=["addr", "count"]).set_index("addr")


def load_histogram_fast(f):
    """
    Load the raw stderr output from spike -g. Skip the first line to ignore the PC Histogram size line.

    NOTE that this won't always work if the program either outputs to stderr or causes an error during its execution.
    """
    return pd.read_csv(
        f,
        sep=" ",
        header=None,
        names=["addr", "count"],
        skiprows=1,
        skipfooter=3,
        engine="python",
        converters={"addr": lambda x: int(x, 16)},
    ).set_index("addr")
