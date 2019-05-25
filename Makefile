#
# rv8-bench: Macro fusion analysis
#

GNUPREFIX=riscv64-unknown-linux-gnu
PREFIX=/home/melse/Documents/build_clang/llvm/build/bin/
SPIKEPREFIX=/home/melse/Dropbox/Cambridge/iii/project/riscv-isa-sim/build/

CC=$(PREFIX)clang
CXX=$(PREFIX)clang++
LLC=$(PREFIX)llc
DUMP=$(GNUPREFIX)-objdump
SPIKE=LD_LIBRARY_PATH=$(SPIKEPREFIX) $(SPIKEPREFIX)spike

SYSROOT=/home/melse/Documents/build_clang/install_multilib/sysroot 
GCCTOOLCHAIN=/home/melse/Documents/build_clang/install_multilib

SMALLFLAGS=-DBENCH_SMALL

CFLAGS=-O3 -emit-llvm -S --sysroot=$(SYSROOT) --target=$(GNUPREFIX)-gnu --gcc-toolchain=$(GCCTOOLCHAIN) $(SMALLFLAGS) -static -g
ASMFLAGS=--sysroot=$(SYSROOT) --target=$(GNUPREFIX)-gnu --gcc-toolchain=$(GCCTOOLCHAIN) -static 
LDFLAGS=-lstdc++ -latomic -lm -Wl,-Ttext-segment,0x10000

LLCFLAGS=-enable-misched=true -riscv-macro-fusion=true -misched-fusion=true -misched-postra=true -enable-post-misched=true

PROGRAMS=aes bigint dhrystone miniz norx primes qsort sha512

BINARIES=$(addsuffix .O3, $(PROGRAMS)) $(addsuffix .O3.fuse, $(PROGRAMS))

DUMPS=$(addprefix dumps/,$(addsuffix .dump, $(BINARIES)))
ALL_BINS=$(addprefix bin/,$(BINARIES))
HISTOGRAMS=$(addprefix output/,$(addsuffix .err, $(BINARIES)))
ANALYSIS=$(addprefix analysis/,$(BINARIES))
LLS=$(addprefix bin/,$(addsuffix .ll, $(BINARIES)))
ASMS=$(addprefix bin/,$(addsuffix .s, $(BINARIES)))

ANALYSE_ARGS=--percentages $(if $(LIMIT),--limit,)

.PRECIOUS: $(HISTOGRAMS) $(LLS) $(ASMS)
.PHONY: clean all analyse

all: $(ALL_BINS) $(DUMPS) $(ANALYSIS) 

clean: 
	@echo RM bin; rm -rf bin dumps

analyse: $(ANALYSIS)

analysis/%: dumps/%.dump output/%.err
	@python3 analyse_pair.py $(ANALYSE_ARGS) --compiler=clang --name=$* dumps/$*.dump output/$*.err 

analysis/%.fuse: dumps/%.fuse.dump output/%.fuse.err
	@python3 analyse_pair.py $(ANALYSE_ARGS) --compiler=clang_mod --name=$* dumps/$*.fuse.dump output/$*.fuse.err 

bin/%.O3: bin/%.O3.s
	@echo ASM $@
	@$(CC) $(ASMFLAGS) $< $(LDFLAGS) -o $@ 

bin/%.O3.fuse: bin/%.fuse.s
	@echo ASM $@
	$(CC) $(ASMFLAGS) $< $(LDFLAGS) -o $@ 

bin/%.fuse.s: bin/%.ll
	@echo LLC $@
	$(LLC) $< $(LLCFLAGS) -o $@

bin/%.O3.s: bin/%.ll
	@echo LLC $@
	@$(LLC) $< -o $@

bin/%.ll: src/%.c
	@echo CC $@
	@mkdir -p $(@D)
	@$(CC) $(CFLAGS) $< -o $@ 

bin/%.ll: src/%.cc
	@echo CXX $@
	@mkdir -p $(@D)
	@$(CXX) $(CFLAGS) $< -o $@ 

dumps/%.dump: bin/%
	@echo DUMP $@
	@mkdir -p $(@D)
	@$(DUMP) -d $< > $@  

output/%.err: bin/%
	@echo RUN $@
	@mkdir -p $(@D)
	@$(SPIKE) -g pk $< > output/$*.out 2> $@

