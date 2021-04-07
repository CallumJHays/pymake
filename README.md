# pymake

`pymake` is a python library and CLI that mimics GNU `make`'s API.

It allows developers to express arbitrarily complex, dependency-based build-trees.

## Example (WIP)

```python
# PyMakefile.py
from pymake import *

# OOP definition - many helpful classes,
# such as this which executes a traditional Makefile
some_library = Makefile('lib/some_library')

# compile source -> object files
object_files = Compile('build/%.o', 'src/%.[ch]', libs=[some_library])

# decorator for custom target type definition
@makes('hello-world', object_files)
def hello_world():
    sh(f'gcc {deps} -o {out}')
```

Invoke from command line with:

```bash
pymake hello_world # matches the target name
# or
pymake hello-world # matches the output path
# or
python PyMakefile.py hello-world # without the `pymake` executable
```

Which will build the `hello-world` application. See [examples/hello-world](examples/hello-world) for more detail.

## Benefits:

- Familiar API and CLI to GNU make
- Utilise existing makefiles via [pymake.Makefile()](TODO)
- Generate targets and dependencies dynamically via regular Python
- Fully type-hinted for an amazing developer experience via editor intellisense
- Debug your PyMakefiles with PDB or other editor-friendly debuggers
- Helpful & colorful error messages for quicker bug-fixing
- Backed by simple, extensible OOP framework
- Callable from CLI or python library
- Provides default implementations of:
  - `pymake clean` - delete all `FileTarget.output` files and clear the cache. Can be overridden.
  - `pymake [help]` - displays help from docstrings of defined targets (with default docstrings)
- Tracks target builds timestamps by default, so that functions with up-to-date dependencies don't needlessly execute (eloquent alternative to build-flags).
- Configurable build log color-coding / formatting
- Cross-platform support where possible [TODO!]
- Support for `async` python code [TODO!]

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
