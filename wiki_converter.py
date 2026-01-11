#!/usr/bin/env python3
"""
Wikipedia Page Converter
Converts Wikipedia HTML content to our fake Wikipedia format with boundary warnings.
"""

from bs4 import BeautifulSoup
import sys
from urllib.parse import urljoin
from datetime import datetime
import requests
import base64
import re

def download_resource(url):
    """Download a resource and return as base64 or None if failed."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return base64.b64encode(response.content).decode('utf-8')
    except Exception as e:
        print(f"  Warning: Could not download {url}: {e}")
        return None

def embed_offline_resources(html_content, body_content):
    """Embed all external resources as base64 data URIs."""

    soup = BeautifulSoup(html_content, 'html.parser')
    body_soup = BeautifulSoup(body_content, 'html.parser')

    print("  Downloading and embedding stylesheets...")
    # Process stylesheets
    for link in soup.find_all('link', {'rel': 'stylesheet'}):
        if 'href' in link.attrs:
            href = link.attrs['href']
            print(f"    Downloading CSS: {href[:80]}...")
            css_data = download_resource(href)
            if css_data:
                style = soup.new_tag('style')
                # Decode base64 and add as CSS
                try:
                    css_content = base64.b64decode(css_data).decode('utf-8')
                    style.string = css_content
                    link.replace_with(style)
                except Exception as e:
                    print(f"    Error processing CSS: {e}")

    print("  Downloading and embedding images...")
    # Process images in body
    for img in body_soup.find_all('img'):
        if 'src' in img.attrs:
            src = img.attrs['src']
            print(f"    Downloading image: {src[:80]}...")
            img_data = download_resource(src)
            if img_data:
                # Determine the media type from the URL
                if src.endswith('.jpg') or src.endswith('.jpeg'):
                    media_type = 'image/jpeg'
                elif src.endswith('.png'):
                    media_type = 'image/png'
                elif src.endswith('.gif'):
                    media_type = 'image/gif'
                elif src.endswith('.svg'):
                    media_type = 'image/svg+xml'
                else:
                    media_type = 'image/jpeg'  # Default

                img['src'] = f"data:{media_type};base64,{img_data}"

    print("  Downloading and embedding fonts...")
    # Process font URLs in stylesheets
    for style in soup.find_all('style'):
        if style.string:
            css_content = style.string
            # Find all font URLs
            font_urls = re.findall(r'url\([\'"]?([^\'")]+\.[wot]f[f2]?)[\'"]?\)', css_content)
            for font_url in font_urls:
                if not font_url.startswith('data:'):
                    full_url = font_url
                    if font_url.startswith('/'):
                        full_url = f"https://en.wikipedia.org{font_url}"
                    elif not font_url.startswith('http'):
                        full_url = urljoin('https://en.wikipedia.org', font_url)

                    print(f"    Downloading font: {font_url[:80]}...")
                    font_data = download_resource(full_url)
                    if font_data:
                        # Determine media type
                        if font_url.endswith('.woff2'):
                            media_type = 'font/woff2'
                        elif font_url.endswith('.woff'):
                            media_type = 'font/woff'
                        elif font_url.endswith('.ttf'):
                            media_type = 'font/ttf'
                        elif font_url.endswith('.otf'):
                            media_type = 'font/otf'
                        else:
                            media_type = 'font/woff'

                        data_uri = f"data:{media_type};base64,{font_data}"
                        css_content = css_content.replace(f"url('{font_url}')", f"url('{data_uri}')")
                        css_content = css_content.replace(f'url("{font_url}")', f'url("{data_uri}")')
                        css_content = css_content.replace(f"url({font_url})", f"url({data_uri})")

            style.string = css_content

    return str(soup), str(body_soup)

def process_wikipedia_html(html_content, source_url, offline=False):
    """Process Wikipedia HTML and preserve original styling."""

    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract title
    title = soup.find('h1', {'class': 'firstHeading'})
    if not title:
        title = soup.find('h1', {'id': 'firstHeading'})
    if not title:
        title = soup.find('h1')
    title_text = title.get_text().strip() if title else "Wikipedia Article"

    # Extract and process the head
    head = soup.find('head')
    head_content = ""
    if head:
        # Process stylesheets to make URLs absolute
        for link in head.find_all('link', {'rel': 'stylesheet'}):
            if 'href' in link.attrs:
                href = link.attrs['href']
                # Make relative URLs absolute
                if href.startswith('/'):
                    href = f"https://en.wikipedia.org{href}"
                elif not href.startswith('http'):
                    href = urljoin(source_url, href)
                link['href'] = href

        # Process other links (icons, etc.)
        for link in head.find_all('link'):
            if 'href' in link.attrs:
                href = link.attrs['href']
                if href.startswith('/'):
                    href = f"https://en.wikipedia.org{href}"
                elif not href.startswith('http'):
                    href = urljoin(source_url, href)
                link['href'] = href

        # Process scripts in head - make URLs absolute but keep them all
        for script in head.find_all('script'):
            if 'src' in script.attrs:
                src = script.attrs['src']
                # Make relative URLs absolute
                if src.startswith('/'):
                    src = f"https://en.wikipedia.org{src}"
                elif not src.startswith('http'):
                    src = urljoin(source_url, src)
                script['src'] = src

        head_content = str(head)

    # Get the body content
    body = soup.find('body')
    if not body:
        body = soup

    # Remove unwanted elements from the body
    for element in body.find_all('noscript'):
        element.decompose()

    # Process scripts in body - keep all but make URLs absolute
    for script in body.find_all('script'):
        src = script.get('src', '')
        # Only remove tracking/analytics scripts
        if 'analytics' in src.lower() or 'tracker' in src.lower() or 'google' in src.lower():
            script.decompose()
        # Remove inline tracking scripts
        elif script.string and ('analytics' in script.string.lower() or 'tracker' in script.string.lower()):
            script.decompose()
        # For other scripts, make URLs absolute
        elif src:
            if src.startswith('/'):
                src = f"https://en.wikipedia.org{src}"
            elif not src.startswith('http'):
                src = urljoin(source_url, src)
            script['src'] = src

    # Remove edit links
    for element in body.find_all('span', {'class': 'mw-editsection'}):
        element.decompose()

    # Remove certain divs we don't want
    for element in body.find_all('div', {'class': ['navbox', 'printfooter', 'mw-authority-control', 'noprint']}):
        element.decompose()

    # Remove "See also" and other navigation boxes
    for element in body.find_all('div', {'role': 'navigation'}):
        element.decompose()

    # Remove edit buttons and similar elements
    for element in body.find_all('span', {'class': 'mw-editsection-bracket'}):
        element.decompose()

    # Process links - block external/wikipedia links, keep internal ones
    for link in body.find_all('a', href=True):
        href = link['href']

        if href.startswith('#'):
            # Keep internal anchor links as-is
            pass
        elif href.startswith('/wiki/'):
            # Wikipedia link - convert to onclick handler
            wiki_url = f"https://en.wikipedia.org{href}"
            link['data-boundary-url'] = wiki_url
            link['onclick'] = f"showBoundaryWarning('{wiki_url}', 'wikipedia'); return false;"
            del link['href']
        elif href.startswith('http://') or href.startswith('https://') or href.startswith('//'):
            # External link - convert to onclick handler
            external_url = href if href.startswith('http') else f"https:{href}"
            link['data-boundary-url'] = external_url
            link['onclick'] = f"showBoundaryWarning('{external_url}', 'external'); return false;"
            del link['href']
        elif not href.startswith('http'):
            # Internal relative link - make absolute
            link['href'] = urljoin(source_url, href)

    # Process images
    for img in body.find_all('img'):
        if 'src' in img.attrs:
            src = img['src']
            if src.startswith('//'):
                img['src'] = 'https:' + src
            elif not src.startswith('http'):
                img['src'] = urljoin(source_url, src)

    # Get just the body content (without the body tag itself)
    body_content = ''.join([str(child) for child in body.children])

    # If offline mode, embed all resources
    if offline:
        print("Converting to offline mode...")
        head_content, body_content = embed_offline_resources(head_content, body_content)

    return {
        'title': title_text,
        'head_content': head_content,
        'body_content': body_content,
        'offline': offline
    }

def generate_html(data):
    """Generate the complete HTML page using Wikipedia's original styling."""

    # Boundary warning CSS to inject into head
    boundary_css = '''    <style>
    /* Boundary Modal */
    .modal-overlay {
        display: none;
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.85);
        backdrop-filter: blur(5px);
        z-index: 9999;
        align-items: center;
        justify-content: center;
    }

    .modal-overlay.active {
        display: flex;
    }

    .boundary-modal {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 2px solid #00ff41;
        border-radius: 3px;
        padding: 30px;
        max-width: 500px;
        box-shadow: 0 0 40px rgba(0, 255, 65, 0.3), inset 0 0 20px rgba(0, 255, 65, 0.1);
        color: #00ff41;
        font-family: 'Courier New', monospace;
        animation: glitch 0.3s ease-in-out;
    }

    @keyframes glitch {
        0%, 100% { transform: translate(0); }
        20% { transform: translate(-2px, 2px); }
        40% { transform: translate(-2px, -2px); }
        60% { transform: translate(2px, 2px); }
        80% { transform: translate(2px, -2px); }
    }

    .boundary-modal h2 {
        color: #00ff41;
        font-size: 24px;
        margin: 0 0 20px 0;
        text-align: center;
        border: none;
        font-family: 'Courier New', monospace;
        text-shadow: 0 0 10px rgba(0, 255, 65, 0.7);
        letter-spacing: 2px;
    }

    .boundary-modal p {
        color: #00ff41;
        font-size: 14px;
        line-height: 1.8;
        margin-bottom: 20px;
        text-align: left;
    }

    .boundary-modal .warning {
        background: rgba(255, 0, 0, 0.1);
        border-left: 3px solid #ff0040;
        padding: 10px;
        margin: 15px 0;
        color: #ff0040;
        font-size: 13px;
    }

    .boundary-modal .link-display {
        background: rgba(0, 0, 0, 0.5);
        border: 1px solid #00ff41;
        padding: 10px;
        margin: 15px 0;
        word-break: break-all;
        font-size: 12px;
        color: #0ff;
    }

    .modal-buttons {
        display: flex;
        gap: 15px;
        justify-content: center;
        margin-top: 25px;
    }

    .modal-btn {
        padding: 10px 25px;
        border: 2px solid #00ff41;
        background: transparent;
        color: #00ff41;
        cursor: pointer;
        font-family: 'Courier New', monospace;
        font-size: 14px;
        font-weight: bold;
        transition: all 0.3s;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .modal-btn:hover {
        background: #00ff41;
        color: #1a1a2e;
        box-shadow: 0 0 20px rgba(0, 255, 65, 0.5);
    }

    .modal-btn.danger {
        border-color: #ff0040;
        color: #ff0040;
    }

    .modal-btn.danger:hover {
        background: #ff0040;
        color: #fff;
        box-shadow: 0 0 20px rgba(255, 0, 64, 0.5);
    }

    .blink {
        animation: blink 1s infinite;
    }

    @keyframes blink {
        0%, 49% { opacity: 1; }
        50%, 100% { opacity: 0; }
    }
    </style>
'''

    # Boundary modal HTML
    boundary_modal = '''
    <!-- Boundary Warning Modal -->
    <div class="modal-overlay" id="boundaryModal">
        <div class="boundary-modal">
            <h2>⚠ REALITY BOUNDARY DETECTED ⚠</h2>
            <p>You are attempting to exit this mirror and access <strong>another Wikipedia page</strong>.</p>
            <div class="warning">
                <span class="blink">▶</span> WARNING: Crossing between wiki-spaces may cause temporal displacement.
            </div>
            <p>Target destination:</p>
            <div class="link-display" id="targetLink"></div>
            <p style="font-size: 12px; color: #0ff;">This page contains references to other Wikipedia articles. Proceeding will navigate away from the current mirror.</p>
            <div class="modal-buttons">
                <button class="modal-btn" onclick="closeModal()">STAY HERE</button>
                <button class="modal-btn danger" onclick="proceedToLink()">TRAVERSE BOUNDARY</button>
            </div>
        </div>
    </div>

    <script>
        let pendingUrl = null;

        function showBoundaryWarning(url, type) {{
            pendingUrl = url;

            if (type === 'wikipedia') {{
                document.querySelector('.boundary-modal h2').textContent = '⚠ REALITY BOUNDARY DETECTED ⚠';
                document.querySelector('.boundary-modal p:first-of-type').textContent = 'You are attempting to exit this mirror and access another Wikipedia page.';
            }} else if (type === 'external') {{
                document.querySelector('.boundary-modal h2').textContent = '⚠ EXTERNAL LINK WARNING ⚠';
                document.querySelector('.boundary-modal p:first-of-type').textContent = 'You are attempting to access an external website outside this mirror.';
            }}

            document.getElementById('targetLink').textContent = url;
            document.getElementById('boundaryModal').classList.add('active');
        }}

        function closeModal() {{
            document.getElementById('boundaryModal').classList.remove('active');
            pendingUrl = null;
        }}

        function proceedToLink() {{
            if (pendingUrl) {{
                window.open(pendingUrl, '_blank');
                closeModal();
            }}
        }}

        // Handle hash links
        document.addEventListener('click', function(e) {{
            const link = e.target.closest('a[href^="#"]');
            if (link) {{
                e.preventDefault();
                const target = link.getAttribute('href');
                if (target && target !== '#') {{
                    const element = document.querySelector(target);
                    if (element) {{
                        element.scrollIntoView({{ behavior: 'smooth' }});
                    }}
                }}
            }}
        }});

        // Close modal on escape key
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') {{
                closeModal();
            }}
        }});

        // Close modal on overlay click
        document.getElementById('boundaryModal').addEventListener('click', function(e) {{
            if (e.target === this) {{
                closeModal();
            }}
        }});
    </script>
'''

    # Inject boundary CSS into the original head
    head_with_css = data['head_content'].replace('</head>', f'{boundary_css}</head>')

    html = f'''<!DOCTYPE html>
<html lang="en">
{head_with_css}
<body>
{data['body_content']}{boundary_modal}</body>
</html>
'''

    return html

