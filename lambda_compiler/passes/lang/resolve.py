from __future__ import annotations
from typing import *
from dataclasses import dataclass, field
from ...ast.path import Path
from ...ast import lang_linked as lang
from ...ast import hlir_linked as hlir
from copy import copy

class ResolveCrateError(Exception):
    pass

@dataclass
class NamespaceEntry:
    path: Path
    is_public: bool

@dataclass
class ModEntry(NamespaceEntry):
    mod: ModuleNamespace

@dataclass
class AliasEntry(NamespaceEntry):
    target: Path

@dataclass
class ExternEntry(NamespaceEntry):
    name: str

@dataclass
class DefinitionEntry(NamespaceEntry):
    is_impure: bool

@dataclass
class RootNamespace:
    crates: Dict[str, ModuleNamespace] = field(default_factory=dict)

    def insert_crate(self, crate: lang.LinkedExternCrate | hlir.LinkedExternCrate) -> ModuleNamespace:
        if crate.name not in self.crates:
            self.crates[crate.name] = ModuleNamespace(self, None, Path(()) / crate.name, crate.file)

        return self.crates[crate.name]

    def insert_absolute(self, path: Path, entry: NamespaceEntry):
        path_crate_name = path.components[0]
        rest_path = Path(path.components[1:])
        if path_crate_name not in self.crates:
            raise ResolveCrateError(f"'{path}' is from an undeclared extern crate")

        crate = self.crates[path_crate_name]
        crate.insert_absolute(rest_path, entry)

    def resolve_absolute(self, path: Path, allow_private: bool = False) -> NamespaceEntry:
        path_crate_name = path.components[0]
        rest_path = Path(path.components[1:])
        if path_crate_name not in self.crates:
            raise ResolveCrateError(f"'{path}' is from an undeclared extern crate")

        crate = self.crates[path_crate_name]
        if len(rest_path.components) == 0:
            return ModEntry(crate.path, True, crate)

        return crate.resolve(rest_path, allow_private)

    def resolve(self, path: Path, mod: ModuleNamespace) -> NamespaceEntry:
        prefix = path.components[0]
        rest_path = Path(path.components[1:])
        if prefix == "self":
            return mod.resolve(rest_path, allow_private = True)
        elif prefix == "crate":
            crate_name = mod.path.components[0]
            return self.crates[crate_name].resolve(rest_path, allow_private = True)
        elif prefix == "super":
            while prefix == "super":
                if mod.parent is None:
                    raise ResolveCrateError(f"crate root '{mod.path}' has no parent module")
                mod = mod.parent
                prefix = rest_path.components[0]
                rest_path = Path(rest_path.components[1:])
            rest_path = Path([prefix] + list(rest_path.components))
            return mod.resolve(rest_path, allow_private = True)
        else:
            return self.resolve_absolute(path)

@dataclass
class ResolveExprContext:
    is_impure: bool
    locals: Set[str] = field(default_factory = set)

    def __copy__(self) -> ResolveExprContext:
        return ResolveExprContext(self.is_impure, set(self.locals))

@dataclass
class ModuleNamespace:
    root: RootNamespace
    parent: Optional[ModuleNamespace]

    path: Path
    file: lang.SourceFile | hlir.SourceFile

    entries: Dict[str, NamespaceEntry] = field(default_factory = dict)

    @property
    def name(self) -> str:
        return self.path.components[-1]

    def get_entry(self, name: str) -> NamespaceEntry:
        if name not in self.entries:
            raise ResolveCrateError(f"'{self.path}::{name}' is undefined in {self.file.src}")

        return self.entries[name]

    def insert_entry(self, name: str, entry: NamespaceEntry):
        if name in self.entries:
            raise ResolveCrateError(f"redefinition of '{self.path}::{name}' in {self.file.src}")

        self.entries[name] = entry

    def insert_mod(self, ext_mod: lang.LinkedMod) -> ModuleNamespace:
        mod = ModuleNamespace(self.root, self, self.path / ext_mod.name, ext_mod.file)
        self.insert_entry(ext_mod.name, ModEntry(mod.path, ext_mod.is_public, mod))
        return mod

    def insert_absolute(self, path: Path, entry: NamespaceEntry):
        name = path.components[0]
        rest_path = Path(path.components[1:])
        if len(rest_path.components) == 0:
            return self.insert_entry(name, entry)

        if name not in self.entries:
            mod = ModuleNamespace(self.root, self, self.path / name, self.file)
            self.insert_entry(name, ModEntry(self.path / name, True, mod))

        entry = self.entries[name]
        if not isinstance(entry, ModEntry):
            raise ResolveCrateError(f"'{self.path}::{name}' is not a module, cannot define '{self.path}::{path}' in it")

        entry.mod.insert_absolute(rest_path, entry)

    def resolve(self, path: Path, allow_private: bool = False) -> NamespaceEntry:
        if len(path.components) == 0:
            is_public = True
            if self.parent is not None:
                is_public = self.parent.entries[self.name].is_public
            return ModEntry(self.path, is_public, self)

        name = path.components[0]
        rest_path = Path(path.components[1:])
        entry = self.get_entry(name)

        if not allow_private and not entry.is_public:
            raise ResolveCrateError(f"cannot access private member '{entry.path}'")

        if isinstance(entry, AliasEntry):
            # alias visibility is checked at entry creation time, ignore here
            entry = self.root.resolve_absolute(entry.target, allow_private = True)

        if len(rest_path.components) == 0:
            return entry

        match entry:
            case ExternEntry(path, is_public, name):
                raise ResolveCrateError(f"cannot get member of non-module 'extern impure {name}'")
            case DefinitionEntry(path):
                raise ResolveCrateError(f"cannot get member of non-module '{path}'")
            case ModEntry(path, is_public, mod):
                return mod.resolve(rest_path, allow_private = False)
            case _:
                raise ResolveCrateError(f"unexpected entry type encountered: {entry}")

