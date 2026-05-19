from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Type

from src.israel_sources.Jobnet import JobnetAdapter
from src.israel_sources.alljobs import AllJobsAdapter
from src.israel_sources.base import IsraelSourceAdapter, SearchQuery
from src.israel_sources.company_careers import CompanyCareersAdapter
from src.israel_sources.comeet import ComeetAdapter
from src.israel_sources.drushim import DrushimAdapter
from src.israel_sources.gotfriends import GotFriendsAdapter
from src.israel_sources.global_apis import ArbeitnowAdapter, GreenhouseAdapter, LeverAdapter, RemoteOkAdapter, RemotiveAdapter
from src.israel_sources.indeed import IndeedIsraelAdapter
from src.israel_sources.jobmaster import JobMasterAdapter
from src.israel_sources.models import IsraeliJob


ADAPTER_CLASSES: Dict[str, Type[IsraelSourceAdapter]] = {
    "drushim": DrushimAdapter,
    "Drushim": DrushimAdapter,
    "alljobs": AllJobsAdapter,
    "jobmaster": JobMasterAdapter,
    "gotfriends": GotFriendsAdapter,
    "indeed": IndeedIsraelAdapter,
    "Jobnet": JobnetAdapter,
    "jobnet": JobnetAdapter,
    "company_careers": CompanyCareersAdapter,
    "comeet": ComeetAdapter,
    "remotive": RemotiveAdapter,
    "arbeitnow": ArbeitnowAdapter,
    "remoteok": RemoteOkAdapter,
    "greenhouse": GreenhouseAdapter,
    "lever": LeverAdapter,
}


def get_adapter(source: str) -> IsraelSourceAdapter:
    try:
        return ADAPTER_CLASSES[source]()
    except KeyError as exc:
        available = ", ".join(sorted(ADAPTER_CLASSES))
        raise ValueError(f"Unknown Israeli job source '{source}'. Available sources: {available}") from exc


def get_all_adapters() -> List[IsraelSourceAdapter]:
    source_order = [
        "drushim",
        "alljobs",
        "jobmaster",
        "gotfriends",
        "indeed",
        "Jobnet",
        "company_careers",
        "comeet",
        "remotive",
        "arbeitnow",
        "remoteok",
        "greenhouse",
        "lever",
    ]
    return [get_adapter(source) for source in source_order]


def search_all_sources(query: SearchQuery) -> List[IsraeliJob]:
    jobs: List[IsraeliJob] = []
    seen: set = set()

    def _search_one(adapter):
        try:
            return adapter.search(query)
        except Exception:
            return []

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(_search_one, adapter): adapter for adapter in get_all_adapters()}
        for future in as_completed(futures):
            for job in future.result():
                key = (job.source, job.source_job_id)
                if key not in seen:
                    seen.add(key)
                    jobs.append(job)
                    if len(jobs) >= query.limit:
                        return jobs
    return jobs[: query.limit]
