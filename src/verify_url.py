import asyncio
import threading
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from random import choice
from urllib.parse import urlparse

import cloudscraper
import curl_cffi
import httpx
import requests
import tls_client
from curl_cffi import AsyncSession
from loguru import logger

from .NotionBlock import BlockBaseClass
from .Proxy import Proxy
from .until import get_config, rebuild_page_id, get_disable_certificate_verification_ssl


# Base class for sending async requests
class SendAgentBaseClass(ABC):
    """Base class for sending async requests, encapsulates link validity verification logic"""

    def __init__(self):
        # Maximum concurrency
        self.max_request_cnt = get_config('max_request_cnt')

        # Whether to enable proxy for link validity verification, when False all links do not use proxy
        self.enable_proxy = get_config('enable_proxy')

        # Proxy configuration
        self.proxy = {
            "http": f"http://127.0.0.1:{get_config('http_port')}",
            "https": f"http://127.0.0.1:{get_config('http_port')}"
        }

        # Request timeout
        self.timeout = get_config('request_timeout')
        self.task_timeout = self.timeout * 3  # Task timeout
        # Random User-Agent
        self.USER_AGENTS = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edg/120.0.0.0 Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 14; SAMSUNG SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/24.0 Chrome/120.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) OPR/96.0.0.0 Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Linux; Android 13; SM-A536U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; Trident/6.0)"
        ]

        # Whether to enable certificate verification
        self.certificate_verification = get_config('certificate_verification')

        # Status codes indicating valid links
        self.correct_status_code = [200, 201, 202, 204]

    @classmethod
    @abstractmethod
    def send_agent_name(cls) -> str:
        """
        Sending proxy client name, used for log output
        :return: str, directly return proxy client name
        """
        pass

    def get_random_headers(self) -> dict:
        """Randomly generate request headers"""
        return {
            "User-Agent": choice(self.USER_AGENTS),
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

    @abstractmethod
    async def send_limit_request(self, url: str, enable_proxy: bool):
        """Send request with concurrency limit, async clients use semaphore limit, sync clients use thread pool limit"""
        pass

    @abstractmethod
    def is_response_valid(self, response, url_name: str) -> bool:
        """
        Determine if response is valid
        :param response: request response result
        :param url_name: text storing link in notion page
        :return: bool, whether valid
        """
        pass

    async def run(self, urls: list[str], urls_name: list[str], block_ids: list[str]) -> list[tuple[str, bool]]:
        """
        Entry function for async link validity verification
        :param urls: all urls to be verified
        :param urls_name: all text storing links in notion page to be verified
        :param block_ids: block ids storing links
        :return: list[(block id storing link, whether link is valid)]
        """
        try:
            # Create verification tasks
            tasks = []
            for url, url_name, block_id in zip(urls, urls_name, block_ids):
                disable_proxy_task = asyncio.create_task(self.send_limit_request(url, False))  # No proxy task

                # Create proxy task only when proxy is enabled, otherwise set task to None
                if self.enable_proxy:
                    enable_proxy_task = asyncio.create_task(self.send_limit_request(url, True))
                else:
                    enable_proxy_task = None

                tasks.append((disable_proxy_task, enable_proxy_task, url, url_name, block_id))

            # Process verification results
            ret = []  # Return value
            all_request_cnt = len(urls)
            valid_url_cnt = 0  # Valid link counter
            for idx, (disable_proxy_task, enable_proxy_task, url, url_name, block_id) in enumerate(tasks):
                # No proxy task result
                disable_proxy_response = (await asyncio.gather(disable_proxy_task, return_exceptions=True))[0]
                disable_proxy_result = self.check_response(disable_proxy_response, url, url_name)

                # Process proxy task result only when proxy is enabled, otherwise set result to False
                if self.enable_proxy:
                    enable_proxy_response = (await asyncio.gather(enable_proxy_task, return_exceptions=True))[0]
                    enable_proxy_result = self.check_response(enable_proxy_response, url, url_name)
                else:
                    enable_proxy_result = False

                # Either no proxy or proxy being True is sufficient
                is_url_valid = any([disable_proxy_result, enable_proxy_result])
                valid_url_cnt += 1 if is_url_valid else 0

                # Log output
                if self.enable_proxy:
                    result_info = f"With proxy request:{enable_proxy_result}, Without proxy request:{disable_proxy_result}, Final result:{is_url_valid}"
                else:
                    result_info = f'Result:{is_url_valid}'

                logger.info(
                    f"{self.send_agent_name()}({idx + 1}/{all_request_cnt}) | "
                    f"{url_name}({self._format_url(url)}...) | " +
                    result_info
                )

                ret.append((block_id, is_url_valid))

            logger.info(f"{self.send_agent_name()} detected {valid_url_cnt} reachable links")
            return ret
        except Exception as e:
            err = Exception(f"{self.send_agent_name()}: Exception occurred: {e}")
            logger.error(err)
            raise err from e

    def _format_url(self, url):
        """Format url, only keep domain and its first 20 characters"""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc  # Get domain part
        return domain[:20]

    def check_response(self, response, url, url_name) -> bool:
        """Check if response is valid, also invalid when result is exceptional"""
        result = False

        if not isinstance(response, Exception):
            result = self.is_response_valid(response, url_name)
        else:
            logger.debug(
                f"{self.send_agent_name()}: "
                f"Exception occurred when sending request to {url_name}({url}): {response}"
            )

        return result

    @abstractmethod
    async def close_send_agent(self):
        """Close proxy, will be called at async context manager exit"""
        pass

    @abstractmethod
    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            await self.close_send_agent()
            return True
        except Exception as e:
            err = Exception(f"{self.send_agent_name()}: Failed to close request proxy: {e}")
            err.__cause__ = e
            logger.exception(err)
            return False


# Base class for async client link validity verification
class AsyncSendAgentBaseClass(SendAgentBaseClass):
    """Base class for async client link validity verification, encapsulates async client request sending logic"""

    def __init__(self):
        super().__init__()

        self.semaphore = asyncio.Semaphore(self.max_request_cnt)  # Request concurrency

        self.agent = None  # Request sending client, all requests are sent using this attribute

    @abstractmethod
    async def set_send_agent(self) -> None:
        """Set request sending client (self.agent), only one client instance is created per object, called at async context manager entrance"""
        pass

    @abstractmethod
    async def send_request(self, url: str, enable_proxy: bool):
        """
        Send async request using self.agent
        :param url: url to send
        :param enable_proxy: whether to enable proxy
        :return: request result(response)
        """
        pass

    async def send_limit_request(self, url: str, enable_proxy: bool):
        """Request with concurrency limit using semaphore and timeout limit"""
        async with self.semaphore:
            result = await asyncio.wait_for(
                self.send_request(url, enable_proxy),
                timeout=self.task_timeout
            )

            return result

    async def __aenter__(self):
        """Async context entrance, instantiate self.agent"""
        try:
            await self.set_send_agent()
            return self
        except Exception as e:
            err = Exception(f"{self.send_agent_name()}: Failed to set proxy: {e}")
            err.__cause__ = e
            logger.exception(err)
            return False


# httpx
class HttpxAgent(AsyncSendAgentBaseClass):
    """Send async request using httpx"""

    def __init__(self):
        super().__init__()

        self.agent: dict[str, httpx.AsyncClient]

    @classmethod
    def send_agent_name(cls) -> str:
        return 'httpx'

    async def set_send_agent(self):
        # One client each for with proxy and without proxy
        self.agent = {
            'enable_proxy': httpx.AsyncClient(
                timeout=self.timeout,
                proxy=self.proxy['http'],
                follow_redirects=True,
                verify=self.certificate_verification
            ),
            'disable_proxy': httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                verify=self.certificate_verification
            )
        }

    async def send_request(self, url: str, enable_proxy: bool) -> httpx.Response:
        headers = self.get_random_headers()  # Random headers
        client = self.agent['enable_proxy'] if enable_proxy else self.agent['disable_proxy']  # Select client

        response = await client.get(url, headers=headers)  # Send request

        return response

    def is_response_valid(self, response: httpx.Response, url_name: str) -> bool:
        """Check status code"""
        return response.status_code in self.correct_status_code

    async def close_send_agent(self):
        """Close all clients"""
        for agent in self.agent.values():
            await agent.aclose()


