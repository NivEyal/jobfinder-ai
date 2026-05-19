from contextlib import ExitStack
from dataclasses import fields
from unittest.mock import patch

import pytest

from src.israel_sources.base import IsraelSourceAdapter, SearchQuery
from src.israel_sources.global_apis import ArbeitnowAdapter, GreenhouseAdapter, LeverAdapter, RemoteOkAdapter, RemotiveAdapter
from src.israel_sources.models import IsraeliJob
from src.israel_sources.registry import get_adapter, get_all_adapters, search_all_sources
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


# --- clean_text ---

def test_clean_text_none_returns_empty_string():
    assert IsraelSourceAdapter.clean_text(None) == ""


def test_clean_text_strips_html_tags():
    result = IsraelSourceAdapter.clean_text("<b>Hello</b> <i>World</i>")
    assert "<b>" not in result
    assert "<i>" not in result
    assert "Hello" in result
    assert "World" in result


def test_clean_text_normalizes_whitespace():
    result = IsraelSourceAdapter.clean_text("  too   many   spaces  ")
    assert result == "too many spaces"


def test_clean_text_collapses_internal_whitespace():
    result = IsraelSourceAdapter.clean_text("word1\t\n\r  word2")
    assert result == "word1 word2"


def test_clean_text_decodes_html_entities():
    result = IsraelSourceAdapter.clean_text("AT&amp;T &lt;Corp&gt;")
    assert result == "AT&T <Corp>"


def test_clean_text_converts_non_string_to_str():
    assert IsraelSourceAdapter.clean_text(42) == "42"
    assert IsraelSourceAdapter.clean_text(3.14) == "3.14"


def test_clean_text_empty_string():
    assert IsraelSourceAdapter.clean_text("") == ""


def test_clean_text_html_with_extra_whitespace():
    result = IsraelSourceAdapter.clean_text("  <div>  Hello   World  </div>  ")
    assert result == "Hello World"


# --- extract_email ---

def test_extract_email_returns_valid_email():
    result = IsraelSourceAdapter.extract_email("Send your CV to jobs@example.com today")
    assert result == "jobs@example.com"


def test_extract_email_returns_first_match_when_multiple():
    result = IsraelSourceAdapter.extract_email("a@foo.com or b@bar.com")
    assert result == "a@foo.com"


def test_extract_email_returns_none_when_no_email():
    result = IsraelSourceAdapter.extract_email("No email address here at all")
    assert result is None


def test_extract_email_returns_none_for_empty_string():
    result = IsraelSourceAdapter.extract_email("")
    assert result is None


def test_extract_email_returns_none_for_none_input():
    result = IsraelSourceAdapter.extract_email(None)
    assert result is None


def test_extract_email_handles_subdomains():
    result = IsraelSourceAdapter.extract_email("contact@mail.company.co.il")
    assert result == "contact@mail.company.co.il"


def test_extract_email_handles_plus_addressing():
    result = IsraelSourceAdapter.extract_email("user+tag@example.org")
    assert result == "user+tag@example.org"


def test_extract_email_ignores_malformed_no_at_sign():
    result = IsraelSourceAdapter.extract_email("notanemail.com")
    assert result is None


def test_extract_email_ignores_malformed_no_domain():
    result = IsraelSourceAdapter.extract_email("user@")
    assert result is None


# --- stable_id ---

def test_stable_id_is_deterministic():
    result1 = IsraelSourceAdapter.stable_id("https://example.com/job/1", "Engineer", "Acme")
    result2 = IsraelSourceAdapter.stable_id("https://example.com/job/1", "Engineer", "Acme")
    assert result1 == result2


def test_stable_id_same_inputs_same_output_repeated_calls():
    ids = {IsraelSourceAdapter.stable_id("url", "title", "company") for _ in range(10)}
    assert len(ids) == 1


def test_stable_id_different_inputs_different_output():
    id1 = IsraelSourceAdapter.stable_id("url1", "title", "company")
    id2 = IsraelSourceAdapter.stable_id("url2", "title", "company")
    assert id1 != id2


