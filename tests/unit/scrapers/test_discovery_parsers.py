from abg_discovery.scraper import AbgDiscovery
from academictransfer_discovery.scraper import AcademicTransferDiscovery
from core.domain.interfaces.http import BaseHttpClient
from euraxess_discovery.scraper import EuraxessDiscovery
from eurosciencejobs_discovery.scraper import EuroScienceJobsDiscovery
from naturecareers_discovery.scraper import NatureCareersDiscovery
from researchgate_discovery.scraper import ResearchGateDiscovery


class MockHttpClient(BaseHttpClient):
    def __init__(self, responses: dict[str, bytes] | None = None):
        self.responses = responses or {}

    def fetch(self, url: str) -> bytes | None:
        return self.responses.get(url)

    def post(
        self,
        url: str,
        data: dict | str | None = None,
        headers: dict | None = None,
    ) -> bytes | None:
        return self.responses.get(url)

    def close(self) -> None:
        pass


def test_abg_search_page_parsing():
    html = """
    <div>
        <table>
            <tr>
                <td>
                    <a href="/candidatOffres/show/id_offre/133882">
                        Postdoctoral Researcher in Quantum Physics
                    </a>
                </td>
            </tr>
            <tr>
                <td>
                    <a href="/candidatOffres/show/id_offre/133883">
                        PhD Candidate in Materials Science
                    </a>
                </td>
            </tr>
        </table>
    </div>
    """
    scraper = AbgDiscovery(MockHttpClient())
    jobs = scraper._parse_search_page(html)

    assert len(jobs) == 2
    assert jobs[0].title == "Postdoctoral Researcher in Quantum Physics"
    assert jobs[0].url == "https://www.abg.asso.fr/candidatOffres/show/id_offre/133882"
    assert jobs[0].source == "ABG"
    assert jobs[1].title == "PhD Candidate in Materials Science"
    assert jobs[1].url == "https://www.abg.asso.fr/candidatOffres/show/id_offre/133883"


def test_euraxess_search_page_parsing():
    html = """
    <div class="view-content">
        <article>
            <a href="/jobs/241850">
                <span>Tenure-Track Assistant Professor in Computer Science</span>
            </a>
        </article>
        <article>
            <a href="/jobs/241851">
                <span>Postdoc in Condensed Matter Theory</span>
            </a>
        </article>
    </div>
    """
    scraper = EuraxessDiscovery(MockHttpClient())
    jobs = scraper._parse_search_page(html)

    assert len(jobs) == 2
    assert jobs[0].title == "Tenure-Track Assistant Professor in Computer Science"
    assert jobs[0].url == "https://euraxess.ec.europa.eu/jobs/241850"
    assert jobs[0].source == "EURAXESS"
    assert jobs[1].title == "Postdoc in Condensed Matter Theory"
    assert jobs[1].url == "https://euraxess.ec.europa.eu/jobs/241851"


def test_researchgate_search_page_parsing():
    html = """
    <div class="job-list">
        <div class="job-item">
            <a href="https://www.researchgate.net/job/1038270_Physician_Head_of_Clinical_Development">
                Head of Clinical Development
            </a>
        </div>
        <div class="job-item">
            <a href="/job/1038271_Postdoctoral_Fellow_in_Neuroscience">
                Postdoctoral Fellow in Neuroscience
            </a>
        </div>
    </div>
    """
    scraper = ResearchGateDiscovery(MockHttpClient())
    jobs = scraper._parse_search_page(html)

    assert len(jobs) == 2
    assert "https://www.researchgate.net/job/1038270_Physician_Head_of_Clinical_Development" in [
        j.url for j in jobs
    ]
    assert "https://www.researchgate.net/job/1038271_Postdoctoral_Fellow_in_Neuroscience" in [
        j.url for j in jobs
    ]
    assert any("Clinical Development" in j.title for j in jobs)


