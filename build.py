#!/usr/bin/env python3
import yaml
import sys
import os
from pathlib import Path

# Import config
config = yaml.safe_load(open("config.yml"))

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

# Given a benchmark name, build .wasm files for both asyncify and wasmfx modes.
def build_benchmarks(benchmark: str):
    if benchmark not in BENCHMARKS:
        print(f"Error: Benchmark '{benchmark}' is not recognized.")
        sys.exit(1)
    
    # do different things if the benchmark uses `switch`
    if uses_switch(benchmark):
        asyncify_impl = "asyncify_switch_impl.c"
        wasmfx_impl = "wasmfx_switch_impl.c"
        wasmfx_imports = "imports_switch.wat"
        # TODO: this doesn't work yet
        fiber_wasmfx_imports = "fiber_wasmfx_imports_switch"
    else:
        asyncify_impl = "asyncify_impl.c"
        wasmfx_impl = "wasmfx_impl.c"
        wasmfx_imports = "imports.wat"
        fiber_wasmfx_imports = "fiber_wasmfx_imports"

    # Compile to asyncify .wasm
    os.system(f"{config['WASICC']} -DSTACK_POOL_SIZE={config['STACK_POOL_SIZE']} -DASYNCIFY_DEFAULT_STACK_SIZE={config['ASYNCIFY_DEFAULT_STACK_SIZE']} src/asyncify/{asyncify_impl} {config['WASIFLAGS']} examples/{benchmark}.c -o {benchmark}_asyncify.pre.wasm")
    os.system(f"{config['ASYNCIFY']} {benchmark}_asyncify.pre.wasm -o {benchmark}_asyncify.wasm")
    os.system(f"chmod +x {benchmark}_asyncify.wasm")

    # Compile wasmfx imports
    os.system(f"{config['WASICC']} -xc {config['SHADOW_STACK_FLAG']} -DWASMFX_CONT_TABLE_INITIAL_CAPACITY={config['WASMFX_CONT_TABLE_INITIAL_CAPACITY']} -E src/wasmfx/{wasmfx_imports}.pp | sed 's/^#.*//g' > src/wasmfx/{wasmfx_imports}")
    os.system(f"{config['WASM_INTERP']} -d -i src/wasmfx/{wasmfx_imports} -o {fiber_wasmfx_imports}.wasm")

    # Compile to wasmfx .wasm
    # TODO: figure out how wasm-merge can be factored out
    os.system(f"{config['WASICC']} {config['SHADOW_STACK_FLAG']} -DWASMFX_CONT_SHADOW_STACK_SIZE={config['WASMFX_CONT_SHADOW_STACK_SIZE']} -DWASMFX_CONT_TABLE_INITIAL_CAPACITY={config['WASMFX_CONT_TABLE_INITIAL_CAPACITY']} -Wl,--export-table,--export-memory,--export=__stack_pointer src/wasmfx/{wasmfx_impl} {config['WASIFLAGS']} examples/{benchmark}.c -o {benchmark}_wasmfx.pre.wasm")
    os.system(f"{config['WASM_MERGE']} {fiber_wasmfx_imports}.wasm \"{fiber_wasmfx_imports}\" {benchmark}_wasmfx.pre.wasm \"main\" -o {benchmark}_wasmfx.wasm")


def clean_artefacts(benchmark: str):
    os.system(f"rm {benchmark}_asyncify.pre.wasm")

def clean_all(benchmark: str):
    os.system(f"rm {benchmark}_*.sh")
    os.system(f"rm {benchmark}_asyncify.wasm")
    os.system(f"rm {benchmark}_wasmfx.wasm")
    # TODO: clean wasmfx .wasm when we have them
    
# ---- Script generation ----

ENGINES = {

    "wasmtime": {
        "asyncify": """{prefix} {set_arch} {wasmtime} run -W=exceptions,function-references,gc,stack-switching {benchmark}_asyncify.wasm {arg}""",
        "wasmfx": """{prefix} {set_arch} {wasmtime} run -W=exceptions,function-references,gc,stack-switching {benchmark}_wasmfx.wasm {arg}""",
    },

    "d8": {
        "asyncify": """{prefix} {set_arch} {d8} --experimental-wasm-wasmfx {v8_js_loader} -- {benchmark}_asyncify.wasm {arg}""",
        "wasmfx": """{prefix} {set_arch} {d8} --experimental-wasm-wasmfx {v8_js_loader} -- {benchmark}_wasmfx.wasm {arg}""",
    },
    
    "wizard": {
        "asyncify": """{prefix} {set_arch} {wizard} --ext:stack-switching {benchmark}_asyncify.wasm {arg}""",
        "wasmfx": """{prefix} {set_arch} {wizard} --ext:stack-switching {benchmark}_wasmfx.wasm {arg}""",
    },
}

def make_script(filename: Path, content: str):
    filename.write_text(content)
    filename.chmod(0o755)

def generate_scripts(benchmark: str):

    # set arguments for benchmarks that need them
    if benchmark in {"itersum", "itersum_switch"}:
        arg = 1000000
    elif benchmark in {"treesum", "treesum_switch"}:
        arg = 20
    elif benchmark in {"sieve", "sieve_switch"}:
        arg = 2000
    else:
        arg = ""

    for engine, modes in ENGINES.items():
            for mode, template in modes.items():
                script_name = f"{benchmark}_{engine}_{mode}.sh"
                content = template.format(
                    set_arch = "setarch -R ",
                    prefix=config["PREFIX"],
                    benchmark=benchmark,
                    wasmtime=config["WASMTIME_PATH"],
                    d8=config["D8_PATH"],
                    wizard=config["WIZARD_PATH"],
                    v8_js_loader=config["V8_JS_LOADER"],
                    arg=arg
                )
                make_script(Path(script_name), content)
                print("Generated scripts for benchmark:", benchmark)

def main():
    if not (((len(sys.argv) > 2) and (sys.argv[1] in {"run","compile","clean-all","clean"})) or ((sys.argv[1] == "make-all"))):
        print("Usage: ./build <compile|run|clean|clean-all> <benchmark program> | <make-all>")
        sys.exit(1)

    mode = sys.argv[1]
    if mode != "make-all": benchmark = sys.argv[2]
    
    if mode == "compile":
        build_benchmarks(benchmark)
        print("Built .wasm files for benchmark:", benchmark)
    elif mode == "clean-all":
        clean_all(benchmark)
        print("Cleaned *all* artefacts for benchmark:", benchmark)
    elif mode == "clean":
        clean_artefacts(benchmark)
        print("Cleaned side-products for benchmark:", benchmark)
    elif mode == "make-all":
        for benchmark in BENCHMARKS:
            build_benchmarks(benchmark)
            generate_scripts(benchmark)
    else:
        generate_scripts(benchmark)
        


if __name__ == "__main__":
    main()
