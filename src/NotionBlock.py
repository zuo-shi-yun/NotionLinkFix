from abc import ABC, abstractmethod

from loguru import logger


# Notion block base class
class BlockBaseClass(ABC):
    """Notion block base class"""

    @abstractmethod
    def block_type(self) -> str:
        """
        Returns the block type, refer to: https://developers.notion.com/reference/block
        :return: str, block type
        """
        pass

    @staticmethod
    @abstractmethod
    def get_url_and_name(block) -> tuple[str, str]:
        """
        Get url and name from the block
        :param block: Raw content of notion page. Refer to structure details: https://developers.notion.com/reference/retrieve-a-block
        :return: Returns url and the text storing the url
        """
        pass

    def parse_block(self, block) -> tuple[str, str]:
        """
        Calls get_url_and_name, encapsulates logic for validating return values
        :param block:Raw content of notion page.
        :return: Returns url and the text storing the url
        """
        try:
            url, name = self.get_url_and_name(block)  # Get url, name

            if not url or not name:  # Both should not be None
                raise Exception(f"url or name is empty, url:{url}, name:{name}")

            return url, name
        except Exception as e:
            err = Exception(f"Failed to parse block {block['id']}: {e}")
            logger.error(err)
            raise err from e


# Bulleted list item block
class BulletedListItem(BlockBaseClass):
    """Bulleted list item block"""

    def block_type(self) -> str:
        return 'bulleted_list_item'  # Type: unordered list

    @staticmethod
    def get_url_and_name(block) -> tuple[str, str]:
        rich_text = block['bulleted_list_item']['rich_text']
        url = ''
        name = ''

        for i in rich_text:  # A line may contain multiple rich texts with different formats
            name = i.get('plain_text', '')
            url = i.get('href', '')

            if url is None:
                continue

            if len(url) != 0:
                break

        return url, name
