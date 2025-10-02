#!/usr/bin/env python3

from concurrent.futures import Future
import datetime, json, os, subprocess, sys, requests
from time import sleep
from typing import Any
from app.databaseHelpers import check_db, get_current_phase, record_solves, update_db
#from app.env import get_clean_env
from app.extensions import db, globals
#from app.fileUploads import get_most_recent_file
from app.models import EventTracker

####### 
# functions to be used during grading process
#######
def do_grade(args: dict) -> tuple[dict,dict]:
    '''
    This method is the actual grading and token reading for all manual based questions
    The method gets called from the Jinja template rendering (inside { } in the graded.html file)
    '''
    #logger.info(f"---------Calling {globals.manual_grading_script} with arguments: {args}")
    globals.fatal_error = False
    manual_grading_list = list()
    for ques,ans in args.items():
        if (ques not in globals.grading_parts.keys()) or (globals.grading_parts[ques]['mode'] not in globals.VALID_CONFIG_MODES):
            #globals.log("debug",f"The key {ques} is not a valid grading aspect or valid part of question configuration. Skipping")
            globals.log('debug',f"The key {ques} is not a valid grading aspect or valid part of question configuration. Skipping")
            continue
        if (globals.grading_parts[ques]['mode'] in globals.MANUAL_MODE) and (globals.grading_parts[ques]['mode'] != "button"):
            index = int(ques[-1]) 
            manual_grading_list.insert(index,{ques:ans})

    grade_cmd = [f"{globals.custom_script_dir}/{globals.manual_grading_script}"]
    grade_args = dict()
    if len(manual_grading_list) != 0:
        for entry in manual_grading_list:
            grade_args[list(entry.keys())[0]] = list(entry.values())[0]
        grade_cmd.append(json.dumps(grade_args))
    
    if globals.phases_enabled == True:
        current_phase = get_current_phase()
        if current_phase != 'completed':
            grade_cmd.append(current_phase)
        else:
            tmp = [f'{grade_key} : Success' for grade_key in globals.grading_parts.keys()]
            results = dict(tmp)
            return get_results(results)
            
    try:
        out = subprocess.run(grade_cmd, capture_output=True, check=True)
        #globals.log("info",f"Grading process finished: {out}")
        globals.log('info',f"Grading process finished: {out}")
        output = out.stdout.decode('utf-8')
        if (output == "") or (output == None):
            #globals.log("error","Grading script finished without returning any output.")
            globals.log('error',"Grading script finished without returning any output.")
            globals.fatal_error = True
    # Something happened if there was a non-zero exit status. Log this and set fatal_error
    except subprocess.CalledProcessError as e:
        #globals.log("error",f"Grading script {globals.manual_grading_script} returned with non-zero exit status {e.returncode}.\tStdout: {e.stdout}\tStderr: {e.stderr}")
        globals.log('error',f"Grading script {globals.manual_grading_script} returned with non-zero exit status {e.returncode}.\tStdout: {e.stdout}\tStderr: {e.stderr}")
        globals.fatal_error = True
        output = ""

    results = []
    for sub in output.split('\n'):
        if ':' in sub:
            results.append(map(str.strip, sub.split(':', 1)))
    results = dict(results)             

    with globals.app.app_context():
        event_data = {
            "lab":globals.lab_name,
            "support_code":globals.support_code,
            "event_type":"Grading Result",
            "output":results,
            "recorded_at": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        new_event = EventTracker(data=json.dumps(event_data))
        db.session.add(new_event)
        db.session.commit()

    # ensure all grading parts have a result
    for grading_key in globals.grading_parts.keys():
        if globals.grading_parts[grading_key]['mode'] not in globals.MANUAL_MODE:
            continue
        ## IMPORTANT -- Below should only occur if phases are not configured. I believe below code provides grade for ungraded questions, where we dont want that if phase has not been reached
        if not globals.phases_enabled:
            if grading_key not in results:
                #globals.log("info",f"Grading script, {globals.manual_grading_script}, did not yield a result for grading part {grading_key}. Assigning value of 'Failed'")
                globals.log('info',f"Grading script, {globals.manual_grading_script}, did not yield a result for grading part {grading_key}. Assigning value of 'Failed'")
                results[grading_key] = "Failed"

    for k,v in results.items():
        update_db('q',k,v)

    return get_results(results)

def get_results(results: dict) -> tuple[dict,dict]:
    # for each result that is returned, check if success is in the message. 
    # If success is in the message, then read and store the token for that check
    end_results = results.copy()
    tokens = {}
    for key, value in results.items():
        if key not in globals.grading_parts.keys():
            #globals.log("debug",f"Found key in results that is not a grading part. Removing {key} from results dict. ")
            globals.log('debug',f"Found key in results that is not a grading part. Removing {key} from results dict. ")
            del end_results[key]
        if "success" in value.lower():
            tokens[key] = read_token(key)
            #update_db('q', key)
        elif check_db(key):             ### check DB to see if failed question was passed previously & update results accordingly
            results[key] = "Success"
            tokens[key] = read_token(key)
        else:
            tokens[key] = "You did not earn a token for this part"
    if globals.phases_enabled == True:
        update_db('p')
    #globals.log("info",f"Grading Results: {end_results}")
    #globals.log("info",f"Grading tokens: {tokens}")
    globals.log('info',f"Grading Results: {end_results}")
    globals.log('info',f"Grading tokens: {tokens}")
    return end_results, tokens


def post_submission(tokens: dict) -> Any:
    '''
    This method will send a POST to the grader for automatic grading.
    All POST attempts are logged.
    Method will try 4 times (sleep 1 second between each failed attempt).
    After 4 failures, the method will log an error and return. 
    '''
    token_values = tokens.values()
    
    
    # build the request headers and payload to send to the grader
    headers = {
        "accept": "text/plain",
        "Content-Type": "application/json",
        "x-api-key": f"{globals.grader_key}"
    }
    payload = f'{{"id":"{globals.lab_id}","sectionIndex":0,"questions":['
    for token in token_values:
        payload = payload + f'{{"answer":"{token}"}},'
    payload = payload[:-1] + "]}"

    # Try to POST results to the grader 4 times
    ## return immediately on success
    ## log error if still failure after 4 tries
    attempts = 0
    while attempts < 4:
        #globals.log("debug",f"Attempting {globals.grading_verb} submission to URL: {globals.grader_url}\tHeaders: {headers}\tPayload: {payload}")
        globals.log('debug',f"Attempting {globals.grading_verb} submission to URL: {globals.grader_url}\tHeaders: {headers}\tPayload: {payload}")
        attempts = attempts + 1
        try: 
            if globals.grading_verb == "POST":
                r = requests.post(globals.grader_url, data=payload, headers=headers)
                if r.status_code == 200:
                    #globals.log("debug",f"Got 200 from {globals.grader_url} after POST")
                    globals.log('debug',f"Got 200 from {globals.grader_url} after POST")
                    globals.fatal_error = False
                    return
                elif r.status_code == 405:
                    #globals.log("debug",f"Got 405 from {globals.grader_url} after POST. Changing to PUT.")
                    globals.log('debug',f"Got 405 from {globals.grader_url} after POST. Changing to PUT.")
                    globals.grading_verb = "POST"
                else:
                    #globals.log("error",f"Got {r.status_code} from {globals.grader_url} attempting to POST. Message: {r.content}")
                    globals.log('error',f"Got {r.status_code} from {globals.grader_url} attempting to POST. Message: {r.content}")
            if globals.grading_verb == "PUT":
                r = requests.put(globals.grader_url, data=payload, headers=headers)
                if r.status_code == 200:
                    #globals.log("debug",f"Got 200 from {globals.grader_url} after PUT")
                    globals.log('debug',f"Got 200 from {globals.grader_url} after PUT")
                    globals.fatal_error = False
                    return
                else:
                    #globals.log("error",f"Got {r.status_code} from {globals.grader_url} attempting to PUT. Message: {r.content}")
                    globals.log('error',f"Got {r.status_code} from {globals.grader_url} attempting to PUT. Message: {r.content}")
        except Exception as e:
            #globals.log("error",f"Got exception {e} while trying to PUT/POST data to {globals.grader_url}")
            globals.log('error',f"Got exception {e} while trying to PUT/POST data to {globals.grader_url}")
        
        sleep(1)
        #globals.log("info","Trying grader submission again after failure on previous attempt.")
        globals.log('info',"Trying grader submission again after failure on previous attempt.")

    #globals.log("error",f"All attempts to submit results to grader failed.\tURL: {globals.grader_url}\tVerb: {globals.grading_verb}\tHeaders: {headers}\tPayload: {payload}")
    globals.log('error',f"All attempts to submit results to grader failed.\tURL: {globals.grader_url}\tVerb: {globals.grading_verb}\tHeaders: {headers}\tPayload: {payload}")
    globals.fatal_error = True


def done_grading(future: Future) -> None:
    '''
    Callback function for do_grade. 
    It is meant to check to see if the results need to be PUT to the grading server
    Saves solves to the DB
    '''
    with globals.app.app_context():
        results, tokens = future.result()

        #globals.log("info",f"Server sees {globals.manual_grading_script} results as: {results}")
        globals.log('info', f"Server sees {globals.manual_grading_script} results as: {results}")
        #globals.log("info",f"Server sees tokens as: {tokens}")
        globals.log('info', f"Server sees tokens as: {tokens}")

        # save results and tokens so they can be accessed globally
        globals.manual_results
        globals.tokens['manual'] = tokens

        globals.scheduler.add_job(id="Record_Solves",func=record_solves)

        if globals.grader_post:
            post_submission(tokens)


def read_token(part_name: str) -> str:
    '''
    Function below reads tokens. 
    '''
    # get the token name for this part
    try:
        value = globals.grading_parts[part_name]['token_name']
    except KeyError:
        #globals.log("error",f"There is no match for {part_name} in the config file. Valid part names from config file are: {globals.grading_parts.keys()}")
        globals.log("error",f"There is no match for {part_name} in the config file. Valid part names from config file are: {globals.grading_parts.keys()}")
        if globals.grader_post:
            globals.fatal_error = True
        return "Unexpected error encountered. Contact an administrator."
    
    # pull tokens from guestinfo if that is the setting
    if globals.token_location == 'guestinfo':
        try: 
            output = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.{value}'", shell=True, capture_output=True)
            if 'no value' in output.stderr.decode('utf-8').lower():
                #globals.log("error",f"No value found when querying guestinfo variables for guestinfo.{value}")
                globals.log("error",f"No value found when querying guestinfo variables for guestinfo.{value}")
                if globals.grader_post:
                    globals.fatal_error = True
                return "Unexpected error encountered. Contact an administrator."
            return output.stdout.decode('utf-8').strip()
        except:
            #globals.log("error","unable to get token from guestinfo vars")
            globals.log("error","unable to get token from guestinfo vars")
            if globals.grader_post:
                globals.fatal_error = True
            return "Unexpected error encountered. Contact an administrator."
    
    # read token from file if guestinfo is not the setting
    else:
        try:
            return globals.static_tokens[part_name]
        except Exception as e:
            #globals.log("error",f"Error returning token for check {part_name}")
            globals.log("error",f"Error returning token for check {part_name}")
            if globals.grader_post:
                globals.fatal_error = True
            return "Unexpected error encountered. Contact an administrator."