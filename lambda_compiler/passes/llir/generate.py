from __future__ import annotations
from typing import *
from dataclasses import dataclass, field
from collections import defaultdict

from .runtime import lambda_runtime_llir
from .target import Architecture
from ...ast.mlir import *

class GenerateLLIRError(Exception):
    pass

@dataclass
class InstanceType:
    id: int

    def __str__(self) -> str:
        return f"%lambda_c{self.id}"

    def __repr__(self) -> str:
        return str(self)

@dataclass
class IndexFactory:
    index: int = 0

    ARG = CaptureLiteral(0)
    SELF = CaptureLiteral(1)
    CONT = CaptureLiteral(2)

    def skip(self, n: int):
        self.index += n

    def next(self) -> ValueLiteral:
        id = self.index
        self.index += 1

        return CaptureLiteral(id)

@dataclass
class RealizedLiteral:
    pass

@dataclass
class SimpleLiteral(RealizedLiteral):
    lit: ValueLiteral

@dataclass
class ImplConstruction(RealizedLiteral):
    lit: ValueLiteral

@dataclass
class ValueUses:
    capture_uses: DefaultDict[int, int] = field(default_factory = lambda: defaultdict(int))
    extern_uses: DefaultDict[str, int] = field(default_factory = lambda: defaultdict(int))
    def_uses: DefaultDict[Path, int] = field(default_factory = lambda: defaultdict(int))
    inst_uses: DefaultDict[InstancePath, int] = field(default_factory = lambda: defaultdict(int))
    impl_uses: DefaultDict[ImplementationPath, int] = field(default_factory = lambda: defaultdict(int))

    @staticmethod
    def count_uses(impl: Implementation) -> ValueUses:
        uses = ValueUses()

        uses.capture_uses[0] = 0
        uses.count_impl(impl)
        return uses

    def count_impl(self, impl: Implementation):
        match impl:
            case ReturnImplementation() as impl:
                self.count_lit(impl.value)
            case TailCallImplementation() as impl:
                self.count_lit(impl.fn)
                self.count_lit(impl.arg)
            case ContinueCallImplementation() as impl:
                self.count_lit(impl.fn)
                self.count_lit(impl.arg)
                self.count_lit(impl.next)
            case _:
                raise GenerateLLIRError(f"unexpected AST node encountered: {impl}")

    def count_lit(self, lit: ValueLiteral):
        match lit:
            case CaptureLiteral(id):
                self.capture_uses[id] += 1
            case ExternLiteral(name):
                self.extern_uses[name] += 1
            case DefinitionLiteral(path):
                self.def_uses[path] += 1
            case InstanceLiteral(inst):
                self.inst_uses[inst] += 1
            case ImplementationLiteral(impl, captures):
                self.count_impl_construction(impl, captures)
            case _:
                raise GenerateLLIRError(f"unexpected AST node encountered: {lit}")

    def count_impl_construction(self, impl: ImplementationPath, captures: List[int | InstancePath]):
        self.impl_uses[impl] += 1
        for cap in captures:
            match cap:
                case InstancePath():
                    self.inst_uses[cap] += 1
                case int():
                    self.capture_uses[cap] += 1

