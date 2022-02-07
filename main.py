import anytree
import requests
import bs4
from anytree import Node, RenderTree
import re
import asyncio
import aiohttp
import copy
import time
import graphviz

def time_execution(func):
    def func_to_return(*args, **kw):
        start = time.time()
        result = func(*args, **kw)
        end = time.time()
        print("Time execution function=", end - start)
        return result

    return func_to_return


class FindTreeUrls:
    headers = {
        "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 05 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Mobile Safari/537.36"
    }

    def __init__(self):
        self.root = Node("Urls", parent=None)

    def print_my_tree(self):
        for pre, fill, node in RenderTree(self.root):
            print("%s%s" % (pre, node.name))

    def find_domain(self, url):
        res = re.search(".+\/", url)
        if res is None:
            return None
        domain = res.group(0)
        return domain[8:-1]

    def check_domain_in_url(self, url) -> bool:
        if re.match(f"https://{self.domain}", url) is None:
            return False
        return True

    def execute_request(self, url):
        if re.match('http', url) is None:
            return False

        print("execute request with url=", url)
        try:
            resp = requests.get(url=url, headers=self.headers)
            if resp.status_code != 200:
                print(f"url={url}")
                print(f"Oops, we have a problem")
                print(f"Response status={resp.status_code}")
                return False
            return resp.text
        except Exception as ex:
            print(ex)
            return False

    def get_urls_from_page(self, page) -> set:
        soup = bs4._soup(page, "html.parser")
        all_a = soup.find_all('a')
        all_href = []
        for a in all_a:
            href = a.get("href")
            if href:
                all_href.append(href)
        all_href = set(all_href)
        return all_href

    """ def to_the_file(self):
        from anytree.exporter import DotExporter
        # graphviz needs to be installed for the next line!
        DotExporter(self.root).to_picture("root.png")"""

    def execute_request_and_get_urls(self, url) -> list:
        page = self.execute_request(url)
        urls = []
        if page:
            urls = self.get_urls_from_page(page)
            urls = list(urls)
        return urls

    def check_available_node_in_tree(self, value):
        res = anytree.search.findall_by_attr(self.root, value=value)
        if len(res) == 0:
            return False
        return True

    def calls_to_next_step(self, list_to_return, depth):
        for node in list_to_return:
            self.next_step(node, node.name, copy.deepcopy(depth))

    def next_step(self, parent_node, url, depth):
        print("url=", url)
        depth += 1
        if depth >= self.max_depth:
            return True

        if self.check_domain_in_url(url) is False:
            print(f"domain not in {url}")
            return True

        print(depth * "_" + "try execute request with url=", url)
        urls = self.execute_request_and_get_urls(url)
        print(depth * "_" + "urls=", urls)
        list_to_return = []
        for url_in_for in urls:
            if self.check_available_node_in_tree(url_in_for) is False:
                if self.check_domain_in_url(url_in_for):
                    node = Node(url_in_for, parent=parent_node)
                    list_to_return.append(node)
            else:
                Node(url_in_for, parent=parent_node)

        self.calls_to_next_step(list_to_return, depth)

    @time_execution
    def main(self, start_url="https://google.com/", max_depth=10000):

        self.domain = self.find_domain(start_url)
        if self.domain is None:
            print("Oops, something wrong with domain....")
            return False

        print(f"domain={self.domain}")
        self.start_url = start_url
        self.max_depth = max_depth

        start_node = Node(start_url, parent=self.root)
        urls = self.execute_request_and_get_urls(start_url)

        for url in urls:
            parent_node = Node(url, parent=start_node)
            depth = 0
            self.next_step(parent_node, url, depth)
        self.print_my_tree()


class FindTreeUrlsAsync(FindTreeUrls):

    async def execute_request(self, url):

        if re.match('https', url) is None:
            return False

        print("execute request with url=", url)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status != 200:
                        print(f"url={url}")
                        print(f"Oops, we have a problem")
                        print(f"Response status={response.status}")
                        return False
                    page = await response.text()
                    return page
        except Exception as ex:
            print(ex)
            return False

    async def execute_request_and_get_urls(self, url) -> list:
        page = await self.execute_request(url)
        urls = []
        if page:
            urls = self.get_urls_from_page(page)
            urls = list(urls)
        return urls

    async def calls_to_next_step(self, list_to_return, depth):
        for node in list_to_return:
            asyncio.ensure_future(self.next_step(node, node.name, copy.deepcopy(depth)), loop=self.loop)

    async def next_step(self, parent_node, url, depth):
        depth += 1
        if depth >= self.max_depth:
            return True

        if self.check_domain_in_url(url) is False:
            print(f"domain not in {url}")
            return True

        print(depth * "_" + "try execute request with url=", url)
        urls = await self.execute_request_and_get_urls(url)
        print(depth * "_" + "urls=", urls)

        list_to_return = []
        for url_in_for in urls:
            if self.check_available_node_in_tree(url_in_for) is False:
                if self.check_domain_in_url(url_in_for):
                    node = Node(url_in_for, parent=parent_node)
                    list_to_return.append(node)
            else:
                Node(url_in_for, parent=parent_node)

        await self.calls_to_next_step(list_to_return, depth)

    @time_execution
    def main(self, start_url="https://google.com/", max_depth=10000):

        self.domain = self.find_domain(start_url)
        if self.domain is None:
            print("Oops, something wrong with domain....")
            return False

        print(f"domain={self.domain}")
        self.start_url = start_url
        self.max_depth = max_depth

        start_node = Node(start_url, parent=self.root)

        loop = asyncio.get_event_loop()
        self.loop = loop
        urls = loop.run_until_complete(asyncio.gather(self.execute_request_and_get_urls(start_url)))
        list_tasks = []
        for url in urls[0]:
            parent_node = Node(url, parent=start_node)
            depth = 0
            list_tasks.append(self.next_step(parent_node, url, depth))

        loop.run_until_complete(asyncio.gather(*list_tasks))

        self.print_my_tree()


def main():
    url = "https://uvik.net/"
    obj = FindTreeUrls()
    obj.main(url, 100)
    obj2 = FindTreeUrlsAsync()
    obj2.main(url, 100)


if __name__ == '__main__':
    main()
