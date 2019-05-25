"""
Check basic blocks for certain types of macro-op fusion opportunities. Each function separates
neighbour opportunities from long-range opportunities that weren't picked up by the compiler.
"""

lds = {"ld", "lw", "lb", "lbu", "lh", "lhu"}
adds = {"add", "addi", "addw", "addiw", "mv"}
slls = {"slli", "slliw"}
srls = {"srli", "srliw"}


def check_block_lea(block):
    watching = {}
    neighbours = []
    limit = []
    distances = []

    for i, insn in enumerate(block):
        if insn.is_slli():
            watching[insn.rd] = i
        elif insn.is_add():
            if insn.rd == insn.rs1 and insn.rd in watching:
                if watching[insn.rd] == i - 1:
                    neighbours.append(insn.pc)
                else:
                    distances.append(i - watching[insn.rd])
                    limit.append(insn.pc)

                del watching[insn.rd]
        else:
            for arg in insn.args:
                if arg in watching:
                    assert not arg[0].isdigit(), arg
                    del watching[arg]

    return neighbours, limit, distances


def check_block_ix_ld(block):
    watching = {}
    neighbours = []
    limit = []
    distances = []

    for i, insn in enumerate(block):
        addr, raw, insn, args = insn.pc, insn.raw, insn.insn, insn.args

        if insn in adds:
            # potential LEA, add rd to watching
            watching[args[0]] = i
        elif insn in lds:
            offset = args[1].split("(")[1][:-1]
            if args[0] == offset and args[0] in watching:
                if watching[args[0]] == i - 1:
                    neighbours.append(addr)
                else:
                    distances.append(i - watching[args[0]])
                    limit.append(addr)
                del watching[args[0]]
        elif len(args) > 0:
            # if we read or write the intermediate result, we can't
            # fuse these instructions

            for arg in args:
                if arg in watching:
                    del watching[arg]

    return neighbours, limit, distances


def check_block_cuw(block):
    watching = {}
    neighbours = []
    limit = []
    distances = []

    for i, insn in enumerate(block):
        addr, raw, insn, args = insn.pc, insn.raw, insn.insn, insn.args

        if insn in slls:
            # potential LEA, add rd to watching
            watching[args[0]] = i
        elif insn in srls:
            if args[0] == args[1] and args[0] in watching:
                if watching[args[0]] == i - 1:
                    neighbours.append(addr)
                else:
                    distances.append(i - watching[args[0]])
                    limit.append(addr)
                del watching[args[0]]
        elif len(args) > 0:
            # if we read or write the intermediate result, we can't
            # fuse these instructions

            for arg in args:
                if arg in watching:
                    del watching[arg]

    return neighbours, limit, distances


opportunities = ["lea", "ix_ld", "cuw"]
checkers = {"lea": check_block_lea, "ix_ld": check_block_ix_ld, "cuw": check_block_cuw}
