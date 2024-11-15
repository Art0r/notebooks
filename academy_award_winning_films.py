from bs4 import BeautifulSoup
from typing import Optional
import concurrent.futures
import requests
import os
import re

ROOT_URL = "https://en.wikipedia.org"
URL = f"{ROOT_URL}/wiki/List_of_Academy_Award%E2%80%93winning_films"
NOMINEES_PATH = os.path.join(os.getcwd(), "oscar_nominees")


def download_nominees_pages():
    nominees_response = requests.get(URL)
    nominees_html = nominees_response.content.decode()
    nominees_soup = BeautifulSoup(nominees_html, 'html.parser')
    nominees_table = nominees_soup.select_one(".wikitable")
    nominees_links = [a["href"] for a in nominees_table.select(
        "a") if "_in_film" not in a["href"] and "#" not in a["href"]]

    if os.path.isdir(NOMINEES_PATH):

        for file in os.listdir(NOMINEES_PATH):
            file_path = os.path.join(NOMINEES_PATH, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        os.removedirs(NOMINEES_PATH)

    os.makedirs(NOMINEES_PATH)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        def get_nominee_page(link): return requests.get(
            ROOT_URL + link).content.decode()
        def write_page_to_file(link, index): return open(os.path.join(
            NOMINEES_PATH, f"{index}.html"), "w").write(get_nominee_page(link))

        futures = [executor.submit(write_page_to_file, link, index)
                   for index, link in enumerate(nominees_links)]
        for future in futures:
            future.result()


def nominee_page_process_data_and_return() -> dict[str, list]:
    data: dict[str, list] = {"Country": [], "Title": []}

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:

        futures = [executor.submit(_nominee_page_data, file)
                   for file in os.listdir(NOMINEES_PATH)]
        results = [future.result()
                   for future in futures if future.result() is not None]

        for result in results:

            country = result[0].replace("/n", "")
            title = result[1].replace("/n", "")

            country = result[0].replace("\n", "")
            title = result[1].replace("\n", "")

            country = re.sub(r"\[.*?\]", "", country)
            title = re.sub(r"\[.*?\]", "", title)

            data["Country"].append(country)
            data["Title"].append(title)

    return data


def _nominee_page_data(file: str) -> Optional[tuple[str, str]]:
    def nominee_page_file_content(file): return open(
        os.path.join(NOMINEES_PATH, file), 'r').read()

    def nominee_page_as_bs4(file): return BeautifulSoup(
        nominee_page_file_content(file), "html.parser") if ".html" in file else None

    try:

        info_table = nominee_page_as_bs4(file).select_one(
            ".infobox").select_one('tbody')

        if info_table is not None:
            country = info_table.find_all(lambda tag: tag.text == "Country")[
                0].find_next("td").text
            title = info_table.select_one(".infobox-above").text

            return (country, title)

    except IndexError:
        return None
    except AttributeError:
        return None

    return None
