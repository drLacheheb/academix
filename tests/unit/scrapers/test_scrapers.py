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


def test_abg_inline_links_and_formatting_edge_case():
    html = """
    <html>
        <body>
            <h1>PhD Position in Bio-Photonics</h1>
            <table class="tab_offre_infos">
                <tr><th>Référence</th><td>ABG-9999</td></tr>
                <tr><th>Date limite de candidature</th><td>15/10/2026</td></tr>
            </table>
            <div id="offre_page">
                <div class="desc">
                    <div class="box">
                        <h2>Description du sujet</h2>
                        <div class="text">
                            <p>For details, visit <a href="https://lab.fr/project">Lab Page</a>.</p>
                            <p>Contact: <a href="mailto:curie@lab.fr">curie@lab.fr</a>.</p>
                        </div>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """
    http = HttpClient()
    scraper = AbgSourcing(http)
    detail = scraper._parse_detail_page(html, "https://www.abg.asso.fr/job/2")

    assert detail.job_details is not None
    assert "[Lab Page](https://lab.fr/project)" in detail.job_details
    assert "[curie@lab.fr](mailto:curie@lab.fr)" in detail.job_details


def test_abg_long_dashes_and_dividers_edge_case():
    html = """
    <html>
        <body>
            <h1>PhD Position in Polaritonic Quantum Devices</h1>
            <div id="offre_page">
                <div class="desc">
                    <div class="box">
                        <h2>Description du sujet</h2>
                        <div class="text">
                            <p>Projet expérimental ANR commun.</p>
                            <p>------------------------------------------------------------</p>
                            <p>------------------------------------------------------------</p>
                            <p>Nonlinear optical phenomena in quantum devices.</p>
                            <p>------------------------------------------------------------</p>
                        </div>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """
    http = HttpClient()
    scraper = AbgSourcing(http)
    detail = scraper._parse_detail_page(html, "https://www.abg.asso.fr/job/133882")

    assert detail.job_details is not None
    assert "--------------------------------" not in detail.job_details
    assert "\n---\n" in detail.job_details
    expected_snippet = "Projet expérimental ANR commun.\n\n---\n\nNonlinear optical phenomena"
    assert expected_snippet in detail.job_details


def test_abg_labeled_item_and_deadline_edge_case():
    html = """
    <html>
        <body>
            <h1>PhD in Physics</h1>
            <div id="offre_page">
                <div class="desc">
                    <div class="box">
                        <h2>Profil du candidat</h2>
                        <div class="text">
                            <p>Master in physics required.</p>
                        </div>
                        <div class="item">
                            <label>Date limite de candidature</label>
                            <div class="text infos">30/09/2026</div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """
    http = HttpClient()
    scraper = AbgSourcing(http)
    detail = scraper._parse_detail_page(html, "https://www.abg.asso.fr/job/124837")

    assert detail.job_details is not None
    assert "- **Deadline:** 2026-09-30" in detail.job_details
    assert "- **Date limite de candidature:** 30/09/2026" in detail.job_details


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


def test_euraxess_inline_links_and_formatting_edge_case():
    html = """
    <html>
        <body>
            <h1 class="ecl-content-block__title">Doctoral student in biomedical science</h1>
            <div>
                <h2 id="job-information">Job Information</h2>
                <dl>
                    <dt>Organisation/Company</dt><dd>Malmö University</dd>
                    <dt>Application Deadline</dt><dd>2026-09-14T12:00:00+00:00</dd>
                </dl>
            </div>
            <div>
                <h2 id="offer-description">Offer Description</h2>
                <div>
                    <p>Link to the department:<br />
                    <a href="https://mau.se/en/about-us/management-and-organisation/faculty-of-health-and-society/department-of-biomedical-science/">BMV</a></p>
                    <p>Link to the research environment:<br />
                    <a href="http://www.mau.se/brcb">BRCB</a></p>
                    <p>Link to the project:<br />
                    <a href="https://mau.se/en/research/projects/bioinhale/">https://mau.se/en/research/projects/bioinhale/</a></p>
                    <p>We require strong <strong>interdisciplinary</strong> background.</p>
                </div>
            </div>
        </body>
    </html>
    """
    http = HttpClient()
    scraper = EuraxessSourcing(http)
    detail = scraper._parse_detail_page(html, "https://euraxess.ec.europa.eu/jobs/461243")

    assert detail.job_details is not None
    assert (
        "[BMV](https://mau.se/en/about-us/management-and-organisation/faculty-of-health-and-society/department-of-biomedical-science/)"
        in detail.job_details
    )
    assert "[BRCB](http://www.mau.se/brcb)" in detail.job_details
    assert (
        "[https://mau.se/en/research/projects/bioinhale/](https://mau.se/en/research/projects/bioinhale/)"
        in detail.job_details
    )
    assert "**interdisciplinary**" in detail.job_details


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


