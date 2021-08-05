
1. use pyenv (https://github.com/pyenv/pyenv) to set up latest Python (3.9)
2. set up poetry (https://github.com/python-poetry/poetry); see XMLTransformECS2ECHO10 project
3. write python script as described below
4. fix `update.sh` to actually run the python script and update the git repo
5. configure GitHub Actions to run `update.sh` daily


### Python script
- read repos from config.yml, clone/update them
- for each environment:
  - check out all the repos to the branch for that environment (ie, `git checkout SBX`)
  - for each component:
    - if version has 'tag', find the most recent tag in git history that matches the given tag pattern
    - if version has 'file' and 'regex', open up that file, find the line matching the given regex, extract the version from that
    - save the component's 'name' and version
  - dump all the saved component names+versions to the file for the environment (e.g., SBX.md)