# curl_cffi
class CurlCffiAgent(AsyncSendAgentBaseClass):
    """Send async request using curl_cffi"""

    def __init__(self):
        super().__init__()

        self.agent: curl_cffi.AsyncSession

        self.impersonate = "chrome"  # Impersonate latest version of chrome browser

    @classmethod
    def send_agent_name(cls) -> str:
        return 'curl_cffi'

    async def set_send_agent(self):
        self.agent = AsyncSession(max_clients=self.max_request_cnt)  # Set maximum concurrency value

    async def send_request(self, url: str, enable_proxy: bool) -> curl_cffi.Response:
        headers = self.get_random_headers()
        proxy_config = self.proxy if enable_proxy else None

        response = await self.agent.get(
            url,
            headers=headers,
            proxy=proxy_config,
            timeout=(self.timeout, self.timeout),
            impersonate=self.impersonate,
            allow_redirects=True,
            verify=self.certificate_verification
        )

        return response

    def is_response_valid(self, response: curl_cffi.Response, url_name: str) -> bool:
        return response.status_code in self.correct_status_code

    async def close_send_agent(self):
        await self.agent.close()


# Base class for simulating async requests using thread pool
class ThreadedSendAgentBaseClass(SendAgentBaseClass):
    """Base class for simulating async requests using thread pool"""

    def __init__(self):
        super().__init__()

        self.executor = ThreadPoolExecutor(max_workers=self.max_request_cnt)  # Thread pool

        self.thread_local = threading.local()  # Thread-local variable, one client instance per thread
        self.agents = []  # Store all proxy instances
        self.agents_lock = threading.Lock()  # Thread lock to prevent multi-threaded simultaneous operations on proxy instances

    @abstractmethod
    def get_send_agent(self):
        """
        Get request sending client instance, will be called when each thread is created for the first time
        :return: directly return request client instance
        """
        pass

    @abstractmethod
    def send_request(self, agent, url: str, enable_proxy: bool):
        """
        Send request using agent
        :param agent: client to use, request is sent by this parameter
        :param url: url to be verified
        :param enable_proxy: whether to enable proxy
        :return: directly return response result
        """
        pass

    def send_request_with_different_agent(self, url: str, enable_proxy: bool):
        """
        Call send_request to send request, provide different agent instances for each thread
        :param url: url to be verified
        :param enable_proxy: whether to enable proxy
        :return: return send_request function result
        """
        # Whether this is the first instance of the thread
        with self.agents_lock:
            if not hasattr(self.thread_local, 'agent'):
                agent = self.get_send_agent()  # Get client instance

                self.thread_local.agent = agent  # Save client instance

                self.agents.append(agent)

        agent = self.thread_local.agent

        return self.send_request(agent, url, enable_proxy)

    async def send_limit_request(self, url: str, enable_proxy: bool):
        """
        Call send_request to send request, request with concurrency limit using thread pool and timeout limit
        :param url: url to be verified
        :param enable_proxy: whether to enable proxy
        :return: return send_request function result
        """
        loop = asyncio.get_running_loop()  # Get current event loop

        # Send request using thread pool
        result = await asyncio.wait_for(
            loop.run_in_executor(
                self.executor,
                self.send_request_with_different_agent,
                url,
                enable_proxy
            ),
            timeout=self.task_timeout
        )

        return result

    @abstractmethod
    def close_one_agent(self, agent) -> bool:
        """
        Close one client instance
        :param agent: client instance to close
        :return: bool, whether successfully closed
        """
        pass

    async def close_send_agent(self):
        """Close all clients"""

        # We do not want the operation of closing the client to affect the operation of subsequent functions,
        # and at the same time, we hope to catch exceptions
        def close_send_agent_by_try_catch(agent):
            try:
                self.close_one_agent(agent)
            except Exception as e:
                err = Exception(f"Error when closing {self.send_agent_name()}: {e}")
                err.__cause__ = e
                logger.exception(err)

        loop = asyncio.get_running_loop()  # Get current event loop
        tasks = []
        for agent in self.agents:
            task = loop.run_in_executor(
                self.executor,
                close_send_agent_by_try_catch,
                agent
            )
            tasks.append(task)

        self.agents.clear()

        async def not_block_execution():
            await asyncio.gather(*tasks)
            self.executor.shutdown()  # Close thread pool

        asyncio.create_task(not_block_execution())

    async def __aenter__(self):
        """Async context entrance, do not instantiate any client instance, return directly"""
        return self


