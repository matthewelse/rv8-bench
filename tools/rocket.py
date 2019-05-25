from dataclasses import dataclass

from .riscv import RISCVInstruction
from .instructions import mask_matches
from .rocket_consts import RocketSignal, ALU_FN

from .rocket_signals import signals
from . import rvc
from .utils import pairwise

def signals_for_insn(insn: RISCVInstruction) -> RocketSignal:
    if insn.is_compressed():
        # complicated urgh
        matches = set()

        for name, (mask, match) in rvc.mask_matches.items():
            if insn.raw.uint & mask == match:
                matches.add(name)

        if len(matches) > 1:
            if matches <= {'C_LUI', 'C_ADDI16SP'}:
                if insn.rd in {0, 2}:
                    match = 'C_ADDI16SP'
                    assert insn.insn == 'addi', insn
                else:
                    match = 'C_LUI'
                    assert insn.insn == 'lui', insn
            elif matches <= {'C_JALR', 'C_ADD', 'C_EBREAK'}:
                if insn.rs1 == 0 and insn.rs2 == 0:
                    match = 'C_EBREAK'
                    assert insn.insn == 'ebreak'
                elif insn.rs1 != 0 and insn.rs2 == 0:
                    match = 'C_JALR'
                    assert insn.insn == 'jalr'
                else:
                    match = 'C_ADD'
                    assert insn.insn == 'add' 
            # elif matches == 
            else:
                print(insn, matches)
                raise RuntimeError()
        else:
            if len(matches) == 0:
                print(insn)
                raise RuntimeError()
            match = matches.pop()

        expanded = rvc.expands[match]
        return expanded, signals[expanded]
    else:
        for name, (mask, match) in mask_matches.items():
            if insn.raw.uint & mask == match:
                return name, signals[name]


@dataclass
class DualIssueConfig:    
    # extra_alu => extra_alu_branches
    # extra_alu_branches => just fuse branch instructions.
    extra_alu_branches: bool = False
    extra_alu: bool = False
    
    can_share_reads: bool = False
    can_forward_reads: bool = False

    integer_read_ports: int = 2
    integer_write_ports: int = 1

    # Number of pipeline stages we can forward from
    forwarding_cycles: int = 3

    float_read_ports: int = 3
    float_write_ports: int = 1

    def alu_stage(self):
        if self.extra_alu:
            return '2 x ALU'
        elif self.extra_alu_branches:
            return 'ALU + branch'
        else:
            return 'ALU'

    def reg_stage(self):
        parts = []

        if self.can_share_reads:
            parts.append('share')
        if self.can_forward_reads:
            parts.append('forward')
        if self.integer_read_ports > 2:
            extra = self.integer_read_ports - 2

            if extra == 1:
                parts.append('read port')
            else:
                parts.append('{} read ports'.format(extra))
        if self.integer_write_ports > 1:
            extra = self.integer_write_ports - 1

            if extra == 1:
                parts.append('write port')
            else:
                parts.append('{} write ports'.format(extra))

        if len(parts) > 0:
            return ' + '.join(parts)
        else:
            return 'baseline'

    def describe(self):
        return '{}, {}'.format(self.alu_stage(), self.reg_stage())


def read_regs(insn: RISCVInstruction, signal: RocketSignal):
    regs = set()

    if signal.rxs1:
        regs.add(insn.rs1)
    if signal.rxs2:
        regs.add(insn.rs2)

    return regs

def float_regs(insn: RISCVInstruction, signal: RocketSignal):
    regs = set()

    if signal.rfs1:
        regs.add(insn.rs1)
    if signal.rfs2:
        regs.add(insn.rs2)
    if signal.rfs3:
        regs.add(insn.rs3)

    return regs

