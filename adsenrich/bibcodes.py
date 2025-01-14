import os
import string
from adsenrich.utils import u2asc, issn2bib
from adsenrich.data import *
from adsputils import load_config

proj_home = os.getenv("PWD", None)
conf = load_config(proj_home=proj_home)

class BibstemException(Exception):
    pass

class NoPubYearException(Exception):
    pass

class NoBibcodeException(Exception):
    pass

class BibcodeGenerator(object):

    def __init__(self, bibstem=None, token=None, url=None):
        if not token:
            token = conf.get("_API_TOKEN", None)
        if not url:
            url = conf.get("_API_URL", None)

        self.api_token = token
        self.api_url = url
        self.bibstem = bibstem

    def _int_to_letter(self, integer):
        try:
            return string.ascii_letters[int(integer) - 1]
        except Exception as err:
            return integer

    def _get_author_init(self, record):
        try:
            author_init = record['authors'][0]['name']['surname']
            author_init = author_init.strip()[0]
            author_init = u2asc(author_init).upper()
        except Exception as err:
            author_init = '.'
        return author_init

    def _get_pubyear(self, record):
        try:
            pub_year = record['publication']['pubYear']
        except Exception as err:
            raise NoPubYearException(err)
        else:
            return pub_year

    def _get_volume(self, record):
        try:
            volume = record['publication']['volumeNum']
            if "-" in volume:
                vol_list = volume.strip().split("-")
                volume = vol_list[0]
        except Exception as err:
            volume = '.'
        return volume

    def _get_issue(self, record):
        try:
            issue = str(record['publication']['issueNum'])
        except Exception as err:
            issue = None
        return issue

    def _get_pagenum(self, record):
        pagination = record.get('pagination', None)
        if pagination:
            fpage = pagination.get('firstPage', None)
            epage = pagination.get('electronicID', None)
            rpage = pagination.get('pageRange', None)
            if fpage:
                page = fpage
            elif epage:
                page = epage
            elif rpage:
                page = rpage
            else:
                page = '.'
            page = page.replace(',', '')
            return page
        else:
            return '.'

    def _deletter_page(self, page):
        is_letter = None
        if 'L' in page or 'l' in page:
            page = page.replace('L', '.').replace('l', '.')
            is_letter = 'L'
        elif 'P' in page or 'p' in page:
            page = page.replace('P', '').replace('p', '')
            is_letter = 'P'
        elif 'S' in page or 's' in page:
            page = page.replace('S', '').replace('s', '')
            is_letter = 'S'
        elif 'A' in page:
            page = page.replace('A', '')
            is_letter = 'A'
        elif 'C' in page:
            page = page.replace('C', '')
            is_letter = 'C'
        elif 'E' in page:
            page = page.replace('E', '')
            is_letter = 'E'
        return (page, is_letter)

    def _get_normal_pagenum(self, record):
        page = self._get_pagenum(record)
        is_letter = None
        if page:
            (page, is_letter) = self._deletter_page(page)
            if len(str(page)) >= 5:
                page = str(page)[-5:]
            else:
                page = page.rjust(4, '.')
            if is_letter:
                page = page[-4:]
        return (page, is_letter)

    def _get_converted_pagenum(self, record):
        try:
            page = self._get_pagenum(record)
            (page, is_letter) = self._deletter_page(page)
            if page:
                page_a = None
                if len(str(page)) >= 6:
                    page = page[-6:]
                    page_a = self._int_to_letter(page[0:2])
                    page = page[2:]
                if page_a:
                    if not is_letter:
                        is_letter = page_a
        except Exception as err:
            page = None
            is_letter = None
        return page, is_letter

    def _get_bibstem(self, record):
        if self.bibstem:
            return self.bibstem
        else:
            bibstem = None
            try:
                issn_rec = []
                try:
                    issn_rec = record['publication']['ISSN']
                except Exception as err:
                    pass
                for i in issn_rec:
                    issn = i.get('issnString', None)
                    try:
                        if len(issn) == 8:
                            issn = issn[0:4] + '-' + issn[4:]
                    except Exception as err:
                        pass
                    if issn:
                        if not bibstem:
                            bibstem = issn2bib(token=self.api_token,
                                               url=self.api_url,
                                               issn=issn)
            except Exception as err:
                pass
        if bibstem:
            return bibstem
        else:
            raise BibstemException('Bibstem not found.')

    def make_bibcode(self, record, bibstem=None):
        try:
            year = self._get_pubyear(record)
        except Exception as err:
            year = None
        try:
            if not bibstem:
                bibstem = self._get_bibstem(record)
        except Exception as err:
            bibstem = None
        try:
            volume = self._get_volume(record)
        except Exception as err:
            volume = ''
        try:
            author_init = self._get_author_init(record)
        except Exception as err:
            author_init = ''
        if not (year and bibstem):
            raise NoBibcodeException("You're missing year and or bibstem -- no bibcode can be made!")
        else:
            bibstem = bibstem.ljust(5, '.')
            volume = volume.rjust(4, '.')
            author_init = author_init.rjust(1, '.')
            issue = None

            # Special bibstem, page, volume, issue handling
            if bibstem in IOP_BIBSTEMS:
                # IOP get converted_pagenum/letters for six+ digit pages
                (pageid, is_letter) = self._get_converted_pagenum(record)
                if bibstem == 'JCAP.':
                    # JCAP is an IOP journal
                    try:
                        issue = self._get_issue(record)
                        volume = issue.rjust(4, '.')
                        issue = None
                    except:
                        issue = None
                elif bibstem == 'ApJL.':
                    # ApJ/L are IOP journals
                    bibstem = 'ApJ..'
                    issue = 'L'
                if is_letter:
                    if not issue:
                        issue=is_letter

            elif bibstem in APS_BIBSTEMS:
                # APS get converted_pagenum/letters for six+ digit pages
                (pageid, is_letter) = self._get_converted_pagenum(record)
                if is_letter:
                    if not issue:
                        issue=is_letter

            elif bibstem in OUP_BIBSTEMS:
                # APS get converted_pagenum/letters for six+ digit pages
                (pageid, is_letter) = self._get_converted_pagenum(record)
                if is_letter:
                    if not issue:
                        issue=is_letter

            elif bibstem in AIP_BIBSTEMS:
                #AIP: AIP Conf gets special handling
                (pageid, is_letter) = self._get_converted_pagenum(record)
                if bibstem == 'AIPC.':
                    if is_letter:
                        if not issue:
                            issue=is_letter
                else:
                    issue = self._int_to_letter(self._get_issue(record))


            elif bibstem in SPRINGER_BIBSTEMS:
                # IOP get converted_pagenum/letters for six+ digit pages
                (pageid, is_letter) = self._get_normal_pagenum(record)
                if bibstem == 'JHEP.':
                    try:
                        issue = self._get_issue(record)
                        volume = issue.rjust(4, '.')
                        issue = None
                    except:
                        issue = None
                if is_letter:
                    if not issue:
                        issue=is_letter

            else:
                (pageid, is_letter) = self._get_normal_pagenum(record)
                if is_letter:
                    if not issue:
                        issue = is_letter

            if not issue:
                pageid = pageid.rjust(5, '.')
                issue = ''
            else:
                pageid = pageid.rjust(4, '.')

            try:
                bibcode = year + bibstem + volume + issue + pageid + author_init
                if len(bibcode) != 19:
                    raise Exception('Malformed bibcode, wrong length!')
            except Exception as err:
                bibcode = None
            return bibcode
