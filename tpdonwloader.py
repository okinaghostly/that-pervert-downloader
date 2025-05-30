import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin, urlparse
import time
import re

def download_images(base_link):
    session = requests.Session()
    current_page = base_link
    parsed = urlparse(base_link)
    domain = parsed.path.replace('/', '_')
    if not domain:
        domain = 'site'

    pagination_limit = 1000

    destination_folder = os.path.join('images', domain)
    os.makedirs(destination_folder, exist_ok=True)

    page_number = 1

    while current_page:
        print(f"Accessing: {current_page}")
        try:
            resp = session.get(current_page, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f"Error accessing {current_page}: {e}")
            break

        soup = BeautifulSoup(resp.text, 'html.parser')

        try:
            body = soup.body
            if not body:
                raise Exception("body not found")

            background = body.find('div', id='background')
            if not background:
                raise Exception("div#background not found")

            container = background.find('div', id='container')
            if not container:
                raise Exception("div#container not found")

            page = container.find('div', id='page')
            if not page:
                raise Exception("div#page not found")

            pageinner = page.find('div', id='pageinner')
            if not pageinner:
                raise Exception("div#pageinner not found")

            content = pageinner.find('div', id='content')
            if not content:
                raise Exception("div#content not found")

            contentinner = content.find('div', id='contentinner')
            if not contentinner:
                raise Exception("div#contentinner not found")

            post_list = contentinner.find('div', id='post_list')
            if not post_list:
                raise Exception("div#post_list not found")

        except Exception as e:
            print(f"Error navigating page structure: {e}")
            break

        post_containers = post_list.find_all('div', class_='postContainer')
        if not post_containers:
            print("No postContainer found.")
            break

        for i, post in enumerate(post_containers):
            try:
                article = post.find('div', class_='article post-normal')
                if not article:
                    print(f"Post {i}: div.article post-normal not found")
                    continue

                post_top = article.find('div', class_='post_top')
                if not post_top:
                    print(f"Post {i}: div.post_top not found")
                    continue

                content_div = post_top.find('div', class_='post_content')
                if not content_div:
                    print(f"Post {i}: div.post_content not found")
                    continue

                anon_divs = content_div.find_all('div')
                if not anon_divs or len(anon_divs) < 1:
                    print(f"Post {i}: anonymous div not found inside post_content")
                    continue

                image_container = anon_divs[0].find('div', class_='image')
                if not image_container:
                    print(f"Post {i}: div.image not found")
                    continue

                image_link = anon_divs[0].find('a', class_='prettyPhotoLink')
                if not image_link:
                    print(f"Post {i}: <a> tag with class prettyPhotoLink not found")
                    continue

                href = image_link.get('href')
                if href:
                    # Convert "//img0..." to "https://img0..."
                    if href.startswith('//'):
                        img_url = 'https:' + href
                    else:
                        img_url = urljoin(current_page, href)

                    try:
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:112.0) Gecko/20100101 Firefox/112.0',
                            'Referer': current_page
                        }

                        response = session.get(img_url, headers=headers, timeout=10)
                        response.raise_for_status()

                        # Check if it is actually an image
                        content_type = response.headers.get('Content-Type', '')
                        if 'image' not in content_type:
                            print(f"Post {i}: Content is not an image ({content_type})")
                            continue

                        # Detect image extension
                        ext = os.path.splitext(img_url)[-1].split('?')[0]
                        if not ext or ext.lower() not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                            ext = '.' + content_type.split('/')[-1].split(';')[0]
                            if ext == '.octet-stream':
                                ext = '.jpg'  # fallback

                        filename = os.path.join(destination_folder, f"page{page_number}_img{i}{ext}")

                        with open(filename, 'wb') as f:
                            f.write(response.content)

                        print(f"Image saved: {filename}")
                    except Exception as e:
                        print(f"Post {i}: Error downloading image from {img_url}: {e}")
                else:
                    print(f"Post {i}: <a> tag does not contain href")

            except Exception as e:
                print(f"Error processing post {i}: {e}")

        # Pagination
        try:
            pagination = contentinner.find('div', class_='pagination')
            if not pagination:
                print("Div .pagination not found.")
                break

            pagination_main = pagination.find('div', class_='pagination_main')
            if not pagination_main:
                print("Div .pagination_main not found.")
                break

            next_link = pagination_main.find('a', class_='next')
            if next_link and next_link.get('href'):
                next_href = next_link['href']

                match = re.search(r'(\d+)(?:\D*)$', next_href)
                if match:
                    number_in_link = int(match.group(1))

                    if number_in_link > pagination_limit:
                        print(f"Number {number_in_link} exceeds current limit ({pagination_limit}). Moving to next link in the list.")
                        break
                    else:
                        pagination_limit = number_in_link
                        current_page = urljoin(current_page, next_href)
                        page_number += 1
                        time.sleep(1)
                else:
                    current_page = urljoin(current_page, next_href)
                    page_number += 1
                    time.sleep(1)
            else:
                print("Link with class 'next' not found. End of pagination.")
                break

        except Exception as e:
            print("Error accessing pagination:", e)
            break

def main():
    if not os.path.exists("links.txt"):
        print("File links.txt not found.")
        return

    with open("links.txt", "r", encoding='utf-8') as file:
        links = [line.strip() for line in file if line.strip()]

    for link in links:
        download_images(link)

if __name__ == "__main__":
    main()
