# feax
Preprocessor for feax OpenType code

Feax is a set of extensions to provide easier and more powerful ways to write fea code.
For the specification of the feax language see [docs/feaextensions.md](docs/feaextensions.md). For plans about the future see [docs/feax_future.md](docs/feax_future.md).

## Installation steps

If you do not already have the repository checked out, download the source code:

```
git clone https://github.com/silnrsi/feax.git
cd feax
```


### Install in a virtual environment (venv)

Create a virtual environment (this works the same in Ubuntu/WSL2/macOS):
```
python3 -m venv venv
```
Get inside the virtual environment (venv) (you have to do this every time you want to use the tools again):
```
source venv/bin/activate
```

Then install (update) the toolchain and install the feax library and the makefea script:
```
python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install .
```

You can deactivate your virtual environment (venv) by typing:
```
deactivate
```
or by closing your terminal.

### Install in editable mode
Alternatively to install in editable mode:
```
python3 -m pip install -e .
```

By default the dependencies pulled in are using releases.

### Install from git for freshest possible dependencies
Install from git main/master to track the freshest versions of the dependencies:
```
python3 -m pip install --upgrade -e .[git]
```

## Running the script

```
makefea
```

Usage:

```
makefea -h (or --help)
```