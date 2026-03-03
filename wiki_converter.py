#!/usr/bin/env python3
"""
Wikipedia Page Converter
Converts Wikipedia HTML content to our fake Wikipedia format.
"""

from bs4 import BeautifulSoup
import sys
from urllib.parse import urljoin
from datetime import datetime
import requests
import base64
import re
import time

def download_resource(url, retries=4, delay=2.0):
    """Download a resource and return as base64 or None if failed.
    delay: seconds to wait before making the request (rate limiting).
    Retries with exponential backoff on 429 (Too Many Requests).
    """
    if delay > 0:
        time.sleep(delay)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 429:
                wait = int(response.headers.get('Retry-After', 2 ** (attempt + 1)))
                print(f"      Rate limited (429). Waiting {wait}s... (attempt {attempt+1}/{retries})")
                time.sleep(wait)
                continue
            response.raise_for_status()
            return {
                'data': base64.b64encode(response.content).decode('utf-8'),
                'content_type': response.headers.get('content-type', 'application/octet-stream')
            }
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                print(f"  Warning: Timeout downloading {url[:60]}... (retry {attempt+1}/{retries-1})")
            else:
                print(f"  Warning: Could not download {url[:60]}... (timeout after {retries} attempts)")
        except requests.exceptions.HTTPError as e:
            print(f"  Warning: Could not download {url[:60]}...: {e}")
            break
        except Exception as e:
            print(f"  Warning: Could not download {url[:60]}...: {e}")
            break

    return None

def embed_images_in_body(body):
    """Embed all images in body as base64 data URIs."""
    print("  Downloading and embedding images...")
    image_count = 0

    for img in body.find_all('img'):
        if 'src' in img.attrs:
            src = img.attrs['src']
            if src.startswith('data:'):
                continue  # Skip already embedded images

            print(f"    Image: {src[:60]}...")
            resource = download_resource(src)
            if resource:
                media_type = resource['content_type'].split(';')[0]
                img['src'] = f"data:{media_type};base64,{resource['data']}"
                image_count += 1
                print(f"      ✓ Embedded")
            else:
                print(f"      ✗ Failed")

    print(f"  Successfully embedded {image_count} images")


