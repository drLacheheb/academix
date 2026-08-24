from abg_discovery.scraper import AbgDiscovery
from core.domain.interfaces.http import BaseHttpClient
from euraxess_discovery.scraper import EuraxessDiscovery
from researchgate_discovery.scraper import ResearchGateDiscovery


class MultiPageMockHttpClient(BaseHttpClient):
    def __init__(
        self, get_pages: dict[str, bytes], post_pages: dict[tuple[str, str], bytes] | None = None
    ):
        self.get_pages = get_pages
        self.post_pages = post_pages or {}

    def fetch(self, url: str) -> bytes | None:
        return self.get_pages.get(url)

    def post(
        self,
        url: str,
        data: dict | str | None = None,
        headers: dict | None = None,
    ) -> bytes | None:
        if isinstance(data, str):
            for (ep, payload_sub), resp in self.post_pages.items():
                if ep == url and payload_sub in data:
                    return resp
        return None

    def close(self) -> None:
        pass


def test_euraxess_search_all_full_scroll_pagination():
    # Page 0 has 2 jobs, Page 1 has 1 job, Page 2 is empty
    page0 = b"""
    <div>
        <a href="/jobs/101"><span>Job 101</span></a>
        <a href="/jobs/102"><span>Job 102</span></a>
    </div>
    """
    page1 = b"""
    <div>
        <a href="/jobs/103"><span>Job 103</span></a>
    </div>
    """
    page2 = b"""<div></div>"""

    dummy = EuraxessDiscovery(MultiPageMockHttpClient({}))
    mock_http = MultiPageMockHttpClient(
        {
            dummy._build_browse_url(0): page0,
            dummy._build_browse_url(1): page1,
            dummy._build_browse_url(2): page2,
        }
    )

    scraper = EuraxessDiscovery(mock_http, max_pages=-1)
    jobs = scraper.search_all()

    assert len(jobs) == 3
    assert [j.url for j in jobs] == [
        "https://euraxess.ec.europa.eu/jobs/101",
        "https://euraxess.ec.europa.eu/jobs/102",
        "https://euraxess.ec.europa.eu/jobs/103",
    ]


def test_researchgate_search_all_max_pages_limit():
    page1 = b"""<div><a href="/job/201_Slug_One">Job 201</a></div>"""
    page2 = b"""<div><a href="/job/202_Slug_Two">Job 202</a></div>"""
    page3 = b"""<div><a href="/job/203_Slug_Three">Job 203</a></div>"""

    mock_http = MultiPageMockHttpClient(
        {
            "https://www.researchgate.net/jobs?page=1": page1,
            "https://www.researchgate.net/jobs?page=2": page2,
            "https://www.researchgate.net/jobs?page=3": page3,
        }
    )

    # Limit to 2 pages max
    scraper = ResearchGateDiscovery(mock_http, max_pages=2)
    jobs = scraper.search_all()

    assert len(jobs) == 2
    assert jobs[0].url == "https://www.researchgate.net/job/201_Slug_One"
    assert jobs[1].url == "https://www.researchgate.net/job/202_Slug_Two"


def test_abg_search_all_post_pagination():
    page1_html = b"""
    <div>
        <a href="/candidatOffres/show/id_offre/501">ABG Offer 501</a>
    </div>
    """
    page2_html = b"""
    <div>
        <a href="/candidatOffres/show/id_offre/502">ABG Offer 502</a>
    </div>
    """
    page3_empty = b"""<div></div>"""

    mock_http = MultiPageMockHttpClient(
        get_pages={},
        post_pages={
            (AbgDiscovery.SEARCH_ENDPOINT, "page=1"): page1_html,
            (AbgDiscovery.SEARCH_ENDPOINT, "page=2"): page2_html,
            (AbgDiscovery.SEARCH_ENDPOINT, "page=3"): page3_empty,
        },
    )

    scraper = AbgDiscovery(mock_http, max_pages=-1)
    jobs = scraper.search_all()

    assert len(jobs) == 2
    assert jobs[0].url == "https://www.abg.asso.fr/candidatOffres/show/id_offre/501"
    assert jobs[1].url == "https://www.abg.asso.fr/candidatOffres/show/id_offre/502"
