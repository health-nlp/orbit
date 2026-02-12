from fastapi import FastAPI, Query

from fastapi.responses import RedirectResponse
from pybool_ir.query.pubmed.parser import PubmedQueryParser

import entrez.searchresult as sr
from entrez.esearch import ESearch 
from entrez.efetch import EFetch
from entrez.esummary import ESummary

import threading
import lucene
import os
import pathlib

app = FastAPI(title="Orbit")
vm = lucene.getVMEnv()
lock = threading.Lock()
parser = PubmedQueryParser()

@app.get("/", include_in_schema=False)
async def docs_redirect():
    return RedirectResponse(url="/docs")

# Test index folder content
@app.get("/test", include_in_schema=False)
async def test_index(): 
    folder = pathlib.Path(LOCAL_PUBMED_INDEX_PATH)
    files = [p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()]
    print(files)

@app.get("/entrez/eutils/esearch.fcgi", tags=["PubMed Entrez"])
async def esearch(
    term: str = Query(default=None, description="Search term using boolean queries", examples=["cancer", "(headache and ibuprofen)"]),
    retstart: int = Query(default="0", description="the start index for UIDs (default=0)"),
    retmax: int = Query(default="20", description="the end index for UIDs (default=20)"), 
    retmode: str = Query(default="xml", description="Return format xml or json (default=xml)", openapi_examples={"xml": {"value": "xml"},"json": {"value": "json"},"trec": {"value": "trec"}}),
    field: str = Query(default=None, description="Limitation to certain Entrez fields"), 
    db: str = Query(default="pubmed", description="Database to search"),
    trecqid: str = Query(default="0", description="When returning a TREC run, the qid field."),
    trectag: str = Query(default="orbit", description="When returning a TREC run, the tag field.")
):
    """
        ESearch-like endpoint.
        Example: GET /esearch?term=cancer+AND+therapy
    """

    if term is None:
        return sr.SearchResult(error="Empty term and query_key - nothing todo", retmode=retmode)

    esearch = ESearch(term=term, retstart=retstart, retmax=retmax, retmode=retmode, field=field, trecqid=trecqid, trectag=trectag)
    return esearch.search()

@app.get("/entrez/eutils/efetch.fcgi", tags=["PubMed Entrez"])
async def efetch(
    id: str = Query(default=..., description="Comma seperated list of UIDs (e.g. '12345678', '90123456')"),
    retmode: str = Query(default="json", description="Return format (json is default)"),
    retstart: int = Query(default=None, description="optional start-index of given id-list"),
    retmax: int = Query(default=None, descrition="optional start-index of given id-list")
):

    efetch = EFetch(id=id, retmode=retmode, retstart=retstart, retmax=retmax)
    return efetch.fetch()


@app.get("/entrez/eutils/esummary.fcgi", tags=["PubMed Entrez"])
async def esummary(
    id: str = Query(default=..., description="Comma seperated list of UIDs"),
    retmode: str = Query(default="json", description="return format: xml/json"),
    retstart: int = Query(default=0, description="the start index (default=0)"), 
    retmax: int = Query(default=20, description="the end index (default=20)")
):

    esummary = ESummary(id=id, retmode=retmode, retstart=retstart, retmax=retmax)
    return esummary.summarize()

@app.get("/entrez/eutils/info.fcgi", tags=["PubMed Entrez"])
async def esummary():

    return "todo"

@app.get("/ct/api/v2/version", tags=["ClinicalTrials.gov"])
async def ctgov_version():
    return "todo"

@app.get("/ct/api/v2/studies", tags=["ClinicalTrials.gov"])
async def ctgov_studies():
    return "todo"

@app.get("/ct/api/v2/studies/{nctId}", tags=["ClinicalTrials.gov"])
async def ctgov_study():
    return "todo"

@app.get("/ct/api/v2/studies/metadata", tags=["ClinicalTrials.gov"])
async def ctgov_studies_metadata():
    return "todo"

@app.get("/ct/api/v2/studies/search-areas", tags=["ClinicalTrials.gov"])
async def ctgov_studies_search_areas():
    return "todo"