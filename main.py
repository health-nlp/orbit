from fastapi import FastAPI

from pybool_ir.experiments.retrieval import AdHocExperiment
from pybool_ir.index.pubmed import PubmedIndexer
from pybool_ir.query.pubmed.parser import PubmedQueryParser

import threading
import lucene

app = FastAPI()
vm = lucene.getVMEnv()
lock = threading.Lock()
parser = PubmedQueryParser()

@app.get("/esearch")
def esearch(term: str):
    lock.acquire()
    vm.attachCurrentThread()
    try:
        ast = parser.parse_ast(term)
        parser.parse_lucene(term)
        formatted_query = parser.format(ast)
        print(formatted_query)
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
    with AdHocExperiment(PubmedIndexer(index_path="/app/index"), raw_query=term) as experiment:
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