def test_stable_id_order_matters():
    id1 = IsraelSourceAdapter.stable_id("a", "b", "c")
    id2 = IsraelSourceAdapter.stable_id("c", "b", "a")
    assert id1 != id2


def test_stable_id_returns_16_char_hex():
    result = IsraelSourceAdapter.stable_id("any", "input", "here")
    assert len(result) == 16
    assert all(c in "0123456789abcdef" for c in result)


def test_stable_id_skips_empty_parts():
    id_with_empty = IsraelSourceAdapter.stable_id("url", "", "company")
    id_without_empty = IsraelSourceAdapter.stable_id("url", "company")
    assert id_with_empty == id_without_empty


# --- make_url ---

def test_make_url_no_params():
    adapter = RemotiveAdapter()
    url = adapter.make_url("/jobs")
    assert url.startswith(adapter.base_url.rstrip("/"))
    assert "?" not in url


def test_make_url_with_params():
    adapter = RemotiveAdapter()
    url = adapter.make_url("/jobs", {"search": "python", "location": "Israel"})
    assert "search=python" in url
    assert "location=Israel" in url
    assert "?" in url


def test_make_url_filters_none_params():
    adapter = RemotiveAdapter()
    url = adapter.make_url("/jobs", {"search": "python", "location": None})
    assert "location" not in url
    assert "search=python" in url


def test_make_url_filters_empty_string_params():
    adapter = RemotiveAdapter()
    url = adapter.make_url("/jobs", {"search": "python", "extra": ""})
    assert "extra" not in url


def test_make_url_filters_empty_list_params():
    adapter = RemotiveAdapter()
    url = adapter.make_url("/jobs", {"search": "python", "tags": []})
    assert "tags" not in url


def test_make_url_all_none_params_produces_no_query_string():
    adapter = RemotiveAdapter()
    url = adapter.make_url("/jobs", {"a": None, "b": None})
    assert "?" not in url


def test_make_url_none_params_arg():
    adapter = RemotiveAdapter()
    url = adapter.make_url("/jobs", None)
    assert "?" not in url


def test_make_url_joins_path_correctly():
    adapter = RemotiveAdapter()
    url1 = adapter.make_url("jobs")
    url2 = adapter.make_url("/jobs")
    assert url1 == url2


# --- SearchQuery ---

def test_search_query_keyword_text_joins_with_space():
    query = SearchQuery(keywords=["Python", "Developer"], locations=[], limit=10)
    assert query.keyword_text == "Python Developer"


def test_search_query_keyword_text_single_keyword():
    query = SearchQuery(keywords=["Engineer"], locations=[], limit=10)
    assert query.keyword_text == "Engineer"


def test_search_query_keyword_text_empty_keywords():
    query = SearchQuery(keywords=[], locations=[], limit=10)
    assert query.keyword_text == ""


def test_search_query_location_text_joins_with_space():
    query = SearchQuery(keywords=[], locations=["Tel Aviv", "Remote"], limit=10)
    assert query.location_text == "Tel Aviv Remote"


def test_search_query_location_text_single_location():
    query = SearchQuery(keywords=[], locations=["Israel"], limit=10)
    assert query.location_text == "Israel"


def test_search_query_location_text_empty_locations():
    query = SearchQuery(keywords=[], locations=[], limit=10)
    assert query.location_text == ""


def test_search_query_default_limit():
    query = SearchQuery()
    assert query.limit == 25


def test_search_query_is_frozen():
    query = SearchQuery(keywords=["Python"], locations=["Israel"], limit=10)
    with pytest.raises((AttributeError, TypeError)):
        query.limit = 99


# --- sample_job smoke tests ---

@pytest.mark.parametrize("source", [
    "drushim",
    "alljobs",
    "jobmaster",
    "gotfriends",
    "indeed",
    "Jobnet",
    "company_careers",
    "remotive",
    "arbeitnow",
    "remoteok",
    "greenhouse",
    "lever",
])
def test_sample_job_returns_israeli_job(source):
    adapter = get_adapter(source)
    job = adapter.sample_job()
    assert isinstance(job, IsraeliJob)
    assert job.source
    assert job.source_job_id
    assert job.title
    assert job.company
    assert job.apply_url


