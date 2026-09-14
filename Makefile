obj-m += src/gpu_uvoc_mt6789.o

KDIR ?= /lib/modules/$(shell uname -r)/build
ARCH ?= $(shell uname -m | sed -e 's/x86_64/x86/' -e 's/aarch64/arm64/')
LLVM ?= 0
CROSS_COMPILE ?=
OPP ?= 1200

all: src/opp_table.h
	$(MAKE) -C $(KDIR) ARCH=$(ARCH) $(if $(filter 1,$(LLVM)),LLVM=1) $(if $(CROSS_COMPILE),CROSS_COMPILE=$(CROSS_COMPILE)) M=$(PWD) modules

# Generate default OPP table (1200-1700 step 50). Example: make gen OPP=1500
gen:
	python3 tools/gen_opp.py $(OPP) > src/opp_table.h

src/opp_table.h:
	python3 tools/gen_opp.py $(OPP) > src/opp_table.h

clean:
	$(MAKE) -C $(KDIR) ARCH=$(ARCH) M=$(PWD) clean
