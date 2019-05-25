"""
RISC-V specific tools
"""
from bitstring import BitArray

regs = (
    ["zero", "ra", "sp", "gp", "tp"]
    + ["t{}".format(x) for x in range(3)]
    + ["s{}".format(x) for x in range(2)]
    + ["a{}".format(x) for x in range(8)]
    + ["s{}".format(x) for x in range(2, 12)]
    + ["t{}".format(x) for x in range(3, 7)]
)

assert len(regs) == 32

fp_regs = (
    ["ft{}".format(x) for x in range(8)]
    + ["fs{}".format(x) for x in range(2)]
    + ["fa{}".format(x) for x in range(8)]
    + ["fs{}".format(x) for x in range(2, 12)]
    + ["ft{}".format(x) for x in range(8, 12)]
)

assert len(fp_regs) == 32

x0 = 0
ra = 1
sp = 2


def rvc_regs(raw):
    # check the RVC quadrant
    quad = raw[-2:].uint
    index = raw[-16:-13].uint
    rs1p = raw[-10:-7].uint + 8
    rs2p = raw[-5:-2].uint + 8
    rs2 = raw[-7:-2].uint
    rd_base = raw[-12:-7].uint

    # print(quad, index)

    if quad == 0:
        # q0
        rd = rs2p
        rs1 = rs1p
        rs2 = rs2p

        if index == 0:
            # addi4spn
            rs1 = sp

        # other cases: the same
        return rd, rs1, rs2, x0
    elif quad == 1:
        # q1
        rd = rd_base
        rs1 = rd_base
        rs2 = rs2p

        if index == 2:
            rs1 = x0
        elif index == 4:
            rd = rs1p
            rs1 = rs1p
        elif index == 5:
            rd = x0
            rs1 = rs1p
        elif index == 6:
            rd = rs1p
            rs1 = rs1p
            rs2 = x0
        elif index == 7:
            rd = x0
            rs1 = rs1p
            rs2 = x0

        return rd, rs1, rs2, x0
    elif quad == 2:
        # q2
        rd = rd_base
        rs1 = sp
        rs2 = rs2

        if index == 0:
            rs1 = rd_base
        elif index == 4:
            # print(raw.bin, raw[-13])
            if raw[-13]:
                # jalr_add
                if rs2 != 0:
                    # add
                    rs1 = rd_base
                else:
                    rd = ra
                    rs1 = rd_base
            else:
                # jr_mv
                if rs2 != 0:
                    # mv
                    # print('mv insn detected')
                    rs1 = x0
                else:
                    # jar
                    rd = x0
                    rs1 = rd_base

        return rd, rs1, rs2, x0


class RISCVInstruction:
    def __init__(self, pc, raw, insn, args):
        self.pc = pc
        self.raw = BitArray(uint=raw, length=32)
        self.insn = insn
        self.args = args

        # print(self.raw)

        if self.raw[-2:].uint != 3:
            # RVC
            self.rd, self.rs1, self.rs2, self.rs3 = rvc_regs(self.raw)
        else:
            # if not RVC, registers are in obvious places
            self.rd = self.raw[-12:-7].uint
            self.rs1 = self.raw[-20:-15].uint
            # assert self.rs1 == 18, self.raw
            # print(self.raw)
            self.rs2 = self.raw[-25:-20].uint
            self.rs3 = self.raw[-32:-27].uint

    def is_compressed(self):
        """This is actually backed up by the spec"""
        return self.raw.uint & 0x3 != 3

    def is_control_flow(self):
        """Simple way of testing"""
        if self.insn.startswith('b') or self.insn.startswith('j'):
            return True
        else:
            if self.insn[0] in 'BCJ':
                print(self.insn)
            return False

    def is_slli(self):
        return self.insn == 'slli'

    def is_srli(self):
        return self.insn == 'srli'

    def is_ld(self):
        return self.insn in ('ld', 'lw', 'lwu', 'lh', 'lhu', 'lb', 'lbu')

    def is_add(self):
        return self.insn == 'add'

    def is_addi(self):
        return self.insn in ('addi', 'mv')

    def __str__(self):
        return "%x: %x %s %s" % (self.pc, self.raw.uint, self.insn, ",".join(self.args))

    def __repr__(self):
        return str(self)
