"""Fabfile for deepbills project"""

from fabric.api import *

env.forward_agent = True # this is for remote `git pull` commands
env.hosts = ['deepbills.cato.org']
env.user = 'favila'
env.gitrepo = 'git@dancingmammoth.beanstalkapp.com:/deepbills.git'
env.editordir = '../AKN/Editor'
env.vocabfiles = ['acts.xml', 'billversions.xml', 'committees.xml', 'federal-bodies.xml', 'people.xml']
env.basexclientcmd = 'basexclient -Uadmin -Padmin'

def deploy():
    "Deploy everything; same as 'deploy_virtualenv deploy_deepbills deploy_editor deploy_reload'"
    deploy_deepbills()
    deploy_editor()
    deploy_reload()


def push_deepbills():
    "Push local master to origin, in preparation for a 'git pull' on production"
    local('git push origin master')


def deploy_deepbills():
    """Update code and virtualenv on production"""
    run('if [ ! -d deepbills ]; then git clone %(gitrepo)s; fi' % env)
    with cd('deepbills'):
        run('git pull origin master')
    run("if [ ! -d env ]; then virtualenv env --prompt='(deepbills)'; fi")
    run("if [ ! -d virtualenv-install-cache ]; then mkdir virtualenv-install-cache; fi")
    with cd('deepbills'):
        run('source ../env/bin/activate && pip install -r requirements.txt --download-cache=~/virtualenv-install-cache')


def deploy_editor():
    """Rsync editor files to production

    Nginx (or web server) needs to know 
    """
    local("rsync -az -e 'ssh -c arcfour' --exclude='.*' --exclude='.git/' --delete-after --delete-excluded %(editordir)s -- %(user)s@%(host)s:" % env)


def deploy_reload():
    """Reloads servers to pick up new code.

    Only absolutely necessary after an nginx config change or a deploy_deepbills
    """
    uwsgi_service('stop')
    uwsgi_service('start')

def uwsgi_service(cmd):
    """Issue cmd to the uwsgi service

    Commands are passed unchanged to the underlying `service uwsgi` shell command
    Important ones are: start, stop, reload

    User that is logged in (env.user) should have an sudoers line like so:

    env.user  ALL = (root) NOPASSWD: /usr/sbin/service nginx *, /usr/sbin/service uwsgi *
    """
    # shell is false so user doesn't need ability to run a shell as root!
    sudo('service uwsgi {} deepbills'.format(cmd), shell=False)


def nginx_service(cmd):
    """Issue cmd to the nginx service

    Commands are passed unchanged to the underlying `service nginx` shell command
    Important ones are: start, stop, reload

    User that is logged in (env.user) should have an sudoers line like so:

    env.user  ALL = (root) NOPASSWD: /usr/sbin/service nginx *, /usr/sbin/service uwsgi *
    """
    # shell is false so user doesn't need ability to run a shell as root!
    sudo('service nginx {}'.format(cmd), shell=False)


def basex_service(cmd):
    """Start or stop the underlying basex database

    cmds may be 'start' or 'stop'
    """
    shellcmds = {
        'start': 'nohup basexserver -S',
        'stop':  'basexserver stop',
    }
    run(shellcmds[cmd])


def backup_live_db():
    "Create a backup of the live DB; does not download!"
    run('{env.basexclientcmd} -c"CREATE BACKUP deepbills"'.format(env=env))


def download_latest_backup():
    "Download the most recent backup on live; does not create new backup!"
    output = run('dir BaseXData/deepbills-* | sort -r | head -1').stdout
    latestfile = output.strip()

    with lcd('~'):
        get(latestfile, latestfile)


def restore_local():
    "Restore the most recent db backup locally available"
    local('{env.basexclientcmd} -c"RESTORE deepbills; OPEN deepbills; OPTIMIZE; CLOSE"'.format(env=env))


def sync_db_to_local():
    """Copy remote db to local db.

    Same as backup_live_db download_latest_backup restore_local
    """
    backup_live_db()
    download_latest_backup()
    restore_local()


def new_bills_and_automarkup():
    "Pull down and add new bills, sync to remote, add to remote db, and create automarkup."
    backup_live_db()
    with lcd('../fdsysScraper/data'):
        local('make')
    with cd('data'):
        run('./add_new_bills.sh')
    run('{env.basexclientcmd} create-auto-markup-docs.bxs'.format(env=env))


def update_vocabularies():
    "Update the vocabulary datafiles"
    remotefiledir = '/home/favila/data/deepbills/vocabularies'
    replacecmd = 'REPLACE vocabularies/{0} {1}/{0}'
    replacecmds = '; '.join(replacecmd.format(fn, remotefiledir) for fn in env.vocabfiles)
    fullcmd = '{env.basexclientcmd} -c"OPEN deepbills; SET CHOP true; {replacecmds}; OPTIMIZE; CLOSE"'
    run(fullcmd.format(replacecmds=replacecmds, env=env))
