import asyncio
import time
from abc import ABC, abstractmethod
from asyncio import Lock
from asyncio import Semaphore
from collections import deque

from loguru import logger
from notion_client import AsyncClient

from .until import get_config, rebuild_page_id, is_block_should_in_page, \
    get_formatted_time, print_var


# Base class for sending Notion requests asynchronously
class AsyncSendNotionRequestBaseClass(ABC):
    """Base class for sending Notion requests asynchronously"""

    def __init__(self):
        self.notion_api_key: list[str] = get_config('notion_api_key')  # notion api key

        self.clients = []  # Each api key corresponds to a client
        self.semaphores = []  # Semaphore for each client
        self.rate_limiters = []  # Rate limiter for each client
        self.max_requests_per_second = 2  # Maximum requests per second for each client
        self.max_retries = get_config('max_retries')  # Maximum number of retries

        # Statistics
        self.total_requests = 0  # Total number of requests
        self.requests_lock = Lock()

    @abstractmethod
    def notion_request_name(self) -> str:
        """
        Request client name, used for log output
        :return: Returns the request client name directly
        """
        pass

    @abstractmethod
    async def send_request(self, block_id: str, client: AsyncClient, **kwargs):
        """
        Send request asynchronously
        :param block_id: Block id/page id for the request
        :param client: Client used to send the request
        :param kwargs: Possible parameters
        :return: Returns the request result directly
        """
        pass

    async def _rate_limited_request(self, client_idx, block_id: str, initial_delay=1.0, **kwargs) -> tuple:
        """
        Request with rate limiting and exponential backoff retry
        :param client_idx: Client index
        :param block_id: Block ID/Page ID
        :param initial_delay: Initial backoff delay (seconds)
        :param kwargs: Possible parameters
        :return: Request result, returns the result of send_request and the client index that sent the request
        """
        semaphore = self.semaphores[client_idx]  # Semaphore
        rate_limiter = self.rate_limiters[client_idx]  # Rate limiter
        client = self.clients[client_idx]  # Client used to send the request

        retry_count = 0  # Retry count
        last_exception = None  # Last exception

        while retry_count <= self.max_retries:  # Retry at most max_retries times
            async with semaphore:  # Limit concurrent requests per second
                # Check rate limit
                now = time.time()

                # Remove old request timestamps older than 1 second
                while rate_limiter and now - rate_limiter[0] >= 1.0:
                    rate_limiter.popleft()

                # If rate limit is reached, wait
                if len(rate_limiter) >= self.max_requests_per_second:
                    sleep_time = 1.0 - (now - rate_limiter[0])
                    if sleep_time > 0:
                        await asyncio.sleep(sleep_time)

                # Record request time
                rate_limiter.append(time.time())

                # Statistics
                async with self.requests_lock:
                    self.total_requests += 1
                    request_num = self.total_requests

                retry_info = f" [Retry {retry_count}/{self.max_retries}]" if retry_count > 0 else ""  # Output different log information based on whether retrying
                logger.info(
                    f"Client #{client_idx + 1} | {self.notion_request_name()} #{request_num} | Block: {block_id}{retry_info}")

                try:
                    request_results = await self.send_request(block_id, client, **kwargs)  # Send request

                    if retry_count > 0:
                        logger.info(f"Client #{client_idx + 1} | Block: {block_id} retry successful")

                    return request_results, client_idx
                except Exception as e:
                    last_exception = e
                    error_msg = str(e)

                    if retry_count >= self.max_retries:  # Reached maximum retry count
                        err = Exception(
                            f"Client #{client_idx + 1} {self.notion_request_name()} failed (reached maximum retry count): {e}")
                        logger.error(err)
                        raise err from e

                    delay = initial_delay * (2 ** retry_count)  # Exponential backoff delay
                    jitter = delay * 0.1 * (time.time() % 1)  # Add jitter to avoid thundering herd
                    total_delay = delay + jitter

                    logger.warning(f"Client #{client_idx + 1} | Block: {block_id} | "
                                   f"Error: {error_msg} | Waiting {total_delay:.2f}s before retry")

                    retry_count += 1
                    await asyncio.sleep(total_delay)

        e = Exception(
            f"Client #{client_idx + 1} request completely failed: {last_exception}")  # If execution reaches here, it's almost impossible to be a network issue, please check the send_request function
        logger.error(e)
        raise e

    @abstractmethod
    async def process_block_recursive(self, initial_block_id, **kwargs):
        """
        Process blocks recursively
        :param initial_block_id: Initial page id
        :param kwargs: Possible parameters
        :return:
        """
        pass

    async def __aenter__(self):
        """Async context manager entry"""

        # Create client and rate limiter for each API key
        for i, api_key in enumerate(self.notion_api_key):
            client = AsyncClient(auth=api_key)  # Async client
            self.clients.append(client)

            # Semaphore
            semaphore = Semaphore(self.max_requests_per_second)
            self.semaphores.append(semaphore)

            # Rate limiter
            rate_limiter = deque(maxlen=self.max_requests_per_second)
            self.rate_limiters.append(rate_limiter)

            logger.info(
                f"Initialize {self.notion_request_name()} client #{i + 1} ready (limit: {self.max_requests_per_second} req/s)")

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        for client in self.clients:
            await client.aclose()


