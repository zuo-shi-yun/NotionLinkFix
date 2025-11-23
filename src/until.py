import logging.config
import os
import ssl
import sys
from datetime import datetime
from pprint import pformat

import urllib3
import yaml
from loguru import logger
from pydantic import BaseModel, Field, ValidationError


# Set up logging
def set_log(log_level='INFO', log_filename='log'):
    """
    Set up logging
    :param log_level: Log level: INFO, DEBUG, WARNING, ERROR, CRITICAL
    :param log_filename: Log filename, path will be logs/{log_filename}_{time}.txt
    :return: None
    """
    try:
        file_path = f'logs/{log_filename}_{get_formatted_time()}.txt'
        file_dir = os.path.dirname(file_path)

        if file_dir and not os.path.exists(file_dir):
            os.makedirs(file_dir)

        logger.remove()

        # Output to file
        logger.add(
            file_path,
            format="{time:HH:mm:ss} | {level: ^8} | {message}",
            level=log_level,
            colorize=False,
            encoding='utf-8'
        )

        # Output to console
        logger.add(
            sys.stderr,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: ^8}</level> |<level>{message}</level>",
            level=log_level,
            colorize=True
        )

        logging.disable()  # close httpx log
    except Exception as e:
        err = Exception(f"Failed to set log: {e}")
        logger.error(err)
        raise err from e


# Check if configuration file is correct
class AppConfig(BaseModel):
    """Check if configuration file is correct"""
    enable_proxy: bool = Field(description="Whether to enable proxy")

    clash_profile_url: str = Field(description="Clash configuration file download URL")

    http_port_name: str = Field(description="HTTP port key name in Clash")
    http_port: int = Field(description="HTTP port used by proxy")

    api_port_name: str = Field(description="API port key name in Clash")
    api_port: int = Field(description="API port of Clash")

    socks_port_name: str = Field(description="SOCKS port key name in Clash")
    socks_port: int = Field(description="SOCKS port used by proxy")

    clash_log_level_name: str = Field(description="Log level key name in Clash")
    clash_log_level: str = Field(description="Log level in Clash")

    profile_node: str = Field(description="Node key name in Clash configuration file")

    max_request_cnt: int = Field(description="Maximum request count")
    request_timeout: int = Field(description="Request timeout")
    max_retries: int = Field(description="Maximum retry count")

    notion_backup_page_id: str = Field(description="Notion backup page ID")
    notion_valid_link_page_id: str = Field(description="Notion valid link page ID")

    notion_api_key: list[str] = Field(description="Notion API Key", min_length=1)

    callout_content: str = Field(description="Callout content in Notion")

    certificate_verification: bool = Field(description="Whether to verify certificate")

    email_addr: str = Field(description="Email address")
    email_password: str = Field(description="Email password")
    email_host: str = Field(description="Email server")
    email_port: int = Field(description="Email port")
    email_content: str = Field(description="Email content")

    ignore_validity_check_url: list[str] = Field(description="URLs to ignore validity check")


# Initialize project
def init(log_level='INFO', log_filename='log'):
    """
    Initialize project, set up logging, check configuration file, disable urllib3 warnings
    """
    try:
        set_log(log_level, log_filename)

        check_config()

        disable_urllib3_warning()
    except Exception as e:
        err = Exception(f'Project initialization failed: {e}')
        logger.error(err)
        raise err from e


# Print step name
def print_title(step_name: str, delimiter='-'):
    """Print step name"""

    s = f"{delimiter * 25}{step_name}{delimiter * 25}"
    logger.info(s)


# Print variable, log level: DEBUG
def print_var(var, var_name, sort_dicts=True):
    """Print variable, log level: DEBUG"""

    # var information and should be printed
    var_dict = {
        'Page raw content': {
            'print': True,
            'description': 'The raw content of the notion page(The original content requested)'
        },
        'Sorted page content': {
            'print': True,
            'description': 'The original data of the notion backup page sorted in the order of the original page'
        },
        'Sorted page tree structure': {
            'print': True,
            'description': 'displayed hierarchically in a tree structure:The original data of notion backup pages sorted in the order of the original pages '
        },
        'Notion content after URL validation': {
            'print': True,
            'description': 'Only the notion page data that stores valid links and blocks that should appear on the page is retained'
        },
        'Tree structure for inserting valid links into Notion page': {
            'print': True,
            'description': 'The after clean tree structure of the valid links to be inserted into the notion page'
        },
        'clash_yaml_content': {
            'print': True,
            'description': 'The content of the clash configuration file'
        }
    }

    # Conservative strategy: Do not print only when it is explicitly set not to print
    if var_name in var_dict and not var_dict[var_name]['print']:
        return

    logger.debug(f"{'*' * 25}{var_name}{'*' * 25}")

    s = pformat(var, sort_dicts=sort_dicts)
    logger.debug(s)


# Check if configuration file is correct
def check_config():
    """Check if configuration file is correct"""
    # Read
    with open('config.yml', 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)

    # Validate
    try:
        AppConfig(**config_data)
        logger.debug("Configuration file validation passed")
    except ValidationError as e:
        err = Exception(f'Configuration file validation failed: {e}')
        logger.error(err)
        raise err from e


# Read the corresponding value from the YAML file based on the given key
def get_config(key):
    """
    Read the corresponding value from the YAML file based on the given key
    :param key: The key to be searched for
    :return: The value corresponding to the key. If the key does not exist, raise an exception
    """
    yaml_file = 'config.yml'
    try:
        with open(yaml_file, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
        return data[key]
    except Exception as e:
        err = Exception(f'Failed to read configuration information: {e}')
        logger.error(err)
        raise err from e


# Get SSL context without certificate verification
def get_disable_certificate_verification_ssl():
    """Get SSL context without certificate verification"""
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.Verify_mode = ssl.CERT_NONE
    return ssl_context


# Disable certificate verification warning
def disable_urllib3_warning():
    """Disable certificate verification warning"""
    if not get_config('certificate_verification'):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Get page ID separated by hyphens
def rebuild_page_id(page_id: str):
    """Get page ID separated by hyphens"""
    if page_id.count('-') != 4:
        part1 = page_id[:8]
        part2 = page_id[8:12]
        part3 = page_id[12:16]
        part4 = page_id[16:20]
        part5 = page_id[20:]

        ret = part1 + '-' + part2 + '-' + part3 + '-' + part4 + '-' + part5

        return ret
    else:
        return page_id


# Check if block should appear in page
def is_block_should_in_page(block_type: str) -> bool:
    """
    Check if block should appear in page
    :param block_type: Block type
    :return: bool, if False, the block is considered to appear in the page storing all links due to misoperation and will not be inserted into the Notion page storing valid links
    """
    valid_block_type = ['heading_2', 'toggle', 'divider', 'callout', 'bulleted_list_item', 'child_page', 'paragraph']

    return block_type in valid_block_type


def get_formatted_time(use_in_log=True) -> str:
    """
    Get formatted time
    :param use_in_log: If True, use "_" to connect time, otherwise use "-" to connect year-month-day, use ":" to connect hour-minute-second
    :return: str, formatted time
    """

    # Get current time
    current_time = datetime.now()
    if use_in_log:
        # Format time
        formatted_time = current_time.strftime('%Y_%m_%d_%H_%M_%S')
    else:
        formatted_time = current_time.strftime('%Y-%m-%d %H:%M:%S')

    return formatted_time