# requests
class RequestsAgent(ThreadedSendAgentBaseClass):
    """Send request using requests"""

    def __init__(self):
        super().__init__()

    @classmethod
    def send_agent_name(cls) -> str:
        return "requests"

    def get_send_agent(self) -> requests.Session:
        return requests.Session()  # Client instance

    def send_request(self, agent: requests.Session, url: str, enable_proxy: bool) -> requests.Response:
        headers = self.get_random_headers()  # Random request headers

        # Send request
        response = agent.get(
            url,
            headers=headers,
            proxies=self.proxy if enable_proxy else None,
            timeout=self.timeout,
            verify=self.certificate_verification
        )

        return response

    def is_response_valid(self, response: requests.Response, url_name: str) -> bool:
        return response.status_code in self.correct_status_code

    def close_one_agent(self, agent: requests.Session):
        agent.close()  # Close client


# cloudscraper
class CloudScraperAgent(ThreadedSendAgentBaseClass):
    """Send request using cloudscraper"""

    def __init__(self):
        super().__init__()

    @classmethod
    def send_agent_name(cls) -> str:
        return 'cloudscraper'

    def get_send_agent(self) -> cloudscraper.CloudScraper:
        # cloudscraper needs to set whether to disable certificate verification through ssl context
        if not self.certificate_verification:
            ssl_context = get_disable_certificate_verification_ssl()
            agent = cloudscraper.create_scraper(ssl_context=ssl_context)
        else:
            agent = cloudscraper.create_scraper()

        return agent

    def send_request(self, agent: cloudscraper.CloudScraper, url: str, enable_proxy: bool) -> requests.Response:
        proxies = self.proxy if enable_proxy else None

        response = agent.get(
            url,
            proxies=proxies,
            timeout=self.timeout,
            allow_redirects=True
        )

        return response

    def is_response_valid(self, response: requests.Response, url_name: str) -> bool:
        return response.status_code in self.correct_status_code

    def close_one_agent(self, agent: cloudscraper.CloudScraper):
        agent.close()


