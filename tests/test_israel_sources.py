from dataclasses import fields

from src.israel_sources.base import SearchQuery
from src.israel_sources.drushim import DrushimAdapter
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
    assert get_adapter("techmap").source == "techmap"


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
        "comeet",
        "techmap",
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


def test_search_engine_filters_unrelated_adapter_results():
    matching = IsraeliJob(
        source="test",
        source_job_id="1",
        title="Senior Backend Python Developer",
        company="API Co",
        location="Remote",
        description="Build Python APIs",
        apply_url="https://example.com/1",
        apply_email=None,
        apply_method="external_url",
        posted_at=None,
    )
    unrelated = IsraeliJob(
        source="test",
        source_job_id="2",
        title="Sales Manager",
        company="Sales Co",
        location="Remote",
        description="Own enterprise sales pipeline and work with Backend Developer teams",
        apply_url="https://example.com/2",
        apply_email=None,
        apply_method="external_url",
        posted_at=None,
    )

    filtered = IsraelSearchEngine.filter_jobs_by_query(
        [matching, unrelated],
        SearchQuery(keywords=["Backend Developer"], locations=["Remote"], limit=10),
    )

    assert filtered == [matching]
    assert IsraelSearchEngine.job_matches_query(
        unrelated,
        SearchQuery(keywords=["Backend Developer"], locations=["Remote"], limit=10),
    ) is False


def test_search_engine_accepts_economic_roles_for_economist_query():
    budget_control = IsraeliJob(
        source="test",
        source_job_id="finance-1",
        title="רפרנט/ית לתכנון פיננסי ובקרה תקציבית",
        company="Finance Co",
        location="Israel",
        description="עבודה בצוות כספים, תקציב, בקרה ואנליזות",
        apply_url="https://example.com/finance-1",
        apply_email=None,
        apply_method="external_url",
        posted_at=None,
    )
    unrelated = IsraeliJob(
        source="test",
        source_job_id="driver-1",
        title="נהג/ת עם רישיון רכב ציבורי",
        company="Transport Co",
        location="Israel",
        description="הסעות ושירות לקוחות",
        apply_url="https://example.com/driver-1",
        apply_email=None,
        apply_method="external_url",
        posted_at=None,
    )

    filtered = IsraelSearchEngine.filter_jobs_by_query(
        [budget_control, unrelated],
        SearchQuery(keywords=["כלכלן"], locations=["Israel"], limit=10),
    )

    assert filtered == [budget_control]


def test_drushim_economist_query_uses_finance_filters_and_no_broad_area():
    adapter = DrushimAdapter()

    url = adapter.build_search_url(
        SearchQuery(keywords=["כלכלן"], locations=["Israel", "Tel Aviv", "Haifa"], limit=200),
        page=3,
    )

    assert "api/jobs/search" in url
    assert "searchterm=%D7%9B%D7%9C%D7%9B%D7%9C%D7%9F" in url
    assert "catdir=9" in url
    assert "subcat=100" in url
    assert "page=3" in url
    assert "area=" not in url


def test_drushim_economist_parser_keeps_finance_jobs_and_drops_unrelated():
    adapter = DrushimAdapter()
    payload = """
    {
      "ResultList": [
        {
          "Code": 1,
          "Company": {"CompanyDisplayName": "Finance Co"},
          "SendCVButtonModel": {"ButtonLink": "https://www.drushim.co.il/sendcv.aspx?jobcode=1"},
          "JobInfo": {"Link": "/job/1/abc/", "JobCode": 1},
          "JobContent": {
            "FullName": "רפרנט/ית לתכנון פיננסי ובקרה תקציבית",
            "Description": "תפקיד בצוות כספים ובקרה",
            "Requirements": "Excel וניתוח תקציב",
            "SubCategories": [{"NameInHebrew": "כלכלן/ית"}],
            "Categories": [{"NameInHebrew": "כספים / שוק ההון"}],
            "Regions": [{"NameInHebrew": "תל אביב"}]
          }
        },
        {
          "Code": 2,
          "Company": {"CompanyDisplayName": "Transport Co"},
          "SendCVButtonModel": {"ButtonLink": "https://www.drushim.co.il/sendcv.aspx?jobcode=2"},
          "JobInfo": {"Link": "/job/2/abc/", "JobCode": 2},
          "JobContent": {
            "FullName": "נהג/ת עם רישיון רכב ציבורי",
            "Description": "הסעות ושירות לקוחות",
            "Requirements": "רישיון נהיגה",
            "SubCategories": [{"NameInHebrew": "תחבורה"}],
            "Categories": [{"NameInHebrew": "כללי"}],
            "Regions": [{"NameInHebrew": "חיפה"}]
          }
        }
      ]
    }
    """

    jobs = adapter.parse_jobs(payload, SearchQuery(keywords=["כלכלן"], locations=["Israel"], limit=200))

    assert len(jobs) == 1
    assert jobs[0].source_job_id == "1"
    assert jobs[0].title == "רפרנט/ית לתכנון פיננסי ובקרה תקציבית"


