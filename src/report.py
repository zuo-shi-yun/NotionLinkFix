import email.utils
import html
import os
import smtplib
from email.mime.text import MIMEText

from loguru import logger

from .until import get_formatted_time, get_config, print_title


# Send email
def send_email(valid_url_cnt=0, invalid_url_cnt=0, error_email_content=None):
    """
    Send email
    :param valid_url_cnt: Number of valid links
    :param invalid_url_cnt: Number of invalid links
    :param error_email_content: Whether it is an error report email
    :return:
    """
    try:
        email_addr = get_config('email_addr')
        email_password = get_config('email_password')

        # Set email information based on config.yml file content
        email_content: str = get_config('email_content')
        email_content = (email_content.replace('{valid_url_cnt}', str(valid_url_cnt))
                         .replace('{all_url_cnt}', str(invalid_url_cnt + valid_url_cnt)))

        # Configure email information
        message = MIMEText(error_email_content or email_content)
        message['To'] = email.utils.formataddr(('User', email_addr))
        message['From'] = email.utils.formataddr(('NotionLinkFix', email_addr))
        message['Subject'] = 'Running result'

        # Send email
        email_host = get_config('email_host')
        email_port = get_config('email_port')
        server = smtplib.SMTP_SSL(email_host, email_port)
        server.login(email_addr, email_password)

        server.sendmail(email_addr, [email_addr], msg=message.as_string())
    except Exception as e:
        err = Exception(f"Failed to send email: {e}")
        logger.error(err)
        raise err from e


