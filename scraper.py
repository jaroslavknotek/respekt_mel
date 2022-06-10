from tqdm.auto import tqdm
import logging

from pyquery import PyQuery

import typing
import re
import requests
from datetime import datetime
import json
import os
import requests
import re
import sys

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)


class TqdmLoggingHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg)
            self.flush()
        except Exception:
            self.handleError(record)  
            

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(TqdmLoggingHandler(level=logging.DEBUG))


def process_headers(curl_cmd):
    header_lines = [header_line.strip().strip('\'') for header_line in curl_cmd.split('-H')[1:]]
    header_colon_idx = [ header_line.index(':') for header_line in header_lines]
    headers_kv = [ (line[:idx],line[idx+1:].strip())    for idx, line in zip(header_colon_idx, header_lines)]
    headers = dict(headers_kv)
    if 'Accept-Encoding' in  headers:
        del headers['Accept-Encoding']
    return headers

class EmptyArticleException(Exception):
    pass
    

class Article(typing.NamedTuple):
    link:str
    text:str
    date_text:str
    authorship:str
        
def get_articles_uris(respekt_uribase,issue_uri, headers):
    response = requests.get(issue_uri, headers= headers)
    item_regex = r'/tydenik/\d*/\d*/[^"]*'
    uris = re.findall(item_regex, response.text)
    safe_uris = [uri.replace('&quot;',"") for uri in uris]
    return [ '/'.join([respekt_uribase.rstrip('/'),uri.lstrip('/')]) for uri in safe_uris]

def parse_article(article_html):
    pq = PyQuery(article_html)
    text = pq("#postcontent").text().replace("\xa0", " ")
    
    authorship = pq(".authorship-names").text()
    date_text = pq(".authorship-note").text()
    return text, date_text,authorship


def get_article(article_uri,headers):
    try:
        response = requests.get(article_uri, headers= headers)
        text, date_text,authorship = parse_article(response.text)
        if text == '' and date_text == '' and authorship=='':
            raise EmptyArticleException(f"Text empty. Check session. Uri: {article_uri}, text {response.text}")
            
        return Article(link=article_uri, text=text, date_text=date_text, authorship=authorship)
    except EmptyArticleException as eae:
        raise
    except Exception as e:
        logger.error(f"getting article {article_uri} failed. Error {e}")

def collect_article_uris(respekt_uribase,headers, year_from=1990,skip_issues=1, year_to = None):
    if year_to is None:
        year_to = datetime.now().year
    tydenik_uribase = '/'.join([respekt_uribase,"tydenik/{}/{}"])

    uri_blacklist = [
        'https://www.respekt.cz/tydenik/2005/52/rejstrik-2005?issueId=871',
        'https://www.respekt.cz/tydenik/2000/33/czechvztek-05?issueId=593',
        'https://www.respekt.cz/tydenik/2006/41/festival-dokumentarnich-filmu-jihlava?issueId=926',
        'https://www.respekt.cz/tydenik/2006/43/tyden-a-veda?issueId=928',
        'https://www.respekt.cz/tydenik/2019/28/vsechno-je-jejich',
        'https://www.respekt.cz/tydenik/2020/34/respekt-%e2%80%a2-despekt?issueId=100470'
    ]
    all_uris_list = []
    for y,iid in [(year, year_issue_number )for year in range( year_from,year_to +1) for year_issue_number in range(1,60)][skip_issues-1:]:
        uri_resolved = tydenik_uribase.format(y,iid)
        logger.info(f"scraping {uri_resolved} for article uris")
        uris = get_articles_uris(respekt_uribase,uri_resolved,headers)
        
        for uri in uris:
            if uri not in uri_blacklist:
                yield uri
            

def scrape_articles(headers, year_from=1990,issue_from=1, year_to=2023):
    respekt_uribase = "https://www.respekt.cz"
    logger.info("starting collecting article uris")
    article_uris= collect_article_uris(respekt_uribase, headers,year_from=year_from,skip_issues=issue_from, year_to=year_to)
        
    logger.info("starting loading data")
    for uri in tqdm(article_uris):
        logger.debug(f"reading {uri}")
        article = get_article(uri,headers)
        save_article(article)

        
def save_article(article, path='articles'):
    article_id = '-'.join(list(re.findall(r"tydenik/(\d*)/(\d*)/([^?]*)", article.link)[0]))
    article_filename = f"{article_id}.json"
    os.makedirs(path, exist_ok=True)
    filepath = os.path.join(path,article_filename)
    with open(filepath,'w')as f:
    
        article_dict = {
            "link":article.link,
            "text":article.text,
            "authorship":article.authorship,
            "date_text":article.date_text
        }
        json.dump(article_dict,f)
        logging.debug(f"{article_id} saved to {filepath}")
    
    


if __name__ == "__main__":
    # curl is used to extract all headers to avoid authentification
    curl = sys.argv[1]
    headers = process_headers(curl)
    scrape_articles(headers)