# cnv-tests
This repository contains tests. These tests are to verify funstionality for openshift + CNV installation.

# Getting statrted
## Login to your openshift instance
```
oc login -u user -p password
```
## Running the tests
```
    sudo dnf install pipenv
    pipenv --three install -rrequirements.txt
    pipenv run pytest tests
```
