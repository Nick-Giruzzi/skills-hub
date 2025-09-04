# Skills Hub Server Grading README
> This document will explain how grading works in the Skills Hub Server.<br>

## Grading

It was referenced in the `config_README.md` file but the Skills Hub Server has been updated to allow for two grading scripts to be entered into its configuration. 
- One grading script to be used for all questions that are defined with the `cron` grading type 
- One grading script then to be used for all questions that are a `manual` grading type (text, button).

This is due to the fact that the grading mode is now configured on a per-question basis, and if the developer wants to be able to grade both types then this allows for it. They were separated as well due to the nature of each grading type as we don't want to run the same grading script every time grading occurs whether it be cron or a user submission. So this allows for separation of them.

The grading script should only print out a string for each task/token that follows the format: `key : status -- optional msg`, where the status is either `Failure` or `Success`, followed by an optional message starting with two hyphens (`--`) if the developer wants to provide feedback to the user.
<br><br>

The `key` should be the part of the you are grading.  

The `status` should be the status of the grading check, `Success` or `Failure`

The ` -- optional msg` should contain any feedback the developer wants to provide feedback to the user.

For all grading response, feedback can be provided to the user by appending the string ` -- ` to the result (success or failure). The characters ` -- ` indicate a comment/feedback and so any message following it will be provided to the user.

For example:

    If the grading for `GradingCheck1` failed and I wanted to return the feedback message `Connection timed out` for that grading check, I would use the following code:

    ```python
    results['GradingCheck1'] = "Failure -- Connection timed out
    ```

Examples can be found [in this file](../custom_scripts/manualGradingExample.py)

Your grading script should output one (1)  `key:status` pair per line. Each new line (and therefore each `key:value` pair) will be treated as different parts of a multi-part lab.

Feel free to include as much or as little detail in the message as you'd like the competitor to see. The only requirement is: The word 'success' must be present in the `status` field of any part you want to display a token for.

The Grading Server will use the `keys` output by the grading script to display output to the user.

The Grading Server will also display the `values` output by the grading script to the user. This can help the user figure out why they failed a particular part if useful messages are provided. **Do not include any text in the values that you do not want users to see.**

Your grading script should start with a 'shebang' line which gives the absolute path to the interpreter that should be used to run the program.

- Bash scripts should start with `#!/bin/bash`
- Python scripts should start with `#!/usr/bin/python3`
- PowerShell scripts should start with `#!/snap/bin/pwsh`

Your grading script must have the executable bit set. Ensure you run the following command: `chmod +x <your_script>`.

Example grading scripts are [here](./src/custom_scripts/).

## Additional Functionality/Notes

### `manualGradingScript.py` runSSHCommand function

I've added the function `runSSHCommand` at the top of the `manualGradingExample.py` script. This function can be used to execute SSH commands to a remote host.

It requires the following arguments to be passed to it:
- The `username` you want to log into on remote host.
- The `password` for that user.
- The `hostname` of remote host you want to connect to (IP address or DNS name work).
- A **list** variable that contains all the commands you want to execute on the remote host.

This function will always return a **dictionary** data type, regardless if the connection/commands pass or fail. So make sure to check the output after calling the function. 

If `error` is present as a key in the functions output, that means one of the following has occurred:
1. One of the required arguments was missing in the function call. 
2. The command(s) were not passed in as a list data type.
3. The SSH connection failed and couldn't be completed.

If the connection succeeds, the function will then loop through running all of the passed commands and storing their output into a dictionary. Once all commands have been ran, it will close the connection and return the results. 

The results dictionary will follow this structure:

```json
{
    "cmd1": {
            "command":"Command executed",
            "stdout": "**output returned from running command**",
            "stderr": "**errors/exceptions messages returned from running the command**"
        }
}
```

Some bash commands are weird with how they return data, some commands return it through `stdout` while others return some information from `stderr`, so both are saved.

It is configured to return a dictionary object.

### execute_in_docker
_NOTE: This function has not been fully tested and may contain bugs_

This function can be used to execute an uploaded script in an isolated docker container. Its default configuration is to run a container with the python:latest image.

The function has 4 accepted arguments, with 2 being required. They are:
    1. (**Required**) `file_name` : Name of uploaded file to be executed in container, should be passed from Server to grading script.
    2. (**Required**) `docker_image`: Name of image to be used when creating + running container. (ex: `python:latest`, `rust:latest`, etc.)
    3. `libs`: Boolean value that determines if libraries are to be imported and used in container. Default value is `False`.
    4. `lib_folder`: Individual folder ONLY, NOT absolute path. This is only required if `libs` is set to `True`. (ex: `python`, `rust`).

If you are intending to use this function, There are a few edits that are required from the dev to make this function work correctly, they are:
    - Downloaded and/or configured docker image that is needed to run script (Python, Rust, C, etc.)
        - `python:latest` and `rust:latest` have already been downloaded to host.
    - Ensure `docker_command` variable contains correct format and command to execute script.
    - If extra additional libs are expected/required, do the following: 
        - Download all required libs locally and save to the  to the associated folder inside the `docker_libs` folder.
            - Example: `python` libs would be downloaded to the `/home/user/skillsHub/docker_libs/python` folder

