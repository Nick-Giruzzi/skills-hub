#!/usr/bin/python3

import subprocess, logging, re, socket, requests, ipaddress, os, sys
from flask import Flask
from datetime import datetime
from time import sleep
from pythonping import ping
# local imports
from app.extensions import globals


def checkLocalPorts() -> str:
    '''
    Runs a subprocess to list open TCP and UDP ports
    Returns Stdout from the subprocess
    '''
    stdout = subprocess.run(f"ss -nltup", shell=True, capture_output=True).stdout.decode("UTF-8")
    return stdout


def checkLocalPortLoop(interval: int = 30) -> None:
    '''
    Checks open ports forever in a loop. Default time between checks is 30s. 
    Logs results to the same logger as the rest of the Skills Hub (in one line)
    Logs in a more readable format written to /var/log/open-ports
    '''

    globals.log("info",f"Checking local open ports every {interval} seconds")
    while True:
        date = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
        open_ports = checkLocalPorts()
        stripped = re.sub(r"\s+", " ", open_ports).replace("\n", "\\n") 
        globals.log("info",f"SERVICE/PORT LOGS: Open ports: {stripped}")

        with open("/var/log/open-ports", "a") as f:
            f.write(f"""
########
{date}
{open_ports}""")
        sleep(interval)


def isIPv4(host: str) -> bool:
    '''
    Checks the IP version of a given address
    Returns True if the address is IPv4
    Returns False if the address is IPv6
    If host is a hostname/FQDN, attempts to resolve as IPv4
    If unsuccessful, assumes address is IPv6 
    '''
    if isValidIPv4(host):
        globals.log("info",f"SERVICE/PORT LOGS: Regex matched {host} as a valid IPv4 address")
        return True
    elif isValidIPv6(host):
        globals.log("info",f"SERVICE/PORT LOGS: Regex matched {host} as a valid IPv6 address")
        return False
    # If it is not IPv4 or IPv6 here, then we have a FQDN or Hostname and attempt to resolve  
    else:
        try:
            ipAddr = socket.gethostbyname(str(host))    
            globals.log("info",f"Resolved IPv4 address is {ipAddr}")
            return True
        except socket.gaierror as e:
            errNum = e.errno
            if errNum == int(-5):
                globals.log("info",f"SERVICE/PORT LOGS: Treating {host} as an IPv6 address")
                return False
            elif errNum == int(-3):
                globals.log("error",f"SERVICE/PORT LOGS: Failed to resolve {host} - Check DNS Entry. Assuming IPv4 in the meantime")
                return True
            else:
                globals.log("error",f"SERVICE/PORT LOGS: Socket Error in isIPv4 Function - {e}. Assuming IPv4 in the meantime")
                return True
        except Exception as e:
            globals.log("error",f"SERVICE/PORT LOGS: Exception in isIPv4 Function - {e}. Assuming IPv4 in the meantime") 
            return True


def isValidIPv4(host: str) -> bool:
    '''
    A regular expression to check if a given host
    value matches the pattern of an IPv4 address. 
    Returns True if address matches the pattern
    Returns False if it does not
    ''' 
    ipv4_re = re.compile(
    (r'((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.)'
     r'{3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])'))
    return bool(ipv4_re.match(host))


def isValidIPv6(host: str) -> bool:
    '''
    A regular expression to check if a given host 
    value matches the pattern of an IPv6 address. 
    Returns True if address matches the pattern 
    Returns False if it does not
    '''
    ipv6_re = re.compile(
    ('([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|'
    '([0-9a-fA-F]{1,4}:){1,7}:|'
    '([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|'
    '([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|'
    '([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|'
    '([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|'
    '([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|'
    '[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|'
    ':((:[0-9a-fA-F]{1,4}){1,7}|:)|'
    'fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|'
    '::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|'
    r'(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|'
    '(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|'
    '([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|'
    r'(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|'
    '(2[0-4]|1{0,1}[0-9]){0,1}[0-9])'))
    return bool(ipv6_re.match(host))


def checkPing(host: str, count: int = 1) -> bool:
    '''
    Checks to see if a host is able to be reached via ping
    Returns True if the host can be pinged
    Returns False if the host cannot be pinged
    '''
    globals.log("info",f"Pinging host {host}")
    try:
        results = subprocess.run(f"ping {host} -W 1 -c {count}", shell=True, capture_output=True)
        exit_code = results.returncode
        stdout_string = " \\n ".join(line.strip() for line in str(results.stdout.decode("UTF-8")).splitlines())
        stderr_string = " \\n ".join(line.strip() for line in str(results.stderr.decode("UTF-8")).splitlines())
        globals.log("info",f"SERVICE/PORT LOGS: Exit code {exit_code} from pinging {host}")
        if exit_code == 0:
            globals.log("info",f"SERVICE/PORT LOGS: Successful ping to host {host} - {stdout_string}")
            return True
        globals.log("warning",f"SERVICE/PORT LOGS: Failed to ping host {host} - {stderr_string}")
        return False
    except Exception as e:
        globals.log("error",f"SERVICE/PORT LOGS: Failed to ping host {host}. Got exception {str(e)}")
        return False


