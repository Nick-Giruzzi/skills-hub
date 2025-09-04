#!/usr/bin/env python3

import subprocess, os, yaml, socket, sys
from flask import Flask
from flask_apscheduler import APScheduler
from datetime import timedelta, time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List, Dict, Set, Union

class Globals():
    def __init__(self) -> None:
        # Static defaults (non-configurable)
        self.VALID_CONFIG_MODES: List[str] = ['button', 'cron', 'text', 'text_single', 'mc', 'upload']
        self.MANUAL_MODE: List[str] = ['button', 'text', 'text_single', 'mc', 'upload']
        self.VALID_TOKEN_LOCATIONS: List[str] = ['guestinfo', 'static']
        self.VALID_SUBMISSION_METHODS: List[str] = ['display', 'grader_post']
        self.VALID_SERVICE_TYPES: List[str] = ['ping', 'socket', 'web']

        # Directories
        self.basedir: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.custom_script_dir: str = f"{self.basedir}/custom_scripts"
        self.hosted_file_directory: str = f"{self.basedir}/hosted_files"
        if not os.path.exists(self.hosted_file_directory):
            os.mkdir(self.hosted_file_directory)
        self.uploaded_file_directory: str = f"{self.basedir}/uploaded_files"
        if not os.path.exists(self.uploaded_file_directory):
            os.mkdir(self.uploaded_file_directory)
        self.yaml_path: str = f"{self.basedir}/config.yml"
        self.ssl_dir: str = f"{self.basedir}/app/ssl"
        self.challenge_files: str = f"{self.basedir}/challenge_files"
        if not os.path.exists(self.challenge_files):
            os.mkdir(self.challenge_files)
        self.logs_dir: str = f"{self.basedir}/logs"
        if not os.path.exists(self.logs_dir):
            os.mkdir(self.logs_dir)

        # Initialize overridable vars
        self.app: Flask = None
        self.app_host: str = "0.0.0.0"
        self.app_port: int = 8888
        self.app_cert: Optional[str] = None
        self.app_key: Optional[str] = None
        self.lab_name: str = ""
        self.port_checker: bool = False
        self.grading_enabled: bool = False
        self.hosted_files_enabled: bool = False
        self.info_home_enabled: bool = False
        self.services_home_enabled: bool = False
        self.accessible_enabled: bool = False

        # Configuration globals
        self.conf: dict = {}
        self.lab_id: str = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.isolationTag'", shell=True, capture_output=True).stdout.decode('utf-8').strip().replace("-", "")
        self.support_code: str = self.lab_id[:8]
        self.variant_index: int = self._init_variant_index()
        self.lab_code: str = self._init_lab_code()
        self.in_workspace: bool = "workspace" in self.lab_code

        self.startup_enabled:bool = False
        self.startup_workspace: bool = False
        self.startup_scripts: List[str] = []
        self.required_services: List[dict] = []
        self.blocking_services: List[dict] = []
        self.blocking_threadpool = ThreadPoolExecutor(thread_name_prefix="BlockingServices")

        self.grading_mode: List[str] = []
        self.manual_grading_script: Optional[str] = None
        self.cron_grading_script: Optional[str] = None
        self.grading_rateLimit: timedelta = timedelta(seconds=0)
        self.grading_parts: Optional[dict] = None
        self.question_order: List[str] = []
        self.token_location: str = ""
        self.submission_method: str = "display"
        self.grader_post: bool = False
        self.services_list: Optional[List[dict]] = None
        self.services_status: Dict[str, List[str]] = {}
        self.q_modes: Set[str] = set()
        self.lab_completed: bool = False
        self.lab_completion_time: str = ""
        self.grader_url: Optional[str] = ""
        self.grader_key: Optional[str] = ""

        self.bookmarks: Optional[dict] = None
        self.filelist: list = os.listdir(f"{self.basedir}/uploaded_files")

        # Cron
        self.cron_limit: Optional[int] = None
        self.cron_interval: Optional[int] = None
        self.cron_delay: Optional[int] = None
        self.cron_at: Optional[str] = None
        self.cron_type: Optional[str] = None

        # Runtime values
        now = time().strftime("%m/%d/%Y %H:%M:%S")
        self.manual_submit_time: str = now
        self.cron_submit_time: str = now
        self.manual_results: Optional[dict] = None
        self.cron_results: Optional[dict] = None
        self.tokens: Dict[str, Dict] = { "manual": {}, "cron": {} }
        self.static_tokens: Optional[dict] = None
        self.grading_verb: str = "POST"

        # Phases
        self.phases_enabled: bool = False
        self.phases: Optional[dict] = None
        self.phase_order: List[str] = []
        self.current_phase: Optional[str] = None

        # Server state
        self.fatal_error: bool = False
        self.task: Optional[str] = None
        self.server_ready: bool = False
        self.executor = None
        self.scheduler: APScheduler = APScheduler()

    def __repr__(self) -> str:
        """
        Return a string representation of the object.

        Returns:
            str: String with each attribute/value listed on a new line
        """

        attrs = vars(self)
        lines = [f"{k}={v!r}" for k, v in sorted(attrs.items())]
        return f"<Globals:\n  " + "\n  ".join(lines) + "\n>"


    def _init_variant_index(self) -> int:
        """
        Return the variant index if it exists in env var. Default to -1.

        Returns:
            int: The variant index
        """
        variant = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.variant'", shell=True, capture_output=True).stdout.decode('utf-8').strip()
        #variant = get_clean_env('CS_VARIANT')
        if variant and "##" not in variant and len(variant) <= 2:
            return int(variant)
        return -1


    def _init_lab_code(self) -> str:
        """
        Return the lab code if it exists in env var. Default to 'workspace'.

        Returns:
            str: The lab Code. Default is 'workspace'.
        """

        #code = get_clean_env('CS_CODE', '')
        code = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.code'", shell=True, capture_output=True).stdout.decode('utf-8').strip()
        return "workspace" if not code or "##" in code else code


    def resolve(self, conf: dict, default: str = '') -> str:
        """
        Resolves a configuration value.
        Read from env var first. Then fallback to the configuration dictionary.
        If value does not exist in env var or config, use the provided default.

        Args:
            key (str): Config to lookup
            conf (dict): Configuration dictionary value.
            default (str, optional): Default value. Defaults to ''.

        Returns:
            str: The configuration value.
        """
        return conf or default


    def resolve_bool(self, conf: Union[dict, bool], default: bool = False) -> bool:
        """
        Resolves a configuration boolean value.
        Read from env var first. Then fallback to the configuration dictionary.
        If value does not exist in env var or config, use the provided default.

        Args:
            key (str): Config to lookup
            conf (dict): Configuration dictionary value.
            default (str, optional): Default value. Defaults to ''.

        Returns:
            bool: The configuration value.
        """
        if isinstance(conf, dict):
            return conf.get('enabled', default)
        return conf or default


    def resolve_int(self, conf_val, default: int) -> int:
        """
        Resolves a configuration int value.
        Read from env var first. Then fallback to the configuration dictionary.
        If value does not exist in env var or config, use the provided default.

        Args:
            key (str): Config to lookup
            conf (dict): Configuration dictionary value.
            default (str, optional): Default value. Defaults to ''.

        Returns:
            int: The configuration value.
        """

        if isinstance(conf_val, int):
            return conf_val
        return default

    def resolve_ip(self, conf_val, default: str) -> str:
        """
        Resolves a configuration IP address value by ensuring it is a valid IP address.
        Read from env var first. Then fallback to the configuration dictionary.
        If value does not exist in env var or config, use the provided default.

        Args:
            key (str): Config to lookup
            conf (dict): Configuration dictionary value.
            default (str, optional): Default value. Defaults to ''.

        Returns:
            bool: The configuration value.
        """
        try:
            socket.gethostbyname(conf_val)
            return conf_val
        except (socket.gaierror, TypeError):
            return default


    def resolve_port(self, conf_val, default: int) -> int:
        """
        Resolves a configuration TCP port value by ensuring it is a valid TCP port.
        Read from env var first. Then fallback to the configuration dictionary.
        If value does not exist in env var or config, use the provided default.

        Args:
            key (str): Config to lookup
            conf (dict): Configuration dictionary value.
            default (str, optional): Default value. Defaults to ''.

        Returns:
            bool: The configuration value.
        """

        if isinstance(conf_val, int) and 1 <= conf_val <= 65535:
            return conf_val
        return default


    def load_config(self, conf: dict, app: Flask):
        app.logger.info("Loading application config")
        self.conf = conf
        self.app = app
        self.app_host = self.resolve_ip(conf.get('app', {}).get('host'), '0.0.0.0')
        self.app_port = self.resolve_port(conf.get('app', {}).get('port'), 8888)
        self.app_cert = conf.get('app').get('tls_cert', '')
        self.app_key = conf.get('app').get('tls_key', '')
        if (self.app_cert == '') or (self.app_key == ''):
            app.logger.error("One or both required files to run over HTTPS not configured")
            exit(1)
        elif (not os.path.isfile(os.path.join(self.ssl_dir, self.app_cert))) or (not os.path.isfile(os.path.join(self.ssl_dir, self.app_key))):
            app.logger.error("One or both of the configured TLS files do not exist.")
            exit(1)
        self.startup_scripts = conf.get('startup', {}).get('scripts',[])
        self.startup_enabled = conf.get('startup', {}).get('enabled',False)
        self.startup_workspace = conf.get('startup', {}).get('runInWorkspace',False)
        self.lab_name = self.resolve(conf.get('lab_name'), "")
        self.port_checker = self.resolve_bool(conf.get('port_checker'), False)
        self.grading_enabled = self.resolve_bool(conf.get('grading').get('enabled'), False)
        if (self.grading_enabled) and (conf.get('grading').get('manual_grading', False)):
            self.manual_grading_script = self.resolve(conf.get('grading').get('manual_grading_script'))
            self.grading_mode.append('manual')
        if (self.grading_enabled) and (conf.get('grading').get('cron_grading', False)):
            self.cron_grading_script = self.resolve(conf.get('grading').get('cron_grading_script'))
            self.grading('cron')
        if self.grading_enabled:
            token_loc = conf.get('grading').get('token_location', '')
            if token_loc in self.VALID_TOKEN_LOCATIONS:
                app.logger.info(f"Token location set as: {token_loc}")
                self.token_location = token_loc
                if self.token_location == 'static':
                    self.static_tokens = conf.get('grading').get('tokens')
            else:
                app.logger.warning(f"Unknown token location configured in config.yml. Defaulting to'guestinfo'")
                self.token_location = 'guestinfo'
        self.hosted_files_enabled = self.resolve_bool(conf.get('hosted_files').get('enabled'), False)
        self.info_home_enabled = self.resolve_bool(conf.get('info_and_services'), False)
        self.services_home_enabled = self.resolve_bool(conf.get('info_and_services'), False)
        if self.resolve_bool(conf.get('info_and_services').get('bookmarks_enabled'),False):
            self.bookmarks = conf.get('info_and_services').get('bookmarks')
        self.grading_parts = conf['grading']['parts']
        if 'manual' in self.grading_mode:
            try:
                if not os.access(os.path.join(self.custom_script_dir,self.manual_grading_script), os.X_OK):
                    app.logger.error(f"Manual grading script {self.manual_grading_script} is not executable.")
                    exit(1)
            except Exception as e:
                app.logger.error(f"Got exception {e} while checking if manual grading script {self.manual_grading_script} is executable.")
                exit(1)
        if 'cron' in self.grading_mode:
            try:
                if not os.access(os.path.join(self.custom_script_dir,self.cron_grading_script), os.X_OK):
                    app.logger.error(f"Cron grading script {self.cron_grading_script} is not executable.")
                    exit(1)
            except Exception as e:
                app.logger.error(f"Got exception {e} while checking if cron grading script {self.cron_grading_script} is executable.")
                exit(1)
        self.required_services = conf.get('required_services', [])
        if (self.required_services == []) or (self.required_services == None):
            ...
            app.logger.info("No required services configured.")
        else:
            for service in self.required_services:
                # ensure host is defined in required services
                if 'host' not in service:
                    app.logger.error(f"Missing host definition in required service: {service}")
                    exit(1)
                # ensure type is defined in required services. If default to ping type. 
                if 'type' not in service:
                    app.logger.info(f"Missing type definition in required service: {service}. Defaulting to ping.")
                    service['type'] = "ping"
                # ensure defined type is valid
                if service['type'] not in self.VALID_SERVICE_TYPES:
                    app.logger.error(f"Invalid required service type in: {service}. Valid types are {self.VALID_SERVICE_TYPES}.")
                    exit(1)
                # ensure port is defined for socket type
                if service['type'] == 'socket' and 'port' not in service:
                    app.logger.error(f"Missing port definition in required service: {service}. Port definition is required with socket type")
                    exit(1)
                # ensure web options are set/defaulted
                if service['type'] == 'web':
                    if 'port' not in service:
                        app.logger.info(f"Missing web port definition in required service: {service}. Defaulting to 80")
                        service['port'] = 80
                    if 'path' not in service:
                        app.logger.info(f"Missing web path definition in required service: {service}. Defaulting to /")
                        service['path'] = '/'
                # ensure block startup scripts is defined. Default to False if not
                if 'block_startup_scripts' not in service:
                    app.logger.info(f"Missing block startup script definition in service: {service}. Defaulting to False")
                    service['block_startup_scripts'] = False
                if not isinstance(service['block_startup_scripts'], bool):
                    app.logger.error(f"Invalid type for block_startup_scripts. Must be true/false")
                    exit(1)
                # add to blocking services if needed
                if service['block_startup_scripts']:
                    self.blocking_services.append(service)
        app.logger.debug(f"Final Config: {self}")


    @classmethod
    def from_yaml(cls, instance: Optional["Globals"] = None, app: Optional["Flask"] = None) -> "Globals":
        instance = instance or cls()
        if not os.path.isfile(instance.yaml_path):
            print("Could not find config.yml file.")
            sys.exit(1)

        with open(instance.yaml_path, 'r') as config_file:
            try:
                conf = yaml.safe_load(config_file)
            except yaml.YAMLError:
                print("Error Reading YAML in config file")
                sys.exit(1)

        instance.load_config(conf or {}, app)
        return instance

    def mv_challenge_files(self):
        if (self.hosted_files_enabled) and (len(os.listdir(self.challenge_files)) != 0):
            if 'challenge' not in os.listdir(self.hosted_file_directory):
                os.system(f'cp -r {self.challenge_files} {self.hosted_file_directory}')