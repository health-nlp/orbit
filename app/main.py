from functools import lru_cache
from fastapi import FastAPI, HTTPException, Query, Response

from pybool_ir.experiments.retrieval import AdHocExperiment
from pybool_ir.index.pubmed import PubmedIndexer
from pybool_ir.query.pubmed.parser import PubmedQueryParser
from pybool_ir.index.pubmed import PubmedArticle
from pybool_ir.query.ast import AtomNode, OperatorNode
from typing import List, Dict, Any, Tuple

import searchresult as sr

import threading
import lucene
import os
import pathlib

# LOCAL_INDEX_PATH now can be controlled via environment variable.
# Default for normal runs (in docker) is /app/index.
# For CI/Test we will set LOCAL_INDEX_PATH via the workflow/environment to the test index folder.
LOCAL_INDEX_PATH = os.getenv("LOCAL_INDEX_PATH", "index")

app = FastAPI()
vm = lucene.getVMEnv()
lock = threading.Lock()
parser = PubmedQueryParser()

# Test index folder content
@app.get("/test")
async def test_index(): 
    folder = pathlib.Path(LOCAL_INDEX_PATH)
    files = [p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()]
    print(files)


@lru_cache(maxsize=64)
def _idlist(query: str, retstart: int, retmax: int) -> Tuple[int, List[str]]:
    # Run the ad-hoc experiment using the index at LOCAL_INDEX_PATH
    lock.acquire()
    try:
        vm.attachCurrentThread()
        with AdHocExperiment(PubmedIndexer(index_path=LOCAL_INDEX_PATH), raw_query="test",page_start=retstart, page_size=retmax) as ex:
            results = ex.run
            ids = [str(res.doc_id) for res in results]
            total_count = next(ex.count())
            return (total_count, ids)
    except Exception as e:
        print(f"DEBUG Fehler: {e}")
        raise e
    finally:
        lock.release()

# Helper methods for esearch      
def set_field_recursively(node, new_field):
    # Atom (= echtes Term-Leaf)
    if hasattr(node, "field"):
        node.field = new_field

    # rekursiv über Kinder (Operatoren etc.)
    if hasattr(node, "children"):
        for child in node.children:
            set_field_recursively(child, new_field)


def _esearch(query: str, retmode: str, retmax:int, retstart: int, field: str) -> sr.SearchResult:
    print(f"Running esearch for query: {query}")
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
    if not vm.isCurrentThreadAttached():
        vm.attachCurrentThread()

    # Parse and prepare query (will raise on malformed query)
    ast = parser.parse_ast(query)
    parser.parse_lucene(query)
    formatted_query = parser.format(ast)

    total_count, id_list = _idlist(formatted_query, retstart, retmax)

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
@app.get("/entrez/eutils/esearch.fcgi")
async def esearch(
    term: str = Query(default=None, description="Search term using boolean queries"),
    retstart: int = Query(default="0", description="the start index for UIDs (default=0)"),
    retmax: int = Query(default="20", description="the end index for UIDs (default=20)"), 
    retmode: str = Query(default="xml", description="Return format xml or json (default=xml)"),
    field: str = Query(default=None, description="Limitation to certain Entrez fields"),    # currently not used
    db: str = Query(default="pubmed", description="Database to search")
):

    if term is None:
        return sr.SearchResult(error="Empty term and query_key - nothing todo", retmode=retmode)

    return _esearch(term, retmode, retmax, retstart, field)



# --------------
# --- EFETCH ---
# --------------

# Implementing EFetch endpoint
# TODO finish implementation, by adding more options according to PubMed Documentation  
# TODO adjust return structure to use searchresult classes 
@app.get("/efetch")
async def efetch(
    id: str = Query(default=..., description="Comma seperated list of UIDs (e.g. '12345678', '90123456')"),
    retmode: str = Query(default="json", description="Return format (json is default)"),
    retstart: int = Query(default=None, description="optional start-index of given id-list"),
    retmax: int = Query(default=None, descrition="optional start-index of given id-list")
):
    
    uid_list = [p.strip() for p in id.split(",") if p.strip()]
    
    if retstart is not None and retmax is not None:
        start = max(retstart, 0)
        end = start + retmax
        uid_list = uid_list[start:end]

    lock.acquire()
    try: 
        vm.attachCurrentThread()
        query = " OR ".join([f"id:{uid}" for uid in uid_list])

        with AdHocExperiment(PubmedIndexer(index_path=LOCAL_INDEX_PATH, store_fields=True)) as experiment:
            articles: List[PubmedArticle] = experiment.indexer.search(query=query, n_hits=len(uid_list))
            article_dicts = [article.to_dict() for article in articles]

            return sr.EFetchResult(retmode=retmode, article_dicts=article_dicts)

    except Exception as e: 
        return sr.SearchResult(error=str(e), retmode=retmode)
    finally: 
        lock.release()



# ----------------
# --- ESUMMARY ---
# ----------------
@app.get("/esummary")
async def esummary(
    id: str = Query(default=..., description="Comma seperated list of UIDs"),
    retmode: str = Query(default="json", description="return format: xml/json"),
    retstart: int = Query(default=0, description="the start index (default=0)"), 
    retmax: int = Query(default=20, description="the end index (default=20)")
):

    uid_list = [p.strip() for p in id.split(",") if p.strip()]

    start = max(retstart, 0)
    end = start + retmax
    uid_list = uid_list[start:end]

    lock.acquire()
    try: 
        vm.attachCurrentThread()
        query = " OR ".join([f"id:{uid}" for uid in uid_list])

        with AdHocExperiment(PubmedIndexer(index_path=LOCAL_INDEX_PATH, store_fields=True)) as experiment: 
            articles: List[PubmedArticle] = experiment.indexer.search(query=query, n_hits=len(uid_list))

            summaries = [to_summary(a) for a in articles]

            return sr.ESummaryResult(
                retstart=retstart,
                retmax=retmax,
                retmode=retmode,
                summaries=summaries
            )

    except Exception as e: 
        return sr.SearchResult(retmode=retmode, error=str(e))

    finally: 
        lock.release()

# ESummary Helper
def to_summary(article: PubmedArticle) -> dict: 
    d = article.to_dict()

    print(str(d))

    return {
        "uid": d.get("id"),
        "title": d.get("title"),
        "journal": d.get("journal"),
        "pubdate": d.get("pubdate"),
        "authors": [a.get("names") for a in d.get("authors", [])][:5]
    }
