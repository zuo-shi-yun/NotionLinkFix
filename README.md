![NotionLinkFix](https://socialify.git.ci/zuo-shi-yun/NotionLinkFix/image?custom_description=Detect+and+update+the+validity+of+links+stored+in+Notion+pages%0A%E6%A3%80%E6%B5%8B%E5%B9%B6%E6%9B%B4%E6%96%B0%E5%AD%98%E5%82%A8%E5%9C%A8Notion%E9%A1%B5%E9%9D%A2%E4%B8%AD%E7%9A%84%E9%93%BE%E6%8E%A5%E6%9C%89%E6%95%88%E6%80%A7&description=1&logo=https%3A%2F%2Fi.postimg.cc%2Fv8XQxPmz%2Flogo.png&name=1&theme=Light)
[English](README.md)|[简体中文](README-ZH.md) <br>
Efficiently check the validity of links stored in a Notion page and store the valid links in another Notion page.

Using the Notion API to retrieve and modify Notion page content, the system verifies the validity of links
asynchronously using multiple methods, supports sending proxy requests via Clash, displays the test results in a web
format, and notifies the user via email with the results.

This system is highly flexible and extensible: it uses configuration files for management; operations related to Notion
pages are highly decoupled; and an asynchronous link validation base class has been designed. Whether modifying
Notion-related operations or adding new link validation methods, both are easily achievable.

The overall workflow of the system is shown in the diagram below.

[![Obtain-links-from-the-Notion-page-that-stores-all-the-links.png](https://i.postimg.cc/3wv3VYYw/Obtain-links-from-the-Notion-page-that-stores-all-the-links.png)](https://postimg.cc/FfhtJtft)
Download the program and start checking the validity of your links. Testing 300 links only takes 3 minutes.

<details>

<summary>

## Quick Start

</summary>

<details>
<summary>

### Necessary Preparation

</summary>

<details>
<summary>Prepare Notion</summary>

<details>
<summary>Notion Page Guidelines</summary>

- The Notion page that stores all the links must only contain the following block types. Any other blocks will be
  ignored.
    - heading_2
    - toggle
    - divider
    - callout
    - bulleted_list_item
- The block used to store links must be of type: bulleted_list_item.
- You can refer to this [page](https://www.notion.so/Store-all-links-page-2b5e8041ffd4804ea38de68cd79c1bf2?pvs=21)
  to design your page, any text formatting and block order within the page will be fully preserved when storing valid
  links in the Notion page.
- If you wish for Notion to store more block types or use other block types to store links, please refer to the "Expand
  System / Notion-Related Modifications".

</details>

<details>
<summary>Prepare the Notion API key and link it to the Notion page.</summary>

- The system will perform Notion page operations using the Notion API key. For the application process, refer
  to [here](https://developers.notion.com/reference/capabilities)。
- Once the application is successful, record the API key and associate it with the Notion page storing all the links and
  the Notion page storing the valid links. For the association process, refer
  to [here](https://developers.notion.com/docs/create-a-notion-integration#give-your-integration-page-permissions)
- Each API key can send a maximum of 2 requests per second, so by applying for and associating multiple keys, you can
  increase concurrency efficiency. Based on testing, two keys are sufficient to achieve high efficiency, and there is no
  significant improvement in efficiency when using more than four keys.
- Record the IDs of the two pages. For the process of querying the ID, refer
  to [here](https://developers.notion.com/docs/working-with-page-content#creating-a-page-with-content)of the "Where can
  I find my page's ID?" section.

</details>
</details>

<details>
<summary>Prepare the proxy</summary>

- If you wish to verify link validity through a proxy, you will also need a VPN that provides a YAML configuration file
  compatible with Clash.

</details>

<details>
<summary>Prepare the email account.</summary>

- If you want to receive the test results via email, you will need to obtain the authorization code and other relevant
  information for your email account.
  <br> This information includes:
    - Email address
    - Email password/authorization code
    - Email SMTP server address
    - Email SMTP server port
- If you're unsure how to obtain this information, you can search for "How to send emails via SMTP to XX email
  provider."
- If you wish to send emails through other methods, please refer to "Expand System / Modify Email Sending Method".
- If you do not wish to send emails, you can ignore this preparation step.

</details>
</details>

<details>
<summary>

### Deploy the system

</summary>

<details>
<summary>Choose the version that suits you</summary>

- The system provides three release versions, namely:
    - Executable version for Windows x64 system
    - Source version for Windows x64 system
    - Source version for Linux amd64 system
- Please download the appropriate release version based on your needs.
- If you wish to modify the code, please note that the system's**minimum Python version requirement is 3.11.**
- All release versions come with the Clash core, so there is no need to download it separately.
- If you wish to use this project on other systems or with a different Clash core, please refer to "Expand System /
  Modify Clash Version."

</details>

<details>
<summary>Deploy and test the system</summary>

1. Download the release version or clone the branch corresponding to your operating system from this repository.<br>
   If you downloaded the source version, you will also need to install the`requirements.txt`dependencies. Please note
   that the system's**minimum Python version requirement is 3.11**
2. Configure the Clash proxy.<br>If you do not want to send requests through a proxy, set `enable_proxy` in the
   `config.yml` file to `False` and ignore the rest of this entry.
    1. Modify the value of `clash_profile_url` in the `config.yml` file.
    2. Run the `test.exe` or `test.py` file and select option 1.
    3. After the clash configuration file has been downloaded successfully, review the `clash/config.yaml` file and
       modify the rest of the configuration in the `*Clash-related Configuration*` configuration item accordingly.
    4. Once the configuration is complete, run `test` again and select option 2. This test will check the connectivity
       of `x.com`, and normally at least one of the tests will come back true. Please observe the output to test if the
       agent is configured properly.
3. Notion-related configuration:
    1. Use the api key and page id obtained in "Necessary Preparation/Preparation of Notion" to complete the
       configuration under `*Notion-related Configuration*` in the `config.yml` file.
    2. Run `test` and select option 3, the system will output the content of the notification page that stores all
       the links in a visual form, observe the output to check if the configuration is correct.
4. Configure the email sending function.
   <br>
   If you do not want to send email, set `send_email` to `False` in the `config.yml` file and ignore the rest of
   this entry.
    1. Complete all configurations under `*Email-related Configuration*` in the `config.yml` file, using the
       mailbox-related information you obtained in Necessary Preparation/Preparing Mailboxes.
    2. Run `test` and select option 4 to send an email to the mailbox you specified. Observe the output and check
       the mailbox to see if the configuration is correct.
5. First run:
    1. Run the `NotionLinkFix.exe` or `main.py` file and the system will run the complete detection process.
    2. After the detection is finished, check the detection result in html format in the `url_check_result`
       directory and click `INVALID LINKS` to view the invalid links.
    3. Due to the strong anti-crawling ability of some websites, the system may misjudge the URL as invalid.

       If you are sure that this is a false positive, copy the link and paste it into the
       `ignore_validity_check_url` under `*Link Verification-related Configuration*` in the `config.yml` file.

       Links configured in this item will be considered connectable regardless of the test results. This item
       supports adding multiple links.

6. The project is successfully deployed. You can set the setting to a timed task to periodically check the validity
   of links.
7. If you add a new link later, add it to **the notification page where all links are stored**. Adding to the
   notification page where valid links are stored is **not effective**.

   You can also run option 5 of `test` and enter your newly added link to check if the system can correctly detect
   its connectivity.

</details>
</details>

</details>

<details>
<summary>

## Branching Systems

</summary>
The default branch is windows, if you want to use this project under linux system please switch to linux branch.
<details>
<summary>Modify log level, variable output</summary>

- The system uses loguru to manage logs, and the default log level is INFO.
- The default logging level is INFO. The output level of the runtime process variables is DEBUG. If you want to see
  these variables, please modify the logging level in the `init` function on line 15 of the `main.py` file.
    - You can also modify the `log_filename` parameter of the `init` function to change the log file name.
- Because the system will generate a large number of tree variables to store the structure of the notion, the output of
  these trees may be very large and thus lead to confusion in the log, you can modify the `print_var` function in the
  `until.py` file, the `var_dict` variable of the function records the information of all the process variables
  generated by the system during operation and whether they are output or not, you can check the value of the You can
  view the value of `description` and modify the value of `print` to ensure that only the variables you wish to view are
  output.
    - You can also call this function to output your own variables. This function uses a conservative policy of not
      outputting variables for which the value of `print` is `False`, so you don't need to save your variables to
      `var_dict` when you output them.

</details>

<details>
<summary>Changing the clash version</summary>

- The version of the clash kernel in the windows branch is win64 and the version of the clash kernel in the linux branch
  is linux-amd64, if you wish to use another version of the kernel, see [here](https://www.clash.la/archives/755/).
    - Regardless of the version, please make sure to choose the **Clash Premium** kernel **,** only these kernels
      support
      clash control via api.
- Please place your clash kernel in the `clash` directory and record the filename.
- Modify the `*self*.clash_path` variable in the `Proxy` class of the `Proxy.py` file to the value of the clash kernel
  filename recorded in the previous step.
- Run option 2 of `test` to check if the modification was successful.
- You may also need to modify the `change_clash_proxy`, `open_clash_proxy`, and `close_clash_proxy` functions in the
  `Proxy` class if the proxy fails to start.

</details>

<details>
<summary>Add a new link validation method</summary>
The link validation methods stored in the `verify_url.py` file are well-designed, you only need to inherit from the corresponding base class and implement some necessary and simple abstract functions, the program will automatically call your class and check the connectivity of the link, you do not need to pay attention to the validation logic.

If your authentication method natively supports asynchronous , please inherit `AsyncSendAgentBaseClass` class ,
otherwise inherit `ThreadedSendAgentBaseClass` class .

Programs have well-established exception management measures, unless a particular exception is one you expect to occur,
then you may not use any `try` blocks. Arbitrary `try` blocks can cause the program to incorrectly determine whether a
link is valid or not.
<details>
<summary>Link validation base class: `SendAgentBaseClass`</summary>

This is the base class for `AsyncSendAgentBaseClass` and `ThreadedSendAgentBaseClass` that encapsulates the link
validation logic (`run`function) and provides some utility methods.

You need to implement the following abstract functions, please refer to the source code for detailed design.

1. `send_agent_name` function: used to set the name of your authentication method, this function is used for log output.
   Please return the name of your authentication method directly.
2. `is_response_valid` function: use `response, url_name` parameter to determine whether the response of the request is
   valid or not.
    - The `response` parameter will not be an exception, the type of the parameter is the type of response you sent to
      the request.
    - You can implement your own detection logic, such as whether the response contains `url_name`, whether the response
      is Cloudflare and other anti-crawler mechanism to intercept.
    - The simplest way is to determine if the response status code is in `*self*.correct_status_code`. This is how the
      original program is designed.

Class properties that may help you:

1. `*self*.proxy`: records the proxy configuration in the `config.yml` file.
2. `*self*.timeout`: the request timeout. Requests exceeding this value will be treated as request failures.
3. `*self*.USER_AGENTS`: stores a number of user clients to be used for request headers, which will be called in the
   `get_random_headers` function.
4. `*self*.CERTIFICATE_VERIFICATION`: records whether to ignore certificate verification configuration items in the
   `config.yml` file.
5. `*self*.correct_status_code`: status code representing a successful response.

Class methods that may help you:

- `get_random_headers`: get random request headers. Used to make requests more authentic.

</details>

<details>
<summary>Asynchronous validation base class:`AsyncSendAgentBaseClass`</summary>

If your inspection method supports asynchrony natively, please inherit this class and implement the abstract methods in
it, refer to the source code for detailed design.

This class uses semaphores to limit concurrency, multiple concurrent programs sharing the same request client, and
encapsulates an asynchronous context manager.

In addition to the abstract methods in `SendAgentBaseClass`, you need to implement the following abstract methods.

1. `set_send_agent` function: assigns your request client to `*self*.agent`.
    - E.g. `httpx.AsyncClient`
2. `close_send_agent` function: closes `*self*.agent`. will be called on asynchronous context exit.
3. `send_request` function: sends a request through the `*self*.agent` property and returns the request result.
    - You need to implement both proxied and unproxied requests. This is determined by the `enable_proxy` parameter.
    - You may also need to pay attention to the following configurations when sending requests:
        1. Request timeout time. You can pass the `*self*.timeout` parameter.
        2. Whether to ignore certificate validation. The `*self*.certificate_verification` parameter can be passed.
        3. Whether to allow redirection.
        4. Set request headers. Random request headers can be obtained by calling the `get_random_headers` method.
        5. Set the request proxy.
    - Note that the request is considered to have failed when the function runs longer than `*self*.task_timeout`, which
      is three times `*self*.timeout`.

</details>

<details>
<summary>Synchronized validation base class:`ThreadedSendAgentBaseClass`</summary>

If your detection method only supports synchronous, please inherit this class and implement the abstract methods in it,
refer to the source code for detailed design.

This class uses a thread pool to simulate asynchrony and manages concurrency by limiting the thread pool size, providing
a different request client for each thread, and encapsulating an asynchronous context manager.

In addition to the abstract methods in `SendAgentBaseClass`, you need to implement the following abstract methods.

1. `get_send_agent` function: returns your request method client directly. Will be called when each thread is first
   created.
    - Such as `requests.Session()`
2. `close_one_agent` function: closes the client passed via the `agent` parameter. Will be called on asynchronous
   context exit.
3. `send_request` function: sends a request via the `agent` parameter of this method and returns the request result.
    - You need to implement both proxied and unproxied requests. This is determined by the `enable_proxy` parameter.
    - You may also need to pay attention to the following configurations when sending requests:
        1. Request timeout time. You can pass the `*self*.timeout` parameter.
        2. Whether to ignore certificate validation. The `*self*.certificate_verification` parameter can be passed.
        3. Whether to allow redirection.
        4. Set request headers. Random request headers can be obtained by calling the `get_random_headers` method.
        5. Set the request proxy.
    - Note that the request is considered to have failed when the function runs longer than `*self*.task_timeout`, which
      is three times `*self*.timeout`.

</details>

</details>

<details>
<summary>Notion Related Changes</summary>
Because of the complexity of the notion design, it is not easy to modify the notion-related operations. Although the project has tried to hide the specific operation logic as much as possible, you still need to read [the notionAPI design](https://developers.notion.com/reference/intro) carefully.
<details>
<summary>Modifying blocks that should appear in a notification page</summary>

- If you want to add a block that should appear in the notion page, please modify the `is_block_should_in_page` function
  in the `until.py` file. See the source code for the detailed design.
- See [here](https://developers.notion.com/reference/block) for the full list of block types.
- If these blocks are used to store links, you will also need to read "Adding block types for storing links in
  notification pages".
- If a link is detected as unreachable, the program will delete these blocks, which may result in a notification page
  with no links stored in it. The system removes these empty blocks by calling the `delete_invalid_block` function
  stored in the `verify_url.py` file. Therefore, you may also need to modify this function to enable the deletion of
  empty blocks.

</details>

<details>
<summary>Adding the block type for storing links in the notification page</summary>

- First read "Modifying the blocks that should appear in the notion page".
- Inherit and implement the `BlockBaseClass` class stored in the `NotionBlock.py` file and implement its abstract
  methods. Refer to the source code for detailed design.
- The system will automatically call your class and fetch the links stored in the block, you don't need to pay attention
  to the call logic.
- Please note that the `Link previews` block is very complex to operate,
  see [here](https://developers.notion.com/docs/link-previews) for details.

</details>

<details>
<summary>More complex operations</summary>

- If you want to change the way you send your notion api requests, or if you want to implement more complex page
  operations (e.g. adding support for the link previews block), then you may need to make some extensive code changes.
- Perhaps the `AsyncSendNotionRequestBaseClass` class stored in the `NotionRequests.py` file, which encapsulates the
  method for sending multi-batch asynchronous requests with a retry mechanism and rate limiting, will help.

</details>

</details>

<details>
<summary>Modifying the mail sending method</summary>

- The system uses `smtplib` to send mail.
- If you wish to use another method, such as calling a third-party api, modify the `send_email` function stored in the
  `report.py` file.

</details>


</details>
