CLANG       := clang
MAIN        := echo
TARGET      := lambda-$(MAIN)

CC          := $(CLANG)
C_OPT       := -Oz -ffunction-sections -fdata-sections
C_INC       :=
C_STD       := -std=c17
C_WARN      := -Wall -Wextra
C_SAN       :=
C_LINK      := -Wl,--gc-sections
C_FLAGS     := $(C_OPT) $(C_SAN) $(C_INC) $(C_STD) $(C_WARN)

MAIN_LL     := build/$(MAIN).main.ll
LANG_SRC    := $(wildcard src/*.lambda)
C_SRC       := $(wildcard src/*.c)

LANG_DEPS   := build/$(MAIN).ll.d
C_DEPS      := $(C_SRC:src/%.c=build/%.c.d)
DEPS        := $(LANG_DEPS) $(C_DEPS)
OBJECTS     := $(MAIN_LL:build/%.ll=build/%.ll.o) $(LANG_SRC:src/%.lambda=build/%.ll.o) $(C_SRC:src/%.c=build/%.c.o)

.PHONY: all clean
all: build/$(TARGET) build/$(TARGET).stripped

clean:
	rm -rf build

build:
	mkdir -p $@

build/%.hlir:
	lambda-lang2hlir -P build/ -o $@ $<

build/%.hlis: build/%.hlir
	lambda-hlir2hlis -o $@ $<

build/%.mlir: build/%.hlir
	lambda-hlir2mlir -o $@ $<

build/%.opt.mlir: build/%.mlir
	lambda-mlir2opt -P build/ -o $@ $<

build/%.ll: build/%.opt.mlir
	lambda-mlir2llir -o $@ $<

build/%.main.ll: build/%.opt.mlir
	lambda-mlir2main -P build/ -o $@ $<

build/%.ll.d: src/%.lambda | build
	lambda-lang2deps -O build/ -P src/ -o $@ $<

build/%.ll.o: build/%.ll
	$(CLANG) $(C_OPT) $(C_SAN) -c -o $@ $<

build/%.c.d: src/%.c | build
	$(CC) -MM -MT build/$*.c.o -MP -MF $@ $<

build/%.c.o: src/%.c
	$(CC) $(C_FLAGS) -c -o $@ $<

build/$(TARGET): $(OBJECTS)
	$(CC) $(C_LINK) $(C_FLAGS) -o $@ $^

build/$(TARGET).stripped: build/$(TARGET)
	strip -s -o $@ $^

$(DEPS):

include $(DEPS)