# tls-client
class TlsClientAgent(ThreadedSendAgentBaseClass):
    """Send request using tls-client"""

    def __init__(self):
        super().__init__()

        self.client_identifier = "chrome112"  # tls-client client identifier

    @classmethod
    def send_agent_name(cls) -> str:
        return 'tls_client'

    def get_send_agent(self) -> tls_client.Session:
        return tls_client.Session(
            client_identifier=self.client_identifier,
            random_tls_extension_order=True,
        )

    def send_request(self, agent: tls_client.Session, url: str, enable_proxy: bool) -> tls_client.sessions.Response:
        response = agent.get(
            url,
            proxy=self.proxy if enable_proxy else None,
            timeout_seconds=self.timeout,
            insecure_skip_verify=not self.certificate_verification,  # Whether to disable certificate verification
            allow_redirects=True
        )

        return response

    def is_response_valid(self, response: tls_client.sessions.Response, url_name: str) -> bool:
        return response.status_code in self.correct_status_code

    def close_one_agent(self, agent: tls_client.Session):
        agent.close()


# Verify url validity
class VerifyUrl:
    """Entry class for url validity verification"""

    def __init__(self, content):
        self.content = content  # Notion page content

        self.all_urls_info = None  # All url information {block_id:{'url':url,'url_name':url_name}}
        self.valid_urls_and_names = {}  # Valid link information, same structure as all_urls_info
        self.invalid_urls_and_names = {}  # Invalid link information, same structure as all_urls_info

    def _get_all_block_url_name_id(self, content) -> dict:
        """Extract url, name, id from blocks"""
        res = {}
        for block_id in content:  # Traverse all blocks
            block = content[block_id]
            block_type = block['type']

            # Traverse BlockBaseClass subclasses
            for notion_block in BlockBaseClass.__subclasses__():
                notion_block = notion_block()

                if block_type == notion_block.block_type():  # If block type matches
                    url, name = notion_block.parse_block(block)  # Parse block content

                    res[block_id] = {
                        'url': url,
                        'url_name': name,
                    }

                    break

        return res

    def get_unverified_urls(self):
        """Get dictionary of unverified urls"""
        if len(self.invalid_urls_and_names) == 0:
            return self.all_urls_info
        else:
            return self.invalid_urls_and_names

    def save_validated_urls_and_name(self, block_id, is_url_valid):
        """Update notion page structure and statistics based on verification results"""
        url = self.all_urls_info[block_id]['url']
        url_name = self.all_urls_info[block_id]['url_name']

        # Statistics
        if is_url_valid:
            if block_id not in self.valid_urls_and_names:
                self.valid_urls_and_names[block_id] = {
                    'url': url,
                    'url_name': url_name,
                }
            if block_id in self.invalid_urls_and_names:
                del self.invalid_urls_and_names[block_id]
        else:
            self.invalid_urls_and_names[block_id] = {
                'url': url,
                'url_name': url_name,
            }

        # Notion page structure
        if 'is_url_valid' in self.content[block_id] and self.content[block_id]['is_url_valid'] == False:
            self.content[block_id]['is_url_valid'] = is_url_valid
        elif 'is_url_valid' not in self.content[block_id]:
            self.content[block_id]['is_url_valid'] = is_url_valid
        self.content[block_id]['url'] = url

    async def run(self):
        """Entry function for link validity verification"""
        try:
            self.all_urls_info = self._get_all_block_url_name_id(self.content)  # Get all urls and their information

            with Proxy():  # Enable proxy
                # All request clients
                send_agents = [j for i in SendAgentBaseClass.__subclasses__() for j in i.__subclasses__()]

                # Traverse all request clients
                for send_agent in send_agents:
                    unverified_urls = self.get_unverified_urls()  # Get links to be verified

                    async with send_agent() as agent:  # Client instance
                        agent: SendAgentBaseClass

                        blocks_id = list(unverified_urls.keys())
                        urls = [info['url'] for info in unverified_urls.values()]
                        urls_name = [info['url_name'] for info in unverified_urls.values()]

                        results = await agent.run(urls, urls_name, blocks_id)

                        # Process results
                        for block_id, is_url_valid in results:
                            self.save_validated_urls_and_name(block_id, is_url_valid)

            return self.content
        except Exception as e:
            err = Exception(f"Error verifying url: {e}")
            logger.error(err)
            raise err from e


