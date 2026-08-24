import json

from abg_sourcing.scraper import AbgSourcing
from academictransfer_sourcing.scraper import AcademicTransferSourcing
from core.infrastructure.http.http_client import HttpClient
from euraxess_sourcing.scraper import EuraxessSourcing
from eurosciencejobs_sourcing.scraper import EuroScienceJobsSourcing
from naturecareers_sourcing.scraper import NatureCareersSourcing
from researchgate_sourcing.scraper import ResearchGateSourcing


def test_abg_html_parsing():
    html = """
    <html>
        <body>
            <h1>Postdoctoral Researcher in Quantum Physics</h1>
            <table class="tab_offre_infos">
                <tr><th>Référence</th><td>RéfABG-133882</td></tr>
                <tr><th>Type de contrat</th><td>Sujet de Thèse</td></tr>
                <tr><th>Date limite de candidature</th><td>31/08/2026</td></tr>
            </table>
            <div id="offre_page">
                <div class="desc">
                    <div class="box">
                        <h2>Société / Organisme</h2>
                        <div class="text">ESPCI Paris</div>
                    </div>
                    <div class="box">
                        <h2>Description du sujet</h2>
                        <div class="text">
                            <p>Ce projet vise à explorer la conversion optique non linéaire.</p>
                        </div>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """
    http = HttpClient()
    scraper = AbgSourcing(http)
    detail = scraper._parse_detail_page(html, "https://www.abg.asso.fr/job/1")

    assert detail.job_details is not None
    assert "ESPCI Paris" in detail.job_details
    assert "2026-08-31" in detail.job_details
    assert "## Description du sujet" in detail.job_details
    assert "conversion optique non linéaire" in detail.job_details


def test_euraxess_html_parsing():
    html = """
    <html>
        <body>
            <h1 class="ecl-content-block__title">PhD in Nano-optics</h1>
            <div>
                <h2 id="job-information">Job Information</h2>
                <dl>
                    <dt>Organisation/Company</dt><dd>Max Planck Institute</dd>
                    <dt>Application Deadline</dt><dd>2026-10-15T23:59:59Z</dd>
                </dl>
            </div>
            <div>
                <h2 id="work-locations">Work Location</h2>
                <dl>
                    <dt>Country</dt><dd>Germany</dd>
                    <dt>City</dt><dd>Munich</dd>
                </dl>
            </div>
            <div>
                <h2 id="offer-description">Offer Description</h2>
                <div>
                    <p>We are researching nano-optical devices in microcavities.</p>
                </div>
            </div>
        </body>
    </html>
    """
    http = HttpClient()
    scraper = EuraxessSourcing(http)
    detail = scraper._parse_detail_page(html, "https://euraxess.ec.europa.eu/jobs/1")

    assert detail.job_details is not None
    assert "Max Planck Institute" in detail.job_details
    assert "Munich, Germany" in detail.job_details
    assert "2026-10-15" in detail.job_details
    assert "nano-optical devices" in detail.job_details


def test_academictransfer_html_parsing():
    html = """
    <html>
        <head>
            <script type="application/ld+json">
            {
                "@type": "JobPosting",
                "title": "Assistant Professor in Computer Science",
                "hiringOrganization": {"name": "TU Delft"},
                "jobLocation": {"address": {"addressLocality": "Delft", "addressCountry": "NL"}},
                "validThrough": "2026-12-31"
            }
            </script>
        </head>
        <body>
            <section>
                <h2>Job description</h2>
                <div>
                    <p>You will conduct research and teaching in artificial intelligence.</p>
                </div>
            </section>
        </body>
    </html>
    """
    http = HttpClient()
    scraper = AcademicTransferSourcing(http)
    detail = scraper._parse_detail_page(html, "https://www.academictransfer.com/en/jobs/1/")

    assert detail.job_details is not None
    assert "TU Delft" in detail.job_details
    assert "Delft, NL" in detail.job_details
    assert "artificial intelligence" in detail.job_details


def test_naturecareers_html_parsing():
    data = {
        "@type": "JobPosting",
        "title": "Principal Investigator in Cancer Biology",
        "hiringOrganization": {"name": "Francis Crick Institute"},
        "jobLocation": {"address": {"addressLocality": "London", "addressCountry": "UK"}},
        "validThrough": "2026-11-30",
        "description": (
            "<h2>About the Role</h2>"
            "<p>Leading research in oncogenic signaling and cellular senescence.</p>"
        ),
    }
    html = f"""
    <html>
        <head>
            <script type="application/ld+json">
            {json.dumps(data)}
            </script>
        </head>
        <body></body>
    </html>
    """
    http = HttpClient()
    scraper = NatureCareersSourcing(http)
    detail = scraper._parse_detail_page(html, "https://www.nature.com/naturecareers/job/123/")

    assert detail.job_details is not None
    assert "Francis Crick Institute" in detail.job_details
    assert "London, UK" in detail.job_details
    assert "oncogenic signaling" in detail.job_details


def test_researchgate_html_parsing():
    data = {
        "@type": "JobPosting",
        "title": "Senior Postdoctoral Fellow in Neuroscience",
        "hiringOrganization": {"name": "Harvard University"},
        "jobLocation": {"address": {"addressLocality": "Cambridge", "addressCountry": "US"}},
        "validThrough": "2026-09-30",
        "description": (
            "<h2>Project Description</h2>"
            "<p>Investigating neural circuits of decision making in primates.</p>"
        ),
    }
    html = f"""
    <html>
        <head>
            <script type="application/ld+json">
            {json.dumps(data)}
            </script>
        </head>
        <body></body>
    </html>
    """
    http = HttpClient()
    scraper = ResearchGateSourcing(http)
    detail = scraper._parse_detail_page(html, "https://www.researchgate.net/job/123_Neuro/")

    assert detail.job_details is not None
    assert "Harvard University" in detail.job_details
    assert "Cambridge, US" in detail.job_details
    assert "neural circuits" in detail.job_details


def test_eurosciencejobs_html_parsing():
    html = """
    <html>
        <body>
            <div class="col-xl-9">
                <h1>Policy Officer - Climate Science</h1>
                <h2>Policy Officer - Climate Science</h2>
                <h2>European Science Foundation</h2>
                <h2>Strasbourg, France</h2>
                <div class="row">
                    <h2>Description</h2>
                    <p>Supporting environmental research synthesis and scientific communication.</p>
                </div>
            </div>
        </body>
    </html>
    """
    http = HttpClient()
    scraper = EuroScienceJobsSourcing(http)
    detail = scraper._parse_detail_page(
        html, "https://www.eurosciencejobs.com/job_display/123/Policy"
    )

    assert detail.job_details is not None
    assert "European Science Foundation" in detail.job_details
    assert "Strasbourg, France" in detail.job_details
    assert "environmental research synthesis" in detail.job_details