def main():
    if len(sys.argv) < 2:
        print("Usage: python wiki_converter.py <url_or_file> [output_file] [--offline]")
        print("  <url_or_file>: Wikipedia URL (e.g., https://en.wikipedia.org/wiki/Python) or local HTML file")
        print("  [output_file]: Optional output filename (default: fake_wiki_page.html)")
        print("  [--offline]: Optional flag to embed all resources (CSS, images, fonts) for offline use")
        print("\nExamples:")
        print("  python wiki_converter.py https://en.wikipedia.org/wiki/Python")
        print("  python wiki_converter.py https://en.wikipedia.org/wiki/Python my_page.html --offline")
        print("  python wiki_converter.py saved_page.html output.html")
        sys.exit(1)

    input_source = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "fake_wiki_page.html"
    offline = '--offline' in sys.argv

    # Check if input is a URL or file
    if input_source.startswith('http://') or input_source.startswith('https://'):
        print(f"Fetching: {input_source}")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(input_source, headers=headers, timeout=10)
            response.raise_for_status()
            html_content = response.text
            source_url = input_source
        except requests.exceptions.RequestException as e:
            print(f"✗ Error fetching URL: {e}")
            sys.exit(1)
    else:
        print(f"Reading: {input_source}")
        try:
            with open(input_source, 'r', encoding='utf-8') as f:
                html_content = f.read()
            source_url = "https://en.wikipedia.org"
        except FileNotFoundError:
            print(f"✗ Error: File not found: {input_source}")
            sys.exit(1)
        except IOError as e:
            print(f"✗ Error reading file: {e}")
            sys.exit(1)

    print(f"Processing Wikipedia content...")
    data = process_wikipedia_html(html_content, source_url, offline=offline)

    print(f"Generating HTML...")
    html = generate_html(data)

    print(f"Writing to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    if offline:
        import os
        file_size = os.path.getsize(output_file) / (1024 * 1024)
        print(f"✓ Done! Created {output_file} ({file_size:.1f} MB)")
    else:
        print(f"✓ Done! Created {output_file}")

if __name__ == "__main__":
    main()