# Delete blocks storing invalid links in notion page structure
def delete_invalid_block(content: dict, tree: dict) -> dict:
    """
    Delete blocks storing invalid links in notion page structure (excluding excluded urls)
    :param tree: sorted tree structure
    :param content: original page content
    :return: tree structure after clearing child blocks
    """

    def is_delete_node(node: dict, sibling_node: list[dict], delete_step: int) -> bool:
        """
        Whether this block should be deleted, delete when unordered list stores invalid url link or divider has no valid content between it or block has no child blocks
        :param node: block
        :param sibling_node: all blocks at the same level under the same parent block as node
        :param delete_step: which deletion pass
        :return: bool, whether should be deleted
        """
        nonlocal content
        block_type = node['type']
        node_id = f"{block_type}_{node['id']}"

        if node['id'] != rebuild_page_id(get_config('notion_backup_page_id')):
            is_url_valid = content[node_id].get('is_url_valid')
            url = content[node_id].get('url')
        else:  # Don't process page first level structure
            is_url_valid = None
            url = None

        try:
            if delete_step == 1:  # First pass deletion: remove blocks storing invalid links
                if is_url_valid is False:
                    if url in get_config('ignore_validity_check_url'):
                        return False  # Don't delete if url in ignore validity check url list
                    else:
                        return True
                elif is_url_valid is True:
                    return False
            elif delete_step in [2, 3]:
                if block_type == 'divider':  # Pass 2 and 3 deletion only delete dividers
                    if len(sibling_node) == 1:  # Third pass deletion: remove divider when only one divider exists at this level
                        return True
                    else:  # Second pass deletion: remove divider at top when no blocks exist between dividers
                        idx = sibling_node.index(node)
                        # Not the last block and next block is also a divider
                        if idx < len(sibling_node) - 1 and sibling_node[idx + 1]['type'] == 'divider':
                            return True
                        else:
                            return False
                else:
                    return False
            elif delete_step in [4, 5]:
                # Pass 4 and 5 deletion: remove heading_2 blocks and toggle blocks with no child blocks
                if block_type in ['heading_2', 'toggle']:
                    if len(node['children']) == 0:
                        return True
                    else:
                        return False
                else:
                    return False
        except Exception as e:
            err = Exception(f"Unexpected error for node {node_id}: {e}")
            logger.error(err)
            raise err from e

    def delete_block(node: dict, delete_step: int, sibling_node: list[dict] = None):
        """
        Recursively delete child blocks
        :param node: block
        :param delete_step: which deletion pass
        :param sibling_node: all blocks at the same level under the same parent block as node
        :return: all child blocks after deleting child blocks
        """
        delete_block_no = []
        for no, child in enumerate(node['children']):  # Traverse all child blocks under this block
            delete_result = delete_block(child, delete_step, node['children'])  # Recursively delete child blocks
            if delete_result is None:  # This child block has no child blocks
                delete_block_no.append(no)
            else:  # This child block still has blocks
                node['children'][no] = delete_result

        # Delete all child blocks with no child blocks under this block
        for idx in delete_block_no[::-1]:
            del node['children'][idx]

        is_delete = is_delete_node(node, sibling_node, delete_step)  # If this block should be deleted
        if is_delete:
            return None
        else:
            return node

    # Check whether blocks should be deleted 6 times in total
    for delete_step in range(1, 6):
        tree = delete_block(tree, delete_step)

    return tree
