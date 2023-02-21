CLANG       := clang
TARGET      := lambda-crackme
CRATES      := std io crackme

CC          := $(CLANG)
C_OPT       := -Oz -ffunction-sections -fdata-sections
C_INCLUDES  :=
C_STD       := -std=c17
C_WARN      := -Wall -Wextra
C_SAN       :=
C_LINK      := -Wl,--gc-sections
C_FLAGS     := $(C_OPT) $(C_SAN) $(C_INCLUDES) $(C_STD) $(C_WARN)

MAIN_LL     := build/main.ll
HLIR_SRC    := $(wildcard src/*.hlir)
MLIR_SRC    := $(wildcard src/*.mlir)
C_SRC       := $(wildcard src/*.c)

OBJECTS     := $(MAIN_LL:build/%.ll=build/%.ll.o) $(HLIR_SRC:src/%.hlir=build/%.ll.o) $(MLIR_SRC:src/%.mlir=build/%.ll.o) $(C_SRC:src/%.c=build/%.c.o)

.PHONY: all clean
all: build/$(TARGET)

clean:
	rm -rf build

build/%.mlir: src/%.hlir
	@mkdir -p $$(dirname $@)
	lambda-hlir2mlir -o $@ $^

build/%.ll: build/%.mlir
	@mkdir -p $$(dirname $@)
	lambda-mlir2llir -o $@ $^

$(MAIN_LL):
	@mkdir -p $$(dirname $@)
	lambda-llir2main $(CRATES) -o $@

build/%.ll.o: build/%.ll
	$(CLANG) $(C_OPT) $(C_SAN) -c -o $@ $^

build/%.c.o: src/%.c
	@mkdir -p $$(dirname $@)
	$(CC) $(C_FLAGS) -c -o $@ $^

build/$(TARGET): $(OBJECTS)
	$(CC) $(C_LINK) $(C_FLAGS) -o $@ $^
