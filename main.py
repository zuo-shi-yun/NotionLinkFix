import asyncio

from loguru import logger

from src.NotionRequest import delete_notion_valid_link_page_content, insert_valid_link_to_notion_page, \
    get_notion_page_content, InsertValidLinkToNotionPage
from src.report import generate_html, send_email
from src.until import get_config, init, print_title, print_var
from src.verify_url import VerifyUrl, delete_invalid_block


def main():
    try:
        # Initialization
        init(log_level='INFO', log_filename='log')  # Log level set to INFO, output path: log/
        # init(log_level='DEBUG', log_filename='debug_log')  # For debugging

        # Get page content
        notion_backup_page_id = get_config("notion_backup_page_id")  # Notion ID for storing all URLs
        print_title(f'Starting to retrieve content of Notion page {notion_backup_page_id}')
        notion_backup_page = asyncio.run(  # Retrieve page content
            get_notion_page_content(
                notion_backup_page_id,
                auto_sort=True,
                print_tree=True
            )
        )
        print_title(f'Successfully retrieved content from Notion page {notion_backup_page_id}')
        # debug info
        notion_backup_page_content = notion_backup_page['sorted_content']  # Sorted page content
        print_var(notion_backup_page_content, 'Sorted page content', sort_dicts=False)
        notion_backup_page_tree = notion_backup_page['tree']  # Page tree structure
        print_var(notion_backup_page_tree, 'Sorted page tree structure', sort_dicts=False)

        # Verify links
        print_title('Starting to verify links')
        verify_url = VerifyUrl(notion_backup_page_content)
        verified_url_content = asyncio.run(verify_url.run())  # Verify URL connectivity
        # report info
        valid_urls = [i['url'] for i in verify_url.valid_urls_and_names.values()]  # Valid URLs
        valid_urls_name = [i['url_name'] for i in verify_url.valid_urls_and_names.values()]  # Valid URL names
        invalid_urls = [i['url'] for i in verify_url.invalid_urls_and_names.values()]  # Invalid URLs
        invalid_urls_name = [i['url_name'] for i in verify_url.invalid_urls_and_names.values()]  # Invalid URL names
        valid_url_cnt = len(valid_urls)
        invalid_url_cnt = len(invalid_urls)
        print_title(f'Verification complete, {valid_url_cnt} valid links, {invalid_url_cnt} invalid links')
        # Write results to HTML
        generate_html(valid_urls, valid_urls_name, invalid_urls, invalid_urls_name, 'url_check_result/check_result')

        # delete store valid notion page content
        notion_valid_link_page_id = get_config("notion_valid_link_page_id")  # Notion page ID for storing valid links
        print_title('Starting to delete content from Notion page storing valid links')
        asyncio.run(delete_notion_valid_link_page_content(notion_valid_link_page_id))  # Delete content from Notion page
        print_title('Successfully deleted content from Notion page storing valid links')

        # Delete blocks storing invalid links from the page structure
        verified_url_tree = delete_invalid_block(verified_url_content, notion_backup_page_tree)
        print_var(verified_url_content, 'Notion content after URL validation', sort_dicts=False)

        # Insert valid links into the Notion page
        print_title('Starting to insert valid links into Notion page')
        clean_tree = InsertValidLinkToNotionPage.clean_tree(verified_url_tree)  # Clean up the tree structure
        print_var(clean_tree, 'Tree structure for inserting valid links into Notion page', sort_dicts=False)
        asyncio.run(  # insert
            insert_valid_link_to_notion_page(
                tree=clean_tree['node_children'],
                parent_id=notion_valid_link_page_id
            )
        )
        print_title('Successfully inserted valid links into Notion page')

        # Send email
        if get_config("send_email"):
            send_email(valid_url_cnt, invalid_url_cnt)
            print_title('Email sent successfully')
    except Exception as e:
        logger.exception(e)
        send_email(error_email_content=f'check failed:{e}')
    finally:
        print_title('Program finished')


if __name__ == '__main__':
    main()
