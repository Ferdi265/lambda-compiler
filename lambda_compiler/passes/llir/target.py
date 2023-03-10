from __future__ import annotations
from typing import *
from dataclasses import dataclass, field

@dataclass
class Architecture:
    triple: str
    data_layout: str
    ptr_size: int
    ptr_align: int

TARGETS = {
    "x86_64": Architecture("x86_64-pc-linux-gnu", "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128", 8, 8),
    "amd64": Architecture("amd64-pc-linux-gnu", "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128", 8, 8),
    "i686": Architecture("i686-pc-linux-gnu", "e-m:e-p:32:32-p270:32:32-p271:32:32-p272:64:64-f64:32:64-f80:32-n8:16:32-S128", 4, 4),
    "i386": Architecture("i386-pc-linux-gnu", "e-m:e-p:32:32-p270:32:32-p271:32:32-p272:64:64-f64:32:64-f80:32-n8:16:32-S128", 4, 4),
    "aarch64": Architecture("aarch64-unknown-linux-gnu", "e-m:e-i8:8:32-i16:16:32-i64:64-i128:128-n32:64-S128", 8, 8),
    "armv7": Architecture("armv7-unknown-linux-gnueabi", "e-m:e-p:32:32-Fi8-i64:64-v128:64:128-a:0:32-n32-S64", 4, 4),
    "armv6": Architecture("armv6-unknown-linux-gnueabi", "e-m:e-p:32:32-Fi8-i64:64-v128:64:128-a:0:32-n32-S64", 4, 4),
    "armv5": Architecture("armv5-unknown-linux-gnueabi", "e-m:e-p:32:32-Fi8-i64:64-v128:64:128-a:0:32-n32-S64", 4, 4),
    "armv4": Architecture("armv4-unknown-linux-gnueabi", "e-m:e-p:32:32-Fi8-i64:64-v128:64:128-a:0:32-n32-S64", 4, 4),
}
