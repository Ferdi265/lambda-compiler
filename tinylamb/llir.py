from __future__ import annotations
from dataclasses import dataclass, field
from collections import defaultdict
from typing import *

from .dedup import *
from .llir_runtime import *

class GenerateLLIRError(Exception):
    pass

@dataclass
class Architecture:
    triple: str
    data_layout: str
    ptr_size: int
    ptr_align: int

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

    ARG = AnonymousLiteral(0)
    SELF = AnonymousLiteral(1)
    CONT = AnonymousLiteral(2)

    def skip(self, n: int):
        self.index += n

    def next(self) -> ValueLiteral:
        id = self.index
        self.index += 1

        return AnonymousLiteral(id)

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
    inst_uses: DefaultDict[Tuple[Path, int], int] = field(default_factory = lambda: defaultdict(int))
    global_uses: DefaultDict[Path, int] = field(default_factory = lambda: defaultdict(int))

    inst_table: Dict[Tuple[Path, int], Instance] = field(default_factory = dict)

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

    def count_lit(self, lit: ValueLiteral):
        match lit:
            case AnonymousLiteral(id):
                self.capture_uses[id] += 1
            case IdentLiteral(ExternGlobal(ident)):
                self.extern_uses[ident] += 1
            case InstanceLiteral(inst):
                self.inst_uses[(inst.path, inst.inst_id)] += 1
                self.inst_table[(inst.path, inst.inst_id)] = inst
            case ImplementationLiteral(impl):
                self.count_impl_construction(impl)
            case PathLiteral(PathGlobal(path)):
                self.global_uses[path] += 1

    def count_impl_construction(self, impl: Implementation):
        for id in impl.anonymous_captures:
            self.capture_uses[id] += 1

    def get_instance(self, key: Tuple[Path, int]) -> Instance:
        return self.inst_table[key]

@dataclass
class GenerateLLIRContext:
    arch: Architecture

    llir: str = ""
    instance_type_cache: OrderedSet[int] = field(default_factory = OrderedSet)
    extern_cache: OrderedSet[str] = field(default_factory = OrderedSet)
    global_cache: OrderedSet[Path] = field(default_factory = OrderedSet)
    init_cache: List[InstanceDefinition] = field(default_factory = list)

    def mangle_crate_init(self, crate: Path) -> str:
        assert len(crate.components) == 1
        crate_name = crate.components[0]
        return f"_L{len(crate_name)}I{crate_name}"

    def mangle_crate_fini(self, crate: Path) -> str:
        assert len(crate.components) == 1
        crate_name = crate.components[0]
        return f"_L{len(crate_name)}F{crate_name}"

    def mangle_path(self, path: Path) -> str:
        return "_L" + "".join(f"{len(name)}N{name}" for name in path.components)

    def mangle_def(self, inst_def: InstanceDefinition) -> str:
        return f"{self.mangle_path(inst_def.path)}"

    def mangle_inst(self, inst: Instance, alt: bool) -> str:
        alt_str = "X" if alt else ""
        return f"{self.mangle_path(inst.path)}G{inst.inst_id}{alt_str}"

    def mangle_impl(self, impl: Implementation) -> str:
        return f"{self.mangle_path(impl.path)}L{impl.lambda_id}I{impl.continuation_id}"

    def mangle_lit(self, lit: ValueLiteral) -> str:
        match lit:
            case AnonymousLiteral(id):
                return f"%{id}"
            case InstanceLiteral(inst):
                return f"@{self.mangle_inst(inst, alt=False)}"
            case _:
                raise GenerateLLIRError(f"unexpected literal type: {lit}")

    def declare_global(self, path: Path):
        self.global_cache.add(path)

    def write_runtime(self):
        self.llir += lambda_runtime_llir.format(
            triple = self.arch.triple,
            data_layout = self.arch.data_layout,
            ptr_bits = self.arch.ptr_size * 8,
            ptr_align = self.arch.ptr_align
        )

    def write_global(self, path: Path):
        if path not in self.global_cache:
            self.llir += f"@{self.mangle_path(path)} = external global %lambda*, align {self.arch.ptr_align}\n"
            self.global_cache.add(path)

    def write_extern(self, name: str):
        if name not in self.extern_cache:
            self.llir += f"@{name} = external global %lambda*, align {self.arch.ptr_align}\n"
            self.extern_cache.add(name)

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
            case AnonymousLiteral(id):
                if id == 0:
                    return IndexFactory.ARG
                else:
                    return self.write_load_capture(index_factory, id - 1)
            case IdentLiteral(ExternGlobal(name)):
                return self.write_load_extern(index_factory, name)
            case PathLiteral(PathGlobal(path)):
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

    def write_store_impl(self, index_factory: IndexFactory, impl: Implementation, lamb: ValueLiteral):
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

    def write_crate_init_fini(self, crate: Path):
        self.llir += "define external dso_local void @{crate_init}() unnamed_addr {{\n".format(
            crate_init = self.mangle_crate_init(crate)
        )

        index_factory = IndexFactory()
        index_factory.next()

        for inst_def in self.init_cache:
            index = index_factory.next()
            self.write_lambda_ref(InstanceLiteral(inst_def.inst), 1)
            self.llir += "    {index} = call %lambda* @lambda_null_call(%lambda* @{inst_path})\n".format(
                index = self.mangle_lit(index),
                inst_path = self.mangle_inst(inst_def.inst, alt = False)
            )
            self.llir += "    store %lambda* {index}, %lambda** @{inst_def_path}, align {ptr_align}\n".format(
                index = self.mangle_lit(index),
                inst_def_path = self.mangle_def(inst_def),
                ptr_align = self.arch.ptr_align
            )

        self.llir += "    ret void\n"
        self.llir += "}\n"
        self.llir += "\n"

        self.llir += "define external dso_local void @{crate_fini}() unnamed_addr {{\n".format(
            crate_fini = self.mangle_crate_fini(crate)
        )

        index_factory = IndexFactory()
        index_factory.next()

        for inst_def in reversed(self.init_cache):
            index = index_factory.next()
            self.llir += "    {index} = load %lambda*, %lambda** @{inst_def_path}, align {ptr_align}\n".format(
                index = self.mangle_lit(index),
                inst_def_path = self.mangle_def(inst_def),
                ptr_align = self.arch.ptr_align
            )
            self.llir += "    call void @lambda_unref(%lambda* {index})\n".format(
                index = self.mangle_lit(index)
            )

        self.llir += "    ret void\n"
        self.llir += "}\n"
        self.llir += "\n"


