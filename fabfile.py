"""Fabfile for deepbills project"""

from fabric.api import *

env.hosts = ['deepbills.dancingmammoth.com']
env.user = 'favila'
env.gitrepo = 'https://github.com/favila/deepbills.git'
env.editordir = '../AKN/Editor'
env.vocabfiles = ['acts.xml', 'billversions.xml', 'committees.xml', 'federal-bodies.xml', 'people.xml']


def push_and_deploy():
    push_deepbills()
    deploy()


def deploy():
    deploy_virtualenv()
    deploy_deepbills()
    deploy_editor()
    restart_servers()


def push_deepbills():
    local('git push beanstalk')


def deploy_virtualenv():
    #set up the virtualenv
    run('if [ ! -d env ]; then virtualenv env; fi')


def deploy_deepbills():
    # upload requirements.txt and install everything
    run('if [ ! -d deepbills ]; then git clone %(gitrepo)s; fi' % env)
    with cd('deepbills'):
        run('git pull')
        run('source ../env/bin/activate && pip install -r requirements.txt && python setup.py develop')


def deploy_editor():
    #rsync editor files, make symlink
    #Only copy HouseXML, Editor, BCN, AkomaNtoso
    local("rsync -arz -e 'ssh -c arcfour' --exclude='.*' --exclude='.git/' %(editordir)s -- %(user)s@%(host)s:" % env)


def restart_servers():
    with settings(warn_only=True):
        wsgi_stop()
        basex_stop()
        with settings(user='root'):
            nginx_stop()
    wsgi_start()
    basex_start()
    with settings(user='root'):
        nginx_start()


def wsgi_stop():
    with cd('deepbills'):
        run('source ../env/bin/activate && pserve --stop-daemon development.ini')


def nginx_stop():
    run('service nginx stop')


def basex_stop():
    run('basexserver stop')


def basex_start():
    run('nohup basexserver -S')


def nginx_start():
    run('service nginx start')


def wsgi_start():
    with cd('deepbills'):
        run('source ../env/bin/activate && pserve --daemon development.ini')


def backup_live_db():
    run('basexclient -Uadmin -Padmin -c"CREATE BACKUP deepbills"')


def download_latest_backup():
    """Download the most recent backup on live"""
    output = run('dir BaseXData/deepbills-* | sort -r | head -1').stdout
    latestfile = output.strip()

    with lcd('~'):
        get(latestfile, latestfile)


def restore_local():
    local('basexclient -Uadmin -Padmin -c"RESTORE deepbills"')
    local('basexclient -Uadmin -Padmin -c"OPEN deepbills; OPTIMIZE; CLOSE"')


def sync_db_to_local():
    backup_live_db()
    download_latest_backup()
    restore_local()


def new_bills_and_automarkup():
    backup_live_db()
    with lcd('../fdsysScraper/data'):
        local('make')
        run('make createnew_remote')
    with cd('data'):
        run('./add_new_bills.sh')
    run('basexclient -Uadmin -Padmin create-auto-markup-docs.bxs')


def update_vocabularies():
    remotefiledir = '/home/favila/data/deepbills/vocabularies'
    # remotefiledir = '/Users/favila/Documents/workingcopies/deepBills/fdsysScraper/data/templates/vocabularies'
    replacecmd = 'REPLACE vocabularies/{0} {1}/{0}'
    replacecmds = '; '.join(replacecmd.format(fn, remotefiledir) for fn in env.vocabfiles)
    fullcmd = 'basexclient -Uadmin -Padmin -c"OPEN deepbills; SET CHOP true; {}; OPTIMIZE; CLOSE"'
    run(fullcmd.format(replacecmds))
