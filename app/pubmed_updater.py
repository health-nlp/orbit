import os
import subprocess

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import RedirectResponse
from pybool_ir.query.pubmed.parser import PubmedQueryParser

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pydantic import BaseModel

import entrez.searchresult as sr
from entrez.esearch import ESearch 
from entrez.efetch import EFetch
from entrez.esummary import ESummary
from entrez.einfo import EInfo

from ctgov.studies import studies as get_ctgov_studies
from ctgov.studies import study as get_ctgov_study
from ctgov.studies import metadata as get_ctgov_metadata
from ctgov.studies import searchareas as get_ctgov_searchareas

class PubMedUpdater: 
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.job_id = "pubmed_auto_update"
        self.update_target = os.getenv("ORBIT_PUBMED_UPDATE_PATH", "./data/updates")
        self.index_path = os.getenv("ORBIT_PUBMED_INDEX_PATH", "./data/index")

    def _run_update_task(self):
        try: 
            subprocess.run(["uv", "run", "-m", "pybool_ir.cli", "pubmed", "update", "-u", self.update_target], check=True)

            subprocess.run(["uv", "run", "-m", "pybool_ir.cli", "pubmed", "process", "-b", self.update_target, "-o", "update_tmp.jsonl"], check=True)
            subprocess.run(["uv", "run", "-m", "pybool_ir.cli", "pubmed", "index", "-b", "update_tmp.jsonl", "-i", self.index_path, "--append"], check=True)

            if os.path.exists("update_tmp.jsonl"): 
                os.remove("update_tmp.jsonl")
        except subprocess.CalledProcessError as e: 
            print(f">>> Error while updating: {e}")

    def set_frequency(self, frequency: str): 
        if self.scheduler.get_job(self.job_id):
            self.scheduler.remove_job(self.job_id)

        freq = frequency.lower()
        if freq == "daily": 
            trigger = CronTrigger(hour=2, minute=0)
        elif freq == "weekly": 
            trigger = CronTrigger(day_of_week="sun", hour=2, minute=0)
        elif freq == "monthly": 
            trigger = CronTrigger(day='1', hour=2, minute=0)
        elif freq == "off": 
            return "automatic updates deactivated"
        else: 
            raise ValueError("Illegal frequency. Allowed frequencies are: daily, weekly, monthly or off")
        
        self.scheduler.add_job(
            func=self._run_update_task,
            trigger=trigger,
            id=self.job_id,
            replace_existing=True
        )

        return f"Update frequency successfully set to '{freq}'."
    
