from __future__ import annotations
from typing import *
from dataclasses import dataclass, field
from copy import copy
import os.path
from abc import ABC, abstractmethod

from .ast import *
from .parse_lang import *
from .parse_hlir import *

class CollectCrateError(Exception):
    pass

@dataclass
class Local(Ident):
    pass

@dataclass
class ExternGlobal(Ident):
    pass

@dataclass
class PathGlobal(PathExpr):
    pass

@dataclass
class NamespaceEntry:
    path: Path
    is_public: bool

@dataclass
class SubModule(NamespaceEntry):
    module: ModuleNamespace

@dataclass
class Alias(NamespaceEntry):
    target: Path

@dataclass
class ExternEntry(NamespaceEntry):
    name: str

@dataclass
class Definition(NamespaceEntry):
    is_impure: bool

@dataclass
class CrateInfo:
    name: str
    src: str
    dir: str
    owns_dir: bool

@dataclass
class Loader(ABC):
    @abstractmethod
    def initial_crate_name_and_dir(self, file_path: str) -> CrateInfo:
        ...

    @abstractmethod
    def load_crate(self, parent: RootNamespace, crate: str) -> ModuleNamespace:
        ...

    @abstractmethod
    def load_mod(self, mod: ModuleNamespace, name: str) -> ModuleNamespace:
        ...

@dataclass
class RootNamespace:
    main_crate: str
    blacklist_crates: OrderedSet[str] = field(default_factory = OrderedSet)
    crates: Dict[str, ModuleNamespace] = field(default_factory = dict)

    def insert_crate(self, crate: ModuleNamespace):
        crate_name = crate.get_name()
        if crate_name in self.crates:
            raise CollectCrateError(f"redefinition of crate '{crate_name}'")

        self.crates[crate_name] = crate

    def resolve_absolute(self, path: Path) -> NamespaceEntry:
        path_crate_name = path.components[0]
        rest_path = Path(path.components[1:])
        if path_crate_name not in self.crates:
            raise CollectCrateError(f"'{path}' is from an undeclared extern crate")

        crate = self.crates[path_crate_name]
        if len(rest_path.components) == 0:
            return SubModule(crate.path, True, crate)

        return crate.resolve(rest_path, allow_private = False)

    def resolve(self, path: Path, mod: ModuleNamespace) -> NamespaceEntry:
        prefix = path.components[0]
        rest_path = Path(path.components[1:])
        if prefix == "self":
            return mod.resolve(rest_path)
        elif prefix == "crate":
            crate_name = mod.path.components[0]
            return self.crates[crate_name].resolve(rest_path, allow_private = True)
        elif prefix == "super":
            while prefix == "super":
                if mod.parent is None:
                    raise CollectCrateError(f"crate root '{mod.path}' has no parent module")
                mod = mod.parent
                prefix = rest_path.components[0]
                rest_path = Path(rest_path.components[1:])
            return mod.resolve(rest_path, allow_private = True)
        else:
            return self.resolve_absolute(path)

@dataclass
class ModuleNamespace:
    root: RootNamespace
    parent: Optional[ModuleNamespace]
    path: Path
    src: str
    dir: str
    owns_dir: bool = False

    entries: Dict[str, NamespaceEntry] = field(default_factory = dict)

    def get_name(self) -> str:
        return self.path.components[-1]

    def get_entry(self, name: str) -> NamespaceEntry:
        if name not in self.entries:
            raise CollectCrateError(f"'{self.path}::{name}' is undefined")

        return self.entries[name]

    def insert_entry(self, name: str, entry: NamespaceEntry):
        if name in self.entries:
            raise CollectCrateError(f"redefinition of '{self.path}::{name}'")

        self.entries[name] = entry

    def insert_submod(self, name: str, is_public: bool, loader: Loader) -> ModuleNamespace:
        if name in self.entries:
            raise CollectCrateError(f"redefinition of '{self.path}::{name}'")

        mod = loader.load_mod(self, name)
        self.entries[name] = SubModule(mod.path, is_public, mod)
        return mod

    def strip_private(self):
        for name in list(self.entries.keys()):
            if not self.entries[name].is_public:
                del self.entries[name]

    def resolve(self, path: Path, allow_private: bool = False) -> NamespaceEntry:
        name = path.components[0]
        rest_path = Path(path.components[1:])
        entry = self.get_entry(name)

        if not allow_private and not entry.is_public:
            raise CollectCrateError(f"cannot access private member '{entry.path}'")

        if isinstance(entry, Alias):
            entry = self.root.resolve_absolute(entry.target)

        if len(rest_path.components) == 0:
            return entry

        match entry:
            case ExternEntry() as ext:
                raise CollectCrateError(f"cannot get member of non-module 'extern impure {ext.name}'")
            case Definition() as definition:
                raise CollectCrateError(f"cannot get member of non-module '{definition.path}'")
            case SubModule() as submod:
                return submod.module.resolve(rest_path, allow_private = False)
            case _:
                raise CollectCrateError(f"unexpected entry type encountered: {entry}")

@dataclass
class CollectExprContext:
    is_impure: bool
    locals: OrderedSet[str] = field(default_factory = OrderedSet)
    referenced: OrderedSet[str] = field(default_factory = OrderedSet)

    def __copy__(self) -> CollectExprContext:
        return CollectExprContext(self.is_impure, copy(self.locals), OrderedSet())

