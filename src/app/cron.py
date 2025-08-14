#!/usr/bin/env python3

import datetime, os, sys, subprocess
from app.databaseHelpers import record_solves
from time import sleep
#from app.env import get_clean_env
from app.extensions import globals, logger
from app.grading import post_submission, read_token

def set_cron_vars(conf: dict) -> None:
    '''
    This is going to set the value of the cron global vars
    First try to see if there are any test guestinfo variables set
    If there are test guestinfo variables set, then use those
    If there are no test guestinfo variables set, then use the config file or defaults
    '''
    cron_interval_cmd = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.test_cron_interval'", shell=True, capture_output=True)
    if 'no value' in cron_interval_cmd.stderr.decode('utf-8').lower():
        globals.cron_interval = conf['grading']['cron_interval'] if conf['grading']['cron_interval'] else 60
    else:
        globals.cron_interval = int(cron_interval_cmd.stdout.decode('utf-8'))
        logger.debug(f"Using a guestinfo var intended for testing: cron_interval = {globals.cron_interval}")

    cron_limit_cmd = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.test_cron_limit'", shell=True, capture_output=True)
    if 'no value' in cron_limit_cmd.stderr.decode('utf-8').lower():
        globals.cron_limit = conf['grading']['cron_limit'] if conf['grading']['cron_limit'] else -1
    else:
        globals.cron_limit = int(cron_limit_cmd.stdout.decode('utf-8'))
        logger.debug(f"Using a guestinfo var intended for testing: cron_limit = {globals.cron_limit}")

    cron_delay_cmd = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.test_cron_delay'", shell=True, capture_output=True)
    if 'no value' in cron_delay_cmd.stderr.decode('utf-8').lower():
        globals.cron_delay = conf['grading']['cron_delay'] if conf['grading']['cron_delay'] else 0
    else:
        globals.cron_delay = int(cron_delay_cmd.stdout.decode('utf-8'))  
        logger.debug(f"Using a guestinfo var intended for testing: cron_delay = {globals.cron_delay}")


    cron_at_cmd = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.test_cron_at'", shell=True, capture_output=True)
    if 'no value' in cron_at_cmd.stderr.decode('utf-8').lower():
        globals.cron_at = conf['grading']['cron_at']
    else:
        globals.cron_at = cron_at_cmd.stdout.decode('utf-8')
        logger.debug(f"Using a guestinfo var intended for testing: cron_at = {globals.cron_at}")

    # calculates the total delay by using the cron_at setting and adding it to the cron_delay
    if globals.cron_at is not None:
        globals.cron_type = "at"
        time = globals.cron_at.split(':')
        current_time = datetime.datetime.now()

        start_time = datetime.datetime(current_time.year, current_time.month, current_time.day, hour=int(time[0]), minute=int(time[1]))
        logger.debug(f"Cron style grading should begin at {start_time}")

        time_diff = (start_time - current_time).total_seconds()
    else:
        globals.cron_type = "every"
        time_diff = 0
    
    globals.cron_delay = globals.cron_delay + time_diff


def do_cron_grade() -> tuple[dict,dict]:
    '''
    This method is the actual grading and token reading for all manual based questions
    The method gets called from the Jinja template rendering (inside { } in the graded.html file)
    '''
    #logger.info(f"---------Calling {globals.manual_grading_script} with arguments: {args}")
    globals.fatal_error = False
        
    try:
        out = subprocess.run([f"{globals.custom_script_dir}/{globals.cron_grading_script}"], capture_output=True, check=True)
        logger.info(f"Grading process finished: {out}")
        output = out.stdout.decode('utf-8')
    
    # Something happened if there was a non-zero exit status. Log this and set fatal_error
    except subprocess.CalledProcessError as e:
        logger.error(f"Grading script {globals.manual_grading_script} returned with non-zero exit status {e.returncode}.\tStdout: {e.stdout}\tStderr: {e.stderr}")
        globals.fatal_error = True
        output = ""
    
    results = []
    for sub in output.split('\n'):
        if ':' in sub:
            results.append(map(str.strip, sub.split(':', 1)))

    results = dict(results)

    # ensure all grading parts have a result
    for grading_key in globals.grading_parts.keys():
        if globals.grading_parts[grading_key]['mode'] != 'cron':
            continue
        if grading_key not in results:
            logger.info(f"Grading script, {globals.cron_grading_script}, did not yield a result for grading part {grading_key}. Assigning value of 'Failed'")
            results[grading_key] = "Failed"

    # for each result that is returned, check if success is in the message. 
    # If success is in the message, then read and store the token for that check
    end_results = results.copy()
    tokens = {}
    for key, value in results.items():
        if key not in globals.grading_parts.keys():
            logger.debug(f"Found key in results that is not a grading part. Removing {key} from results dict. ")
            del end_results[key]
        if "success" in value.lower():
            tokens[key] = read_token(key)
        else:
            tokens[key] = "You did not earn a token for this part"

    logger.debug(f"Grading Results: {end_results}")
    logger.debug(f"Grading tokens: {tokens}")
    return end_results, tokens


def run_cron_thread() -> None:
    '''
    This method is meant to be run inside  a thread. 
    The method will run do_grade on a timer (similar to a cron job)
    '''
    limit = globals.cron_limit
    logger.info(f"Starting cron thread with interval {globals.cron_interval}. Grading is limited to running {limit} times.")

    cron_attempts = 0
    while globals.cron_limit != 0:
        cron_attempts += 1
        globals.cron_limit = globals.cron_limit - 1
        globals.cron_submit_time = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        logger.info(f"Starting cron grading attempt number {cron_attempts}")
        globals.cron_results, tokens = do_cron_grade()
        globals.tokens['cron'] = tokens
        if globals.grader_post:
            post_submission(tokens)
        logger.info(f"Results of cron grading attempt number {cron_attempts}: {globals.cron_results}")
        globals.scheduler.add_job(id="Record_Solves",func=record_solves)
        sleep(globals.cron_interval)
    logger.info(f"The number of grading attempts ({limit}) has been exhausted. No more grading will take place.")
