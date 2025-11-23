import json
import subprocess
import time

import yaml
from curl_cffi import requests
from loguru import logger

from .until import get_config, print_title, print_var


# clash proxy
class Proxy:
    """clash proxy"""

    def __init__(self):
        self.enable_proxy = get_config('enable_proxy')  # Whether to enable proxy

        self.profile_url = get_config('clash_profile_url')  # Clash profile url

        self.http_port = get_config('http_port')  # Clash http port
        self.http_port_name = get_config('http_port_name')  # Clash http port name

        self.api_port = get_config('api_port')  # Clash api port
        self.api_port_name = get_config('api_port_name')  # Clash api port name

        self.socks_port = get_config('socks_port')  # Clash socks port
        self.socks_port_name = get_config('socks_port_name')  # Clash socks port name

        self.profile_node = get_config('profile_node')  # Clash profile node

        self.clash_log_level_name = get_config('clash_log_level_name')  # Clash log level name
        self.clash_log_level = get_config('clash_log_level')  # Clash log level

        self.clash_path = 'clash-linux-amd64'
        self.clash_config_path = 'config.yaml'
        self.profile_file = None  # clash profile file
        self.clash = None  # Clash instance

    def download_profile_file(self):
        """download profile file"""
        retry_limit = get_config('max_retries')  # Maximum retry attempts
        timeout = get_config('request_timeout')  # Request timeout duration
        initial_backoff = 1  # Initial backoff time

        attempt = 0  # Retry count
        while attempt < retry_limit:
            try:
                # Use curl_cffi for request
                response = requests.get(self.profile_url, impersonate="chrome", timeout=(timeout, timeout))

                response.raise_for_status()

                yaml_content = yaml.safe_load(response.text)

                self.profile_file = yaml_content

                with open(f"clash/{self.clash_config_path}", "wb") as file:
                    file.write(response.content)
                    print_var(yaml_content, 'yaml_content', sort_dicts=False)
                    return
            except Exception:
                attempt += 1
                backoff_time = initial_backoff * (2 ** attempt)  # Exponential backoff delay

                logger.warning(
                    f'Clash config file download error, waiting {backoff_time} seconds before retry. Retry attempt: {attempt}'
                )

                time.sleep(backoff_time)

        e = Exception("Clash config file download reached maximum retry attempts, request failed")
        logger.error(e)
        raise e

    def modify_profile_file(self):
        """modify profile file"""
        with open(f'clash/{self.clash_config_path}', "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        if config_data is None:
            config_data = {}

        config_data[self.http_port_name] = self.http_port  # Modify proxy http port
        config_data[self.socks_port_name] = self.socks_port  # Modify proxy socks port
        config_data[self.api_port_name] = f"127.0.0.1:{self.api_port}"  # Modify external-controller
        config_data[self.clash_log_level_name] = self.clash_log_level  # Modify log-level

        # Write back
        with open(f'clash/{self.clash_config_path}', "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def change_clash_proxy(self):
        """change mode to global and change proxy to profile node"""
        # change mode to global
        base_url = f"http://127.0.0.1:{self.api_port}"

        payload = json.dumps({
            "mode": "global"
        })
        headers = {
            'Content-Type': 'application/json'
        }

        response = requests.request("PATCH", base_url + '/configs', headers=headers, data=payload)

        if response.status_code == 204:
            # print(response.text)
            logger.info('Successfully changed proxy mode to global')
        else:
            e = Exception(f'Failed to change proxy mode to global:{response.text}')
            logger.error(e)
            raise e

        # change proxy to profile node
        payload = json.dumps({
            "name": self.profile_node
        })
        headers = {
            'Content-Type': 'application/json'
        }

        response = requests.request("PUT", base_url + '/proxies/GLOBAL', headers=headers, data=payload)
        if response.status_code == 204:
            logger.info(f'Successfully changed proxy to profile node')
        else:
            e = Exception(f'Failed to change proxy to profile node:{response.text}')
            logger.error(e)
            raise e

    def open_clash_proxy(self):
        """open clash proxy"""
        try:
            self.download_profile_file()
            logger.info('Successfully downloaded profile file')

            self.modify_profile_file()
            logger.info('Successfully modified config file')

            cmd = ['./clash/clash-linux-amd64', "-d", './clash']
            self.clash = subprocess.Popen(cmd)
            time.sleep(5)  # wait clash start

            self.change_clash_proxy()
        except Exception as e:
            err = Exception(f"Clash failed to start:{e}")
            logger.error(err)
            self.close_clash_proxy()
            raise err from e

    def close_clash_proxy(self):
        """close clash proxy"""
        try:
            if self.clash:
                self.clash.terminate()

                try:
                    self.clash.wait(timeout=5)
                    logger.info("Clash process terminated gracefully")
                except subprocess.TimeoutExpired:
                    logger.warning("Clash process did not terminate, force killing...")
                    self.clash.kill()
                    self.clash.wait()
                    logger.info("Clash process force killed")

                self.clash = None

            return True
        except Exception as e:
            err = Exception(f"Failed to close Clash: {e}")
            logger.error(err)
            raise err from e

    def __del__(self):
        self.close_clash_proxy()

    def __enter__(self):
        if self.enable_proxy:  # If proxy is enabled, start clash proxy
            self.open_clash_proxy()
            print_title('Clash proxy started successfully')

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.enable_proxy:
            try:
                self.close_clash_proxy()
                print_title("Clash proxy closed successfully")
                return True
            except Exception as e:
                err = Exception(f"Failed to close Clash: {e}")
                err.__cause__ = e
                logger.exception(err)
                return False
        else:
            return True
