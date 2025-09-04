# **Skills Hub**

This is the **Skills Hub** - designed to support execution of Training Labs.

The idea is to have a centralized server that developers can use for startup/grading scripts and users can go to for grading and viewing results inside of labs.

## Using the Skills Hub

At startup, the Skills Hub will read the config file [config.yml](./src/config.yml) and apply the settings configured. Then, the server will run startup scripts, host files for download, supply ways for users to ask for grading, and more!

Edit the [config.yml](./src/config.yml) file to configure the service to behave how you'd like. Check the [supplemental README.md](./src/README.md) for insight on the configuration options available.

### Command Line Options

`--log-level [level]` - Use this option to specify the level at which you want to log. These levels are from the standard [Python logging levels](https://docs.python.org/3/library/logging.html#logging-levels). The default level is `INFO`. Example: `--debug ERROR` will show logs at the error level.

`--debug` - Enable debug logging. This option overrides the log level specified via `--log-level` to enable `DEBUG` level logs.

### Using HTTPS

To run the Skills Hub with HTTPS, your TLS certificate and key should be located in the [ssl directory](./src/app/ssl/). Provide the filename of the TLS certificate and private key in the variables `tls_cert` and `tls_key` in the [config.yml](./src/config.yml) file.

### Running the Skills Hub

In some cases, it makes sense to run the Skills Hub code as a `systemd` service at boot. An example systemd unit is [here](./etc/systemd/system/skillsHub.service). If you're using this type of configuration, you will need to restart the systemd service before changes to the config file are read by the service. Use the following command to restart the service after making configuration changes:

```bash
sudo systemctl restart skillsHub.service
```

To ensure the service started correctly and without errors, run:

```bash
sudo systemctl status skillsHub.service
```

## Logs

Everything the Skills Hub does is logged to Systemd and also to the [logs folder](./src/logs/). 

Log files will automatically be generated when the server is running and multiple files will be created. The log file `app.log` will cotain all logs. Additional log files will be created where specific log levels will only be stored in their associated filename. (`warning` logs will be stored in `warning.log`, `error` logs will be stored in `error.log`, etc.)

If you use a systemd service to start the server. To view the Skills Hub logs via the system journal:

```bash
sudo journalctl -u skillsHub.service
```

The above command will put you in a `more`-style view of the systemd logs for the Skills Hub service. To jump the bottom of the logs (most recent logs) use:

```bash
sudo journalctl -e -u skillsHub.service
```

Additionally, if you wish to follow the logs live as the server is running, the following command will do this

```bash
sudo journalctl -f -u skillsHub.service
```

## Required Environment Variables

In order to operate as intended, the Skills Hub requires 2 environment variables.

1. `code` - This environment variable should be a string that contains a "lab code" or a "slug" that identifies this lab. Example: `c00`. If this environment variable is not set, the Skills Hub will always assume that it is running in a workspace.
2. `variant` - This environment variable should be a string that contains which TopoMojo variant is deployed. Example: `2`. If this environment variable is not set, the Skills Hub will set the variant to a default of `-1`

## Monitoring Required Services

The Skills Hub can be used to monitor services that a lab requires. Examples include: a website that needs to remain operational, a Docker container that should always have an open port, a host that should remain reachable, etc. To configure the Skills Hub to monitor required services, use the `required_services` section of the config file.

On a periodic basis (every 30 seconds by default), the Skills Hub will determine if your required services are reachable. It does this by using the `ping` command, making a TCP socket connection, or by visiting a website. These options and their additional required settings are documented in the config file.

Required services can also block startup scripts from executing. This is useful if your startup script requires that a host is up or a service is available. For example, if your startup script needs to use SSH to configure a host, it would be helpful to ensure that ssh is reachable on that host before running the startup script by configuring a `socket` required service on port `22` for the desired host.

## Service Logger

The Skills Hub comes with an additional `service_logger` that can be used to collect systemd service logs from other VMs in the lab environment. This additional feature is detailed more [here](./src/README.md)

## Startup Configuration

You can use the Skills Hub as a central location for configuring all the machines in your environment.

1. Write a startup script (or more than 1) that will remotely configure each machine in your environment to the lab's specifications. Place all startup scripts in the [custom_scripts](./src/custom_scripts) directory and ensure they are executable (`chmod +x <your_script>`)
2. You can use ssh, psexec, powershell remoting, or any other way to remotely manage each machine in your environment.
3. Your startup script should log all important actions/results to standard out.
4. You can optionally use the `required_services` section to block startup scripts from running until required services are available. This is useful in cases where you need SSH to be available on a target machine for your startup script to function as intended.

Example startup scripts are [here](./src/custom_scripts/).

## Grading

The developer (you) can write a grading script that the server executes under a few circumstances:

- When a button on the website is pressed.
- When a file is uploaded and submitted.
- When the user enters text into the website.

The Skills Hub will read tokens from VMware guestinfo variables or from statically set tokens configured in the [config.yml](./src/config.yml) file. 

### Submission

The Skills Hub can display tokens to users for copy/paste submissions on their own.

The Skills Hub can also POST values to the [Gameboard application](https://github.com/cmu-sei/gameboard) and submit answers on a user's behalf.

The developer only needs to write a grading script that will perform any checks needed to ensure the successful completion of the lab.

### Types of Grading

There are several types of grading that are supported by this server.

- User Presses a Button
  - In this style of grading, the user is expected to press a button to initiate grading. The grading script will execute without command line arguments
- User Enters Text
  - In this style of grading, the user is expected to submit text which answers questions. The grading script will execute with each text submission passed as a command line argument (use argv to get these)
- User selects option (Multiple Choice)
  - In this style of grading, the user is expected to submit an option to answer the question. The grading script will read in the option chose (A, B, C, etc.) and return pass/fail.
- User upload a file for analysis
  - In this style of grading, the user is expected to upload a file and submit it to be analyzed. Files are stored in the [uploaded files folder](./src/uploaded_files) where the grading script will read in the filename as an argument and then perform whatever checks needed on it.
- Automatic/Scheduled Grading (cron job)
  - In this style of grading, the user is not expected to take any action for grading to occur. Grading happens on an interval and/or at a scheduled time
  - Additional config settings maybe be required for this style to operate to your lab's specs.

More information about using each grading type is provided in the [supplemental readme](./src/README.md).

_Caution: Running and/or analyzing files/code uploaded by the user can be dangerous. The developer should take necessary security precautions to ensure user-uploaded code/files do not have unintended consequences._

### Grading Scripts

The developer will need to write their own grading script to perform whatever checks are required as part of the grading process. The grading script can be written in any language and will be executed by the grading server automatically when the user presses a button to initiate grading, at a certain time, or other conditions.

More information on the grading process and its development can be [found here](./src/custom_scripts/README.md)

### Submitting Grading Results

This server supports 2 methods for grading results.

- Display a token
  - This is the default method. In this method, a token will be displayed on the website. The user will have to visit the website, copy the token string out of the VM, then paste it to the Gameboard to submit for credit
- Grader POST
  - This method is used when the developer wants to submit answers to the grader (e.g., Gameboard) on the user's behalf. Using this submission method along with automatic grading, will result in user's being awarded points automatically -- no action is needed by the user after the grading check(s) pass.
  - Additional settings required for this are described in the config file comments.

## Hosting Files

This server can be used to host any files you need to share with the competitor inside the lab environment. To host files, place the files in the [hosted_files](./src/hosted_files/) directory. This will allow competitors to download the files from inside their lab environment.

