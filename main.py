from fastapi import FastAPI, HTTPException, Query

from pybool_ir.experiments.retrieval import AdHocExperiment
from pybool_ir.index.pubmed import PubmedIndexer
from pybool_ir.query.pubmed.parser import PubmedQueryParser
from pybool_ir.index.pubmed_document import PubmedArticle
from typing import List, Dict, Any

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

@app.get("/esearch")
async def esearch(term: str = Query(..., "Search term using boolean queries")):
    """
    ESearch-like endpoint.
    Example: GET /esearch?term=cancer+AND+therapy
    """
    lock.acquire()
    vm.attachCurrentThread()
    try:
        # Parse and prepare query (will raise on malformed query)
        ast = parser.parse_ast(term)
        parser.parse_lucene(term)
        formatted_query = parser.format(ast)
        print("Formatted query:", formatted_query)
    except Exception as e:
        lock.release()
        return {
            "header": {
                "type": "esearch",
                "verison": "0.3-openpm"
            },
            "esearchresult": {
                "ERROR": str(e),
            }
        }

    # Run the ad-hoc experiment using the index at LOCAL_INDEX_PATH
    with AdHocExperiment(PubmedIndexer(index_path=LOCAL_INDEX_PATH), raw_query=term) as experiment:
        results = experiment.run
        lock.release()
        return {
            "header": {
                "type": "esearch",
                "version": "0.3-openpm"
            },
            "esearchresult": {
                "count": f"{len(results)}",
                "retmax": "-1",
                "retstart": "0",
                "idlist": [str(result.doc_id) for result in results],
            },
            "translationset": {

            },
            "querytranslation": formatted_query
        }


# Implementing EFetch endpoint
# TODO finish implementation, by adding more options according to PubMed Documentation   
@app.get("/efetch")
async def efetch(id: str = Query(..., description="Comma seperated list of UIDs (e.g. '12345678', '90123456')")): 
    uid_list = [p.strip() for p in id.split(',') if p.strip()]

    lock.acquire()
    try: 
        vm.attachCurrentThread()
        
        lucene_query = " OR ".join([f"id:'{uid}'" for uid in uid_list])
        print(f"lucene_query: {lucene_query}")

        indexer = PubmedIndexer(index_path=LOCAL_INDEX_PATH, store_fields=True)
        indexer.open()

        articles: List[PubmedArticle] = indexer.search(query=lucene_query, n_hits=len(uid_list))
        article_dicts: List[Dict[str, Any]] = [article.to_dict() for article in articles]

        indexer.close()

        return {
            "header": {
                "type": "efetch",
                "version": "0.3-openpm",
            },
            "articleList": article_dicts,
            "error": None            
        }
    except Exception as e: 
        raise HTTPException(
            status_code = 500,
            detail = f"An error occured while processing Efetch or accessing index: {e}"
        )
    finally:
        lock.release()
