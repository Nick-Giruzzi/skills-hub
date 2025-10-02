#!/usr/bin/env python3

import subprocess, io, datetime, random, string, csv
from flask import Blueprint, render_template, request, Response, current_app, redirect, url_for, abort, send_from_directory, g, make_response, jsonify
# local imports
from app.extensions import globals, db
from app.grading import do_grade 

info = Blueprint("info",__name__, template_folder=f'templates', static_folder=f'static')     # add path to templates/static if error

@info.before_request
def pass_globals():
    g.globs = globals

@info.route('/', methods=['GET'])
def home():
    if not globals.info_home_enabled:
        return redirect(url_for("main.home"))
    return render_template('starting.html')


@info.route('/services', methods=['GET'])
def services():
    if not globals.services_home_enabled:
        return redirect(url_for("main.home"))
    elif globals.services_list == None:
        return render_template('services.html',services=None)
    return render_template('services.html',services=len(globals.services_list),status=globals.services_status, num_status = len(globals.services_status))


@info.route('/bookmarks', methods=['GET'])
def bookmarks():
    return render_template('bookmarks.html')

@info.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'GET':
        return render_template('settings.html')
    else:
        data = request.form
        print(data)
        return render_template('settings.html')


@info.route('/accessibility', methods=['GET'])
def change_mode():
    globals.accessible_enabled = not globals.accessible_enabled
    return make_response(jsonify({"redirect_url":request.referrer}), 200)
    


@info.route('/report', methods=['GET'])
def report():
    try:
        # Create a string buffer to write CSV data
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Query all data from EventTracker table
        result = db.session.execute(db.text('SELECT * FROM EventTracker'))
        
        # Get column names from the cursor description
        column_names = result.keys()
        
        # Write header row
        writer.writerow(column_names)
        
        # Write all data rows
        for row in result:
            writer.writerow(row)       # Get the CSV string value

        csv_data = output.getvalue()
        output.close()
        
        # Create response with CSV data
        response = make_response(csv_data)
        
        # Set headers for file download
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'user_report.csv'
        
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        globals.log("info","User report generated")
        return response
        
    except Exception as e:
        # Log the error (you might want to use proper logging)
        globals.log("error",f"Error generating report: {str(e)}")
        
        # Return error response
        return make_response("Error generating report", 500)


@info.route("restart",methods=['GET'])
def restart():
    globals.log("info","Systemd website restart triggered.")
    subprocess.run("sudo systemctl restart skillsHub.service",shell=True)
    return make_response(jsonify({"redirect_url":'https://skills.hub/lab'}), 200)