#!/usr/bin/env python

"""Generate a report on project dependencies as defined in a config file."""


import os
import re
import subprocess
from typing import List, Optional, TypedDict

import click
import yaml

BRANCH_CHOICES = ['main', 'SBX', 'SIT', 'UAT', 'PROD']


class Version(TypedDict, total=False):
    """Where to find the version, either from a git tag, or matching a regex in a file.

    If `commit` is true, then the commit is used as a fallback value for NSIDC
    CIRRUS versions if their actual commit does not contain a version tag. In
    that case, the displaeyd version is of the form `<commit sha / ancestor
    tag>`, where `ancestor tag` is the most recent tag in the git tree.
    """

    commit: bool  # use commit if there is no matching tag exactly on the commit
    file: str
    regex: str
    tag: str


class Component(TypedDict, total=False):
    """A component whose version we are interested in."""

    name: str
    owner: str
    repo: str
    parsed_version: str
    version: Version


class Repo(TypedDict):
    """A git repo.

    `source` is a string of the format `username/repo`, and `path` is the local
    path where the repo is cloned to.

    """

    name: str
    path: str
    source: str


def clone_repos(repos: List[Repo], ref: str) -> None:
    """Ensure each repo is cloned and up-to-date. If already cloned, a fetch is performed."""
    url_pattern = re.compile('://')

    for repo in repos:
        path = repo['path']
        source = repo['source']

        if not url_pattern.match(source):
            source = f'https://github.com/{source}'

        if not os.path.isdir(path):
            clone_cmd = f'git clone {source} {path}'
            shell(clone_cmd)

        fetch_cmd = f'cd {path} && git fetch'
        shell(fetch_cmd)

        ref_cmd = f'cd {path} && git checkout {ref}'
        shell(ref_cmd)


def component_path(component_repo: str, repos: List[Repo]) -> str:
    """Return the path to the repo directory where a component's version can be found."""
    for repo in repos:
        if repo['name'] == component_repo:
            return repo['path']

    raise Exception(f'No path found for {component_repo}')


def version_from_tag_or_commit(version_pattern: str, path: str, commit: bool) -> str:
    """Return a string representing the component's version, using the git tag at the given path."""
    version_parts = []

    commit_sha = shell('git rev-parse HEAD', cwd=path)

    tag = shell(f"git describe --tags --abbrev=0 --match '{version_pattern}'", cwd=path)
    tag_commit_sha = shell(f'git rev-list -n 1 "{tag}"', cwd=path)

    if commit and (commit_sha != tag_commit_sha):
        version_parts.append(commit_sha[:7])

    all_tags = shell(
        (
            'git show-ref --tags -d | '
            + f"grep '^{tag_commit_sha}' | "
            + "sed -e 's,.* refs/tags/,,' -e 's/^{}//' | "  # noqa: P103
            + ' sort | '
            + f"grep -E '^{version_pattern}$'"
        ),
        cwd=path,
    )
    latest_tag = all_tags.split('\n')[-1]

    version_parts.append(latest_tag)

    return ' / '.join(version_parts)


def shell(cmd: str, *, cwd: Optional[str] = None) -> str:
    """Run a shell command, return its stdout."""
    if cwd is None:
        cwd = os.getcwd()

    try:
        return subprocess.run(
            cmd,
            cwd=cwd,
            shell=True,
            encoding='utf-8',
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        ).stdout.strip()
    except subprocess.CalledProcessError as e:
        print(e.output)
        raise e


def extract_re_match(filepath: str, regex: re.Pattern[str]) -> str:
    """Return the regex's group match from the given filepath.

    For instance, if the file at `filepath` has a line `foobar`, and the regex
    is 'foo(.*)', this function would return 'bar'.
    """
    with open(filepath, 'r') as f:
        text = f.read()

    matches: List[str] = re.findall(regex, text)

    if len(matches) != 1:
        raise Exception(
            f'Did not find exactly one match in {filepath} for {regex}, matches: {matches}'
        )
    else:
        match = matches[0]
        if type(match) == tuple:
            match = '/'.join(match)

    return match