# Get notion page content
class GetNotionPageContent(AsyncSendNotionRequestBaseClass):
    """Get notion page content"""

    def __init__(self):
        super().__init__()

        # Page content and its lock
        self.content_lock = Lock()
        self.notion_page_content = {}  # Raw content obtained from request

        # Block order and its lock
        self.block_order_lock = Lock()
        self.block_order = {}  # Block order information added on top of raw content

    def notion_request_name(self) -> str:
        return 'Request Block'

    async def retain_useful_information(self, block, block_type):
        """
        Retain useful information in the block
        :param block: Raw information of the block. For detailed structure see: https://developers.notion.com/reference/block
        :param block_type: Block type
        :return: None
        """
        async with self.content_lock:  # Ensure thread safety
            block_store_key = f"{block_type}_{block['id']}"  # Construct block key

            # Keys storing useful information in the block
            block_useful_info_keywords = ['id', 'object', 'parent', 'type', block_type]

            # Only retain useful information
            self.notion_page_content[block_store_key] = {
                i: block[i] for i in block_useful_info_keywords if i in block
            }

            parent_id = block['parent'][block['parent']['type']]  # Parent block id
            self.notion_page_content[block_store_key]['no'] = self.block_order[parent_id].index(
                block['id'])  # Order in parent block

    async def send_request(self, block_id: str, client: AsyncClient, **kwargs):
        response = await client.blocks.children.list(block_id=block_id)

        return response

    async def process_block_recursive(self, initial_block_id, **kwargs):
        """
        Recursively get page and its child blocks
        :param initial_block_id: Page id
        :param kwargs: process_block_recursive:bool, if False only get the first layer content on the page
        :return: None
        """

        # Queue of block IDs to be processed
        queue = deque(initial_block_id)
        processed = set()  # Avoid duplicate processing

        batch_num = 0  # Batch number

        while queue:
            batch_num += 1

            # Batch size, minimum of number of blocks to request and maximum concurrency
            batch_size = min(len(queue), len(self.clients) * self.max_requests_per_second)

            current_batch = []  # Block ids to request in current batch
            for _ in range(batch_size):
                if queue:
                    block_id = queue.popleft()
                    if block_id not in processed:
                        current_batch.append(block_id)
                        processed.add(block_id)

            if not current_batch:  # If current batch is empty, all blocks are processed
                break

            logger.info(f"Batch #{batch_num} processing {len(current_batch)} blocks")

            # Create tasks, round-robin assignment to different clients
            tasks = []
            for i, block_id in enumerate(current_batch):
                client_idx = i % len(self.clients)  # Round-robin assignment
                task = asyncio.create_task(self._rate_limited_request(client_idx, block_id))  # Create task
                tasks.append(task)

            # Wait for all tasks in this batch to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            new_blocks_count = 0
            for result in results:
                if isinstance(result, Exception):
                    err = Exception(f"Request block task exception: {result}")
                    logger.error(err)
                    raise err from result

                response, client_idx = result
                if response is None:
                    continue

                res = response.get('results', [])
                if len(res) == 0:  # Block or page is empty
                    continue
                else:
                    res = res[0]

                parent_id = res['parent'][res['parent']['type']]  # Parent block id

                async with self.block_order_lock:
                    self.block_order[parent_id] = []  # Initialize child block order list under parent block

                # Process child blocks of this block
                if kwargs['process_block_recursive']:  # If False, only get the first layer content on the page
                    blocks = response.get('results', [])  # All child blocks in this block
                    for block in blocks:
                        block_type = block.get('type', 'unknown')
                        if is_block_should_in_page(block_type):  # Determine if block should be included in the page
                            async with self.block_order_lock:
                                self.block_order[parent_id].append(block['id'])  # Record this child block order

                            await self.retain_useful_information(block, block_type)  # Store block information

                            # If block has children, add to queue
                            if block.get('has_children', False):
                                child_id = block['id']
                                if child_id not in processed:
                                    queue.append(child_id)
                                    new_blocks_count += 1
                else:
                    self.notion_page_content = response  # First layer content of the page

            logger.info(f"Batch #{batch_num} completed, found {new_blocks_count} new child blocks\n")


