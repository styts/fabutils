import os
import fabric
from fabric.api import run, cd, local
from cuisine import select_package, user_check, user_ensure, user_remove
from cuisine import file_link, file_unlink, file_upload, dir_exists

# cuisine should know if we're on Debian or Redhat
select_package("apt")

project_name = os.environ['PROJECT_NAME']


def tail():
    run('tail -f /home/%s/production/logs/error.log' % project_name)


def run_venv(cmd, env='production'):
    # prefix for activating virtualenv
    prefix = "source /home/" + project_name + "/%s/env/bin/activate &&"
    run(prefix % env + " " + cmd)


def uninstall():
    if fabric.contrib.console.confirm(
        "!!! ACHTUNG !!!\nthis will delete all data!\nContinue?",
        default=False):
        run('service apache2 stop')
        if user_check(project_name):
            user_remove(project_name)
            run('rm -rf /home/%s' % project_name)
        file_unlink('/etc/apache2/sites-enabled/' + project_name)
        run('rm -rf /etc/apache2/sites-available/' + project_name)
        run('service apache2 start')


def setup_system():
    user_ensure(project_name, home='/home/' + project_name)
    if not dir_exists('/home/%s/production' % project_name):
        with cd('/home/%s' % project_name):
            run('git clone file:///root/repos/%s.git production' % project_name
                )
            run('git clone file:///root/repos/%s.git staging' % project_name)
            with cd('production'):
                run('virtualenv env')
                run_venv('pip install -r assets/requirements.txt',
                         env='production')
                with cd('%s/settings' % project_name):
                    file_link('production.py', '__init__.py')
                run('mkdir -p logs')
                run('chown %s:%s logs -R' % (project_name, project_name))
                run('chmod o+wx logs -R')
                run('mkdir -p static')
                run_venv('./manage.py collectstatic --noinput',
                         env="production")
            with cd('staging'):
                run('virtualenv env')
                run_venv('pip install -r assets/requirements.txt',
                         env='staging')
                with cd('%s/settings' % project_name):
                    file_link('staging.py', '__init__.py')
                run('mkdir -p logs')
                run('chown %s:%s logs -R' % (project_name, project_name))
                run('chmod o+wx logs -R')
                run('mkdir -p static')
                run_venv('./manage.py collectstatic --noinput',
                         env="staging")


def setup_apache():
    # apache: vhost
    file_upload('/etc/apache2/sites-available/%s' % project_name,
                'assets/vhost.conf')
    file_link('/etc/apache2/sites-available/%s' % project_name,
              '/etc/apache2/sites-enabled/%s' % project_name)

    # apache: enable mod_rewrite
    run('a2enmod rewrite')

    # apache: restart
    run('service apache2 restart')


def setup():
    # user, home, clone
    setup_system()

    # vhost, reload
    setup_apache()


def pip_update_reqs():
    local('pip freeze -r assets/requirements.txt | \
grep -v "git-remote-helpers" > assets/requirements.txt')


def deploy(env='production'):
    local('git push')
    with cd('/home/%s/%s' % (project_name, env)):
        run('git pull')
        run_venv('./manage.py collectstatic --noinput', env=env)
        run('touch wsgi.py')


def stage():
    deploy(env='staging')


def hello():
    """ for testing the fabutils """
    print "hello world! says fabutils for project %s" % project_name
