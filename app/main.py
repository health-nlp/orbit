from functools import lru_cache
from fastapi import FastAPI, HTTPException, Query, Response

from pybool_ir.experiments.retrieval import AdHocExperiment
from pybool_ir.index.pubmed import PubmedIndexer
from pybool_ir.query.pubmed.parser import PubmedQueryParser
from pybool_ir.index.pubmed import PubmedArticle
from pybool_ir.query.ast import AtomNode, OperatorNode
from typing import List, Dict, Any, Tuple

import searchresult as sr
from esearch import ESearch 
from efetch import EFetch
from esummary import ESummary

import threading
import lucene
import os
import pathlib

# LOCAL_INDEX_PATH now can be controlled via environment variable.
# Default for normal runs (in docker) is /app/index.
# For CI/Test we will set LOCAL_INDEX_PATH via the workflow/environment to the test index folder.
LOCAL_INDEX_PATH = os.getenv("LOCAL_INDEX_PATH", "app/index")

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

    esearch = ESearch(term=term, retstart=retstart, retmax=retmax, retmode=retmode, field=field)
    return esearch.search()

# --------------
# --- EFETCH ---
# --------------
@app.get("/efetch")
async def efetch(
    id: str = Query(default=..., description="Comma seperated list of UIDs (e.g. '12345678', '90123456')"),
    retmode: str = Query(default="json", description="Return format (json is default)"),
    retstart: int = Query(default=None, description="optional start-index of given id-list"),
    retmax: int = Query(default=None, descrition="optional start-index of given id-list")
):

    efetch = EFetch(id=id, retmode=retmode, retstart=retstart, retmax=retmax)
    return efetch.fetch()



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

    esummary = ESummary(id=id, retmode=retmode, retstart=retstart, retmax=retmax)
    return esummary.summarize()