def test_academictransfer_inline_links_and_entities_edge_case():
    html = """
    <html>
        <head>
            <script type="application/ld+json">
            {
                "@type": "JobPosting",
                "title": "PhD Candidate in Cardiology",
                "hiringOrganization": {"name": "Erasmus MC"},
                "jobLocation": {
                    "address": {"addressLocality": "Rotterdam", "addressCountry": "NL"}
                },
                "validThrough": "2026-10-31"
            }
            </script>
        </head>
        <body>
            <section>
                <h2>Requirements</h2>
                <div>
                    <p>Apply via <a href="https://erasmusmc.nl/apply">Erasmus Portal</a>.</p>
                    <p>CAO-NU Salary scale: <strong>€2.770 &ndash; €3.539</strong> per month.</p>
                </div>
            </section>
        </body>
    </html>
    """
    http = HttpClient()
    scraper = AcademicTransferSourcing(http)
    detail = scraper._parse_detail_page(html, "https://www.academictransfer.com/en/jobs/2/")

    assert detail.job_details is not None
    assert "[Erasmus Portal](https://erasmusmc.nl/apply)" in detail.job_details
    assert "**€2.770" in detail.job_details


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


def test_naturecareers_inline_links_edge_case():
    data = {
        "@type": "JobPosting",
        "title": "Postdoctoral Researcher",
        "hiringOrganization": {"name": "Springer Nature"},
        "description": (
            "<p>Please see our <a href='https://springer.com/guidelines'>Author Guidelines</a>.</p>"
            "<p>Requires <strong>PhD</strong> in relevant STEM field.</p>"
        ),
    }
    html = f"""
    <html>
        <head>
            <script type="application/ld+json">
            {json.dumps(data)}
            </script>
        </head>
        <body>
            <dl>
                <dt>Website</dt><dd><a href="https://springernature.com">Apply Online</a></dd>
            </dl>
        </body>
    </html>
    """
    http = HttpClient()
    scraper = NatureCareersSourcing(http)
    detail = scraper._parse_detail_page(html, "https://www.nature.com/naturecareers/job/456/")

    assert detail.job_details is not None
    assert "[Author Guidelines](https://springer.com/guidelines)" in detail.job_details
    assert "[https://springernature.com](https://springernature.com)" in detail.job_details


def test_naturecareers_unicode_bullets_edge_case():
    data = {
        "@type": "JobPosting",
        "title": "Solution Specialist",
        "hiringOrganization": {"name": "Springer Nature"},
        "description": (
            "<p><strong>You are good at:</strong></p>"
            "<p>•    Selling complex products to academic customers</p>"
            "<p>•    Managing sales cycles with multiple stakeholders</p>"
            "<p>▪    Working with product managers and local sales</p>"
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
    detail = scraper._parse_detail_page(html, "https://www.nature.com/naturecareers/job/789/")

    assert detail.job_details is not None
    assert "•" not in detail.job_details
    assert "▪" not in detail.job_details
    expected_list = (
        "- Selling complex products to academic customers\n"
        "- Managing sales cycles with multiple stakeholders\n"
        "- Working with product managers and local sales"
    )
    assert expected_list in detail.job_details


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
            "<p>More info at <a href='https://neuro.harvard.edu'>Harvard Neuro</a>.</p>"
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
    assert "[Harvard Neuro](https://neuro.harvard.edu)" in detail.job_details


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


def test_eurosciencejobs_inline_links_and_filtering_edge_case():
    html = """
    <html>
        <body>
            <div class="col-xl-9">
                <h1>Postdoctoral Scientist</h1>
                <h2>Postdoctoral Scientist</h2>
                <h2>EPFL</h2>
                <h2>Lausanne, Switzerland</h2>
                <div class="row">
                    <h2>Description</h2>
                    <p>Job Description Start</p>
                    <p>Visit the <a href="https://epfl.ch/lab">EPFL Lab</a> for details.</p>
                    <p>Don't forget to mention EuroScienceJobs when applying.</p>
                    <p>Job Description End</p>
                </div>
            </div>
        </body>
    </html>
    """
    http = HttpClient()
    scraper = EuroScienceJobsSourcing(http)
    detail = scraper._parse_detail_page(
        html, "https://www.eurosciencejobs.com/job_display/999/EPFL"
    )

    assert detail.job_details is not None
    assert "[EPFL Lab](https://epfl.ch/lab)" in detail.job_details
    assert "Job Description Start" not in detail.job_details
    assert "Job Description End" not in detail.job_details
