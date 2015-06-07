from __future__ import with_statement
from fabric.api import local
from fabric.colors import green, magenta, yellow
from fabric.context_managers import hide

def up():
    with hide('running'):
        print green(local("docker-compose up -d", capture=True))

def mn():
    with hide('running'):
        local("docker-compose run mininet mn --link tc,bw=0.1 --custom /source/topo3.py --topo project --switch user --controller remote,ip=192.168.59.103 --mac")

def ps():
    with hide('running'):
        print yellow(local("docker-compose ps", capture=True))

def rm():
    with hide('running'):
        print magenta("[1/2] Stop all service...", bold=True)
        print green(local("docker-compose stop", capture=True))

        print magenta("[2/2] Remove all container...", bold=True)
        print green(local("docker-compose rm -f", capture=True))