def generate_html(valid_links: list[str], valid_links_name: list[str], invalid_links: list[str],
                  invalid_links_name: list[str], filename: str):
    """
    Generate HTML report
    :param valid_links: Valid links list
    :param valid_links_name: Valid links name list
    :param invalid_links: Invalid links list
    :param invalid_links_name: Invalid links name list
    :param filename: HTML file path, without .html suffix
    :return: None
    """
    try:
        filename += '_' + get_formatted_time() + '.html'
        file_dir = os.path.dirname(filename)

        # Create directory
        if file_dir and not os.path.exists(file_dir):
            os.makedirs(file_dir)

        # Escape and generate link list
        def escape_link(link):
            return html.escape(str(link))

        def generate_link_items(links, links_name, item_class):
            """Generate link list items"""
            items = []
            for idx, link in enumerate(links):
                escaped_link = escape_link(link)
                items.append(f'''
                    <li class="{item_class}">
                        <a href="{escaped_link}" target="_blank" rel="noopener noreferrer" class="link-text" title="{escaped_link}">
                            {links_name[idx]}
                        </a>
                        <button class="open-btn" onclick="window.open('{escaped_link}', '_blank')" title="Open link">
                            🔗 Open Link
                        </button>
                        <button class="copy-btn" onclick="copyToClipboard('{escaped_link}', this)" title="Copy link">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                            </svg>
                            <span class="copy-text">Copy</span>
                        </button>
                    </li>
                ''')
            return '\n'.join(items)

        valid_items = generate_link_items(valid_links, valid_links_name, 'valid-item')
        invalid_items = generate_link_items(invalid_links, invalid_links_name, 'invalid-item')

        # HTML template
        html_content = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Link Validation Results</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            html {{
                scroll-behavior: smooth;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 40px 20px;
            }}
            
            .report-time {{
                text-align: center;
                color: #6c757d;
                font-size: 1.1em;
                margin-top: -20px;
                margin-bottom: 30px;
            }}
            
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: #ffffff;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            }}
            
            h1 {{
                text-align: center;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                font-size: 2.5em;
                margin-bottom: 40px;
                font-weight: 700;
                letter-spacing: -1px;
            }}
            
            .summary {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 40px;
            }}
            
            .summary-card {{
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                padding: 30px;
                border-radius: 16px;
                text-align: center;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
                cursor: pointer;
                text-decoration: none;
            }}
            
            .summary-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
            }}
            
            .summary-card.valid {{
                background: linear-gradient(135deg, #d4edda 0%, #a3d5a8 100%);
            }}
            
            .summary-card.invalid {{
                background: linear-gradient(135deg, #f8d7da 0%, #f5a3a3 100%);
            }}
            
            .summary-number {{
                font-size: 3em;
                font-weight: 700;
                margin-bottom: 10px;
                line-height: 1;
            }}
            
            .summary-card.valid .summary-number {{
                color: #155724;
            }}
            
            .summary-card.invalid .summary-number {{
                color: #721c24;
            }}
            
            .summary-card.total .summary-number {{
                color: #495057;
            }}
            
            .summary-label {{
                color: #495057;
                font-size: 1.1em;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            
            .search-box {{
                margin-bottom: 30px;
                position: relative;
            }}
            
            .search-box input {{
                width: 100%;
                padding: 16px 50px 16px 20px;
                border: 2px solid #e9ecef;
                border-radius: 12px;
                font-size: 1.05em;
                transition: all 0.3s ease;
                background: #f8f9fa;
            }}
            
            .search-box input:focus {{
                outline: none;
                border-color: #667eea;
                background: #ffffff;
                box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
            }}
            
            .search-icon {{
                position: absolute;
                right: 20px;
                top: 50%;
                transform: translateY(-50%);
                color: #6c757d;
            }}
            
            .section {{
                margin-bottom: 50px;
            }}
            
            .section-header {{
                font-size: 1.5em;
                color: #212529;
                margin-bottom: 20px;
                padding: 15px 20px;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                border-radius: 12px;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            
            .section-header.valid {{
                background: linear-gradient(135deg, #d4edda 0%, #a3d5a8 100%);
                color: #155724;
            }}
            
            .section-header.invalid {{
                background: linear-gradient(135deg, #f8d7da 0%, #f5a3a3 100%);
                color: #721c24;
            }}
            
            .links-list {{
                list-style: none;
                display: grid;
                gap: 12px;
                width: 100%;
            }}
            
            .valid-item, .invalid-item {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 16px 20px;
                border-radius: 10px;
                transition: all 0.3s ease;
                gap: 15px;
                background: #ffffff;
                border: 2px solid transparent;
                max-width: 100%;
                width: 100%;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
            
            .valid-item {{
                background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
                border-left: 5px solid #28a745;
            }}
            
            .invalid-item {{
                background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
                border-left: 5px solid #dc3545;
            }}
            
            .valid-item:hover {{
                transform: translateX(8px);
                box-shadow: 0 4px 20px rgba(40, 167, 69, 0.2);
                border-color: #28a745;
            }}
            
            .invalid-item:hover {{
                transform: translateX(8px);
                box-shadow: 0 4px 20px rgba(220, 53, 69, 0.2);
                border-color: #dc3545;
            }}
            
            .link-text {{
                flex: 1;
                text-decoration: none;
                font-weight: 500;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                min-width: 0;
                max-width: 100%;
                display: block;
            }}
            
            .valid-item .link-text {{
                color: #155724;
            }}
            
            .invalid-item .link-text {{
                color: #721c24;
            }}
            
            .link-text:hover {{
                color: #667eea;
            }}
            
            .open-btn, .copy-btn {{
                flex-shrink: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 0.9em;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 6px;
                transition: all 0.3s ease;
                box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
                white-space: nowrap;
            }}
            
            .open-btn:hover, .copy-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
                background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
            }}
            
            .open-btn:active,.copy-btn:active {{
                transform: translateY(0);
            }}
            
            .copy-btn.copied {{
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            }}
            
            open-btn svg, .copy-btn svg {{
                flex-shrink: 0;
            }}
            
            .open-btn {{
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            }}
    
            .open-btn:hover {{
                background: linear-gradient(135deg, #20c997 0%, #28a745 100%);
            }}
            
            .no-results {{
                text-align: center;
                color: #6c757d;
                padding: 40px;
                font-size: 1.1em;
                font-style: italic;
            }}
            
            @keyframes fadeIn {{
                from {{
                    opacity: 0;
                    transform: translateY(20px);
                }}
                to {{
                    opacity: 1;
                    transform: translateY(0);
                }}
            }}
            
            .valid-item, .invalid-item {{
                animation: fadeIn 0.5s ease;
            }}
            
            /* Responsive design */
            @media (max-width: 768px) {{
                .container {{
                    padding: 20px;
                }}
                
                h1 {{
                    font-size: 1.8em;
                }}
                
                .summary {{
                    grid-template-columns: 1fr;
                }}
                
                .copy-btn .copy-text {{
                    display: none;
                }}
                
                .link-text {{
                    max-width: calc(100% - 60px);
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔗 Link Validation Results Report</h1>
            <div class="report-time">Detection Time: {get_formatted_time(use_in_log=False)}</div>
            <div class="summary">
                <a href="#validSection" class="summary-card valid">
                    <div class="summary-number">{len(valid_links)}</div>
                    <div class="summary-label">✅ Valid Links</div>
                </a>
                <a href="#invalidSection" class="summary-card invalid">
                    <div class="summary-number">{len(invalid_links)}</div>
                    <div class="summary-label">❌ Invalid Links</div>
                </a>
                <div class="summary-card total">
                    <div class="summary-number">{len(valid_links) + len(invalid_links)}</div>
                    <div class="summary-label">📊 Total</div>
                </div>
            </div>
            
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="Search links..." onkeyup="filterLinks()">
                <span class="search-icon">🔍</span>
            </div>
            
            <div class="section" id="validSection">
                <div class="section-header valid">
                    <span>✅</span>
                    <span>Valid Links</span>
                </div>
                <ul class="links-list" id="validList">
                    {valid_items}
                </ul>
            </div>
            
            <div class="section" id="invalidSection">
                <div class="section-header invalid">
                    <span>❌</span>
                    <span>Invalid Links</span>
                </div>
                <ul class="links-list" id="invalidList">
                    {invalid_items}
                </ul>
            </div>
        </div>
        
        <script>
            function copyToClipboard(text, button) {{
                // Create temporary textarea
                const textarea = document.createElement('textarea');
                textarea.value = text;
                textarea.style.position = 'fixed';
                textarea.style.opacity = '0';
                document.body.appendChild(textarea);
                textarea.select();
                
                try {{
                    document.execCommand('copy');
                    
                    // Change button state
                    const originalHTML = button.innerHTML;
                    button.classList.add('copied');
                    button.innerHTML = `
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="20 6 9 17 4 12"></polyline>
                        </svg>
                        <span class="copy-text">Copied!</span>
                    `;
                    
                    // Restore after 2 seconds
                    setTimeout(() => {{
                        button.classList.remove('copied');
                        button.innerHTML = originalHTML;
                    }}, 2000);
                }} catch (err) {{
                    console.error('Copy failed:', err);
                    alert('Copy failed, please copy manually');
                }} finally {{
                    document.body.removeChild(textarea);
                }}
            }}
            
            function filterLinks() {{
                const searchTerm = document.getElementById('searchInput').value.toLowerCase();
                const validList = document.getElementById('validList');
                const invalidList = document.getElementById('invalidList');
                
                filterList(validList, searchTerm);
                filterList(invalidList, searchTerm);
            }}
            
            function filterList(list, searchTerm) {{
                const items = list.getElementsByTagName('li');
                
                for (let item of items) {{
                    const text = item.textContent.toLowerCase();
                    const link = item.querySelector('a');  // Get link element
                    const linkHref = link ? link.href.toLowerCase() : '';  // Get link href
            
                    if (text.includes(searchTerm) || linkHref.includes(searchTerm)) {{  // Search text or link
                        item.style.display = 'flex';
                    }} else {{
                        item.style.display = 'none';
                    }}
            }}
    }}
    
        </script>
    </body>
    </html>"""

        # Write to file
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(html_content)

        print_title(f"HTML file has been generated")
    except Exception as e:
        err = Exception(f"Failed to generate HTML file: {e}")
        logger.error(err)
        raise err from e
