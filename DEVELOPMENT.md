# Requirements

* Python 3.9.6 ([pyenv](https://github.com/pyenv/pyenv) recommended)
* [poetry](https://python-poetry.org/docs/#installation)
* permissions to clone:
    * [nsidc/CIRRUS-NSIDC](https://github.com/nsidc/CIRRUS-NSIDC)
    * [nsidc/CIRRUS-core](https://github.com/nsidc/CIRRUS-core)

# Running the Script

```
poetry install  # install dependencies, set up virtualenv
poetry shell # activate virtualenv
./script.py --help
```

# Linting

To run the linting tools the same way CI (GitHub Actions) does:

```
./lint.sh
```

To run the linting tools and automatically correct any fixable issues:

```
./lint.sh -a
```

# CI / GitHub Actions

* configured in `.github/workflows/`
* the `lint` job runs `lint.sh` and fails if any errors are found
* the `update` job runs `update.sh -o README.md`, and then pushes `README.md` if
  any changes are made
* both jobs run daily at 1:23am
* the secret env var `GH_PAT_DEPS_TOKEN` is set in the GitHub settings for this
  repo with a personal access token tied to an account with permissions to clone
  the repos listed at the top of `config.yml`, as well as permission to push
  updates back to this repo
