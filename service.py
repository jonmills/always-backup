#!/usr/bin/python
import glob
import sys
import os
import time
from multiprocessing import Process
import signal

sys.path.append('./modules')

#getting the config
cfg = eval(file('config').read())
try:
    cfg = eval(file('local.config').read())
except:
    pass

#Getting all sync plugins
modules = {}
for folder in glob.glob("./plugins/*/"):
    try:
       module = folder.split('/')[-2]
       exec("import plugins.%s.main as %s" % (module, module))
       modules.update(eval(file(folder + "plugin_def").read()))
    except:
        if cfg['global']['verbose']:
            print sys.exc_info()
        pass

def service_web():
    run(host=cfg['webserver']['ip'], port=cfg['webserver']['port'], quiet=True)

def get_diff(source, target):
    missing_files = []
    for ident, values in source:
        if values['upd_attr'] not in [ y['upd_attr'] for x, y in target ]:
            missing_files.append(( ident, values))
    return missing_files

def save_stat_file(data, folder):
    path = "%s/%s/state" % (cfg['global']['base_path'], folder)
    file(path, "w").write(str(data))

def get_update_state(folder):
    path = "%s/%s/upd_state" % (cfg['global']['base_path'], folder)
    try:
        return file(path).read()
    except:
        return False

def set_update_state(folder, state):
    path = "%s/%s/upd_state" % (cfg['global']['base_path'], folder)
    file(path, "w").write(state)

def service_sync():
    run = True
    while run:
        if len(cfg['sync_pairs']) > 0:
            for job in cfg['sync_pairs']:
                if cfg['global']['verbose']:
                    print "\n#### Working on '%s' ####" % job['name']
                #Get sync config
                source_name = job['source']['name']
                source =  modules.get(source_name)
                if source == None:
                    sys.stderr.write("Module: %s not found. Skipping sync configuration" % source_name)
                    continue

                target_name = job['target']['name']
                target =  modules.get(target_name)
                if target == None:
                    sys.stderr.write("Module: %s not found. Skipping sync configuration" % target_name)
                    continue
                try:
                    path = "%s/%s/" % (cfg['global']['base_path'], job['name'])
                    os.makedirs(path)
                except os.error:
                    pass

                #Begin Sync
                updState = get_update_state(job['name'])
                need_sync, updState = source['init_function'](job['name'], job['source'].get('options'), cfg['global'], updState, 'source')
                set_update_state(job['name'], updState)
                target['init_function'](job['name'], job['target'].get('options'), cfg['global'], False, 'target')
                if need_sync:
                    #Get a list of the files we want to sync
                    source_files = source['list_function']()
                    missing_files = get_diff(source_files, target['list_function']())
                    #let source pull function push it to the target push function
                    source['pull_function'](missing_files, target['push_function'])
                    #Save out stat file that we can compere next time
                    #Save out stat file that we can compere next time
                    save_stat_file(source_files, job['name'])

        else:
            if cfg['global']['verbose']:
                sys.stderr.write("Sync: Nothing to do. Pleas configure at least a sync pair")

        if not cfg['global']['run_as_service']:
            run = False
            if cfg['global']['verbose']:
                print "Sync job service finished"
        else: 
            if cfg['global']['verbose']:
                print "Starting over after a 10min break"
            try:
                time.sleep(600)
            except:
                if cfg['global']['verbose']:
                    print "Have to end the Sync loop... :("
                return
            
#Including Website
execfile('./website/main.py')

#webservice = Process(target=service_web)
#webservice.deamon = True
#webservice.start()
#if cfg['global']['verbose']:
#    print "Serverstarted. You can use your browser to configure: http://%s:%s" % \
#                                (cfg['webserver']['ip'], cfg['webserver']['port']) 
#
syncservice = Process(target=service_sync)
syncservice.deamon = True
syncservice.start()

def quit(signum, frame):
    if cfg['global']['verbose']:
        print "\nThanks for using always Backup"
    try:
        sys.exit(0)
    except:
        pass

signal.signal(signal.SIGINT, quit)
