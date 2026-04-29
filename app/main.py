import os

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pybool_ir.query.pubmed.parser import PubmedQueryParser

from pubmed_updater import PubMedUpdater
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
app = FastAPI(title="Orbit", servers=[{"url": "/", "description": "Local Server"}])
parser = PubmedQueryParser()
updater_instance = PubMedUpdater()
ORBIT_PUBMED_SERVICE = os.getenv("ORBIT_PUBMED_SERVICE", None)
ORBIT_CTGOV_SERVICE = os.getenv("ORBIT_CTGOV_SERVICE", None)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Erlaubt deinem Browser, von überall zuzugreifen
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
async def docs_redirect():
    return RedirectResponse(url="/docs")

if ORBIT_PUBMED_SERVICE is not None:
    @app.get("/update", tags=["PubMed Updates"])
    async def set_update_frequency(
        frequency: str = Query(..., description="Possible frequencies: 'daily', 'weekly', 'monthly', 'off'")
    ):

        try: 
            message = updater_instance.set_frequency(frequency)
            return {"status": "success", "message": message}
        except ValueError as e: 
            raise HTTPException(status_code=500, detail=str(e))
        
    @app.get("/update/status", tags=["PubMed Updates"])
    async def get_update_status():
        jobs=updater_instance.scheduler.get_jobs()
        return {"active_jobs": len(jobs), "next_run_times": [str(job.next_run_time) for job in jobs], "is_running": updater_instance.scheduler.running}

    @app.get("/entrez/eutils/esearch.fcgi", tags=["PubMed Entrez"])
    async def esearch(
        term: str = Query(default=None, description="Search term using boolean queries", examples=["cancer", "(headache and ibuprofen)"]),
        retstart: int = Query(default="0", description="the start index for UIDs (default=0)"),
        retmax: int = Query(default="20", description="the end index for UIDs (default=20)"), 
        retmode: str = Query(default="xml", description="Return format xml or json (default=xml)", openapi_examples={"xml": {"value": "xml"},"json": {"value": "json"},"trec": {"value": "trec"}}),
        rettype: str = Query(default="uilist", description="Return standard XML output including uilist (default=uilist) or just 'Count' tag (count)"),
        field: str = Query(default=None, description="Limitation to certain Entrez fields"), 
        db: str = Query(default="pubmed", description="Database to search"),
        trecqid: str = Query(default="0", description="When returning a TREC run, the qid field."),
        trectag: str = Query(default="orbit", description="When returning a TREC run, the tag field.")):

        """
            # ESearch-like endpoint.
            
            ## Function
            Provides a list of UIDs matching a text query


            ## Required Parameters
            **term:** Pubmed query. All special characters must be URL encoded. 


            ## Optional Parameters
            **retstart:** Sequential index of the first UID in the retrieved set to be shown in the XML output (default=0, corresponding to the first record of the entire set).
            This parameter can be used in conjunction with retmax to download an arbitrary subset of UIDs retrieved from a search.

            **retmax:** Total number of UIDs from the retrieved set to be shown in the XML output (default=20). By defaul, ESearch only includes the first 20 UIDs retrieved in the XML
            output.

            **rettype:** Retrieval type. There are two allowed values for ESearch 'uilist' (default), which displays the standard XML output, and 'count', which displays only the <Count> tag.

            **retmode:** Retrieval type. Determines the format of the returned output. The default value is 'xml' for ESearch XML, but 'json' is also supported to return output in JSON format.

            **field:** Search field. If used, the entire search term will be limited to the specified Entrez field.

            ## Example
            GET /esearch?term=cancer+AND+therapy
        """

        if term is None:
            return sr.SearchResult(error="Empty term and query_key - nothing todo", retmode=retmode)

        esearch = ESearch(term=term, retstart=retstart, retmax=retmax, retmode=retmode, rettype=rettype, field=field, trecqid=trecqid, trectag=trectag)
        return esearch.search()

        

    @app.get("/entrez/eutils/efetch.fcgi", tags=["PubMed Entrez"])
    async def efetch(
        id: str = Query(default=..., description="Comma seperated list of UIDs (e.g. '12345678', '90123456')"),
        retmode: str = Query(default="xml", description="Return format (xml is default)", openapi_examples={"xml": {"value": "xml"}, "txt": {"value": "txt"}}),
        retstart: int = Query(default=None, description="optional start-index of given id-list"),
        retmax: int = Query(default=None, descrition="optional start-index of given id-list")
    ):
        """
        # EFetch-like endpoint

        ## Functions
        Return formatted data records for a list of input UIDs

        ## Required Parameters
        **id:** UID list. Either a single UID or a comma-delimited list of UIDs may be provided. All of the UIDs must be from the pubmed database.
        There is no set maximum for the number of UIDs that can be passed to EFetch.

        ## Optional Parameters
        **retmode:** Retrieval mode. This parameter specifies the data format of the records returned, such as plain text or XML
        
        **retstart:** Sequential index of the first record to be retrieved (default=0, corresponding to the first of the entire set). This parameter can be used in conjunction
        with retmax to download an arbitrary subset of records from the input set.
        
        **retmax:** Total number of records from the input set ot be retrieved without limitations
        """

        efetch = EFetch(id=id, retmode=retmode, retstart=retstart, retmax=retmax)
        return efetch.fetch()


    @app.get("/entrez/eutils/esummary.fcgi", tags=["PubMed Entrez"])
    async def esummary(
        id: str = Query(default=..., description="Comma seperated list of UIDs"),
        retmode: str = Query(default="json", description="return format: xml/json", openapi_examples={"xml": {"value": "xml"}, "json": {"value": "json"}}),
        retstart: int = Query(default=0, description="the start index (default=0)"), 
        retmax: int = Query(default=20, description="the end index (default=20)")
    ):

        """
        # EFetch-like endpoint

        ## Functions
        Return formatted data records for a list of input UIDs

        ## Required Parameters
        **id:** UID list. Either a single UID or a comma-delimited list of UIDs may be provided. All of the UIDs must be from the pubmed database.
        There is no set maximum for the number of UIDs that can be passed to EFetch.

        ## Optional Parameters
        **retmode:** Retrieval mode. This parameter specifies the data format of the returned output, such as plain JSON or XML

        **retstart:** Sequential index of the first DocSum to be retrieved (default=0, corresponding to the first of the entire set). This parameter can be used in conjunction
        with retmax to download an arbitrary subset of records from the input set.

        **retmax:** Total number of DocSum from the input set ot be retrieved without limitations
        """

        esummary = ESummary(id=id, retmode=retmode, retstart=retstart, retmax=retmax)
        return esummary.summarize()

    @app.get("/entrez/eutils/info.fcgi", tags=["PubMed Entrez"])
    async def info():
        """
        # EInfo-like endpoint

        ## Functions
        Provides a list of the names of all valid Entrez databases
        """

        einfo = EInfo()
        return einfo.get_info()


