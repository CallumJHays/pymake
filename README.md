# pymake

`pymake` is a python library and CLI that mimics GNU `make`'s API.

It allows developers to express and execute arbitrarily complex, dependency-based build-trees.

## Example

```python
# PyMakefile.py
from pymake import *

some_library = Makefile('lib/some_library')

# compile source -> object files
object_files = CompileC('build/%.o', 'src/%.[ch]', libs=[some_library])

# link all object files into an executable
@makes('hello-world', object_files("*"))
def hello_world(deps: List[Path], out: Path):
    sh(f'gcc {deps} -o {out}')
```

The above can be rewritten as:

```python
from pymake import *

hello_world = CompileC(
  'hello-world', 'src/**/*.[ch]',
  libs=[Makefile('lib/some_library')]
)
```

Example CLI invocations:

```bash
pymake hello_world `object_files(a, b, c)`
pymake hello-world
```

Which will build the `hello-world` application. See [examples/hello-world](examples/hello-world) for more detail.

## Benefits

- Familiar API and CLI to GNU make
- Python enables dynamic generation of targets and dependencies
- Utilise existing `Makefiles` via [pymake.Makefile()](TODO)
- Tracks target builds timestamps to a `.pymake-cache` file by default, so that functions with up-to-date dependencies don't needlessly execute (eloquent alternative to using build flags).
- Helpful, <span style="color: cyan">colorful</span> and <span style="color: magenta">>> configurable</span> log & <span style="color: red">error messages</span> for <b>quicker</b> bug-fixing
- Debug your PyMakefiles with PDB or other editor-friendly debuggers
- Supports `async` python code out of the box
- Fully type-hinted for a better developer experience via editor intellisense
- Backed by simple, extensible OOP framework
- Callable from CLI or via python library.
- Provides default implementations of:
  - `pymake clean` - delete all `FileTarget.output` files and clear the cache. Can be overridden.
  - `pymake show` - displays dependencies and help from docstrings of defined targets (with default docstrings)
- Import, reconfigure and run targets programatically from other `PyMakefiles` within a single dependency tree.

## Caveats

- Global mutable state does not work out of the box (ie the `globals` statement in a function body).
  - `pymake` may provide a recommended method for achieving this in the future but for now I can't see a use-case.

## Documentation

TODO

## Alternatives

### [GNU make](https://makefiletutorial.com/)

The OG `make`. At its core it's a shell executor tied to a dependency tree. Editor support for syntax error/highlighting is minimal. Debugging support is even worse.

In order to track target builds that don't output files, you must use build-flags; empty files that exist solely to track the timestamp of a target's execution. This is messy, error-prone, and unusual.

`make` is a better option for very simple build trees thanks to it's terse dependency specification syntax. Widely used in industry for decades (particularly among C/C++ devs), so more maintainable in that regard.

### [SCons](https://github.com/SCons/scons)

Similar to `pymake` being based on python and an extensible OOP framework.

The API is not as nice to use as `pymake` though as the scons library is injected rather than imported. Therefore editors either need an SCons extension to provide intellisense or developers must bend over backwards to achieve this.

Requires usage of the `scons` executable, whereas `PyMakefiles` can be executed directly through python.

## Future Goals

- `pymake --render [target]` - Produce a graphviz graphic or .dot file of the dependency tree required by a target
- Cross-platform support where possible