def checkSocket(host: str, port: str|int) -> bool:
    '''
    Checks to see if a remote socket (host/port pair) is reachable
    Returns True if socket connection is successful (port is reachable)
    Returns False if socket connection failed (port is not reachable)
    '''
    globals.log("info",f"SERVICE/PORT LOGS: Attempting to connect to socket {host}:{port}")
    success = False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) if isIPv4(host) else socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((host, int(port)))
        s.shutdown(socket.SHUT_RDWR)
        globals.log("info",f"SERVICE/PORT LOGS: Successful connection to socket {host}:{port}")
        success = True 
    except socket.gaierror as e:
        globals.log("warning",f"SERVICE/PORT LOGS: Failed connection to socket {host}:{port}. Get Address Info (DNS) error prevented socket connection. Exception: {e}")
    except TimeoutError as e:
        globals.log("warning",f"SERVICE/PORT LOGS: Failed connection to socket {host}:{port}. Connection timeout.")
    except Exception as e:
        globals.log("error",f"SERVICE/PORT LOGS: Failed connection to connect to socket {host}:{port}. Exception {e}")
    finally:
        s.close()
    return success


def checkWeb(host: str, port: int|str = 80, path: str = '/') -> bool:
    '''
    Checks connection to a web URL
    Returns True if the web request returns a 200
    Returns False if the web request returns anything but a 200
    If host is an IP address, IP version is checked as IPv6 requires [ ] brackets 
    '''
    fqdn = re.compile(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}\.?$)')
    if fqdn.search(host): # Check if host is FQDN. If True, IP version does not matter 
        url = f"http://{host}:{port}{path}"
        globals.log("info","SERVICE/PORT LOGS: checkWeb is using FQDN")
    elif isIPv4(host) == True: 
        url = f"http://{host}:{port}{path}"
        globals.log("info","SERVICE/PORT LOGS: checkWeb is using IPv4")
    else:
        url = f"http://[{host}]:{port}{path}" 
        globals.log("info","SERVICE/PORT LOGS: checkWeb is using IPv6")
    globals.log("info",f"SERVICE/PORT LOGS: Attempting to reach {url}")
    try:
        result = requests.get(url=url)
        globals.log("info",f"SERVICE/PORT LOGS: Web request returned {result.status_code}")
        globals.log("debug",f"SERVICE/PORT LOGS: Web request returned {result.status_code}: {result.content}")
        return result.status_code == 200
    except requests.exceptions.Timeout as e:
        globals.log("warning",f"SERVICE/PORT LOGS: Failed connection to {url}. Connection Timeout Exception: {e}")
    except requests.exceptions.InvalidURL as e:
        globals.log("warning",f"SERVICE/PORT LOGS: Failed connection to {url}. Invalid URL Exception: {e}")
    except requests.exceptions.ConnectionError as e:
        globals.log("warning",f"SERVICE/PORT LOGS: Failed connection to {url}. Connection Error: {e}")
    except Exception as e:
        globals.log("error",f"SERVICE/PORT LOGS: Failed connection to {url}. Got Exception: {e}")
    return False


def checkService(service:dict) -> bool:
    '''
    Checks to see if the service is available once. 
    Returns True is the service is reachable. 
    Returns False is the service is unreachable. 
    '''

    globals.log("info",f"SERVICE/PORT LOGS: Checking availability of service: {service}")
    reachable = False
    service_type = service['type']
    if service_type == 'ping':
        reachable = checkPing(service['host'])
    elif service_type =='socket':
        reachable = checkSocket(service['host'],service['port'])
    elif service_type == 'web':
        reachable = checkWeb(service['host'], service['port'], service['path'])
    
    if reachable:
        globals.log("info",f"SERVICE/PORT LOGS: Service available: {service}")
        return True
    else:
        globals.log("error",f"SERVICE/PORT LOGS: Service unavailable: {service}")
        return False


def waitForService(service:dict, interval: int = 2, max_attempts: int = 0):
    '''
    Checks the service in a loop until it becomes available or max_attempts is reached. 
    Returns once the service is available or max_attempts is reached.
    Default time between checks is 2s.
    '''

    service_available = False
    attempts = 0
    while True:
        attempts += 1
        globals.log("info",f"SERVICE/PORT LOGS: Waiting for service to become available (attempt number {attempts}): {service}")
        service_available = checkService(service)
        if service_available:
            return service_available
        if max_attempts and attempts == max_attempts:
            globals.log("error",f"SERVICE/PORT LOGS: Service unavailable after max attempts ({attempts}): {service}")
            return False
        sleep(interval)


