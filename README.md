# feax
Preprocessor for feax OpenType code


### Installation steps

Update the basic toolchain (on Debian/Ubuntu/WSL2):
sudo apt install python3-pip python3-venv python3-wheel python3-setuptools

create a virtual environment:
```
python3 -m venv venv
```
Get inside the virtual environment, you have to do this every time you want to use the pysilfont tools again:
```
source venv/bin/activate
```

Then install update the toolchain and install:
```
python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install .
```

You can deactivate your virtual environment (venv) by typing:
```
deactivate
```
or by closing your terminal.


Alternatively to install in editable mode:
```
python3 -m pip install -e .
```

By default the dependencies pulled in are using releases.


Install from git main/master to track the freshest versions of the dependencies:
```
python3 -m pip install --upgrade -e .[git]


