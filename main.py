from fastapi import FastAPI, HTTPException, Query, Response

from pybool_ir.experiments.retrieval import AdHocExperiment
from pybool_ir.index.pubmed import PubmedIndexer
from pybool_ir.query.pubmed.parser import PubmedQueryParser
from pybool_ir.index.pubmed import PubmedArticle
from typing import List, Dict, Any

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


"""
    ESearch-like endpoint.
    Example: GET /esearch?term=cancer+AND+therapy
"""
@app.get("/esearch")
async def esearch(
    term: str = Query(default=..., description="Search term using boolean queries"),
    retstart: str = Query(default="0", description="the start index for UIDs (default=0)"),
    retmax: str = Query(default="20", description="the end index for UIDs (default=20)"), 
    retmode: str = Query(default="xml", description="Return format xml or json (default=xml)"),
    field: str = Query(default=None, description="Limitation to certain Entrez fields")
):
    
    # filtering for fields
    effective_query = term

    if field: 
        words = term.split()
        operators = {"AND", "OR", "NOT", "AND NOT"}

        processed_terms = [f"{word}[{field}]" if word.upper() in operators and "[" not in words else word for word in words]
        effective_query = " ".join(processed_terms)

    lock.acquire()
    try:
        vm.attachCurrentThread()

        # Parse and prepare query (will raise on malformed query)
        ast = parser.parse_ast(effective_query)
        parser.parse_lucene(effective_query)
        formatted_query = parser.format(ast)
        print("Formatted query:", formatted_query)
    

        # Run the ad-hoc experiment using the index at LOCAL_INDEX_PATH
        with AdHocExperiment(PubmedIndexer(index_path=LOCAL_INDEX_PATH), raw_query=formatted_query) as experiment:
            results = experiment.run()

            total_count = len(results)
            paginated_results = results[retstart : retstart+retmax]
            id_list = [str(res.doc_id) for res in paginated_results]

            result_obj = sr.ESearch(
                format=retmode,
                count=str(total_count),
                retmax=str(retmax),
                retstart=str(retstart),
                id_list=id_list,
                querytranslation=formatted_query,
                translationset={"from": term, "to": formatted_query}
            )

            if retmode.lower() == "xml":
                return Response(content=result_obj.to_xml(), media_type="application/xml")
            elif retmode.lower() == "json":
                return Response(content=result_obj.to_json(), media_type="application/json") 
            else: 
                return Response(content=result_obj.to_json(), media_tpye="application/json")
    
    
    except Exception as e:
        lock.release()

        result_obj = sr.ESearch(error=e)
        return Response(content=result_obj, media_type="application/json")
    finally: 
        lock.release()




# Implementing EFetch endpoint
# TODO finish implementation, by adding more options according to PubMed Documentation  
# TODO adjust return structure to use searchresult classes 
@app.get("efetch")
async def efetch(
    id: str = Query(default=..., description="Comma seperated list of UIDs (e.g. '12345678', '90123456')"),
    retmode: str = Query(default="json", description="Return format (json is default)")
):
    
    uid_list = [p.strip() for p in id.split(",") if p.strip()]

    lock.acquire()
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
        lock.release()
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


# ------------------------------------------------------

#OLD
# @app.get("/efetch")
# async def efetch(id: str = Query(..., description="Comma seperated list of UIDs (e.g. '12345678', '90123456')")): 
#     uid_list = [p.strip() for p in id.split(',') if p.strip()]

#     lock.acquire()
#     try: 
#         vm.attachCurrentThread()
        
#         lucene_query = " OR ".join([f"id:'{uid}'" for uid in uid_list])
#         print(f"lucene_query: {lucene_query}")

#         indexer = PubmedIndexer(index_path=LOCAL_INDEX_PATH, store_fields=True)
#         indexer.open()

#         articles: List[PubmedArticle] = indexer.search(query=lucene_query, n_hits=len(uid_list))
#         article_dicts: List[Dict[str, Any]] = [article.to_dict() for article in articles]

#         indexer.close()

#         return {
#             "header": {
#                 "type": "efetch",
#                 "version": "0.3-openpm",
#             },
#             "articleList": article_dicts,
#             "error": None            
#         }
#     except Exception as e: 
#         raise HTTPException(
#             status_code = 500,
#             detail = f"An error occured while processing Efetch or accessing index: {e}"
#         )
#     finally:
#         lock.release()





# from fastapi import FastAPI

# app = FastAPI()

# @app.get("/")
# def home():
#     return {"message": "API works! Import deactivated."}

# @app.get("/test")
# def test(): 
#     return "This is a text without anything else (TEST)"