def checkServiceLoop(service:dict, interval: int = 30, max_checks: int = 0) -> bool:
    '''
    Checks the availability of the service forever in a loop (or until max_checks is reached). Default time between checks is 30s. 
    '''

    globals.log("info",f"SERVICE/PORT LOGS: Checking service {service} every {interval} seconds")
    attempts = 0
    while True:
        attempts += 1
        globals.log("info",f"SERVICE/PORT LOGS: Service check number {attempts} for {service}")
        checkService(service)
        if max_checks and attempts == max_checks:
            globals.log("warning",f"SERVICE/PORT LOGS: Reached the maximum number of service checks ({max_checks}).. Will no longer check on service {service}.")
            return True
        sleep(interval)


def get_logs(service: dict) -> None:
    log_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    #host_info = {"host":service['host'],"service":service['service']}
    while True:
        sleep(10)
        # `er` variable is intended to track if a service is 'fve' and then when same logs are grabbed they are logged with `.error` rather than `.info` to make for easier tracking.
        er = False
        ## below SSH cmd uses `is-active` option with `systemctl` where the response should be either `actor `inactive` and then Log info accordingly.
        try:
            get_status_cmd = f"sshpass -p {service['password']} ssh -o StrictHostKeyChecking=no {service['user']}@{service['host']} 'systemctl is-active {service['service']}'"
            status_response = subprocess.run(get_status_cmd, shell=True,capture_output=True, timeout=10)
        except subprocess.TimeoutExpired:
            globals.log("warning",f"SERVICE/PORT LOGS: request to host timed out.")
            globals.services_status[service['service']] = [service['host'],f"request to host timed out. Trying again shortly"]
            continue
        except Exception as e:
            globals.log("error",f"SERVICE/PORT LOGS: Exception has occurred when attempting to retrieve service status.")
            globals.log("error",f"SERVICE/PORT LOGS: Exception: {e}")
            globals.services_status[service['service']] = [service['host'],f"Exception has occurred when attempting to retrieve service status."]
            continue
        if status_response.stdout.decode('utf-8') == '':
            globals.log("error",f"SERVICE/PORT LOGS: Error has occurred when attempting to get service status.")
            globals.log("error",f"SERVICE/PORT LOGS: {status_response.stderr.decode('utf-8')}")
            globals.services_status[service['service']] = [service['host'],f"Error has occurred when attempting to get service status."]
            continue
        if status_response.stdout.decode('utf-8').strip('\n') == 'failed':
            er = "SERVICE FAILED: "
            globals.log("error",f"SERVICE/PORT LOGS: {er} {service['service']} is in failed state.")
            globals.services_status[service['service']] = [service['host'],f"Service is in failed state."]
        elif status_response.stdout.decode('utf-8').strip('\n') == 'inactive':
            er = "SERVICE INACTIVE: "
            globals.log("error",f"SERVICE/PORT LOGS: {er} {service['service']} is in inactive state.")
            globals.services_status[service['service']] = [service['host'],f"Service is in inactive state."]
        else:
            globals.services_status[service['service']] = [service['host'],f"Service is in active state."]
        ## grab logs
        try:
            get_log_cmd = f"sshpass -p {service['password']} ssh -o StrictHostKeyChecking=no {service['user']}@{service['host']} 'journalctl --since \"{log_time}\" -u {service['service']}'"
            log_response = subprocess.run(get_log_cmd, shell=True,capture_output=True,timeout=10)
            cur_logs = log_response.stdout.decode('utf-8')
        except subprocess.TimeoutExpired:
            globals.log("error",f"SERVICE/PORT LOGS: SSH connection to host timed out.")
            continue
        except Exception as e:
            globals.log("error",f"SERVICE/PORT LOGS: Exception has occurred when attempting to retrieve logs.")
            globals.log("error",f"SERVICE/PORT LOGS: Exception: {e}")
            continue
        if log_response.stdout.decode('utf-8') == '':
            globals.log("error",f"SERVICE/PORT LOGS: Error has occurred when attempting to collect logs.")
            globals.log("error",f"SERVICE/PORT LOGS: Error: {log_response.stderr.decode('utf-8')}")
            continue
        if "No entries" in cur_logs:
            if er != False:
                globals.log("error",f"SERVICE/PORT LOGS: {er} No new logs fe.")
            else:
                globals.log("info",f"SERVICE/PORT LOGS: No new logs found at this time.")
            continue
        output = cur_logs.split("\n")
        output.remove("")
        for line in output:
            if er == False:
                globals.log("info",f"SERVICE/PORT LOGS: {line}")
            else:
                globals.log("error","SERVICE/PORT LOGS: "+ er + line)
        log_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

