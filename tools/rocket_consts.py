
from enum import Enum
from dataclasses import dataclass

ALU2 = Enum(
    value="ALU2", names=[("ZERO", 0), ("SIZE", 1), ("RS2", 2), ("IMM", 3), ("X", 4)]
)

ALU1 = Enum(value="ALU1", names=[("ZERO", 0), ("RS1", 1), ("PC", 2), ("X", 3)])

IMM = Enum(
    value="IMM",
    names=[("S", 0), ("SB", 1), ("U", 2), ("UJ", 3), ("I", 4), ("Z", 5), ("X", 6)],
)

ALU_FN = Enum(
    value="ALU_FN",
    names=[
        ("ADD", 0),
        ("SL", 1),
        ("SEQ", 2),
        ("SNE", 3),
        ("XOR", 4),
        ("SR", 5),
        ("OR", 6),
        ("AND", 7),
        ("SUB", 10),
        ("SRA", 11),
        ("SLT", 12),
        ("SGE", 13),
        ("SLTU", 14),
        ("SGEU", 15),
        ("X", 16),
        ("MUL", 17),
        ("DIV", 18),
        ("MULH", 19),
        ("MULHSU", 20),
        ("MULHU", 21),
        ("DIVU", 22),
        ("REM", 23),
        ("REMU", 24),
    ],
)

MEM_CMD = Enum(
    value="MEM_CMD",
    names=[
        ("XRD", int("00000", 2)),
        ("XWR", int("00001", 2)),
        ("PFR", int("00010", 2)),
        ("PFW", int("00011", 2)),
        ("XA_SWAP", int("00100", 2)),
        ("FLUSH_ALL", int("00101", 2)),
        ("XLR", int("00110", 2)),
        ("XSC", int("00111", 2)),
        ("XA_ADD", int("01000", 2)),
        ("XA_XOR", int("01001", 2)),
        ("XA_OR", int("01010", 2)),
        ("XA_AND", int("01011", 2)),
        ("XA_MIN", int("01100", 2)),
        ("XA_MAX", int("01101", 2)),
        ("XA_MINU", int("01110", 2)),
        ("XA_MAXU", int("01111", 2)),
        ("FLUSH", int("10000", 2)),
        ("PWR", int("10001", 2)),
        ("PRODUCE", int("10010", 2)),
        ("CLEAN", int("10011", 2)),
        ("SFENCE", int("10100", 2)),
        ("X", 32),
    ],
)

CSR = Enum(
    value="CSR_CMD",
    names=[("N", 0), ("R", 2), ("I", 4), ("W", 5), ("S", 6), ("C", 7), ("X", 8)],
)

ALU_DW = Enum(
    value="ALU_DW", names=[("DW_X", 2), ("DW_XPR", 1), ("DW_64", 1), ("DW_32", 0)]
)

@dataclass
class RocketSignal:
    legal: bool
    fp: bool
    rocc: bool
    branch: bool
    jal: bool
    jalr: bool
    rxs2: bool
    rxs1: bool
    scie: bool
    sel_alu2: ALU2
    sel_alu1: ALU1
    sel_imm: IMM
    alu_dw: bool
    alu_fn: ALU_FN
    mem: bool
    mem_cmd: MEM_CMD
    rfs1: bool
    rfs2: bool
    rfs3: bool
    wfd: bool
    mul: bool
    div: bool
    wxd: bool
    csr: CSR
    fence_i: bool
    fence: bool
    amo: bool
    dp: bool