def simulate_dual_issue(insns: [(RISCVInstruction, RocketSignal)], settings: DualIssueConfig) -> int:
    available_alus = 2 if settings.extra_alu or settings.extra_alu_branches else 1
    available_fpus = 1
    available_x_write_ports = settings.integer_write_ports
    available_x_read_ports = settings.integer_read_ports
    mem_write_ports = 1

    forwarding_primary = [None] * settings.forwarding_cycles
    forwarding_dual = [None] * settings.forwarding_cycles

    can_dual_issue = False

    for (fi, (fn, f)), (si, (sn, s)) in pairwise(insns):
        if can_dual_issue:
            # print('Skip: can dual issue')
            can_dual_issue = False
            continue

        can_dual_issue = True
        verbose = False
        
        # if fi.insn.startswith('fadd') and s.wxd:
        #     verbose = True
        #     print(fi, si, fn, sn)
        # elif si.insn.startswith('fadd') and f.wxd:
        #     verbose = True
        #     print(fi, si, fn, sn)

        if f.branch or f.jal or f.jalr:
            if verbose:
                print('f.branch or f.jal or f.jalr')
            can_dual_issue = False

            forwarding_primary.pop(0)
            forwarding_primary.append(fi.rd if f.wxd else None)

            forwarding_dual.pop(0)
            forwarding_dual.append(None)

            continue

        # check the ALU
        alu_uses = 0

        if f.alu_fn != ALU_FN.X:
            alu_uses += 1
        if s.alu_fn != ALU_FN.X:
            alu_uses += 1

        if verbose:
            print('f.alu_fn = {}, s.alu_fn = {}'.format(f.alu_fn, s.alu_fn))

        if alu_uses > available_alus:
            if verbose:
                print('alu_uses > available_alus')

            can_dual_issue = False

            forwarding_primary.pop(0)
            forwarding_primary.append(fi.rd if f.wxd else None)

            forwarding_dual.pop(0)
            forwarding_dual.append(None)

            continue

        if not settings.extra_alu and alu_uses > 1:
            # check that the second instruction is a branch
            if not s.branch or not settings.extra_alu_branches:
                if verbose:
                    print('not branch or no extra branches')
                can_dual_issue = False

                forwarding_primary.pop(0)
                forwarding_primary.append(fi.rd if f.wxd else None)

                forwarding_dual.pop(0)
                forwarding_dual.append(None)

                continue

        # check the FPU
        fpu_uses = 0

        if f.fp:
            fpu_uses += 1
        if s.fp:
            fpu_uses += 1

        if fpu_uses > available_fpus:
            if verbose:
                print('fpu_uses > available_fpus')

            can_dual_issue = False

            forwarding_primary.pop(0)
            forwarding_primary.append(fi.rd if f.wxd else None)

            forwarding_dual.pop(0)
            forwarding_dual.append(None)

            continue

        # check register writes
        x_reg_writes = 0

        if f.wxd:
            x_reg_writes += 1
        if s.wxd:
            x_reg_writes += 1

        if x_reg_writes > available_x_write_ports:
            if verbose:
                print('x_reg_writes > available_x_write_ports')

            can_dual_issue = False

            forwarding_primary.pop(0)
            forwarding_primary.append(fi.rd if f.wxd else None)

            forwarding_dual.pop(0)
            forwarding_dual.append(None)

            continue

        # check register reads
        x_reg_reads = set()

        f_regs = read_regs(fi, f)
        s_regs = read_regs(si, s)

        # if f.wxd:
        # print(fi.rd, s_regs)

        if f.wxd and fi.rd in s_regs:
            # dependent instructions
            can_dual_issue = False
            continue

        # float dependency
        f_fp_regs = float_regs(fi, f)
        s_fp_regs = float_regs(si, s)

        if f.wfd and fi.rd in s_fp_regs:
            can_dual_issue = False
            continue



        if not settings.can_share_reads:
            if len(f_regs) + len(s_regs) > available_x_read_ports:

                # if s.fp:
                #     print('FP second and too many reg reads')

                can_dual_issue = False

                forwarding_primary.pop(0)
                forwarding_primary.append(fi.rd if f.wxd else None)

                forwarding_dual.pop(0)
                forwarding_dual.append(None)

                continue
        else:
            regs = f_regs | s_regs

            if settings.can_forward_reads:
                # look at the last few register writes

                regs -= set(forwarding_primary)
                regs -= set(forwarding_dual)

            if len(regs) > available_x_read_ports:
                can_dual_issue = False

                

                forwarding_primary.pop(0)
                forwarding_primary.append(fi.rd if f.wxd else None)

                forwarding_dual.pop(0)
                forwarding_dual.append(None)

                continue

        # memory accesses
        mem_count = int(f.mem) + int(s.mem)

        if mem_count > mem_write_ports:
            can_dual_issue = False
            continue

        assert can_dual_issue

        # print('Can dual issue: {} and {} ({}, {})'.format(fi, si, fn, sn))

        forwarding_primary.pop(0)
        forwarding_primary.append(fi.rd if f.wxd else None)

        forwarding_dual.pop(0)
        forwarding_dual.append(si.rd if s.wxd else None)

        yield fi.pc