@dataclass
class GenerateLLIRContext:
    arch: Architecture

    llir: str = ""
    instance_type_cache: Set[int] = field(default_factory = set)
    extern_cache: Set[str] = field(default_factory = set)
    global_cache: Set[Path] = field(default_factory = set)
    inst_cache: Set[InstancePath] = field(default_factory = set)
    impl_cache: Set[ImplementationPath] = field(default_factory = set)
    init_cache: List[Definition] = field(default_factory = list)

    def mangle_crate_init(self, crate: str) -> str:
        return f"_L{len(crate)}I{crate}"

    def mangle_crate_fini(self, crate: str) -> str:
        return f"_L{len(crate)}F{crate}"

    def mangle_path(self, path: Path) -> str:
        return "_L" + "".join(f"{len(name)}N{name}" for name in path.components)

    def mangle_def(self, defi: Definition) -> str:
        return f"{self.mangle_path(defi.path)}"

    def mangle_inst(self, inst: InstancePath, alt: bool) -> str:
        alt_str = "X" if alt else ""
        return f"{self.mangle_path(inst.path)}G{inst.id}{alt_str}"

    def mangle_impl(self, impl: ImplementationPath) -> str:
        return f"{self.mangle_path(impl.path)}L{impl.lambda_id}I{impl.continuation_id}"

    def mangle_lit(self, lit: ValueLiteral) -> str:
        match lit:
            case CaptureLiteral(id):
                return f"%{id}"
            case InstanceLiteral(inst):
                return f"@{self.mangle_inst(inst, alt=False)}"
            case _:
                raise GenerateLLIRError(f"unexpected literal type: {lit}")

    def declare_global(self, path: Path):
        self.global_cache.add(path)

    def declare_inst(self, inst: InstancePath):
        self.inst_cache.add(inst)

    def declare_impl(self, impl: ImplementationPath):
        self.impl_cache.add(impl)

    def write_runtime(self):
        self.llir += lambda_runtime_llir.format(
            triple = self.arch.triple,
            data_layout = self.arch.data_layout,
            ptr_bits = self.arch.ptr_size * 8,
            ptr_align = self.arch.ptr_align
        )

    def write_extern(self, name: str):
        if name not in self.extern_cache:
            self.llir += f"@{name} = external dso_local global %lambda*, align {self.arch.ptr_align}\n"
            self.extern_cache.add(name)

    def write_global(self, path: Path):
        if path not in self.global_cache:
            self.llir += f"@{self.mangle_path(path)} = external dso_local global %lambda*, align {self.arch.ptr_align}\n"
            self.global_cache.add(path)

    def write_inst(self, inst: InstancePath):
        if inst not in self.inst_cache:
            self.llir += f"@{self.mangle_inst(inst, alt=False)} = external dso_local global %lambda, align {self.arch.ptr_align}\n"
            self.inst_cache.add(inst)

    def write_impl(self, impl: ImplementationPath):
        if impl not in self.impl_cache:
            self.llir += f"declare external dso_local %lambda* @{self.mangle_impl(impl)}(%lambda*, %lambda*, %lambda_cont*) unnamed_addr\n"
            self.impl_cache.add(impl)

    def write_instance_type(self, captures: int) -> InstanceType:
        inst_type = InstanceType(captures)

        if captures not in self.instance_type_cache:
            self.llir += f"{inst_type} = type {{ %lambda_header, [ {captures} x %lambda* ] }}\n"
            self.instance_type_cache.add(captures)

        return inst_type

    def write_load_realized_literal(self, lit: RealizedLiteral, index_factory: IndexFactory) -> ValueLiteral:
        match lit:
            case SimpleLiteral(simple_lit):
                return self.write_load_literal(simple_lit, index_factory)
            case ImplConstruction(lamb):
                return lamb
            case _:
                raise GenerateLLIRError(f"unexpected literal type: {lit}")

    def write_load_literal(self, lit: ValueLiteral, index_factory: IndexFactory) -> ValueLiteral:
        match lit:
            case CaptureLiteral(id):
                if id == 0:
                    return IndexFactory.ARG
                else:
                    return self.write_load_capture(index_factory, id - 1)
            case ExternLiteral(name):
                return self.write_load_extern(index_factory, name)
            case DefinitionLiteral(path):
                return self.write_load_global(index_factory, path)
            case InstanceLiteral(inst):
                return lit
            case _:
                raise GenerateLLIRError(f"unexpected literal type: {lit}")


    def write_lambda_ref(self, lit: ValueLiteral, refcount: int):
        self.llir += "    call void @lambda_ref(%lambda* {value}, i{ptr_bits} {refcount})\n".format(
            value = self.mangle_lit(lit),
            refcount = refcount,
            ptr_bits = self.arch.ptr_size * 8
        )

    def write_lambda_unref(self, lit: ValueLiteral):
        self.llir += "    call void @lambda_unref(%lambda* {value})\n".format(
            value = self.mangle_lit(lit)
        )

    def write_lambda_alloc(self, index_factory: IndexFactory, len_captures: int) -> ValueLiteral:
        index = index_factory.next()
        self.llir += "    {index} = call %lambda* @lambda_alloc(i{ptr_bits} {len_captures}, i{ptr_bits} 0)\n".format(
            index = self.mangle_lit(index),
            len_captures = len_captures,
            ptr_bits = self.arch.ptr_size * 8
        )
        return index

    def write_lambda_cont_alloc(self, index_factory: IndexFactory, next: ValueLiteral) -> ValueLiteral:
        index = index_factory.next()
        self.llir += "    {index} = call %lambda_cont* @lambda_cont_alloc(%lambda_cont* {cont}, %lambda* {next})\n".format(
            index = self.mangle_lit(index),
            cont = self.mangle_lit(IndexFactory.CONT),
            next = self.mangle_lit(next)
        )
        return index

    def write_lambda_call(self, index_factory: IndexFactory, fn: ValueLiteral, arg: ValueLiteral, next: ValueLiteral) -> ValueLiteral:
        index = index_factory.next()
        self.llir += "    {index} = tail call %lambda* @lambda_call(%lambda* {fn}, %lambda* {arg}, %lambda_cont* {next})\n".format(
            index = self.mangle_lit(index),
            fn = self.mangle_lit(fn),
            arg = self.mangle_lit(arg),
            next = self.mangle_lit(next)
        )
        return index

    def write_lambda_cont_call(self, index_factory: IndexFactory, value: ValueLiteral) -> ValueLiteral:
        index = index_factory.next()
        self.llir += "    {index} = tail call %lambda* @lambda_cont_call(%lambda* {value}, %lambda_cont* {cont})\n".format(
            index = self.mangle_lit(index),
            value = self.mangle_lit(value),
            cont = self.mangle_lit(IndexFactory.CONT)
        )
        return index

    def write_lambda_null_call(self, index_factory: IndexFactory, value: ValueLiteral) -> ValueLiteral:
        index = index_factory.next()
        self.llir += "    {index} = tail call %lambda* @lambda_null_call(%lambda* {value})\n".format(
            index = self.mangle_lit(index),
            value = self.mangle_lit(value)
        )
        return index

    def write_capture_ptr(self, index_factory: IndexFactory, lamb: ValueLiteral, capture_index: int) -> ValueLiteral:
        index = index_factory.next()
        self.llir += "    {index} = getelementptr inbounds %lambda, %lambda* {lamb}, i{ptr_bits} 0, i32 1, i{ptr_bits} {capture_index}\n".format(
            index = self.mangle_lit(index),
            lamb = self.mangle_lit(lamb),
            capture_index = capture_index,
            ptr_bits = self.arch.ptr_size * 8
        )
        return index

    def write_load_capture(self, index_factory: IndexFactory, capture_index: int) -> ValueLiteral:
        ptr_index = self.write_capture_ptr(index_factory, IndexFactory.SELF, capture_index)
        index = index_factory.next()
        self.llir += "    {index} = load %lambda*, %lambda** {ptr_index}, align {ptr_align}\n".format(
            index = self.mangle_lit(index),
            ptr_index = self.mangle_lit(ptr_index),
            ptr_align = self.arch.ptr_align
        )
        return index

    def write_store_capture(self, index_factory: IndexFactory, value: ValueLiteral, lamb: ValueLiteral, capture_index: int):
        ptr_index = self.write_capture_ptr(index_factory, lamb, capture_index)
        self.llir += "    store %lambda* {value}, %lambda** {ptr_index}, align {ptr_align}\n".format(
            value = self.mangle_lit(value),
            ptr_index = self.mangle_lit(ptr_index),
            ptr_align = self.arch.ptr_align
        )

    def write_store_impl(self, index_factory: IndexFactory, impl: ImplementationPath, lamb: ValueLiteral):
        ptr_index = index_factory.next()
        self.llir += "    {ptr_index} = getelementptr inbounds %lambda, %lambda* {lamb}, i{ptr_bits} 0, i32 0, i32 3\n".format(
            lamb = self.mangle_lit(lamb),
            ptr_index = self.mangle_lit(ptr_index),
            ptr_bits = self.arch.ptr_size * 8
        )
        self.llir += "    store %lambda_fn* @{impl_path}, %lambda_fn** {ptr_index}, align {ptr_align}\n".format(
            impl_path = self.mangle_impl(impl),
            ptr_index = self.mangle_lit(ptr_index),
            ptr_align = self.arch.ptr_align
        )

    def write_load_extern(self, index_factory: IndexFactory, name: str) -> ValueLiteral:
        index = index_factory.next()
        self.llir += "    {index} = load %lambda*, %lambda** @{name}, align {ptr_align}\n".format(
            index = self.mangle_lit(index),
            name = name,
            ptr_align = self.arch.ptr_align
        )
        return index

    def write_load_global(self, index_factory: IndexFactory, path: Path) -> ValueLiteral:
        index = index_factory.next()
        self.llir += "    {index} = load %lambda*, %lambda** @{path}, align {ptr_align}\n".format(
            index = self.mangle_lit(index),
            path = self.mangle_path(path),
            ptr_align = self.arch.ptr_align
        )
        return index

    def write_store_global(self, index_factory: IndexFactory, path: Path, value: ValueLiteral):
        self.llir += "    store %lambda* {value}, %lambda** @{path}, align {ptr_align}\n".format(
            value = self.mangle_lit(value),
            path = self.mangle_path(path),
            ptr_align = self.arch.ptr_align
        )

    def write_crate_init_fini(self, crate: str):
        self.llir += "define external dso_local void @{crate_init}() unnamed_addr {{\n".format(
            crate_init = self.mangle_crate_init(crate)
        )

        index_factory = IndexFactory()
        index_factory.next()

        for defi in self.init_cache:
            lit = InstanceLiteral(defi.inst)
            self.write_lambda_ref(lit, 1)
            index = self.write_lambda_null_call(index_factory, lit)
            self.write_store_global(index_factory, defi.path, index)

        self.llir += "    ret void\n"
        self.llir += "}\n"
        self.llir += "\n"

        self.llir += "define external dso_local void @{crate_fini}() unnamed_addr {{\n".format(
            crate_fini = self.mangle_crate_fini(crate)
        )

        index_factory = IndexFactory()
        index_factory.next()

        for defi in reversed(self.init_cache):
            index = self.write_load_global(index_factory, defi.path)
            self.write_lambda_unref(index)

        self.llir += "    ret void\n"
        self.llir += "}\n"
        self.llir += "\n"


