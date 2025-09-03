#!/usr/bin/env python3

import datetime, json, sys
from typing import Any
from flask import current_app, Flask
#from app.cmi5 import cmi5_send_answered, cmi5_send_completed
from app.extensions import db, globals, record_solves_lock
from app.models import EventTracker, PhaseTracking, QuestionTracking


def initialize_db(app: Flask, conf: dict) -> None:
    # Initialize phases & add to DB
        with app.app_context():
            if conf['grading'].get('phases'):
                globals.phases_enabled = True
                #if ('phase_info' not in conf['grading'] or (len(conf['grading']['phase_info']) == 0)):
                phase_info = conf['grading'].get('phase_info', False)
                if (not phase_info) or (len(conf['grading'].get('phase_info')) == 0):
                    app.logger.error("Phase info missing, disabled, or no phases have been configured. This is required if phases are enabled.")
                    sys.exit(1)
                globals.phases = phase_info
                
                globals.phase_order = sorted(list(globals.phases.keys()),key=str.casefold)
                if 'mini_lab' in globals.phase_order:
                    tmp = globals.phase_order.pop(0)
                    globals.phase_order.append(tmp)
                try:
                    globals.current_phase = get_current_phase()
                except KeyError as e:
                    globals.current_phase = globals.phase_order[0]
                
                p_restart = False
                try:
                    p_chk = PhaseTracking.query.all()
                    if len(p_chk) == len(globals.phases):
                        p_restart = True
                except Exception as e:
                    ...
                if p_restart == False:
                    try:
                        
                        for ind,phase in enumerate(globals.phase_order):
                            new_phase = PhaseTracking(id=ind, label=phase, tasks=','.join(globals.phases[phase]), solved=False,time_solved="---")
                            db.session.add(new_phase)
                            db.session.commit()
                    except Exception as e:
                        app.logger.error(f"Exception occurred: Unable to add phase {phase} to DB. Exception:{e}.\nExiting.")
                        sys.exit(1)

            ## Here we will add all questions to DB for tracking
            globals.question_order = sorted(list(globals.grading_parts.keys()),key=str.casefold)
            q_restart = False
            try:
                q_chk = QuestionTracking.query.all()
                if len(q_chk) == len(globals.grading_parts):
                    q_restart = True
            except Exception as e:
                print(e)
            if q_restart == False:
                try:
                    for index,key in enumerate(globals.question_order,start=1):
                        new_question = QuestionTracking(id=index,label=key,task=globals.grading_parts[key]['text'],response="",q_type=globals.grading_parts[key]['mode'],solved=False,time_solved="---")
                        db.session.add(new_question)
                        db.session.commit()
                except Exception as e:
                    app.logger.error(', '.join(globals.question_order))
                    app.logger.error(f"Exception occurred: Unable to add question {key} to DB. Exception:{e}.\nExiting.")
                    sys.exit(1)


def record_solves() -> None:
    with record_solves_lock:
        with globals.scheduler.app.app_context():
            objs = {
                "Question Solved": QuestionTracking.query.all(),
                "Phase Solved":PhaseTracking.query.all()
            }
            for k,v in objs.items():
                for q in v:
                    if q.solved == True:
                        cur_data = {
                            "lab":globals.lab_name,
                            "support_code":globals.support_code,
                            "event_type":k,
                            k: q.label,
                            "solved_at": q.time_solved,
                            "recorded_at": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        new_event = EventTracker(data=json.dumps(cur_data))
                        db.session.add(new_event)
            db.session.commit()


def check_db(label: str) -> bool:
    with globals.app.app_context():
        cur_question = QuestionTracking.query.filter_by(label=label).first()
        if cur_question == None:
            globals.app.logger.error("No entry found in DB while attempting to mark question completed. Exiting")
            sys.exit(1) 
        return cur_question.solved


def update_db(type_q: str,label: str = None, val: str = None) -> Any:
    with globals.app.app_context():
        if type_q == 'q':
            try:
                cur_question = QuestionTracking.query.filter_by(label=label).first()
                if cur_question == None:
                    globals.app.logger.error("No entry found in DB while attempting to mark question completed. Exiting")
                    globals.app.logger.error("---- NOTE: IF PREVIOUSLY WORKED, ERROR LIKELY CAUSED BY EXTRA TEXT BEING PRINTED FROM GRADING SCRIPT.")
                    sys.exit(1) 
                if (val != None) and ('--' in val):
                    cur_question.response = val.split('--',1)[1]
                if ('--' not in val) and (cur_question.response == ''):
                    cur_question.response = "N/A"
                if "success" in val.lower():
                    cur_question.solved = True
                    cur_question.time_solved = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                db.session.commit()
            except Exception as e:
                globals.app.logger.error(f"Exception occurred while update DB with completed question. Exception: {e}. Exiting.")
                sys.exit(1)
            globals.app.logger.info(f"Question {cur_question.label} marked completed in DB.")
            
        else:
            for p in globals.phase_order:
                phase = PhaseTracking.query.filter_by(label=p).first()
                if phase == None:
                    globals.app.logger.error("No entry found in DB while attempting to find current phase during DB update. Exiting")
                    sys.exit(1) 
                if phase.solved == False:
                    q_list = phase.tasks.split(',')
                    num_q = len(q_list)
                    for q in q_list:
                        cur_q = QuestionTracking.query.filter_by(label=q).first()
                        if cur_q == None:
                            globals.app.logger.error("No entry found in DB while attempting to update phase DB. Exiting")
                            sys.exit(1) 
                        if cur_q.solved == True:
                            num_q -= 1
                    if num_q == 0:
                        phase.solved = True
                        phase.time_solved =datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                        db.session.commit()
                    else:
                        globals.current_phase = phase.label
                        if globals.current_phase == 'mini_lab':
                            globals.mv_challenge_files()
                        return


def get_current_phase() -> str:
    with globals.app.app_context():
        for phase in globals.phase_order:
            cur_phase = PhaseTracking.query.filter_by(label=phase).first()
            if cur_phase == None:
                globals.app.logger.warning(f"Attempted query of current phase and no record found for phase {phase}. Lab likely booting for first time.")
                raise KeyError
            if cur_phase.solved == False:
                globals.current_phase = cur_phase.label
                return cur_phase.label
        globals.lab_completed == True
        globals.lab_completion_time = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        return "completed"


def check_questions() -> None:
    with current_app.app_context():
        solved_tracker = 0
        questions = QuestionTracking.query.all()
        expected = len(questions)
        for q in questions:
            if q.solved == True:
                solved_tracker+= 1
        if solved_tracker == expected:
            globals.lab_completed == True
            globals.lab_completion_time = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            new_event = EventTracker(data=json.dumps({"lab":globals.lab_name, "support_code":globals.support_code, "event_type":"Lab Completed","recorded_at":globals.lab_completion_time}))
            db.session.add(new_event)
            db.session.commit()