if ORBIT_CTGOV_SERVICE is not None:
    
    @app.get("/ct/api/v2/version", 
            tags=["ClinicalTrials.gov"], 
            summary="Orbit Version")
    async def ctgov_version():
        """
        # API Version Endpoint
        
        ## Function
        Returns version information about the Orbit API service.
        
        """
        return {
            "apiVersion": f"2.0.5-(orbit-{ORBIT_VERSION})"
        }

    @app.get("/ct/api/v2/studies", tags=["ClinicalTrials.gov"], summary="Studies")
    async def ctgov_studies(
        rformat: str = Query(default="json", description="how studies should be returned", alias="format", openapi_examples=["json","csv"]),
        query_term: str = Query(default=..., description="other terms query in Essie expression syntax.", alias="query.term"),
        page_start: int = Query(default="0", description="the start index for studies)", alias="pageStart"),
        page_size: int = Query(default="20", description="the end index for studies", alias="pageSize"), 
    ):
        """
        # Studies
        
        ## Function
        Returns a list of clinical trials that match the provided search criteria with support for pagination.
        
        ## Required Parameters
        **query.term:** The search query in Essie expression syntax. Must be URL encoded.

        
        ## Optional Parameters
        **format:** Output format - 'json' (default) or 'csv'.
        
        **pageStart:** Starting index for pagination (default=0).
        
        **pageSize:** Number of results per page (default=20, maximum=100).

        ## Query Syntax (Essie)
        The Essie query syntax supports:
        - **AND**: Both terms must appear (default)
        - **OR**: Either term can appear
        - **NOT**: Exclude term
        - **Phrases**: Use quotes for exact phrases
        - **Fields**: Use field:name syntax (e.g., AREA[Condition]cancer)
        
        ## Query Examples
        - AREA[Condition]cancer AND AREA[InterventionName]immunotherapy
        - AREA[LeadSponsorName]NIH AND AREA[Phase]PHASE3
        - AREA[Location]Germany AND RECR[Recruitment]RECRUITING
        - "breast cancer" AND AREA[OverallStatus]RECRUITING

        ## Example Request
        ```bash
        GET /ct/api/v2/studies?query.term=breast%20cancer
        ```
        """
        return get_ctgov_studies(rformat, query_term, page_start, page_size)


    @app.get("/ct/api/v2/studies/{nctId}", tags=["ClinicalTrials.gov"], summary="Single Study")
    async def ctgov_study(nctId: str):
        """
        # Single Study
        
        ## Function
        Returns the complete record for a single clinical trial identified by its NCT (National Clinical Trial) ID.
        
        ## Required Parameters
        **nctId:** The NCT ID of the clinical trial (e.g., 'NCT01234567'). Must be URL encoded if passed directly.

        ## Example
        ```bash
        GET /ct/api/v2/studies/NCT01234567
        ```

        """
        return get_ctgov_study("json", nctId)


    @app.get("/ct/api/v2/studies/metadata", tags=["ClinicalTrials.gov"], summary="Studies Metadata")
    async def ctgov_studies_metadata():
        """
        # Metadata
        
        ## Function
        Returns information about the structure of the clinical trial data, including available fields, their types, and descriptions.
        """
        return get_ctgov_metadata()

    @app.get("/ct/api/v2/studies/search-areas", tags=["ClinicalTrials.gov"], summary="Studies Search Areas")
    async def ctgov_studies_search_areas():
        """
        # Search Areas
        
        ## Function
        Returns information about all searchable areas (fields) in the ClinicalTrials.gov database.
        
        """
        return get_ctgov_searchareas()