# Notion content sorter, reorganizes raw content according to hierarchical structure
class NotionPageContentSorter:
    """Notion content sorter, reorganizes raw content according to hierarchical structure"""

    @staticmethod
    def sort_content(notion_page_content, block_order, root_id):
        """
        Sort Notion content according to hierarchical structure
        :param notion_page_content: Raw page content
        :param block_order: Block order dictionary {parent_id: [child_id1, child_id2, ...]}
        :param root_id: Root block ID (page ID)
        :return: {
                    'tree': Hierarchical tree structure,
                    'flat_list': Flattened ordered list,
                    'sorted_content': Content dictionary reorganized in order
                }
        """

        # Build tree structure
        tree = NotionPageContentSorter._build_tree(
            root_id, notion_page_content, block_order
        )

        # Flatten tree structure
        flat_list = NotionPageContentSorter._flatten_tree(tree)

        # Reorganize content (add global order number)
        sorted_content = NotionPageContentSorter._reorder_content(
            flat_list, notion_page_content
        )

        return {
            'tree': tree,
            'flat_list': flat_list,
            'sorted_content': sorted_content
        }

    @staticmethod
    def _build_tree(block_id, content_dict, order_dict, depth=0):
        """Recursively build tree structure"""
        # Find block content
        block_content = None
        for key, value in content_dict.items():
            if value.get('id') == block_id:
                block_content = value
                break

        # Build node
        node = {
            'id': block_id,
            'type': block_content.get('type') if block_content else 'unknown',
            'no': block_content.get('no', -1) if block_content else -1,
            'depth': depth,
            'content': block_content,
            'children': []
        }

        # Recursively process child blocks
        if block_id in order_dict:
            child_ids = order_dict[block_id]
            for child_id in child_ids:
                child_node = NotionPageContentSorter._build_tree(
                    child_id, content_dict, order_dict, depth + 1
                )
                node['children'].append(child_node)

            # Sort child blocks by no
            node['children'].sort(key=lambda x: x['no'])

        return node

    @staticmethod
    def _flatten_tree(tree):
        """Flatten tree structure (dfs)"""
        result = []

        def traverse(node, global_index=None):
            if global_index is None:
                global_index = [0]
            result.append({
                'global_no': global_index[0],  # Global order number
                'id': node['id'],
                'type': node['type'],
                'no': node['no'],  # Number in parent block
                'depth': node['depth'],
                'content': node['content'],
                'has_children': len(node['children']) > 0,
                'children_count': len(node['children'])
            })
            global_index[0] += 1

            for child in node['children']:
                traverse(child, global_index)

        traverse(tree)
        return result

    @staticmethod
    def _reorder_content(flat_list, original_content):
        """Reorganize content, add global order information"""
        sorted_content = {}

        for item in flat_list:
            block_id = item['id']

            # Find the key of original content
            original_key = None
            for key, value in original_content.items():
                if value.get('id') == block_id:
                    original_key = key
                    break

            if original_key:
                # Copy original content and add sort information
                sorted_content[original_key] = {
                    **original_content[original_key],
                    'global_no': item['global_no'],  # Global order
                    'depth': item['depth'],  # Depth
                    'has_children': item['has_children'],
                    'children_count': item['children_count']
                }

        return sorted_content

    @staticmethod
    def print_tree(tree, indent=0, show_content=False):
        """Print tree structure"""
        prefix = "  " * indent
        icon = f"{prefix}   📄" if not tree['children'] else "📁"

        output = ''
        if show_content and tree['content']:
            block_type = tree['type']
            if block_type in tree['content'] and isinstance(tree['content'][block_type], dict):
                rich_text = tree['content'][block_type].get('rich_text', [])
                if rich_text and len(rich_text) > 0:
                    output += f"{prefix}   💬 {rich_text[0].get('plain_text', '')}"

        output += f"{icon} [{tree['type']}] ID: {tree['id']} | No: {tree['no']} | Depth: {tree['depth']}"
        logger.debug(output)

        for child in tree['children']:
            NotionPageContentSorter.print_tree(child, indent + 1, show_content)


