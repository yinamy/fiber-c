#!/usr/bin/env python3

import sys
import os
from pathlib import Path

PREFIX = "#!/bin/usr/env bash\n"

# Paths to engines
WASMTIME_PATH = "../wasmtime/target/release/wasmtime"
D8_PATH = "../v8/v8/out/x64.release/d8"
WIZARD_PATH = "../wizard-engine/bin/wizeng.x86-64-linux"

# Paths for building benchmarks
ASYNCIFY_DEFAULT_STACK_SIZE=2097152
STACK_POOL_SIZE=0
WASMFX_CONT_TABLE_INITIAL_CAPACITY=1024
WASMFX_PRESERVE_SHADOW_STACK=1
# Only relevant if WASMFX_PRESERVE_SHADOW_STACK is 1
WASMFX_CONT_SHADOW_STACK_SIZE=65536
ASYNCIFY="../binaryen/bin/wasm-opt --enable-exception-handling --enable-reference-types --enable-multivalue --enable-bulk-memory --enable-gc --enable-stack-switching -O2 --asyncify"
WASICC="../benchfx/wasi-sdk-22.0/bin/clang"
WASIFLAGS="--sysroot=../benchfx/wasi-sdk-22.0/share/wasi-sysroot -std=c17 -Wall -Wextra -Werror -Wpedantic -Wno-strict-prototypes -O3 -I inc"
WASM_INTERP="../specfx/interpreter/wasm"
WASM_MERGE="../binaryen/bin/wasm-merge --enable-multimemory --enable-exception-handling --enable-reference-types --enable-multivalue --enable-bulk-memory --enable-gc --enable-stack-switching"
SHADOW_STACK_FLAG=""

# Paths to imports
WASMFX_IMPORTS = "wasmfx_imports.wasm"
V8_JS_LOADER = "load.mjs"

# List of valid benchmarks

BENCHMARKS = {
    "hello",
    "itersum",
    "sieve",
    "treesum",
    "hello_switch",
    "itersum_switch",
    "sieve_switch",
    "treesum_switch",
}

# ---- Build .wasms for a benchmark ----

def uses_switch(benchmark: str) -> bool:
    return benchmark.endswith("_switch")

# Given a benchmark name, build the benchmark's .wasm files for both asyncify and wasmfx modes.
def build_benchmarks(benchmark: str):
    if benchmark not in BENCHMARKS:
        print(f"Error: Benchmark '{benchmark}' is not recognized.")
        sys.exit(1)

    asyncify_wasm = f"{benchmark}_asyncify.wasm"
    wasmfx_wasm = f"{benchmark}_wasmfx.wasm"
    
    # do different things if the benchmark uses `switch`
    if uses_switch(benchmark):
        asyncify_impl = "asyncify_switch_impl.c"
    else:
        asyncify_impl = "asyncify_impl.c"

    # Compile to asyncify .wasm
    os.system(f"{WASICC} -DSTACK_POOL_SIZE={STACK_POOL_SIZE} -DASYNCIFY_DEFAULT_STACK_SIZE={ASYNCIFY_DEFAULT_STACK_SIZE} src/asyncify/{asyncify_impl} {WASIFLAGS} examples/{benchmark}.c -o {benchmark}_asyncify.pre.wasm")
    os.system(f"{ASYNCIFY} {benchmark}_asyncify.pre.wasm -o {benchmark}_asyncify.wasm")
    os.system(f"chmod +x {benchmark}_asyncify.wasm")
    os.system(f"rm {benchmark}_asyncify.pre.wasm")

    # Compile to wasmfx .wasm
    # TODO: figure out how wasm-merge can be factored out


# ---- Script generation ----

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
    if not ((len(sys.argv) > 1) or (sys.argv[1] == "run") or (sys.argv[1] == "compile")):
        print("Usage: ./build <compile|run> <benchmark program>")
        sys.exit(1)

    mode = sys.argv[1]
    benchmark = sys.argv[2]
    
    if mode == "compile":
        build_benchmarks(benchmark)
        print("Built .wasm files for benchmark:", benchmark)
    else:
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
