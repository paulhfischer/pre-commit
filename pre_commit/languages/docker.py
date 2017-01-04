from __future__ import absolute_import
from __future__ import unicode_literals

import hashlib
import os

from pre_commit import five
from pre_commit.languages import helpers
from pre_commit.util import clean_path_on_failure
from pre_commit.util import mkdirp
from pre_commit.xargs import xargs


ENVIRONMENT_DIR = 'docker'
PRE_COMMIT_LABEL = 'PRE_COMMIT'


def md5(s):
    return five.to_text(hashlib.md5(s).hexdigest())


def docker_tag(repo_cmd_runner):
    return 'pre-commit-{}'.format(
        md5(os.path.basename(repo_cmd_runner.path()))
    ).lower()


def docker_is_running():
    return xargs(('docker',), ['ps'])[0] == 0


def assert_docker_available():
    assert docker_is_running(), (
        'Docker is either not running or not configured in this environment'
    )


def build_docker_image(repo_cmd_runner):
    cmd = (
        'docker', 'build', '--pull',
        '--tag', docker_tag(repo_cmd_runner),
        '--label', PRE_COMMIT_LABEL,
        '.'
    )
    helpers.run_setup_cmd(repo_cmd_runner, cmd)


def install_environment(
        repo_cmd_runner,
        version='default',
        additional_dependencies=(),
):
    assert repo_cmd_runner.exists('Dockerfile'), (
        'No Dockerfile was found in the hook repository'
    )
    assert version == 'default', (
        'Pre-commit does not support language_version for docker '
    )
    assert_docker_available()

    directory = helpers.environment_dir(ENVIRONMENT_DIR, 'default')
    mkdirp(os.path.join(repo_cmd_runner.path(), directory))

    # Docker doesn't really have relevant disk environment, but pre-commit
    # still needs to cleanup it's state files on failure
    env_dir = repo_cmd_runner.path(directory)
    with clean_path_on_failure(env_dir):
        build_docker_image(repo_cmd_runner)


def run_hook(repo_cmd_runner, hook, file_args):
    assert_docker_available()
    # Rebuild the docker image in case it has gone missing, as many people do
    # automated cleanup of docker images.
    build_docker_image(repo_cmd_runner)
    # the docker lib doesn't return stdout on non-zero exit codes,
    # so we run the container directly on the command line
    cmd = (
        'docker', 'run',
        '--rm',
        '-u', '{}:{}'.format(os.getuid(), os.getgid()),
        '-v', '{}:/src:rw'.format(os.getcwd()),
        '--workdir', '/src',
        '--entrypoint', hook['entry'],
        docker_tag(repo_cmd_runner)
    )

    return xargs(cmd + tuple(hook['args']), file_args)
