import asyncio

from loguru import logger

from src.NotionRequest import get_notion_page_content
from src.Proxy import Proxy
from src.report import send_email
from src.until import disable_urllib3_warning, get_config, init
from src.verify_url import SendAgentBaseClass


def check_clash_config_file():
    p = Proxy()
    p.download_profile_file()


async def test_verify_url():
    disable_urllib3_warning()

    with Proxy():
        send_agents = [j for i in SendAgentBaseClass.__subclasses__() for j in i.__subclasses__()]
        for send_agent in send_agents:
            async with send_agent() as agent:
                await agent.run(['https://www.x.com'], ['Twitter'], ['test'])


def check_notion_backup_page_content():
    page_id = get_config("notion_backup_page_id")
    # Get and auto-sort
    asyncio.run(get_notion_page_content(page_id, auto_sort=True, print_tree=True))


def check_send_email():
    send_email(1, 1)


def show_menu():
    """Display the test menu and run the selected test"""
    print("\n" + "=" * 50)
    print("Test Menu".center(50))
    print("=" * 50)
    print("1. Check Clash Configuration File")
    print("2. Test URL Verification")
    print("3. Check Notion Backup Page Content")
    print("4. Check Send Email")
    print("0. Exit")
    print("=" * 50)

    choice = input("\nPlease select a test to run (0-4): ").strip()

    if choice == '1':
        logger.info("Running: Check Clash Configuration File...")
        check_clash_config_file()
        logger.info('Download successful, please check the clash/config.yaml file')
    elif choice == '2':
        logger.info("Running: Test URL Verification...")
        asyncio.run(test_verify_url())
    elif choice == '3':
        logger.info("Running: Check Notion Backup Page Content...")
        check_notion_backup_page_content()
    elif choice == '4':
        logger.info("Running: Check Send Email...")
        check_send_email()
    elif choice == '0':
        logger.info("Exiting program")
    else:
        logger.error("Invalid choice, program will exit")


def main():
    try:
        init('DEBUG', 'testProject')
        show_menu()
        logger.info("Test completed")
    except Exception as e:
        logger.exception(e)


if __name__ == '__main__':
    main()