def test_naturecareers_search_page_and_sitemap_parsing():
    # 1. Test search page HTML parser
    html = """
    <div class="results">
        <a href="/naturecareers/job/12345/senior-scientist-genomics/">
            Senior Scientist in Genomics
        </a>
    </div>
    """
    scraper = NatureCareersDiscovery(MockHttpClient())
    jobs_html = scraper._parse_search_page(html)
    assert len(jobs_html) == 1
    assert jobs_html[0].title == "Senior Scientist in Genomics"
    assert (
        jobs_html[0].url
        == "https://www.nature.com/naturecareers/job/12345/senior-scientist-genomics/"
    )

    # 2. Test sitemap XML parser
    sitemap_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc>https://www.nature.com/naturecareers/job/78910/postdoctoral-fellow-in-ai/</loc>
        </url>
    </urlset>
    """
    mock_http = MockHttpClient({NatureCareersDiscovery.SITEMAP_JOBS_DEFAULT: sitemap_xml})
    scraper_sm = NatureCareersDiscovery(mock_http)
    jobs_sm = scraper_sm.fetch_all_jobs_from_sitemap()
    assert len(jobs_sm) == 1
    assert (
        jobs_sm[0].url
        == "https://www.nature.com/naturecareers/job/78910/postdoctoral-fellow-in-ai/"
    )
    assert "Postdoctoral Fellow In Ai" in jobs_sm[0].title


def test_academictransfer_search_page_and_sitemap_parsing():
    # 1. Test HTML search page parser
    html = """
    <div>
        <article>
            <a href="/en/jobs/345678/assistant-professor-in-robotics/">
                <h3>Assistant Professor in Robotics</h3>
            </a>
        </article>
    </div>
    """
    scraper = AcademicTransferDiscovery(MockHttpClient())
    jobs_html = scraper._parse_search_page(html)
    assert len(jobs_html) == 1
    assert jobs_html[0].title == "Assistant Professor in Robotics"
    assert (
        jobs_html[0].url
        == "https://www.academictransfer.com/en/jobs/345678/assistant-professor-in-robotics/"
    )

    # 2. Test Sitemap XML parser
    sitemap_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc>https://www.academictransfer.com/en/jobs/999/phd-in-quantum-nanotechnology/</loc>
        </url>
    </urlset>
    """
    mock_http = MockHttpClient({AcademicTransferDiscovery.SITEMAP_URL: sitemap_xml})
    scraper_sm = AcademicTransferDiscovery(mock_http)
    jobs_sm = scraper_sm.fetch_all_jobs_from_sitemap()
    assert len(jobs_sm) == 1
    assert "Phd In Quantum Nanotechnology" in jobs_sm[0].title
    assert (
        jobs_sm[0].url
        == "https://www.academictransfer.com/en/jobs/999/phd-in-quantum-nanotechnology/"
    )


def test_eurosciencejobs_search_page_and_sitemap_parsing():
    # 1. Test HTML search page parser
    html = """
    <div>
        <a href="/job_display/556677/Senior_Bioinformatics_Researcher_EMBL">
            Senior Bioinformatics Researcher
        </a>
    </div>
    """
    scraper = EuroScienceJobsDiscovery(MockHttpClient())
    jobs_html = scraper._parse_search_page(html)
    assert len(jobs_html) == 1
    assert jobs_html[0].title == "Senior Bioinformatics Researcher"
    assert (
        jobs_html[0].url
        == "https://www.eurosciencejobs.com/job_display/556677/Senior_Bioinformatics_Researcher_EMBL"
    )

    # 2. Test sitemap and category page crawl parser
    sitemap_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <loc>https://www.eurosciencejobs.com/jobs/bioinformatics</loc>
    </urlset>
    """
    cat_html = b"""
    <div>
        <a href="/job_display/889900/Postdoc_in_Genomics">Link</a>
    </div>
    """
    mock_http = MockHttpClient(
        {
            EuroScienceJobsDiscovery.SITEMAP_URL: sitemap_xml,
            "https://www.eurosciencejobs.com/jobs/bioinformatics": cat_html,
        }
    )
    scraper_sm = EuroScienceJobsDiscovery(mock_http)
    jobs_sm = scraper_sm.fetch_all_jobs_from_sitemap()
    assert len(jobs_sm) == 1
    assert (
        jobs_sm[0].url == "https://www.eurosciencejobs.com/job_display/889900/Postdoc_in_Genomics"
    )
    assert "Postdoc In Genomics" in jobs_sm[0].title