def resolve(crate: lang.LinkedExternCrate) -> List[hlir.Statement]:
    def visit_source_file(file: lang.SourceFile | hlir.SourceFile, mod: ModuleNamespace) -> List[hlir.Statement]:
        match file:
            case lang.SourceFile():
                return visit_lang_source_file(file, mod)
            case hlir.SourceFile():
                return visit_hlir_source_file(file, mod)

    def visit_lang_source_file(file: lang.SourceFile, mod: ModuleNamespace) -> List[hlir.Statement]:
        prog: List[hlir.Statement] = []
        for stmt in file.prog:
            prog += visit_lang_statement(stmt, mod)
        return prog

    def visit_lang_statement(stmt: lang.Statement, mod: ModuleNamespace) -> List[hlir.Statement]:
        match stmt:
            case lang.LinkedExternCrate():
                return visit_extern_crate(stmt, mod)
            case lang.LinkedMod():
                return visit_mod(stmt, mod)
            case lang.Extern():
                return visit_extern(stmt, mod)
            case lang.Import():
                return visit_import(stmt, mod)
            case lang.ImportAll():
                return visit_import_all(stmt, mod)
            case lang.Assignment():
                return visit_assignment(stmt, mod)
            case _:
                raise ResolveCrateError(f"unexpected AST node encountered: {stmt}")

    def visit_extern_crate(ext_crate: lang.LinkedExternCrate | hlir.LinkedExternCrate, mod: ModuleNamespace) -> List[hlir.Statement]:
        if ext_crate.name not in root.crates:
            visit_source_file(ext_crate.file, root.insert_crate(ext_crate))
        return [hlir.ExternCrate(ext_crate.name)]

    def visit_mod(ext_mod: lang.LinkedMod, mod: ModuleNamespace) -> List[hlir.Statement]:
        return visit_source_file(ext_mod.file, mod.insert_mod(ext_mod))

    def visit_extern(ext: lang.Extern | hlir.Extern, mod: ModuleNamespace) -> List[hlir.Statement]:
        mod.insert_entry(ext.name, ExternEntry(mod.path / ext.name, False, ext.name))
        return [hlir.Extern(ext.name)]

    def visit_import(imp: lang.Import, mod: ModuleNamespace) -> List[hlir.Statement]:
        target = root.resolve(imp.path, mod)
        mod.insert_entry(imp.name, AliasEntry(mod.path / imp.name, imp.is_public, target.path))

        if not isinstance(target, DefinitionEntry):
            return []
        elif not imp.is_public:
            return []
        elif not target.is_public:
            raise ResolveCrateError(f"cannot publicly export non-public definition '{target.path}' as {mod.path / imp.name}'")

        return [hlir.Alias(mod.path / imp.name, target.path, imp.is_public)]

    def visit_import_all(imp: lang.ImportAll, mod: ModuleNamespace) -> List[hlir.Statement]:
        target = root.resolve(imp.path, mod)
        if not isinstance(target, ModEntry):
            raise ResolveCrateError(f"cannot import all from non-module '{target.path}'")

        submod = target.mod
        allow_private = mod.path.is_inside(submod.path)

        aliases: List[hlir.Statement] = []
        for name, entry in submod.entries.items():
            if not entry.is_public and not allow_private:
                continue

            if not entry.is_public and imp.is_public:
                continue

            if isinstance(entry, AliasEntry):
                entry = mod.root.resolve_absolute(entry.target)

            mod.insert_entry(name, AliasEntry(mod.path / name, imp.is_public, entry.path))
            if isinstance(entry, DefinitionEntry) and imp.is_public:
                aliases.append(hlir.Alias(mod.path / name, entry.path, imp.is_public))

        return aliases

    def visit_assignment(ass: lang.Assignment, mod: ModuleNamespace) -> List[hlir.Statement]:
        value = visit_expr(ass.value, mod, ResolveExprContext(ass.is_impure))

        mod.insert_entry(ass.name, DefinitionEntry(mod.path / ass.name, ass.is_public, ass.is_impure))
        return [hlir.Assignment(mod.path / ass.name, value, ass.is_public, ass.is_impure)]

    def visit_expr(expr: lang.Expr, mod: ModuleNamespace, ctx: ResolveExprContext) -> hlir.Expr:
        match expr:
            case lang.Paren(expr):
                return hlir.Paren(visit_expr(expr, mod, ctx))
            case lang.Call(fn, arg):
                return hlir.Call(
                    visit_expr(fn, mod, ctx),
                    visit_expr(arg, mod, ctx)
                )
            case lang.Ident() as ident:
                return visit_ident(ident, mod, ctx)
            case lang.Relative() as rel:
                return visit_relative_path(rel, mod, ctx)
            case lang.Lambda() as lamb:
                return visit_lambda(lamb, mod, ctx)
            case _:
                raise ResolveCrateError(f"unexpected AST node encountered: {expr}")

    def visit_ident(ident: lang.Ident, mod: ModuleNamespace, ctx: ResolveExprContext) -> hlir.Expr:
        if ident.name in ctx.locals:
            return hlir.Ident(ident.name)

        entry = mod.resolve(Path(()) / ident.name, allow_private = True)
        match entry:
            case ExternEntry(path, is_public, name):
                if not ctx.is_impure:
                    raise ResolveCrateError(f"cannot use 'extern impure {name}' in pure context")
                return hlir.Ident(name)
            case DefinitionEntry(path, is_public, is_impure):
                if is_impure and not ctx.is_impure:
                    raise ResolveCrateError(f"cannot use impure definition '{path}' in pure context")
                return hlir.Absolute(path)
            case _:
                raise ResolveCrateError(f"unexpected entry type encountered: {entry}")

    def visit_relative_path(rel: lang.Relative, mod: ModuleNamespace, ctx: ResolveExprContext) -> hlir.Expr:
        target = root.resolve(rel.path, mod)
        if not isinstance(target, DefinitionEntry):
            raise ResolveCrateError(f"cannot use non-definition '{target.path}' in an expression")

        if target.is_impure and not ctx.is_impure:
            raise ResolveCrateError(f"cannot use impure definition '{target.path}' in pure context")

        return hlir.Absolute(target.path)

    def visit_lambda(lamb: lang.Lambda, mod: ModuleNamespace, ctx: ResolveExprContext) -> hlir.Expr:
        subctx = copy(ctx)
        subctx.locals.add(lamb.name)

        body = visit_expr(lamb.body, mod, subctx)
        return hlir.Lambda(lamb.name, body)

    def visit_hlir_source_file(file: hlir.SourceFile, mod: ModuleNamespace):
        for stmt in file.prog:
            visit_hlir_statement(stmt, mod)

    def visit_hlir_statement(stmt: hlir.Statement, mod: ModuleNamespace):
        match stmt:
            case hlir.LinkedExternCrate():
                visit_extern_crate(stmt, mod)
            case hlir.Extern():
                visit_extern(stmt, mod)
            case hlir.Assignment():
                visit_hlir_assignment(stmt, mod)
            case hlir.Alias():
                visit_hlir_alias(stmt, mod)
            case _:
                raise ResolveCrateError(f"unexpected AST node encountered: {stmt}")

    def visit_hlir_assignment(ass: hlir.Assignment, mod: ModuleNamespace):
        if not ass.path.is_inside(mod.path):
            raise ResolveCrateError(f"cannot define path {ass.path} in module {mod.path}")

        root.insert_absolute(ass.path, DefinitionEntry(ass.path, ass.is_public, ass.is_impure))

    def visit_hlir_alias(alias: hlir.Alias, mod: ModuleNamespace):
        if not alias.path.is_inside(mod.path):
            raise ResolveCrateError(f"cannot define path {alias.path} in module {mod.path}")

        root.insert_absolute(alias.path, AliasEntry(alias.path, alias.is_public, alias.target))

    root = RootNamespace()
    return visit_source_file(crate.file, root.insert_crate(crate))
