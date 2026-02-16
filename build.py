#!/usr/bin/env python3

import sys
import os
from pathlib import Path

PREFIX = "#!/bin/usr/env bash\n"

# Paths to engines
WASMTIME_PATH = "../wasmtime/target/release/wasmtime"
D8_PATH = "../v8/v8/out/x64.release/d8"
WIZARD_PATH = "../wizard-engine/bin/wizeng.x86-64-linux"


# Paths to imports
WASMFX_IMPORTS = "wasmfx_imports.wasm"
V8_JS_LOADER = "load.mjs"

ENGINES = {

    "wasmtime": {
        "asyncify": """{prefix} {wasmtime} run --preload={wasmfx_imports} -W=exceptions,function-references,gc,stack-switching {benchmark}_asyncify.wasm""",
        "wasmfx": """{prefix} {wasmtime} run --preload={wasmfx_imports} -W=exceptions,function-references,gc,stack-switching {benchmark}_wasmfx.wasm""",
    },

    "d8": {
        "asyncify": """{prefix} {d8} --experimental-wasm-wasmfx {v8_js_loader} -- {benchmark}_asyncify.wasm""",
    },
    
    "wizard": {
        "asyncify": """{prefix} {wizard} --ext:stack-switching {benchmark}_asyncify.wasm""",
        "wasmfx": """{prefix} {wizard} --ext:stack-switching {benchmark}_wasmfx.wasm""",
    },
}


def generate_script(filename: Path, content: str):
    filename.write_text(content)
    filename.chmod(0o755)


def main():
    if len(sys.argv) != 2:
        print("Usage: ./build <benchmark program>")
        sys.exit(1)

    benchmark = sys.argv[1]

    for engine, modes in ENGINES.items():
        for mode, template in modes.items():
            script_name = f"{benchmark}_{engine}_{mode}.sh"
            content = template.format(
                prefix=PREFIX,
                benchmark=benchmark,
                wasmtime=WASMTIME_PATH,
                d8=D8_PATH,
                wizard=WIZARD_PATH,
                wasmfx_imports=WASMFX_IMPORTS,
                v8_js_loader=V8_JS_LOADER,
            )
            generate_script(Path(script_name), content)
    print("Generated scripts for benchmark:", benchmark)


if __name__ == "__main__":
    main()
