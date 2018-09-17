#!/usr/bin/python3

from fabric.contrib.files import append, exists, sed, put
from fabric.api import env, local, run, sudo

import random
import json
import os

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(PROJECT_DIR)

with open(os.path.join(PROJECT_DIR, "deploy.json")) as f:
    envs = json.load(f)

REPO_URL = envs['REPO_URL']
PROJECT_NAME = envs['PROJECT_NAME']
REMOTE_HOST_SSH = envs['REMOTE_HOST_SSH']
REMOTE_HOST = envs['REMOTE_HOST']
REMOTE_USER = envs['REMOTE_USER']
REMOTE_PASSWORD = envs['REMOTE_PASSWORD']

# same name in setting.py of django
STATIC_ROOT_NAME = ''
STATIC_URL_NAME = ''
MEDIA_ROOT = ''

env.user = REMOTE_USER
env.hosts = [
    REMOTE_HOST_SSH,
]
env.password = REMOTE_PASSWORD
username = env.user
# django project path in remote server
project_folder = '/home/{}/{}'.format(env.user, PROJECT_NAME)

yum_requirements = [
    'python36',
    'python36-devel',
    'git'
]


def new_server():
    setup()
    deploy()


def setup():
    _get_latest_yum()
    _install_yum_requirements(yum_requirements)
    _make_venv()


def deploy():
    _get_latest_source()
    # _put_envs()
    _update_settings()
    _update_venv()
    _update_static_files()
    _update_databases()
    # _make_virtualhost()
    _grant_sqlite3()
    # _restart_webserver()


# private
# yum update & upgrade
def _get_latest_yum():
    update_or_not = input('Would you update?: [y|n]')
    if update_or_not == 'y':
        sudo('sudo yum update && sudo yum -y upgrade')


# yum packages install
def _install_yum_requirements(yum_requirements):
    reqs = ''
    for req in yum_requirements:
        reqs += (' ' + req)
    sudo('sudo yum -y install {}'.format(reqs))


# venv
def _make_venv():
    if not exists('~/myvenv'):
        run('python3 -m venv ~/myvenv')


# source
def _get_latest_source():
    # update
    if exists(PROJECT_DIR + '/.git'):
        run('cd {} && git fetch'.format(project_folder))
    # if not exists, clone
    else:
        run('git clone {} {}'.format(REPO_URL, project_folder))
    # get latest git log from local
    current_commit = local('git log -n -1 --format=%H', capture=True)
    run('cd {} && git reset --hard {}'.format(project_folder, current_commit))


def _update_settings():
    settings_path = project_folder + '/{}/settings.py'.format(PROJECT_NAME)
    sed(settings_path, 'DEBUG = True', 'DEBUG = False')
    sed(settings_path, 'ALLOWED_HOSTS = .+$',
        'ALLOWED_HOSTS = ["{}"]'.format(REMOTE_HOST))
    secret_key_file = project_folder + '/{}/secret_key.py'.format(PROJECT_NAME)
    if not exists(secret_key_file):
        chars = 'abcdefghijklmnopqrstuvwxyz!@#$%&^&*()_+-='
        key = ''.join(random.SystemRandom().choices(chars) for _ in range(50))
        append(secret_key_file, 'SECRET_KEY = "{}"'.format(key))
    append(settings_path, '\nfrom .secret_key import SECRET_KEY')


def _update_venv():
    venv_folder = '~/myvenv'
    run('{}/bin/python -m pip install -r requirements.txt'.format(venv_folder))


def _update_static_files():
    venv_folder = '~/myvenv'
    run('cd {} && {}/bin/python manage.py collectstatic --noinput'
        .format(project_folder, venv_folder))


def _update_databases():
    venv_folder = '~/myvenv'
    run('cd {} && {}/bin/python3 manage.py migrate --noinput'
        .format(project_folder, venv_folder))


def _grant_sqlite3():
    sudo('sudo chmod 775 ~/{}/db.sqlite3'.format(PROJECT_NAME))
