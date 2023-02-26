import glob
import os
from argparse import ArgumentParser, Namespace

from bs4 import BeautifulSoup, Tag
from overrides import override

from .chunker import generate_chunks
from .base import BaseImporter, GetChunksResult


class MediumImporter(BaseImporter):

    def __init__(self):
        self._include = 'all'

    @override
    def install_arguments(self, parser: ArgumentParser):
        """
        An opportunity to install arguments on the parser.

        Arguments should be in a new group, start with a `--{importer_name}-`
        and have a default.
        """
        medium_group = parser.add_argument_group('medium')
        medium_group.add_argument('--medium-include', help='If provided and the importer is medium, which set to include',
                                  choices=['all', 'drafts', 'published'], default='published')

    @override
    def retrieve_arguments(self, args: Namespace):
        """
        An opportunity to retrieve arguments configured via install_arguments.
        """
        self._include = args.medium_include

    @override
    def output_base_filename(self, filename) -> str:
        profile_path = f"{filename}/profile/profile.html"
        with open(profile_path, "r") as f:
            soup = BeautifulSoup(f, "html.parser")
            ele = soup.find('a', class_='u-url')
            if not ele:
                raise Exception("Can't find title a")
            username = ele.get_text(strip=True)
            return 'medium-' + username.replace('@', '') + '-' + self._include

    def extract_url_from_soup(self, base_filename: str, soup: BeautifulSoup):
        if (base_filename.startswith('draft_')):
            footer = soup.find('footer')
            if not footer:
                raise Exception("Didn't find footer in draft")
            ele = footer.find('a')
        else:
            ele = soup.find('a', class_='p-canonical')
        if not isinstance(ele, Tag):
            raise Exception("ele not Tag as expected")
        return ele.get('href')

    def extract_image_url_from_soup(self, soup: BeautifulSoup):
        img = soup.find('img', class_='graf-image')
        if not img:
            return ''
        if not isinstance(img, Tag):
            raise Exception("img not Tag as expected")
        return img.get('src')

    def extract_title_from_soup(self, soup: BeautifulSoup):
        h1 = soup.find('h1', class_='p-name')
        return h1.get_text(strip=True) if h1 else ''

    def extract_description_from_soup(self, soup: BeautifulSoup):
        section = soup.find('section', class_='p-summary')
        if section:
            return section.get_text(" ", strip=True)
        paragraphs = [*self.extract_chunks_from_soup(soup)]
        return paragraphs[0] if len(paragraphs) else ''

    def extract_slug_from_filename(self, base_filename):
        base, _ = os.path.splitext(base_filename)
        return base.split('-')[-1]

    def extract_chunks_from_soup(self, soup: BeautifulSoup):
        body = soup.find('section', class_='e-content')
        if not isinstance(body, Tag):
            raise Exception("body not presetnt as expected")
        ps = body.find_all('p')
        text = [p.get_text(" ", strip=True) for p in ps]
        return generate_chunks([text])

    @override
    def get_chunks(self, filename) -> GetChunksResult:
        filenames = glob.glob(f"{filename}/posts/*.html")
        for file in filenames:
            with open(file, 'r') as f:
                base_filename = os.path.basename(file)
                if base_filename.startswith('draft_'):
                    if self._include == 'published':
                        print('Skipping draft ' + base_filename)
                        continue
                else:
                    if self._include == 'drafts':
                        print('Skipping published post' + base_filename)
                        continue
                soup = BeautifulSoup(f, "html.parser")
                url = self.extract_url_from_soup(base_filename, soup)
                image_url = self.extract_image_url_from_soup(soup)
                title = self.extract_title_from_soup(soup)
                description = self.extract_description_from_soup(soup)
                info = {
                    'url': url,
                    'image_url': image_url,
                    'title': title,
                    'description': description
                }
                for chunk in self.extract_chunks_from_soup(soup):
                    yield {
                        "text": chunk,
                        "info": info
                    }