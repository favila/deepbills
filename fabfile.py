"""Fabfile for deepbills project"""

from fabric.api import *

env.hosts = ['deepbills.dancingmammoth.com']
env.user = 'favila'
env.gitrepo = 'https://github.com/favila/deepbills.git'


def push_and_deploy():
	push_deepbills()
	deploy()


def deploy():
	deploy_virtualenv()
	deploy_deepbills()
	deploy_editor()
	restart_servers()
	
def push_deepbills():
	local('git push origin')

def deploy_virtualenv():
	#set up the virtualenv
	run('if [ ! -d env ]; then virtualenv env; fi')

def deploy_deepbills():
	# upload requirements.txt and install everything
	run('if [ ! -d deepbills ]; then git clone %(gitrepo)s; fi' % env)
	with cd('deepbills'):
		run('git fetch')
		run('source ../env/bin/activate && pip install -r requirements.txt')

def deploy_editor():
	#rsync editor files, make symlink
	local('rsync -ar --cvs-exclude ../AKN/Editor %(user)s@%(host)s:' % env)
	run('if [ ! -a deepbills/deepbills/static/Editor ]; then cd deepbills/deepbills/static; '
		' ln -s ../../../Editor; fi')

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