def generate_llir(prog: List[Statement], crate: Path, arch: Architecture) -> str:
    def visit_program(prog: List[Statement]) -> str:
        ctx = GenerateLLIRContext(arch)

        ctx.write_runtime()
        ctx.llir += "\n"

        for stmt in prog:
            match stmt:
                case InstanceDefinition() as inst_def:
                    ctx.declare_global(inst_def.path)

        for stmt in prog:
            match stmt:
                case InstanceDefinition() as inst_def:
                    visit_definition(inst_def, ctx)
                case Instance() as inst:
                    visit_instance(inst, ctx)
                case Implementation() as impl:
                    visit_implementation(impl, ctx)

            ctx.llir += "\n"

        ctx.write_crate_init_fini(crate)

        return ctx.llir

    def visit_definition(inst_def: InstanceDefinition, ctx: GenerateLLIRContext):
        ctx.llir += f"@{ctx.mangle_def(inst_def)} = "

        # TODO: visibility

        ctx.llir += "dso_local global %lambda* "

        if inst_def.needs_init:
            ctx.llir += "null"
            ctx.init_cache.append(inst_def)
        else:
            ctx.llir += f"@{ctx.mangle_inst(inst_def.inst, alt=False)}"

        ctx.llir += f", align {ctx.arch.ptr_align}\n"

    def visit_instance(inst: Instance, ctx: GenerateLLIRContext):
        inst_type = ctx.write_instance_type(len(inst.captures))

        ctx.llir += "@{inst_path_alt} = private dso_local unnamed_addr global {inst_type} {{ %lambda_header {{ i{ptr_bits} 1, i{ptr_bits} {captures}, i{ptr_bits} 0, %lambda_fn* @{impl_path} }}, [ {captures} x %lambda* ] [".format(
            ptr_bits = ctx.arch.ptr_size * 8,
            inst_type = inst_type,
            inst_path_alt = ctx.mangle_inst(inst, alt = True),
            impl_path = ctx.mangle_impl(inst.impl),
            captures = len(inst.captures),
        )

        ctx.llir += ",".join(f" %lambda* @{capture.path}" for capture in inst.captures)

        ctx.llir += f" ] }}, align {ctx.arch.ptr_align}\n"

        ctx.llir += "@{inst_path} = internal dso_local alias %lambda, %lambda* bitcast({inst_type}* @{inst_path_alt} to %lambda*)\n".format(
            inst_type = inst_type,
            inst_path = ctx.mangle_inst(inst, alt = False),
            inst_path_alt = ctx.mangle_inst(inst, alt = True),
        )

    def visit_implementation(impl: Implementation, ctx: GenerateLLIRContext):
        uses = ValueUses.count_uses(impl)

        for name in uses.extern_uses.keys():
            ctx.write_extern(name)

        for path in uses.global_uses.keys():
            ctx.write_global(path)

        ctx.llir += "define internal dso_local %lambda* @{impl_path}(%lambda* %0, %lambda* %1, %lambda_cont* %2) unnamed_addr {{\n".format(
            impl_path = ctx.mangle_impl(impl)
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

        for inst_key, refcount in uses.inst_uses.items():
            inst = uses.get_instance(inst_key)
            ctx.write_lambda_ref(InstanceLiteral(inst), refcount)

        for name, refcount in uses.extern_uses.items():
            lit = ctx.write_load_extern(index_factory, name)
            ctx.write_lambda_ref(lit, refcount)

        for path, refcount in uses.global_uses.items():
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

        ctx.llir += f"    ret %lambda* {ctx.mangle_lit(ret_lit)}\n"
        ctx.llir += "}\n"

    def visit_literal(lit: ValueLiteral, index_factory: IndexFactory, ctx: GenerateLLIRContext) -> RealizedLiteral:
        match lit:
            case ImplementationLiteral(impl):
                lamb = ctx.write_lambda_alloc(index_factory, len(impl.anonymous_captures))
                ctx.write_store_impl(index_factory, impl, lamb)

                for dest_index, id in enumerate(impl.anonymous_captures):
                    value = ctx.write_load_literal(AnonymousLiteral(id), index_factory)

                    ctx.write_store_capture(index_factory, value, lamb, dest_index)

                return ImplConstruction(lamb)

        return SimpleLiteral(lit)

    return visit_program(prog)