# Entry function to get and sort Notion page content
async def get_notion_page_content(page_id: str, auto_sort=True, print_tree=False, process_block_recursive=True):
    """
    Entry function to get and sort Notion page content
    :param page_id: Page ID
    :param auto_sort: Whether to sort (default True)
    :param print_tree: Whether to print tree structure (default False)
    :param process_block_recursive: Whether to recursively get page content
    :return: {
                'raw_content': Raw content,
                'raw_order': Raw order,
                'tree': Hierarchical tree structure,
                'flat_list': Flattened list,
                'sorted_content': Sorted content
            }
    """
    try:
        page_id = rebuild_page_id(page_id)
        initial_page_ids = [page_id]

        async with GetNotionPageContent() as notion:
            # Get all page content
            await notion.process_block_recursive(initial_page_ids, process_block_recursive=process_block_recursive)

            result = {
                'raw_content': notion.notion_page_content,
                'raw_order': notion.block_order,
            }
            print_var(notion.notion_page_content, 'Page raw content', sort_dicts=False)

            if auto_sort:
                # Use sorter to reorganize content
                sorted_data = NotionPageContentSorter.sort_content(
                    notion.notion_page_content,
                    notion.block_order,
                    page_id
                )

                result.update(sorted_data)

                if print_tree:
                    logger.debug(f"{'-' * 25}'Sorted page content'{'-' * 25}")
                    NotionPageContentSorter.print_tree(sorted_data['tree'], show_content=True)

            return result
    except Exception as e:
        err = Exception(f"Exception occurred while getting page content: {e}")
        logger.error(err)
        raise err from e


# Delete Notion page content
class DeleteNotionPageContent(AsyncSendNotionRequestBaseClass):
    """Delete Notion page content"""

    def __init__(self):
        super().__init__()

    def notion_request_name(self) -> str:
        return 'Delete Block'

    async def send_request(self, block_id: str, client: AsyncClient, **kwargs):
        response = await client.blocks.delete(block_id=block_id)

        return response

    async def process_block_recursive(self, initial_block_id: str, **kwargs) -> int:
        """
        Recursively delete all blocks on the page
        :param initial_block_id: Page ID
        :param kwargs: None
        :return: Number of successfully deleted blocks
        """
        try:
            # Only get the first layer content of the page
            page_child = await get_notion_page_content(initial_block_id, auto_sort=False, process_block_recursive=False)
            page_child = page_child['raw_content']

            block_ids = [block['id'] for block in
                         page_child.get('results', [])]  # Get all child block ids of the first layer

            if not block_ids:
                logger.info(f"Page has no child blocks, no deletion needed")
                return 0

            # Delete all child blocks
            tasks = []
            for i, block_id in enumerate(block_ids):
                client_idx = i % len(self.clients)
                task = asyncio.create_task(self._rate_limited_request(client_idx, block_id))
                tasks.append(task)

            # Wait for results
            logger.info(f"Start deleting {len(block_ids)} blocks")
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Count results
            success_count = 0
            failed_count = 0

            # Statistics
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    err = Exception(f"Exception occurred while deleting block {block_ids[i]}: {result}")
                    logger.error(err)
                    raise err from result
                else:
                    success, client_idx = result
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1

            return success_count

        except Exception as e:
            err = Exception(f"Failed to delete page content: {e}")
            logger.error(err)
            raise err from e


# Entry function to delete Notion page content that stores valid links
async def delete_notion_valid_link_page_content(page_id):
    """
    :param page_id: Page id
    :return: Number of successfully deleted blocks
    """
    try:
        async with DeleteNotionPageContent() as deleter:
            deleted_count = await deleter.process_block_recursive(page_id)
            return deleted_count
    except Exception as e:
        err = Exception(f"Failed to delete Notion page content storing valid links: {e}")
        logger.error(err)
        raise err from e


