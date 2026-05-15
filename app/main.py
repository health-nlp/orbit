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

import time
from datetime import datetime

ORBIT_VERSION = "0.1.0"
app = FastAPI(title="Orbit", servers=[{"url": "/", "description": "Local Server"}])
parser = PubmedQueryParser()
updater_instance = PubMedUpdater()
ORBIT_PUBMED_SERVICE = os.getenv("ORBIT_PUBMED_SERVICE", None)
ORBIT_CTGOV_SERVICE = os.getenv("ORBIT_CTGOV_SERVICE", None)
ORBIT_PUBMED_UPDATE_DISPLAY = os.getenv("ORBIT_PUBMED_UPDATE_DISPLAY", None)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
async def docs_redirect():
    return RedirectResponse(url="/docs")

if ORBIT_PUBMED_SERVICE is not None:

    if ORBIT_PUBMED_UPDATE_DISPLAY is not None:
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


        @app.get("/update/verify", tags=["PubMed Updates"])
        async def verify_index_update():
            index_path = updater_instance.index_path
            update_path = updater_instance.update_target

            if not os.path.exists(index_path):
                raise HTTPException(status_code=404, detail=f"Index path not found: {index_path}")

            # Index-Dateien und deren Modification-Time einsammeln
            index_files = []
            for root, dirs, files in os.walk(index_path):
                for f in files:
                    full_path = os.path.join(root, f)
                    mtime = os.path.getmtime(full_path)
                    index_files.append((full_path, mtime))

            if not index_files:
                raise HTTPException(status_code=404, detail="No files found in index directory")

            latest_index_file, latest_index_mtime = max(index_files, key=lambda x: x[1])
            latest_index_dt = datetime.fromtimestamp(latest_index_mtime)

            # Update-Dateien checken (die heruntergeladenen XMLs)
            update_files = []
            if os.path.exists(update_path):
                for root, dirs, files in os.walk(update_path):
                    for f in files:
                        full_path = os.path.join(root, f)
                        mtime = os.path.getmtime(full_path)
                        update_files.append((full_path, mtime))

            latest_update_dt = None
            latest_update_file = None
            if update_files:
                latest_update_file, latest_update_mtime = max(update_files, key=lambda x: x[1])
                latest_update_dt = datetime.fromtimestamp(latest_update_mtime)

            # Wurde der Index NACH dem letzten Update aktualisiert?
            index_is_current = (
                latest_update_dt is None or latest_index_dt >= latest_update_dt
            )

            return {
                "index_path": index_path,
                "index_last_modified": latest_index_dt.isoformat(),
                "index_last_modified_file": latest_index_file,
                "update_path": update_path,
                "update_last_download": latest_update_dt.isoformat() if latest_update_dt else None,
                "update_last_download_file": latest_update_file,
                "index_is_current": index_is_current,
                "checked_at": datetime.now().isoformat(),
            }


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

    @app.get("/entrez/eutils/einfo.fcgi", tags=["PubMed Entrez"])
    async def info():
        """
        # EInfo-like endpoint

        ## Functions
        Provides a list of the names of all valid Entrez databases
        """

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