def generate_llir(prog: List[Statement], crate: str, arch: Architecture) -> str:
    def visit_program(prog: List[Statement]) -> str:
        ctx = GenerateLLIRContext(arch)

        ctx.write_runtime()
        ctx.llir += "\n"

        for stmt in prog:
            match stmt:
                case ExternCrate() | Extern():
                    pass
                case Definition() as defi:
                    ctx.declare_global(defi.path)
                case Instance() as inst:
                    ctx.declare_inst(inst.path)
                case Implementation() as impl:
                    ctx.declare_impl(impl.path)
                case _:
                    raise GenerateLLIRError(f"unexpected AST node encountered: {stmt}")

        for stmt in prog:
            match stmt:
                case ExternCrate() | Extern():
                    pass
                case Definition() as defi:
                    visit_definition(defi, ctx)
                case Instance() as inst:
                    visit_instance(inst, ctx)
                case Implementation() as impl:
                    visit_implementation(impl, ctx)
                case _:
                    raise GenerateLLIRError(f"unexpected AST node encountered: {stmt}")

            ctx.llir += "\n"

        ctx.write_crate_init_fini(crate)

        return ctx.llir

    def visit_definition(defi: Definition, ctx: GenerateLLIRContext):
        ctx.write_inst(defi.inst)

        ctx.llir += f"@{ctx.mangle_def(defi)} = "

        if not defi.is_public:
            ctx.llir += "internal "

        ctx.llir += "dso_local global %lambda* "

        if defi.needs_init:
            ctx.llir += "null"
            ctx.init_cache.append(defi)
        else:
            ctx.llir += f"@{ctx.mangle_inst(defi.inst, alt=False)}"

        ctx.llir += f", align {ctx.arch.ptr_align}\n"

    def visit_instance(inst: Instance, ctx: GenerateLLIRContext):
        inst_type = ctx.write_instance_type(len(inst.captures))

        for capture in inst.captures:
            ctx.write_inst(capture)

        ctx.write_impl(inst.impl)

        ctx.llir += "@{inst_path_alt} = private dso_local unnamed_addr global {inst_type} {{ %lambda_header {{ i{ptr_bits} 1, i{ptr_bits} {captures}, i{ptr_bits} 0, %lambda_fn* @{impl_path} }}, [ {captures} x %lambda* ] [".format(
            ptr_bits = ctx.arch.ptr_size * 8,
            inst_type = inst_type,
            inst_path_alt = ctx.mangle_inst(inst.path, alt = True),
            impl_path = ctx.mangle_impl(inst.impl),
            captures = len(inst.captures),
        )


        ctx.llir += ",".join(f" %lambda* @{ctx.mangle_inst(capture, alt=False)}" for capture in inst.captures)

        ctx.llir += f" ] }}, align {ctx.arch.ptr_align}\n"

        ctx.llir += "@{inst_path} = external dso_local alias %lambda, %lambda* bitcast({inst_type}* @{inst_path_alt} to %lambda*)\n".format(
            inst_type = inst_type,
            inst_path = ctx.mangle_inst(inst.path, alt = False),
            inst_path_alt = ctx.mangle_inst(inst.path, alt = True),
        )

    def visit_implementation(impl: Implementation, ctx: GenerateLLIRContext):
        uses = ValueUses.count_uses(impl)

        for name in uses.extern_uses.keys():
            ctx.write_extern(name)

        for path in uses.def_uses.keys():
            ctx.write_global(path)

        for inst_path in uses.inst_uses.keys():
            ctx.write_inst(inst_path)

        for impl_path in uses.impl_uses.keys():
            ctx.write_impl(impl_path)

        ctx.llir += "define external dso_local %lambda* @{impl_path}(%lambda* %0, %lambda* %1, %lambda_cont* %2) unnamed_addr {{\n".format(
            impl_path = ctx.mangle_impl(impl.path)
        )

        index_factory = IndexFactory()
        index_factory.skip(4)

        unref_arg = False

        for capture_index, refcount in uses.capture_uses.items():
            if capture_index == 0:
                if refcount == 0:
                    unref_arg = True
                elif refcount > 1:
                    ctx.write_lambda_ref(IndexFactory.ARG, refcount - 1)
            else:
                lit = ctx.write_load_capture(index_factory, capture_index - 1)
                ctx.write_lambda_ref(lit, refcount)

        for inst, refcount in uses.inst_uses.items():
            ctx.write_lambda_ref(InstanceLiteral(inst), refcount)

        for name, refcount in uses.extern_uses.items():
            lit = ctx.write_load_extern(index_factory, name)
            ctx.write_lambda_ref(lit, refcount)

        for path, refcount in uses.def_uses.items():
            lit = ctx.write_load_global(index_factory, path)
            ctx.write_lambda_ref(lit, refcount)

        if unref_arg:
            ctx.write_lambda_unref(IndexFactory.ARG)

        ret_lit: ValueLiteral
        match impl:
            case ReturnImplementation() as impl:
                value_r = visit_literal(impl.value, index_factory, ctx)
                value = ctx.write_load_realized_literal(value_r, index_factory)

                ctx.write_lambda_unref(IndexFactory.SELF)
                ret_lit = ctx.write_lambda_cont_call(index_factory, value)
            case TailCallImplementation() as impl:
                fn_r = visit_literal(impl.fn, index_factory, ctx)
                arg_r = visit_literal(impl.arg, index_factory, ctx)
                fn = ctx.write_load_realized_literal(fn_r, index_factory)
                arg = ctx.write_load_realized_literal(arg_r, index_factory)

                ctx.write_lambda_unref(IndexFactory.SELF)
                ret_lit = ctx.write_lambda_call(index_factory, fn, arg, IndexFactory.CONT)
            case ContinueCallImplementation() as impl:
                fn_r = visit_literal(impl.fn, index_factory, ctx)
                arg_r = visit_literal(impl.arg, index_factory, ctx)
                next_r = visit_literal(impl.next, index_factory, ctx)
                fn = ctx.write_load_realized_literal(fn_r, index_factory)
                arg = ctx.write_load_realized_literal(arg_r, index_factory)
                next = ctx.write_load_realized_literal(next_r, index_factory)

                cont = ctx.write_lambda_cont_alloc(index_factory, next)
                ctx.write_lambda_unref(IndexFactory.SELF)
                ret_lit = ctx.write_lambda_call(index_factory, fn, arg, cont)
            case _:
                raise GenerateLLIRError("unexpected AST node encountered: {impl}")

        ctx.llir += f"    ret %lambda* {ctx.mangle_lit(ret_lit)}\n"
        ctx.llir += "}\n"

    def visit_literal(lit: ValueLiteral, index_factory: IndexFactory, ctx: GenerateLLIRContext) -> RealizedLiteral:
        match lit:
            case ImplementationLiteral(impl, captures):
                lamb = ctx.write_lambda_alloc(index_factory, len(captures))
                ctx.write_store_impl(index_factory, impl, lamb)

                for dest_index, cap in enumerate(captures):
                    match cap:
                        case InstancePath():
                            value = ctx.write_load_literal(InstanceLiteral(cap), index_factory)
                        case int():
                            value = ctx.write_load_literal(CaptureLiteral(cap), index_factory)

                    ctx.write_store_capture(index_factory, value, lamb, dest_index)

                return ImplConstruction(lamb)

        return SimpleLiteral(lit)

    return visit_program(prog)