# Insert valid links to Notion page
class InsertValidLinkToNotionPage(AsyncSendNotionRequestBaseClass):
    """Insert valid links to Notion page"""

    def __init__(self):
        super().__init__()

        self.max_children_per_request = 90  # Maximum 90 blocks per request, actually 100 blocks, see details: https://developers.notion.com/reference/patch-block-children

    def notion_request_name(self) -> str:
        return 'Insert Block'

    @staticmethod
    def clean_tree(node) -> dict:
        """
        Recursively clean sorted tree structure, remove process information and update callout content
        :param node: All nodes, including page information
        :return: Notion tree structure with valid information retained
        """
        node_type: str  # Node type
        node_info: dict | None  # Store block information for data insertion, see details: https://developers.notion.com/reference/patch-block-children

        if node['id'] == rebuild_page_id(get_config('notion_backup_page_id')):
            node_type = 'page'
            node_info = None  # No need to create new page
        else:
            node_type = node['type']
            node_info = node['content'][node_type]
        node_children = node['children']  # Uncleaned information of child blocks

        for idx, node_child in enumerate(node_children):  # Traverse and recursively process all child blocks
            node_children[idx] = InsertValidLinkToNotionPage.clean_tree(node_child)

        if node_type == 'callout':  # Update callout content
            # Update content according to config.yml file
            callout_content = get_config('callout_content').replace("{time}", get_formatted_time(False))
            node_info['rich_text'][0]['text']['content'] = callout_content
            node_info['rich_text'][0]['plain_text'] = callout_content

        return {'node_info': {node_type: node_info}, 'node_children': node_children}

    async def send_request(self, block_id: str, client: AsyncClient, **kwargs):
        children_info = kwargs['children_info']  # Insert all child blocks at once

        response = await client.blocks.children.append(
            block_id=block_id,
            children=children_info
        )

        return response

    def _split_children(self, children_info):
        """
        Split child block list into batches according to maximum number (90)
        :param children_info: Child block information list
        :return: Batched child block list
        """
        batches = []
        for i in range(0, len(children_info), self.max_children_per_request):
            batch = children_info[i:i + self.max_children_per_request]
            batches.append(batch)
        return batches

    async def _insert_single_level(self, tree: list[dict], parent_id: str, client_start_idx=0) -> list:
        """
        Insert single level blocks
        :param tree: Tree structure list
        :param parent_id: Parent block ID
        :param client_start_idx: Client index
        :return: List of child block ids obtained after insertion
        """
        if not tree:  # Lowest level blocks have no child nodes
            return []

        children_info = [child['node_info'] for child in tree]  # Child block information

        batches = self._split_children(children_info)  # Split into batches

        if len(batches) == 1:  # Single batch, insert directly
            client_idx = client_start_idx % len(self.clients)

            response, _ = await self._rate_limited_request(client_idx, parent_id, children_info=batches[0])
            children_ids = [block['id'] for block in response.get('results', [])]
            return children_ids
        else:
            # Multiple batches, insert concurrently
            logger.info(f"Split {len(children_info)} blocks into {len(batches)} batches for insertion")

            tasks = []
            for i, batch in enumerate(batches):
                client_idx = (client_start_idx + i) % len(self.clients)
                task = asyncio.create_task(self._rate_limited_request(client_idx, parent_id, children_info=batch))
                tasks.append(task)

            results = await asyncio.gather(*tasks)

            # Collect all batch block IDs
            all_children_ids = []
            for response, _ in results:
                batch_ids = [block['id'] for block in response.get('results', [])]
                all_children_ids.extend(batch_ids)

            return all_children_ids

    async def insert_block_recursive(self, tree: list[dict], parent_id: str, depth=0):
        """
        Recursively insert blocks and their child blocks
        :param tree: Tree structure list
        :param parent_id: Parent block ID
        :param depth: Current depth
        :return:
        """
        if not tree:
            return

        indent = "  " * depth
        logger.info(f"{indent}Level {depth} | Parent block: {parent_id} | {len(tree)} child blocks")

        # Insert all child blocks at once
        children_ids = await self._insert_single_level(tree, parent_id, client_start_idx=depth)

        # Exception handling
        if len(children_ids) != len(tree):
            err = Exception(f"{indent}Expected to insert {len(tree)} blocks, actually got {len(children_ids)} IDs")
            logger.error(err)
            raise err

        # Recursively insert all child blocks of each child block
        tasks = []
        for idx, node in enumerate(tree):
            if idx < len(children_ids) and node['node_children']:
                task = asyncio.create_task(self.insert_block_recursive(
                    node['node_children'],
                    children_ids[idx],
                    depth + 1
                ))
                tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks)

    async def process_block_recursive(self, initial_block_id, **kwargs):
        """Async processing"""
        tree = kwargs['tree']

        await self.insert_block_recursive(tree, initial_block_id)


# Entry function to insert valid links to notion page
async def insert_valid_link_to_notion_page(tree: list[dict], parent_id: str):
    """
    Entry function to insert valid links to notion page
    :param tree: Sorted tree structure
    :param parent_id: Page id
    :return:
    """
    try:
        async with InsertValidLinkToNotionPage() as inserter:
            await inserter.process_block_recursive(parent_id, tree=tree)
    except Exception as e:
        err = Exception(f"Error occurred while inserting to Notion page: {e}")
        logger.error(err)
        raise err from e
