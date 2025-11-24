![NotionLinkFix](https://socialify.git.ci/zuo-shi-yun/NotionLinkFix/image?custom_description=Detect+and+update+the+validity+of+links+stored+in+Notion+pages%0A%E6%A3%80%E6%B5%8B%E5%B9%B6%E6%9B%B4%E6%96%B0%E5%AD%98%E5%82%A8%E5%9C%A8Notion%E9%A1%B5%E9%9D%A2%E4%B8%AD%E7%9A%84%E9%93%BE%E6%8E%A5%E6%9C%89%E6%95%88%E6%80%A7&description=1&logo=https%3A%2F%2Fi.postimg.cc%2Fv8XQxPmz%2Flogo.png&name=1&theme=Light)

高效的检测notion页面中存储的链接的有效性，并将有效链接存储到另一个notion页面中。

通过notion api 获得并修改notion页面内容，使用多种方式异步验证链接有效性，支持通过clash发送代理请求，以网页形式展示检测结果并将检测结果以邮件形式通知使用者。

本系统极易修改、拓展：系统使用配置文件进行管理；对notion页面相关操作高解耦；设计了异步链接验证基类。无论是修改notion相关操作，亦或是添加新的检测链接有效性方式，均极易实现。

系统的整体流程如图所示。

[![cong-cun-chu-suo-you-lian-jie-denotion-ye-mian-huo-de-lian-jie.png](https://i.postimg.cc/hGqF5xjP/cong-cun-chu-suo-you-lian-jie-denotion-ye-mian-huo-de-lian-jie.png)](https://postimg.cc/bZLFGZkK)

下载程序，开始检测你的链接有效性吧。经测试检验300个链接仅需要3分钟。

<details>

<summary>

## 快速开始

</summary>

<details>
<summary>

### 必要的准备

</summary>

<details>
<summary>

准备notion

</summary>

<details>
<summary>

notion页面规范

</summary>

- 存储所有链接的notion页面必须只包含下面的块类型，除此之外的任何块都将被忽视。
    - heading_2
    - toggle
    - divider
    - callout
    - bulleted_list_item
- 存储链接的块只能是：bulleted_list_item。
- 你可以参考这个[页面](https://www.notion.so/Store-all-links-page-2b5e8041ffd4804ea38de68cd79c1bf2?pvs=21)
  来设计你的页面，页面内的任何文本格式、块顺序都将完整的保留到存储有效链接的notion页面。
- 若你希望notion存储更多的块类型或使用其他块类型来存储链接，请参考“拓展系统/notion相关修改”。

</details>

<details>
<summary>

准备notion api key并关联notion页面

</summary>

- 系统将通过notion api key进行notion页面操作，申请流程参阅[这里](https://developers.notion.com/reference/capabilities)。
- 申请成功后，记录api
  key并将key和存储所有链接的notion页面、存储有效链接的notion页面关联。关联流程参阅[这里](https://developers.notion.com/docs/create-a-notion-integration#give-your-integration-page-permissions)。
- 每个key每秒最多发送2个请求，因此可以通过申请并关联多个key提高并发效率。经实测，两个key就可以达到较高的效率，超过4个key后效率无明显提升。
-

记录两个页面的id，查询id流程参阅[这里](https://developers.notion.com/docs/working-with-page-content#creating-a-page-with-content)
的”Where can I find my page's ID?”章节。

</details>
</details>

<details>
<summary>

准备代理

</summary>

- 若你希望通过代理检测链接有效性，你还需要一个vpn，该vpn需提供支持clash的yaml配置文件。

</details>

<details>
<summary>

准备邮箱

</summary>

- 如果你希望将检测结果以邮件形式通知你，你需要获得邮箱的授权码等信息。<br> 这些信息包括：
    - 邮箱地址
    - 邮箱密码/授权码
    - 邮箱SMTP服务器地址
    - 邮箱SMTP服务器端口
- 如果你不知道如何获得这些信息，你可以查询“如何通过SMTP向XX邮箱发送邮件”。
- 如果你希望通过其他方式发送邮件，请参阅“拓展系统/修改邮件发送方式”。
- 如果你不希望发送邮件，可以忽视本项准备。

</details>
</details>

<details>
<summary>

### 部署系统

</summary>

<details>
<summary>

选择适合你的版本

</summary>

- 系统提供三个发行版，分别为：
    - Windows x64系统下的可执行文件版
    - Windows x64系统下的源码版
    - Linux amd 64系统下的源码版
- 请根据你的需要下载合适的发行版本。
- 若你希望修改代码，请注意，系统的**最低python版本要求为3.11。**
- 无论哪个发行版都自带clash内核，无需额外下载。
- 若你希望在其他系统下使用本项目或使用其他clash内核，请参阅“拓展系统/修改clash版本”。

</details>

<details>
<summary>

部署并测试

</summary>

1. 下载发行版或克隆本仓库中对应你的操作系统的分支。<br>若你下载的是源码版还需要安装`requirements.txt`中的依赖，请注意，系统的
   **最低python版本要求为3.11。**
2. 配置clash代理。<br>若你不希望通过代理发送请求，请将`config.yml`文件中的`enable_proxy`设为`False`，并忽略本项接下来的内容。
    1. 修改`config.yml`文件的`clash_profile_url`值。
    2. 运行`test.exe`或`test.py`文件，并选择选项1。
    3. clash配置文件下载成功后，请查看`clash/config.yaml`文件并据此修改`*Clash-related Configuration*`配置项中的其余配置。
    4. 配置完成后再次运行`test`并选择选项2，该测试将检测`x.com`的连通性，正常情况下，将至少有一个检测方式的检测结果为真。请观察输出以检测代理是否配置正常。
3. notion相关配置：
    1. 使用在“必要的准备/准备notion”中获得api key和页面id，完成`config.yml`文件中的`*Notion-related Configuration*`下的配置项。
    2. 运行`test`并选择选项3，系统将以可视化的形式输出存储所有链接的notion页面内容，观察输出结果以检查是否配置正确。
4. 配置邮件发送功能。<br>若你不希望发送邮件，请将`config.yml`文件中的`send_email`设为`False`，并忽略本项接下来的内容。
    1. 使用在“必要的准备/准备邮箱”中获得的邮箱相关信息，完成`config.yml`文件中的`*Email-related Configuration*`配置项下的所有配置。
    2. 运行`test`并选择选项4，系统将发送邮件到你指定的邮箱。观察输出并查看邮箱以检测是否配置正确。
5. 第一次运行：
    1. 运行`NotionLinkFix.exe`或`main.py`文件，系统将运行完整的检测流程。
    2. 检测结束后，查看`url_check_result`目录下的html格式的检测结果，点击`INVALID LINKS`查看无效链接。
    3. 因部分网站的反爬能力较强，系统可能误判该网址为无效。<br>
       若你确定这是误判，请复制链接并将其粘贴到`config.yml`文件中`*Link Verification-related Configuration*`配置项下的
       `ignore_validity_check_url`中。<br>
       配置在该项中的链接，无论检测结果如何都将视为可联通。该项支持添加多个链接。

6. 项目部署成功。你可以将设置设为定时任务以定期检测链接的有效性。
7. 若你后续再次添加新的链接，请将其添加到**存储所有链接的notion页面中**。添加到存储有效链接的notion页面中是**无效的**。

   你也可以运行`test`的选项5，输入你新添加的链接，以检查系统是否可以正确检测其连通性。

</details>
</details>

</details>

<details>
<summary>

## 拓展系统

</summary>
默认分支为windows系统，若你希望在linux系统下使用本项目请切换到linux分支。
<details>
<summary>

修改日志等级、变量输出

</summary>

- 系统使用loguru管理日志，默认日志等级为INFO。
- 系统运行时的过程变量输出等级为DEBUG，若你希望查看这些变量，请修改`main.py`文件中的第15行的`init`函数中的日志等级。
    - 你还可以修改`init`函数的`log_filename`参数以修改日志文件名。
- 因系统运行过程中会产生大量存储notion结构的树变量，这些树的输出可能十分庞大从而导致日志混乱，你可以修改`until.py`文件中的
  `print_var`函数，该函数的`var_dict`变量记录了系统运行过程中所产生的所有过程变量的信息以及是否输出，你可以查看
  `description`的值并修改`print`的值以保证只输出你希望查看的变量。
    - 你也可以调用该函数来输出你自己的变量，该函数采用保守策略，只会不输出`print`的值为`False`的变量，因此在输出你的变量时无需将变量保存到
      `var_dict`中。

</details>

<details>
<summary>

修改clash版本

</summary>

-

windows分支中的clash内核版本为win64，linux分支中的clash内核版本为linux-amd64，若你希望使用其他版本的内核，可以参阅[这里](https://www.clash.la/archives/755/)。

- 无论哪个版本，请注意选择**Clash Premium**的内核，只有这些内核支持通过api控制clash。
- 请将你的clash内核放置在`clash`目录下，并记录文件名。
- 修改`Proxy.py`文件的`Proxy`类中的`*self*.clash_path`变量，该值为上一步中记录的clash内核文件名。
- 运行`test`的选项2，以检测是否修改成功。
- 如果代理无法启动，你可能还需要修改`Proxy`类中的`change_clash_proxy`，`open_clash_proxy`和`close_clash_proxy`函数。

</details>

<details>
<summary>

添加新的链接验证方式

</summary>
存储在`verify_url.py`文件中的链接验证方式设计精良，只需要继承对应的基类并实现一些必要且简单的抽象函数，程序将自动调用你的类并检测链接的连通性，你无需关注验证逻辑。
若你的验证方式原生支持异步，请继承`AsyncSendAgentBaseClass`类，反之继承`ThreadedSendAgentBaseClass`类。
程序有完善的异常管理措施，除非某个异常是你预期出现的，那么你可以不使用任何`try`块。随意的`try`块可能导致程序错误的判断链接是否有效。
<details>
<summary>

链接验证基类：`SendAgentBaseClass`

</summary>

这是`AsyncSendAgentBaseClass`和`ThreadedSendAgentBaseClass`的基类，封装了验证链接逻辑(`run`函数)并提供了一些工具方法。

你需要实现下面这些抽象函数，详细设计请参阅源码。

1. `send_agent_name`函数：用于设置你的验证方式的名称，该函数用于日志输出。请直接返回你的验证方式名称。
2. `is_response_valid`函数：通过`response, url_name`参数判断请求的响应是否有效。
    - `response`参数不会为异常，该参数的类型是你发送的请求的响应类型。
    - 你可以实现你自己的检测逻辑，如响应中是否包含`url_name`，响应是否被Cloudflare等反爬虫机制拦截。
    - 最简单的方式是判断响应状态码是否在`*self*.correct_status_code`中。原有的程序均是如此设计的。

可能帮到你的类属性：

1. `*self*.proxy`：记录了`config.yml`文件中的代理配置。
2. `*self*.timeout`：请求超时时间。超过该值的请求将被视为请求失败。
3. `*self*.USER_AGENTS`：存储了一些用于请求头的用户客户端，将在`get_random_headers`函数中调用。
4. `*self*.certificate_verification`：记录了`config.yml`文件中的是否忽略证书验证的配置项。
5. `*self*.correct_status_code`：代表成功响应的状态码。

可能帮到你的类方法：

- `get_random_headers`：获得随机的请求头。用于使请求更真实。

</details>

<details>
<summary>

异步验证基类：`AsyncSendAgentBaseClass`

</summary>

若你的检测方式原生支持异步，请继承该类并实现其中的抽象方法，详细设计参阅源码。

该类使用信号量限制并发，多个协程共享同一个请求客户端，并封装了异步上下文管理器。

除`SendAgentBaseClass`中的抽象方法，你还需要实现下面这些抽象方法。

1. `set_send_agent`函数：将你的请求客户端赋值给`*self*.agent`。
    - 如`httpx.AsyncClient`
2. `close_send_agent`函数：关闭`*self*.agent`。将在异步上下文出口调用。
3. `send_request`函数：通过`*self*.agent`属性发送请求，并返回请求结果。
    - 你需要实现有代理请求和无代理请求。通过`enable_proxy`参数判断。
    - 在发送请求时，你可能还需要注意下面的配置：
        1. 请求超时时间。可以传递`*self*.timeout`参数。
        2. 是否忽略证书验证。可以传递`*self*.certificate_verification`参数。
        3. 是否允许重定向。
        4. 设置请求头。可以通过调用`get_random_headers`方法获得随机请求头。
        5. 设置请求代理。
    - 请注意，当该函数运行时间超过`*self*.task_timeout`时将被视为请求失败，该值为`*self*.timeout`的三倍。

</details>

<details>
<summary>

同步验证基类：`ThreadedSendAgentBaseClass`

</summary>

若你的检测方式仅支持同步，请继承该类并实现其中的抽象方法，详细设计参阅源码。

该类使用线程池模拟异步，并通过限制线程池大小管理并发，为每个线程提供不同的请求客户端，并封装了异步上下文管理器。

除`SendAgentBaseClass`中的抽象方法，你还需要实现下面这些抽象方法。

1. `get_send_agent`函数：直接返回你的请求方式客户端。将在每个线程第一次创建时调用。
    - 如`requests.Session()`
2. `close_one_agent`函数：关闭通过`agent`参数传递的客户端。将在异步上下文出口调用。
3. `send_request`函数：通过本方法的参数`agent`发送请求，并返回请求结果。
    - 你需要实现有代理请求和无代理请求。通过`enable_proxy`参数判断。
    - 在发送请求时，你可能还需要注意下面的配置：
        1. 请求超时时间。可以传递`*self*.timeout`参数。
        2. 是否忽略证书验证。可以传递`*self*.certificate_verification`参数。
        3. 是否允许重定向。
        4. 设置请求头。可以通过调用`get_random_headers`方法获得随机请求头。
        5. 设置请求代理。
    - 请注意，当该函数运行时间超过`*self*.task_timeout`时将被视为请求失败，该值为`*self*.timeout`的三倍。

</details>

</details>

<details>
<summary>

notion相关修改

</summary>
因notion设计较为复杂，导致不易修改notion相关操作，尽管项目尽可能的隐去了具体的操作逻辑，但你仍需仔细阅读[notionAPI设计](https://developers.notion.com/reference/intro)。
<details>
<summary>

修改应该出现在notion页面中的块

</summary>

- 若你希望添加应该出现在notion页面中的块，请修改`until.py`文件中的`is_block_should_in_page`函数。详细设计参阅源码。
- 全部块类型参阅[这里](https://developers.notion.com/reference/block)。
- 若这些块用于存储链接，你还需要阅读”添加notion页面中存储链接的块类型”
- 若链接的检测结果为无法连通，程序将删除这些块，此操作可能导致notion页面中出现没有存储任何链接的块。系统通过调用存储在
  `verify_url.py`文件中的`delete_invalid_block`函数来删除这些空块。因此，你可能也需要修改该函数来实现对空块的删除。

</details>

<details>
<summary>

添加notion页面中存储链接的块类型

</summary>

- 首先请阅读“修改应该出现在notion页面中的块”。
- 请继承并实现存储在`NotionBlock.py`文件中的`BlockBaseClass`类并实现其抽象方法。详细设计参阅源码。
- 系统将自动调用你的类并获取存储在块中的链接，你无需关注调用逻辑。
- 请注意，`Link previews`块的操作十分复杂，详情参阅[这里](https://developers.notion.com/docs/link-previews)。

</details>

<details>
<summary>

更复杂的操作

</summary>

- 若你希望更换发送notion api请求的方式，或你希望实现更复杂的页面操作(如添加对link preview块的支持)，那么你可能需要大面积修改代码。
- 也许存储在`NotionRequests.py`文件中的`AsyncSendNotionRequestBaseClass`类会起到帮助，该类封装了发送带重试机制和速率限制的多批次异步请求方法。

</details>

</details>

<details>
<summary>

修改邮件发送方式

</summary>

- 系统使用`smtplib`发送邮件。
- 若你希望使用其他方式，如调用第三方api等，请修改存储在`report.py`文件中的
  `send_email`函数。

</details>


</details>