# --- search_all_sources ---

def _make_mock_job(source, job_id, title="Engineer"):
    return IsraeliJob(
        source=source,
        source_job_id=job_id,
        title=title,
        company="Test Co",
        location="Israel",
        description="Test description",
        apply_url=f"https://example.com/{job_id}",
        apply_email=None,
        apply_method="external_url",
        posted_at=None,
    )


def test_search_all_sources_respects_query_limit():
    query = SearchQuery(keywords=["Python"], locations=["Israel"], limit=3)

    jobs = [_make_mock_job("remotive", f"job-{i}") for i in range(10)]

    with patch.object(RemotiveAdapter, "search", lambda self, q: jobs), \
         patch.object(ArbeitnowAdapter, "search", lambda self, q: []), \
         patch.object(GreenhouseAdapter, "search", lambda self, q: []), \
         patch.object(LeverAdapter, "search", lambda self, q: []), \
         patch.object(RemoteOkAdapter, "search", lambda self, q: []):

        results = search_all_sources(query)

    assert len(results) <= query.limit


def test_search_all_sources_returns_empty_when_all_adapters_fail():
    query = SearchQuery(keywords=["Python"], locations=["Israel"], limit=10)

    def raise_error(self, q):
        raise RuntimeError("Network error")

    from src.israel_sources.drushim import DrushimAdapter
    from src.israel_sources.alljobs import AllJobsAdapter
    from src.israel_sources.jobmaster import JobMasterAdapter
    from src.israel_sources.gotfriends import GotFriendsAdapter
    from src.israel_sources.indeed import IndeedIsraelAdapter
    from src.israel_sources.Jobnet import JobnetAdapter
    from src.israel_sources.company_careers import CompanyCareersAdapter

    all_classes = [
        DrushimAdapter, AllJobsAdapter, JobMasterAdapter, GotFriendsAdapter,
        IndeedIsraelAdapter, JobnetAdapter, CompanyCareersAdapter,
        RemotiveAdapter, ArbeitnowAdapter, RemoteOkAdapter,
        GreenhouseAdapter, LeverAdapter,
    ]
    patches = [patch.object(cls, "search", raise_error) for cls in all_classes]

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        results = search_all_sources(query)

    assert results == []


def test_search_all_sources_aggregates_across_adapters():
    query = SearchQuery(keywords=["Python"], locations=["Israel"], limit=100)

    job_remotive = _make_mock_job("remotive", "r-1")
    job_arbeitnow = _make_mock_job("arbeitnow", "a-1")

    with patch.object(RemotiveAdapter, "search", lambda self, q: [job_remotive]), \
         patch.object(ArbeitnowAdapter, "search", lambda self, q: [job_arbeitnow]), \
         patch.object(GreenhouseAdapter, "search", lambda self, q: []), \
         patch.object(LeverAdapter, "search", lambda self, q: []), \
         patch.object(RemoteOkAdapter, "search", lambda self, q: []):

        results = search_all_sources(query)

    result_sources = {j.source for j in results}
    assert "remotive" in result_sources
    assert "arbeitnow" in result_sources


# --- fetch mocking ---

def test_adapter_search_uses_fetch_not_real_http():
    adapter = RemotiveAdapter()
    query = SearchQuery(keywords=["Python"], locations=["Israel"], limit=5)

    mock_payload = '{"jobs":[{"id":99,"title":"Mocked Job","company_name":"Mock Co","candidate_required_location":"Israel","description":"Mocked","url":"https://example.com/99","publication_date":"2026-01-01T00:00:00Z"}]}'

    with patch.object(adapter, "fetch", return_value=mock_payload) as mock_fetch:
        jobs = adapter.search(query)

    mock_fetch.assert_called()
    assert len(jobs) == 1
    assert jobs[0].title == "Mocked Job"
    assert jobs[0].source == "remotive"


