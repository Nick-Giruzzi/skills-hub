#!/usr/bin/env python3

import sys, random, threading, os, signal, sys, argparse, logging, time, signal
from flask_executor import Executor
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor
# local imports
from app import create_app, start_grading_server, run_startup_scripts
from app.grading import done_grading
from app.portServiceChecker import get_logs, waitForService, checkServiceLoop, checkLocalPortLoop
from app.extensions import globals
from app.globals import Globals
from app.databaseHelpers import initialize_db
from app.loggingConfig import setup_logging

# Create flask app obj
app = create_app()
if __name__ == '__main__':
    if os.geteuid() != 0:
        globals.log("error","Program must be ran by root.")
        sys.exit(1)

    '''
    This code will start the threads and handle running all aspect of the server
    '''

    parser = argparse.ArgumentParser(description="Challenge Server")
    parser.add_argument('--debug', action='store_true', help="Enable debug logging. This overrides --log-level.")
    parser.add_argument('--log-level', help="Set the log level to : DEBUG, INFO, WARNING, ERROR, CRITICAL.",
                        default="INFO")
    args = parser.parse_args()

    CORS(app)
    globals.executor = Executor(app)
    globals.executor.add_default_done_callback(done_grading)

    Globals.from_yaml(globals, app)

    setup_logging(app)

    globals.log("info",f"Skills Hub starting up")
    globals.log("debug","Skills Hub Operating in a Workspace" if globals.in_workspace else "Skills Hub Operating in a Gamespace")


    initialize_db(app, globals.conf)

    # start the website
    grading_server_thread = threading.Thread(target=start_grading_server, name="GradingServer", args=(app,))
    grading_server_thread.start()
    
    # wait for blocking services to come up
    globals.log("info",f"Waiting for blocking services to become available")
    globals.blocking_threadpool.map(waitForService, globals.blocking_services)
    globals.blocking_threadpool.shutdown(wait=True)
    globals.log("info",f"All blocking services are available")

    # run startup scripts
    successes, errors = run_startup_scripts(app)
    if errors:
        globals.log("error",f"Startup scripts exited with error(s): {list(errors.keys())}")
        os.kill(os.getpid(), signal.SIGINT)
        time.sleep(0.5)
        sys.exit(1)
    if successes: 
        globals.log("info",f"All startup scripts exited normally: {list(successes.keys())}")

    globals.server_ready = True # mark server as ready after startup scripts finish

    # run a thread that will periodically check on all required services
    if (globals.required_services != []) and (globals.required_services != None):
        globals.log("info","Starting check on required services.")
        service_check_pool = ThreadPoolExecutor(thread_name_prefix="ServiceCheck")
        service_check_pool.map(checkServiceLoop, globals.required_services)

    # run a thread that will periodically list the local open ports 
    port_checker_thread = threading.Thread(target=checkLocalPortLoop, name="LocalPortChecker")
    
    if globals.services_list != None:
        service_checker_pool = ThreadPoolExecutor(thread_name_prefix="Service_logger")
        service_check_pool.map(get_logs, globals.services_list)
    
    port_checker_thread.start()
    grading_server_thread.join()