from functools import lru_cache
from fastapi import FastAPI, HTTPException, Query, Response

from pybool_ir.experiments.retrieval import AdHocExperiment
from pybool_ir.index.pubmed import PubmedIndexer
from pybool_ir.query.pubmed.parser import PubmedQueryParser
from pybool_ir.index.pubmed import PubmedArticle
from typing import List, Dict, Any, Tuple

import searchresult as sr

import threading
import lucene
import os

# LOCAL_INDEX_PATH now can be controlled via environment variable.
# Default for normal runs (in docker) is /app/index.
# For CI/Test we will set LOCAL_INDEX_PATH via the workflow/environment to the test index folder.
LOCAL_INDEX_PATH = os.getenv("LOCAL_INDEX_PATH", "/app/index")

app = FastAPI()
vm = lucene.getVMEnv()
lock = threading.Lock()
parser = PubmedQueryParser()


@lru_cache(maxsize=64)
def _idlist(query: str) -> Tuple[int, List[str]]:
    """
    Grab the id list for a query, caching the result so that it may be paged.
    
    :param query: Description
    :type query: str
    :return: Description
    :rtype: Tuple[int, List[str]]
    """
    # Run the ad-hoc experiment using the index at LOCAL_INDEX_PATH
    lock.acquire()
    try:
        with AdHocExperiment(PubmedIndexer(index_path=LOCAL_INDEX_PATH), raw_query=query) as experiment:
            results = experiment.run
            total_count = len(results)
            return (total_count, [str(res.doc_id) for res in results])
    except Exception as e:
        raise e        
    finally:
        lock.release()

        
def _esearch(query: str, retmode: str, retmax:int, retstart: int) -> sr.SearchResult:
    """
    Docstring for _esearch
    
    :param query: Description
    :type query: str
    :param retmode: Description
    :type retmode: str
    :param retmax: Description
    :type retmax: int
    :param retstart: Description
    :type retstart: int
    :return: Description
    :rtype: SearchResult
    """
    vm.attachCurrentThread()
    # Parse and prepare query (will raise on malformed query)
    ast = parser.parse_ast(query)
    parser.parse_lucene(query)
    formatted_query = parser.format(ast)

    total_count, id_list = _idlist(formatted_query)
    if retmax > total_count:
        retmax = total_count-1
    if retstart > total_count or retstart+retmax > total_count:
        retstart = retmax

    id_list = id_list[retstart:retstart+retmax]

    return sr.ESearchResult(
        retmode=retmode,
        count=str(total_count),
        retmax=str(retmax),
        retstart=str(retstart),
        idlist=id_list,
        querytranslation=formatted_query,
        translationset={"from": query, "to": formatted_query}
    )    

"""
    ESearch-like endpoint.
    Example: GET /esearch?term=cancer+AND+therapy
"""
@app.get("/esearch")
async def esearch(
    term: str = Query(default=None, description="Search term using boolean queries"),
    retstart: int = Query(default="0", description="the start index for UIDs (default=0)"),
    retmax: int = Query(default="20", description="the end index for UIDs (default=20)"), 
    retmode: str = Query(default="xml", description="Return format xml or json (default=xml)"),
    field: str = Query(default=None, description="Limitation to certain Entrez fields"),
    db: str = Query(default="pubmed", description="Database to search")
):

    if term is None:
        return sr.SearchResult(error="Empty term and query_key - nothing todo", retmode=retmode)
    return _esearch(term, retmode, retmax, retstart)


# Implementing EFetch endpoint
# TODO finish implementation, by adding more options according to PubMed Documentation  
# TODO adjust return structure to use searchresult classes 
@app.get("efetch")
async def efetch(
    id: str = Query(default=..., description="Comma seperated list of UIDs (e.g. '12345678', '90123456')"),
    retmode: str = Query(default="json", description="Return format (json is default)")
):
    
    uid_list = [p.strip() for p in id.split(",") if p.strip()]

    try: 
        vm.attachCurrentThread()
        query = " OR ".join([f"id:'{uid}'" for uid in uid_list])
        ast = parser.parse_ast(query)
        parser.parse_lucene(query)
        lucene_query = parser.format(ast)
        print(f"lucene_query: {lucene_query}")
    

        with AdHocExperiment(PubmedIndexer(index_path=LOCAL_INDEX_PATH, store_field=True)) as experiment:
            articles: List[PubmedArticle] = experiment.indexer.search(query=lucene_query, n_hits=len(uid_list))
            article_dicts = [article.to_dict() for article in articles]

            return {
                "header": {
                    "type": "efetch",
                    "version": "0.3-openpm",
                    "retmode": retmode
                },
                "articleList": article_dicts,
                "error": None
            }
    except Exception as e: 
        return {
            "header": {
                "type": "efetch",
                "verison": "0.3-openpm"
            },
            "efetchresult": {
                "ERROR": str(e),
            }
        }

    finally: 
        lock.release()
