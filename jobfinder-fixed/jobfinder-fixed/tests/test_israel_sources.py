from dataclasses import fields

from src.israel_sources.base import SearchQuery
from src.israel_sources.global_apis import ArbeitnowAdapter, GreenhouseAdapter, LeverAdapter, RemoteOkAdapter, RemotiveAdapter
from src.israel_sources.models import IsraeliJob
from src.israel_sources.registry import get_adapter, get_all_adapters
from src.israel_sources.search_engine import IsraelSearchEngine


def test_registered_adapters_return_israeli_job_contract():
    expected_fields = [field.name for field in fields(IsraeliJob)]

    for adapter in get_all_adapters():
        job = adapter.sample_job()
        data = job.to_dict()

        assert isinstance(job, IsraeliJob)
        assert list(data.keys()) == expected_fields
        assert job.source
        assert job.source_job_id
        assert job.title
        assert job.company
        assert job.location
        assert job.description
        assert job.apply_url
        assert job.apply_method
        expanded_job = job.to_job()
        assert expanded_job.source == job.source
        assert expanded_job.source_job_id == job.source_job_id
        assert expanded_job.title
        assert expanded_job.fingerprint


def test_registry_supports_requested_source_aliases():
    assert get_adapter("drushim").source == "drushim"
    assert get_adapter("Drushim").source == "drushim"
    assert get_adapter("Jobnet").source == "jobnet"


def test_search_engine_lists_sources():
    engine = IsraelSearchEngine()
    assert engine.source_names() == [
        "drushim",
        "alljobs",
        "jobmaster",
        "gotfriends",
        "indeed",
        "jobnet",
        "company_careers",
        "remotive",
        "arbeitnow",
        "remoteok",
        "greenhouse",
        "lever",
    ]


def test_search_engine_respects_cancel_callback():
    engine = IsraelSearchEngine(sources=["remotive"], progress_callback=lambda _: None, cancel_callback=lambda: True)
    jobs = engine.search_from_plan(
        {
            "total_limit": 100,
            "jobs_per_source": 100,
            "sources": ["remotive"],
            "queries": [{"keywords": ["Backend Developer"], "locations": ["Remote"], "limit": 100}],
        }
    )

    assert jobs == []


def test_global_api_adapters_parse_jobs():
    remotive = RemotiveAdapter().parse_jobs(
        '{"jobs":[{"id":1,"title":"Backend Developer","company_name":"Remote Co","candidate_required_location":"Worldwide","description":"Python APIs","url":"https://example.com/1","publication_date":"2026-05-01T00:00:00Z"}]}',
        SearchQuery(keywords=["Backend Developer"], locations=["Remote"], limit=10),
    )
    arbeitnow = ArbeitnowAdapter().parse_jobs(
        '{"data":[{"slug":"job-1","title":"Frontend Developer","company_name":"Web Co","location":"Berlin","remote":true,"description":"React","url":"https://example.com/2","created_at":1770000000}]}',
        SearchQuery(keywords=["Frontend Developer"], locations=["Worldwide"], limit=10),
    )
    remoteok = RemoteOkAdapter().parse_jobs(
        '[{"legal":"metadata"},{"id":3,"position":"DevOps Engineer","company":"Ops Co","location":"Remote","tags":["kubernetes"],"url":"https://example.com/3","date":"2026-05-01T00:00:00Z"}]',
        SearchQuery(keywords=["DevOps"], locations=["Remote"], limit=10),
    )
    greenhouse = GreenhouseAdapter().parse_jobs(
        '{"name":"Cloud Co","jobs":[{"id":4,"title":"Data Analyst","absolute_url":"https://example.com/4","content":"SQL analytics","location":{"name":"Tel Aviv"},"updated_at":"2026-05-01T00:00:00Z"}]}',
        SearchQuery(keywords=["Data Analyst"], locations=["Israel"], limit=10),
    )
    lever = LeverAdapter().parse_jobs(
        '[{"id":"5","text":"Product Manager","company":"Product Co","hostedUrl":"https://example.com/5","categories":{"location":"Remote"},"lists":[{"text":"Own roadmap","content":["SaaS"]}],"createdAt":1770000000000}]',
        SearchQuery(keywords=["Product Manager"], locations=["Remote"], limit=10),
    )

    jobs = remotive + arbeitnow + remoteok + greenhouse + lever
    assert len(jobs) == 5
    assert {job.source for job in jobs} == {"remotive", "arbeitnow", "remoteok", "greenhouse", "lever"}
    assert all(job.apply_url for job in jobs)


def test_real_parsers_extract_jobs_from_fixture_snippets():
    jobmaster = get_adapter("jobmaster")
    jobmaster_jobs = jobmaster.parse_jobs(
        """
        <article id="misra9758372" class="CardStyle JobItem font14">
          <a class="CardHeader View_Job_Details" href='/jobs/checknum.asp?key=9758372'>RT Embedded Engineer</a>
          <a class="font14 CompanyNameLink"><span>B-net</span></a>
          <li class="jobLocation"><span>נתניה, תל אביב יפו</span></li>
          <div class="jobShortDescription Gray">Embedded Linux role</div>
        </article>
        """,
        None,
    )
    assert jobmaster_jobs[0].source_job_id == "9758372"

    alljobs = get_adapter("alljobs")
    alljobs_jobs = alljobs.parse_jobs(
        """
        <div class="job-content-top">
          <a title="דרושים | Senior Embedded Software Engineer" href="/Search/UploadSingle.aspx?JobID=8447575">
            <h2>Senior Embedded Software Engineer</h2>
          </a>
          <div class="T14"><a>Example Co</a></div>
          <div class="job-content-top-location-ltr"><b>Location: </b>Netanya</div>
          <div id="job-body-content8447575">C++ Embedded Linux</div>
        </div>
        """,
        None,
    )
    assert alljobs_jobs[0].source_job_id == "8447575"

    gotfriends = get_adapter("gotfriends")
    gotfriends_jobs = gotfriends.parse_jobs(
        """
        <div class="item">
          <a href="/jobslobby/software/full-stack-developer/153797/" class="position p-1108">
            <h2 class="title">Full Stack AI Engineer</h2>
          </a>
          <span class="info-label">מיקום:</span><span class="info-data">ת"א והמרכז</span>
          <div class="desc"><div class="title_c">תיאור המשרה:</div>AI platform role</div>
          <div class="career_num">מס&#x27; משרה: 153797</div>
        </div>
        """,
        None,
    )
    assert gotfriends_jobs[0].source_job_id == "153797"

    jobnet = get_adapter("Jobnet")
    jobnet_jobs = jobnet.parse_jobs(
        """
        <div itemscope itemtype="https://schema.org/JobPosting">
          <a href='/jobs?positionid=13107719'><h2 itemprop="title">Software Engineer</h2></a>
          <p itemprop="hiringOrganization"><a>Example Company</a></p>
          <p class="boxDateCls" itemprop="datePosted">17/05/2026</p>
          <div itemprop="description">Build systems</div>
          <strong>אזור:</strong> תל אביב</div>
        </div>
        """,
        None,
    )
    assert jobnet_jobs[0].source_job_id == "13107719"