def test_parallel_search_filters_each_future_with_its_own_query():
    class QueryAwareAdapter:
        source = "query_aware"

        def search(self, query):
            title = query.keywords[0]
            return [
                IsraeliJob(
                    source=self.source,
                    source_job_id=title,
                    title=title,
                    company="Example",
                    location="Remote",
                    description="Result produced for the requested query",
                    apply_url=f"https://example.com/{title}",
                    apply_email=None,
                    apply_method="external_url",
                    posted_at=None,
                )
            ]

    engine = IsraelSearchEngine(sources=["remotive"])
    engine.adapters = [QueryAwareAdapter()]

    jobs = engine.search_from_plan(
        {
            "total_limit": 10,
            "jobs_per_source": 10,
            "max_workers": 2,
            "max_tasks": 10,
            "queries": [
                {"keywords": ["Alpha Developer"], "locations": ["Remote"], "limit": 10},
                {"keywords": ["Beta Analyst"], "locations": ["Remote"], "limit": 10},
            ],
        }
    )

    assert {job.title for job in jobs} == {"Alpha Developer", "Beta Analyst"}


def test_comeet_adapter_extracts_israel_jobs_from_positions_data():
    comeet = get_adapter("comeet")
    jobs = comeet.parse_jobs(
        """
        <script>
        COMPANY_POSITIONS_DATA = [
          {
            "uid": "abc123",
            "name": "Backend Developer",
            "company_name": "ExampleCo",
            "url_comeet_hosted_page": "https://www.comeet.com/jobs/example/abc123",
            "location": {"name": "Tel Aviv, Israel", "city": "Tel Aviv", "country": "Israel"}
          },
          {
            "uid": "outside",
            "name": "Sales Manager",
            "company_name": "ExampleCo",
            "url_comeet_hosted_page": "https://www.comeet.com/jobs/example/outside",
            "location": {"name": "Berlin", "city": "Berlin", "country": "Germany"}
          }
        ];
        </script>
        """,
        SearchQuery(keywords=["Backend Developer"], locations=["Israel"], limit=10),
    )

    assert len(jobs) == 1
    assert jobs[0].source == "comeet"
    assert jobs[0].title == "Backend Developer"
    assert jobs[0].company == "ExampleCo"


def test_techmap_adapter_extracts_jobs_from_csv():
    techmap = get_adapter("techmap")
    jobs = techmap.parse_jobs(
        '\ufeff"company","category","size","title","level","city","url","updated"\n'
        '"ExampleCo","Fintech","m","Junior Economist","Accountant","תל אביב-יפו",'
        '"https://jobs.example.com/junior-economist?utm_source=techmap","2026-05-19"\n',
        SearchQuery(keywords=["Junior Economist"], locations=["Israel"], limit=10),
    )

    assert len(jobs) == 1
    assert jobs[0].source == "techmap"
    assert jobs[0].title == "Junior Economist"
    assert jobs[0].company == "ExampleCo"
    assert jobs[0].location == "תל אביב-יפו"
    assert jobs[0].apply_url == "https://jobs.example.com/junior-economist"
    assert jobs[0].posted_at.year == 2026


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