def collect_mod(mod: ModuleNamespace, loader: Loader, root: RootNamespace) -> List[Statement]:
    def collect(mod: ModuleNamespace) -> List[Statement]:
        with open(mod.src, "r") as f:
            code = f.read()

        prog = parse_lang(code)
        statements = []
        for stmt in prog:
            new_stmt = visit_statement(stmt, mod)
            if isinstance(new_stmt, list):
                statements += new_stmt
            elif new_stmt is not None:
                statements.append(new_stmt)

        return statements

    def visit_statement(stmt: Statement, mod: ModuleNamespace) -> Union[Optional[Statement], List[Statement]]:
        match stmt:
            case ExternCrate() as ext_crate:
                return visit_extern_crate(ext_crate, mod)
            case Extern() as ext:
                return visit_extern(ext, mod)
            case Mod() as submod:
                return visit_module(submod, mod)
            case Import() as imp:
                return visit_import(imp, mod)
            case NameAssignment() as ass:
                return visit_assignment(ass, mod)
            case _:
                raise CollectCrateError(f"unexpected AST node encountered: {stmt}")

    def visit_extern_crate(ext_crate: ExternCrate, mod: ModuleNamespace) -> ExternCrate:
        root.insert_crate(loader.load_crate(root, ext_crate.name))
        return ext_crate

    def visit_extern(extern: Extern, mod: ModuleNamespace) -> Extern:
        abs_path = mod.path / extern.name
        mod.insert_entry(extern.name, ExternEntry(abs_path, False, extern.name))
        return extern

    def visit_module(submod: Mod, mod: ModuleNamespace) -> List[Statement]:
        return collect(mod.insert_submod(submod.name, submod.is_public, loader))

    def visit_import(imp: Import, mod: ModuleNamespace) -> Optional[PathAlias]:
        abs_path = mod.path / imp.name
        if imp.name in mod.entries:
            raise CollectCrateError(f"redefinition of '{abs_path}'")

        target = root.resolve(imp.path, mod)
        mod.insert_entry(imp.name, Alias(abs_path, imp.is_public, target.path))

        if not isinstance(target, Definition):
            return None
        elif not imp.is_public:
            return None
        elif not target.is_public:
            raise CollectCrateError(f"cannot publicly export non-public definition '{target.path}' as '{abs_path}'")

        return PathAlias(mod.path / imp.name, target.path, imp.is_public)

    def visit_assignment(ass: NameAssignment, mod: ModuleNamespace) -> PathAssignment:
        abs_path = mod.path / ass.name
        if ass.name in mod.entries:
            raise CollectCrateError(f"redefinition of '{abs_path}'")

        value = visit_expr(ass.value, mod, CollectExprContext(ass.is_impure))

        mod.insert_entry(ass.name, Definition(abs_path, ass.is_public, ass.is_impure))
        return PathAssignment(abs_path, value, ass.is_public, ass.is_impure)

    def visit_expr(expr: Expr, mod: ModuleNamespace, ctx: CollectExprContext) -> Expr:
        match expr:
            case Paren(expr):
                return Paren(visit_expr(expr, mod, ctx))
            case Call(fn, arg):
                return Call(
                    visit_expr(fn, mod, ctx),
                    visit_expr(arg, mod, ctx)
                )
            case Ident() as ident:
                return visit_ident(ident, mod, ctx)
            case PathExpr() as path_expr:
                return visit_path(path_expr, mod, ctx)
            case Lambda() as lamb:
                return visit_lambda(lamb, mod, ctx)
            case Macro() as macro:
                return macro
            case _:
                raise CollectCrateError(f"unexpected AST node encountered: {expr}")

    def visit_ident(ident: Ident, mod: ModuleNamespace, ctx: CollectExprContext) -> Expr:
        if ident.name in ctx.locals:
            ctx.referenced.add(ident.name)
            return Local(ident.name)

        entry = mod.resolve(Path(()) / ident.name, allow_private = True)
        match entry:
            case ExternEntry(path, is_public, name):
                if not ctx.is_impure:
                    raise CollectCrateError(f"cannot use 'extern impure {name}' in pure context")
                return ExternGlobal(name)
            case Definition(path, is_public, is_impure):
                if is_impure and not ctx.is_impure:
                    raise CollectCrateError(f"cannot use impure definition '{path}' in pure context")
                return PathGlobal(path)
            case _:
                raise CollectCrateError(f"unexpected entry type encountered: {entry}")

    def visit_path(path_expr: PathExpr, mod: ModuleNamespace, ctx: CollectExprContext) -> PathExpr:
        target = root.resolve(path_expr.path, mod)
        if not isinstance(target, Definition):
            raise CollectCrateError(f"cannot use non-definition '{target.path}' in an expression")

        if target.is_impure and not ctx.is_impure:
            raise CollectCrateError(f"cannot use impure definition '{target.path}' in pure context")

        return PathGlobal(target.path)

    def visit_lambda(lamb: Lambda, mod: ModuleNamespace, ctx: CollectExprContext) -> Lambda:
        subctx = copy(ctx)
        subctx.locals.add(lamb.name)

        body = visit_expr(lamb.body, mod, subctx)
        captures = ctx.locals & subctx.referenced
        captures.remove(lamb.name)

        ctx.referenced |= captures

        return Lambda(lamb.name, body, captures)

    return collect(mod)

def collect_crate_from_hlis(file_path: str, loader: Loader, namespace: RootNamespace):
    raise CollectCrateError("HLIS collection not implemented")

def collect_crate(file_path: str, loader: Loader, namespace: Optional[RootNamespace] = None) -> List[Statement]:
    crate_info = loader.initial_crate_name_and_dir(file_path)
    crate_name = crate_info.name
    crate_dir = crate_info.dir
    crate_src = crate_info.src
    owns_dir = crate_info.owns_dir

    if namespace is None:
        root = RootNamespace(crate_name)
    else:
        root = namespace
    root.blacklist_crates.add(crate_name)

    crate = ModuleNamespace(root, None, Path(()) / crate_name, crate_src, crate_dir, owns_dir)
    root.insert_crate(crate)
    return collect_mod(crate, loader, root)
