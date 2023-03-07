from typing import *
import os

def get_crate_search_path(extra: List[str], with_default: bool = True):
    crate_path = []
    crate_path += extra
    if with_default:
        crate_path += [
            "/usr/lib/lambda/crates/",
            "/usr/local/lib/lambda/crates/",
            os.path.expanduser("~/.local/lib/lambda/crates/")
        ]
    return crate_path