It is configured to return a dictionary object.

### Manual type (text, button, multiple choice, upload)

If your lab doesn't utilize question sets and/or `phases` and have `phases` disabled in `config.yml`, then the grading script can be created like normal without any special formatting.

If you do have question sets and/or `phases` in your lab and have `phases` enabled, you will need to format the grading script in a specific way.

for this explanation, we will assume that the Skills Hub `config.yml` is configured with the following settings (which is also the default phase configuration). For reference, here is what it looks like in the `config.yml` file:

```yml
phases: true
phase_info:
    phase1: ["GradingCheck1", "GradingCheck2"]
    phase2: ["GradingCheck3"]
    phase3: ["GradingCheck4"]
```
<br><br>

#### Understanding Skills Hub Functionality 

In this example, the server is configured with three phases, where questions 1 and 2 are in phase 1, question 3 is in phase 2, and question 4 is in phase 3. 

When phases are configured, the web server will only present the questions on the `tasks` page that are associated with the phase the user is currently on. For example: If the user is on phase 1, only questions 1 and 2 will be presented. Once these questions are solved, it will present the questions for the next phase the next time you visit the `tasks` page.

**IMPORTANT**: In order to specify what phase is currently being graded, the server will pass the name of the current phase being graded to the grading script as an argument. This argument will always be the **FINAL** argument in the argument list. It is created this way because other data may be passed to the grading script based on the question type being graded (`text` questions will pass submitted strings to the grading script), and so appending the phase as the last argument is efficient and allows for easier consistency. 
<br><br>

#### Grading Script Requirements

Due to the server passing the current phase to the grading script, the grading script must have a method of reading in the current phase passed by the server and then grading the corresponding questions based on that data.

Additionally, as the lab progresses there may be different question types that are being graded and so there also needs to be a method of checking the arguments being passed to the grading script and having it react accordingly.

To support this, the Skills Hub Server will always pass any/all submission data that was inputted from the user as a `JSON string`. This string will always be the first argument passed to the grading script (Which is also the 2nd argument when using `sys.argv` in Python)

To help with creating the grading script, I have detailed the method I used to read in the data and have the grading script act correctly based on the data. Please view the data below to view how I accomplished this:

- I created a function for each phase in the grading script, where the name of the function needs to match the phase currently being graded.
- There is no limit to the number of phases you can implement, you just need to ensure that each phase configured in `config.yml` corresponds to a function in your grading script.
- Remember that if data is passed to your grading script, it will be in `JSON` format.
- The code snippet below is the `main` function pulled from `manualGradingExample.py` and so the information below is based off that entire file.
    - The code below contains code that covers all possible configurations that a lab could have when grading (Phases enabled & grade user submission, phases enabled but no user submission, phases disabled but grade user submission, and phases disabled and no user submissions)
    - The `manualGradingExample.py` grading script has a function labeled `phase1` and within it is code that will grade the questions that make up `phase1`(which should be configured in `config.yml`) -- In this scenario is the questions associated with `GradingCheck1` and `GradingCheck2`.
    - Next, it should have another function labeled as `phase2` containing the code to grade the questions that make up `phase2`
    - and lastly the function `phase3` containing the code to grade the question associated with the label `GradingCheck4`.
    - I create a `phases` list object that contains the names of all the phases that need to be graded (Which needs to match what is configured in `config.yml`)
    - I check the passed arguments to see if a phase has been passed by comparing the phase passed to the list of phases.
    - If valid phase has been passed, run its associated function and pass any arguments to it if they are present.
    - If no phase is passed, then the grading script will execute all the functions in the script effectively grading everything in the lab.


```python
if __name__ == '__main__':
    # phases variable should contain list of all phases implemented in the lab & has a function declared above
    phases = ['phase1','phase2','phase3']
    args = sys.argv[1:]
    if len(args) > 0:
        passed_phase = args[-1].strip().lower()
        if passed_phase in phases:
            ## This code will execute IF phases is enabled & current phase was passed to script.
            args.pop(-1)
            if len(args) != 0:
                ## This code executes if user submitted answer & it was passed to grading script. 
                submissions = json.loads(args[0])
                res = globals()[passed_phase](submissions)
            else:
                # This code executes if no submission made from user
                res = globals()[passed_phase]()
                
            for key,val in res.items():
                print(key, ' : ', val)
        else:
            # This code will execute if phases are disabled BUT there is still a submission from the user. For this example, we will execute all the functions above. 
            submissions = json.loads(args[0])
            res = dict()
            for phase in phases:    
                res.update(globals()[phase](submissions))
                
            for key,val in res.items():
                print(key, ' : ', val)
    else:
        ## This code will execute if no args were passed, which means that phases are disabled & no submissions occur from user
        res = dict()
        for phase in phases:
            res.update(globals()[phase]())

        for key,val in res.items():
            print(key, ' : ', val)
```
<br><br>

## Grading Feedback/Response




## **NOTE**

The Grading Server will also display the `values` output by the grading script to the user. This can help the user figure out why they failed a particular part if useful messages are provided. **Do not include any text in the values that you do not want users to see.**