def embed_css_and_fonts_in_head(head, soup):
    """Embed CSS and fonts in head."""
    print("  Downloading and embedding stylesheets...")

    # Process stylesheets
    for link in head.find_all('link', {'rel': 'stylesheet'}):
        if 'href' in link.attrs:
            href = link.attrs['href']
            print(f"    CSS: {href[:60]}...")
            resource = download_resource(href)
            if resource:
                style = soup.new_tag('style')
                try:
                    css_content = base64.b64decode(resource['data']).decode('utf-8')
                    style.string = css_content
                    link.replace_with(style)
                    print(f"      ✓ Embedded")
                except Exception as e:
                    print(f"      ✗ Error: {e}")

    print("  Downloading and embedding fonts...")
    font_count = 0

    # Process fonts in style tags
    for style in head.find_all('style'):
        if style.string:
            css_content = style.string
            font_urls = re.findall(r'url\([\'"]?([^\'")]+\.[wot]f[f2]?)[\'"]?\)', css_content)

            for font_url in font_urls:
                if not font_url.startswith('data:'):
                    full_url = font_url
                    if font_url.startswith('/'):
                        full_url = f"https://en.wikipedia.org{font_url}"
                    elif not font_url.startswith('http'):
                        full_url = urljoin('https://en.wikipedia.org', font_url)

                    print(f"    Font: {font_url[:60]}...")
                    resource = download_resource(full_url)
                    if resource:
                        media_type = resource['content_type'].split(';')[0]
                        data_uri = f"data:{media_type};base64,{resource['data']}"
                        css_content = css_content.replace(f"url('{font_url}')", f"url('{data_uri}')")
                        css_content = css_content.replace(f'url("{font_url}")', f'url("{data_uri}")')
                        css_content = css_content.replace(f"url({font_url})", f"url({data_uri})")
                        font_count += 1
                        print(f"      ✓ Embedded")
                    else:
                        print(f"      ✗ Failed")

            style.string = css_content

    print(f"  Successfully embedded {font_count} fonts")


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

    # Remove site notice / campaign banners (e.g. "Wiki Loves Ramadan")
    for element in body.find_all('div', {'id': ['siteNotice', 'centralNotice', 'mw-siteNotice']}):
        element.decompose()
    for element in body.find_all('div', {'class': lambda c: c and any(x in c for x in ['siteNotice', 'centralNotice'])}):
        element.decompose()

    # Remove old revision banner ("This is an old revision of this page...")
    for element in body.find_all('div', {'id': 'contentSub'}):
        element.decompose()

    # Remove banners, hatnotes, and maintenance boxes
    for element in body.find_all('div', {'class': lambda c: c and any(x in c for x in ['ambox', 'mbox', 'ombox', 'tmbox', 'cmbox', 'fmbox', 'imbox'])}):
        element.decompose()
    for element in body.find_all('div', {'class': 'hatnote'}):
        element.decompose()
    for element in body.find_all('div', {'role': 'note'}):
        element.decompose()
    for element in body.find_all('table', {'class': lambda c: c and any(x in c for x in ['ambox', 'mbox', 'ombox', 'tmbox', 'cmbox', 'fmbox', 'imbox'])}):
        element.decompose()

    # Remove language selector/switcher
    for element in body.find_all('div', {'class': lambda c: c and 'mw-portlet-lang' in c}):
        element.decompose()
    for element in body.find_all('button', {'class': lambda c: c and 'mw-interlanguage-selector' in c}):
        element.decompose()
    for element in body.find_all('div', {'class': lambda c: c and 'after-portlet-lang' in c}):
        element.decompose()
    for element in body.find_all('div', {'id': 'p-lang-btn'}):
        element.decompose()

    # Replace the footer with a research notice
    for footer in body.find_all('footer', {'id': 'footer'}):
        footer.clear()
        footer['style'] = 'text-align: center; padding: 20px; border-top: 1px solid #ccc; margin-top: 30px; color: #666; font-size: 13px;'
        footer.append(BeautifulSoup(
            '<p>This article is created for research purposes only.</p>'
            '<p>University of Konstanz</p>',
            'html.parser'
        ))
    # Also remove the footer container wrapper styling if present
    for container in body.find_all('div', {'class': 'mw-footer-container'}):
        container['style'] = 'background: none; border: none;'

    # Remove "See also" and other navigation boxes
    for element in body.find_all('div', {'role': 'navigation'}):
        element.decompose()

    # Remove edit buttons and similar elements
    for element in body.find_all('span', {'class': 'mw-editsection-bracket'}):
        element.decompose()

    # Disable all links except internal anchors — keep blue link styling
    for link in body.find_all('a', href=True):
        href = link['href']
        if href.startswith('#'):
            pass  # Keep anchor links
        else:
            link['href'] = 'javascript:void(0)'

    # Process images
    for img in body.find_all('img'):
        if 'src' in img.attrs:
            src = img['src']
            if src.startswith('//'):
                img['src'] = 'https:' + src
            elif not src.startswith('http'):
                img['src'] = urljoin(source_url, src)

    # If offline mode, embed all resources (do this BEFORE converting body to string)
    if offline:
        print("Converting to offline mode...")
        # Embed images directly in the body BeautifulSoup object
        embed_images_in_body(body)
        # Embed CSS and fonts in head
        embed_css_and_fonts_in_head(head, soup)
        # Update head_content after embedding
        head_content = str(head)

    # Get just the body content (without the body tag itself)
    body_content = ''.join([str(child) for child in body.children])

    return {
        'title': title_text,
        'head_content': head_content,
        'body_content': body_content,
        'offline': offline
    }

def generate_html(data):
    """Generate the complete HTML page using Wikipedia's original styling."""

    html = f'''<!DOCTYPE html>
<html lang="en">
{data['head_content']}
<body>
{data['body_content']}</body>
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