def generate_main_llir(crates: List[str], arch: Architecture) -> str:
    ctx = GenerateLLIRContext(arch)

    ctx.write_runtime()
    ctx.llir += "\n"

    # global ctors
    for crate in crates:
        ctx.llir += "declare void @{crate_init}() unnamed_addr\n".format(
            crate_init = ctx.mangle_crate_init(crate)
        )

    ctx.llir += "define dso_local void @_LI() {\n"
    for crate in crates:
        ctx.llir += "    tail call void @{crate_init}()\n".format(
            crate_init = ctx.mangle_crate_init(crate)
        )
    ctx.llir += "    ret void\n"
    ctx.llir += "}\n"
    ctx.llir += "\n"

    # global dtors
    for crate in reversed(crates):
        ctx.llir += "declare void @{crate_fini}() unnamed_addr\n".format(
            crate_fini = ctx.mangle_crate_fini(crate)
        )

    ctx.llir += "define dso_local void @_LF() {\n"
    for crate in reversed(crates):
        ctx.llir += "    tail call void @{crate_fini}()\n".format(
            crate_fini = ctx.mangle_crate_fini(crate)
        )
    ctx.llir += "    ret void\n"
    ctx.llir += "}\n"
    ctx.llir += "\n"

    # ctor/dtor declarations
    ctx.llir += "@llvm.global_ctors = appending global [1 x { i32, void()*, i8* }] [{ i32, void()*, i8* } { i32 65535, void()* @_LI, i8* null }]\n"
    ctx.llir += "@llvm.global_dtors = appending global [1 x { i32, void()*, i8* }] [{ i32, void()*, i8* } { i32 65535, void()* @_LF, i8* null }]\n"

    # main
    index_factory = IndexFactory()
    index_factory.next()

    main_crate = crates[-1]
    main_path = Path(()) / main_crate / "main"
    ctx.write_global(main_path)

    ctx.llir += "define dso_local i32 @main() unnamed_addr {\n"
    index = ctx.write_load_global(index_factory, main_path)
    ctx.write_lambda_ref(index, 1)
    ret_index = ctx.write_lambda_null_call(index_factory, index)
    ctx.write_lambda_unref(ret_index)
    ctx.llir += "    ret i32 0\n"
    ctx.llir += "}\n"

    return ctx.llir
