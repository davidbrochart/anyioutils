Anyioutils can be installed through [PyPI](https://pypi.org) or [conda-forge](https://conda-forge.org).

## With `pip`

```bash
pip install anyioutils
```

## With `micromamba`

We recommend using `micromamba` to manage `conda-forge` environments (see `micromamba`'s
[installation instructions](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html)).
First create an environment, here called `my-env`, and activate it:
```bash
micromamba create -n my-env
micromamba activate my-env
```
Then install `anyioutils`.

```bash
micromamba install anyioutils
```

## Development install

You first need to clone the repository:
```bash
git clone https://github.com/davidbrochart/anyioutils
cd anyioutils
```
We recommend working in a conda environment. In order to build `anyioutils`, you will need
`pip`:
```bash
micromamba create -n anyioutils-dev
micromamba activate anyioutils-dev
micromamba install pip
```
Then install `anyioutils` in editable mode:
```bash
pip install -e ".[test,docs]"
```