def test_adapter_search_stops_on_empty_page():
    adapter = RemotiveAdapter()
    query = SearchQuery(keywords=["Python"], locations=["Israel"], limit=50)

    call_count = 0

    def fake_fetch(url, timeout=8):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '{"jobs":[{"id":1,"title":"Job One","company_name":"Co","candidate_required_location":"Israel","description":"Desc","url":"https://example.com/1","publication_date":"2026-01-01T00:00:00Z"}]}'
        return '{"jobs":[]}'

    with patch.object(adapter, "fetch", side_effect=fake_fetch):
        jobs = adapter.search(query)

    assert len(jobs) == 1
    assert call_count == 2


def test_adapter_search_enforces_per_adapter_limit():
    adapter = RemotiveAdapter()
    query = SearchQuery(keywords=["Python"], locations=["Israel"], limit=2)

    many_jobs_payload = '{"jobs":[' + ",".join(
        f'{{"id":{i},"title":"Job {i}","company_name":"Co","candidate_required_location":"Israel","description":"Desc","url":"https://example.com/{i}","publication_date":"2026-01-01T00:00:00Z"}}'
        for i in range(1, 11)
    ) + "]}"

    with patch.object(adapter, "fetch", return_value=many_jobs_payload):
        jobs = adapter.search(query)

    assert len(jobs) <= query.limit


def test_arbeitnow_adapter_fetch_mocked():
    adapter = ArbeitnowAdapter()
    query = SearchQuery(keywords=["React"], locations=["Remote"], limit=5)

    mock_payload = '{"data":[{"slug":"react-dev","title":"React Developer","company_name":"FrontCo","location":"Remote","remote":true,"description":"Build UIs","url":"https://example.com/react-dev","created_at":1770000000}]}'

    with patch.object(adapter, "fetch", return_value=mock_payload):
        jobs = adapter.search(query)

    assert len(jobs) == 1
    assert jobs[0].source == "arbeitnow"
    assert jobs[0].title == "React Developer"


def test_greenhouse_adapter_fetch_mocked():
    adapter = GreenhouseAdapter()
    query = SearchQuery(keywords=["Data"], locations=["Israel"], limit=5)

    mock_payload = '{"name":"DataCo","jobs":[{"id":42,"title":"Data Engineer","absolute_url":"https://example.com/42","content":"Spark pipelines","location":{"name":"Tel Aviv"},"updated_at":"2026-01-01T00:00:00Z"}]}'

    with patch.object(adapter, "fetch", return_value=mock_payload):
        jobs = adapter.search(query)

    assert len(jobs) == 1
    assert jobs[0].source == "greenhouse"
    assert jobs[0].source_job_id == "42"


def test_lever_adapter_fetch_mocked():
    adapter = LeverAdapter()
    query = SearchQuery(keywords=["PM"], locations=["Remote"], limit=5)

    mock_payload = '[{"id":"lever-123","text":"Product Manager","company":"ProdCo","hostedUrl":"https://example.com/lever-123","categories":{"location":"Remote"},"lists":[{"text":"Responsibilities","content":["Own roadmap"]}],"createdAt":1770000000000}]'

    with patch.object(adapter, "fetch", return_value=mock_payload):
        jobs = adapter.search(query)

    assert len(jobs) == 1
    assert jobs[0].source == "lever"
    assert jobs[0].source_job_id == "lever-123"


def test_remoteok_adapter_fetch_mocked():
    adapter = RemoteOkAdapter()
    query = SearchQuery(keywords=["Go"], locations=["Remote"], limit=5)

    mock_payload = '[{"legal":"skip"},{"id":"remoteok-55","position":"Go Developer","company":"GoFirm","location":"Remote","tags":["golang"],"url":"https://example.com/55","date":"2026-01-01T00:00:00Z"}]'

    with patch.object(adapter, "fetch", return_value=mock_payload):
        jobs = adapter.search(query)

    assert len(jobs) == 1
    assert jobs[0].source == "remoteok"
