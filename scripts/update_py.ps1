#!/bin/bash
./scripts/activate.ps1
mkdir shared
pip freeze > shared/requirements.txt
pip install -r shared/requirements.txt -t shared/python --upgrade
