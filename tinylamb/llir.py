from __future__ import annotations
from dataclasses import dataclass, field
from typing import *

from .dedup import *

class GenerateLLIRError(Exception):
    pass

@dataclass
class GenerateLLIRContext:
    llir: str = ""

    def define_global(self, path: Path):
        pass

def generate_llir(prog: List[Statement], crate: Path) -> str:
    def visit_program(prog: List[Statement]) -> str:
        ctx = GenerateLLIRContext()

        for stmt in prog:
            match stmt:
                case InstanceDefinition() as inst_def:
                    ctx.define_global(inst_def.path)

        for stmt in prog:
            match stmt:
                case InstanceDefinition() as inst_def:
                    visit_definition(inst_def, ctx)
                case Instance() as inst:
                    visit_instance(inst, ctx)
                case Implementation() as impl:
                    visit_implementation(impl, ctx)

        return ctx.llir

    def visit_definition(inst_def: InstanceDefinition, ctx: GenerateLLIRContext):
        pass

    def visit_instance(inst: Instance, ctx: GenerateLLIRContext):
        pass

    def visit_implementation(impl: Implementation, ctx: GenerateLLIRContext):
        pass

    return visit_program(prog)