def parse_regex(yaml_regex: str) -> re.Pattern[str]:
    r"""Convert the regex string from the parsed YAML config to a re.Pattern.

    In addition to parsing/compiling the regex, this function also modifies the
    regex so that it works with the rest of the code here. Here's what it changes:

    - the characters `^` and `$` are replaced with `\n` either before or after
      the rest of the regex; other code in this file uses re.findall on a file's
      text, which checks the whole file at once, rather than by line-by-line, in
      which case `^` would only match at the beginning of the file, rather than
      each line; by converting the regex here, the YAML config can still contain
      characters like `^` and `$`, and behave in an expected way.
    """
    if yaml_regex[0] == '^':
        yaml_regex = '\n' + yaml_regex[1:]
    if yaml_regex[-1] == '$':
        yaml_regex = yaml_regex[:-1] + '\n'

    return re.compile(yaml_regex)


def get_output_text(components: List[Component], title: str) -> str:
    """Return a markdown string with title and table of the given components and their versions."""
    lines: List[str] = []

    # header
    lines.append(f'# {title}')
    lines.append('')

    # table
    lines.append('| Component | Owner | Version |')
    lines.append('| -- | -- | -- |')
    lines += [f"| {c['name']} | {c['owner']} | {c['parsed_version']} |" for c in components]

    return '\n'.join(lines)


@click.command()
@click.option(
    '-f',
    '--config-file',
    type=click.Path(exists=True),
    default='config.yml',
    help=(
        'Configuration file defining the components of interest, and where to '
        "find their used versions in the repos. Default: 'config.yml'"
    ),
)
@click.option(
    '-b',
    '--branches',
    '--branch',
    type=click.Choice(BRANCH_CHOICES),
    default=BRANCH_CHOICES,
    multiple=True,
    help=(
        'Which branch(es) in the configured repos to checkout and inspect. '
        'Default: -b main -b SBX -b SIT -b UAT -b PROD'
    ),
)
@click.option(
    '-r',
    '--remote',
    type=str,
    default='origin',
    help="The name of the git remote. Default: 'origin'",
)
@click.option(
    '-o',
    '--output-file',
    type=str,
    help=(
        'Output file name. Default: the first given branch name, with .md '
        "extension, e.g., 'main.md'"
    ),
)
def main(config_file: str, branches: List[str], remote: str, output_file: Optional[str]) -> None:
    """Generate the report."""
    if not config_file:
        print('No config file given, goodbye.')
        return

    if len(branches) == 1:
        branch = branches[0]
        output_file = branch
    elif not output_file:
        print('No output file given for multiple branches, goodbye.')
        return

    output_file = f'{output_file}.md'
    output_file = re.sub('(.md)+', '.md', output_file)

    branch_texts = []
    for branch in branches:
        print(f'branch: {branch}')

        ref = f'{remote}/{branch}'

        with open(config_file, 'r') as f:
            parsed = yaml.safe_load(f)
        clone_repos(parsed['repos'], ref)

        for component in parsed['components']:
            print(f'Checking component {component["name"]}')

            path = component_path(component['repo'], parsed['repos'])
            version = component['version']

            if tag_pattern := version.get('tag'):
                parsed_version = version_from_tag_or_commit(
                    tag_pattern, path, version.get('commit')
                )
            else:
                filepath = os.path.join(path, version['file'])
                regex = parse_regex(version['regex'])

                try:
                    parsed_version = extract_re_match(filepath, regex)
                except Exception:
                    parsed_version = 'could not find version'
            component['parsed_version'] = parsed_version

        branch_texts.append(get_output_text(parsed['components'], branch))
        print('')

    output_text = '\n\n'.join(branch_texts)
    with open(f'{output_file}', 'w') as f:
        f.write(output_text)
    print(f'Wrote {output_file}')


if __name__ == '__main__':
    main()
