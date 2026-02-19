import os

from fastapi import FastAPI, Query

from fastapi.responses import RedirectResponse
from pybool_ir.query.pubmed.parser import PubmedQueryParser

import entrez.searchresult as sr
from entrez.esearch import ESearch 
from entrez.efetch import EFetch
from entrez.esummary import ESummary
from entrez.einfo import EInfo

from ctgov.studies import studies as get_ctgov_studies
from ctgov.studies import study as get_ctgov_study
from ctgov.studies import metadata as get_ctgov_metadata
from ctgov.studies import searchareas as get_ctgov_searchareas

ORBIT_VERSION = "0.1.0"
app = FastAPI(title="Orbit")
parser = PubmedQueryParser()
ORBIT_PUBMED_SERVICE = os.getenv("ORBIT_PUBMED_SERVICE", None)
ORBIT_CTGOV_SERVICE = os.getenv("ORBIT_CTGOV_SERVICE", None)

@app.get("/", include_in_schema=False)
async def docs_redirect():
    return RedirectResponse(url="/docs")

if ORBIT_PUBMED_SERVICE is not None:

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
    async def info():
        einfo = EInfo()
        return einfo.get_info()


if ORBIT_CTGOV_SERVICE is not None:
    
    @app.get("/ct/api/v2/version", tags=["ClinicalTrials.gov"])
    async def ctgov_version():
        return {
            "apiVersion": f"2.0.5-(orbit-{ORBIT_VERSION})"
        }

    @app.get("/ct/api/v2/studies", tags=["ClinicalTrials.gov"])
    async def ctgov_studies(
        rformat: str = Query(default="json", description="how studies should be returned", alias="format", openapi_examples=["json","csv"]),
        query_term: str = Query(default=..., description="Other terms query in Essie expression syntax.", alias="query.term"),
        page_start: int = Query(default="0", description="the start index for studies)", alias="pageStart"),
        page_size: int = Query(default="20", description="the end index for studies", alias="pageSize"), 
    ):
        return get_ctgov_studies(rformat, query_term, page_start, page_size)

    @app.get("/ct/api/v2/studies/metadata", tags=["ClinicalTrials.gov"])
    async def ctgov_studies_metadata():
        return get_ctgov_metadata()

    @app.get("/ct/api/v2/studies/search-areas", tags=["ClinicalTrials.gov"])
    async def ctgov_studies_search_areas():
        return get_ctgov_searchareas()

    @app.get("/ct/api/v2/studies/{nctId}", tags=["ClinicalTrials.gov"])
    async def ctgov_study(nctId: str):
        return get_ctgov_study("json", nctId)

