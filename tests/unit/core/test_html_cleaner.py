from bs4 import BeautifulSoup
from core.utils.html_cleaner import html_to_markdown, inline_to_markdown, parse_dl_to_dict


def test_inline_to_markdown_links():
    soup = BeautifulSoup(
        '<p>Link to the department:<br /><a href="https://mau.se/bmv">BMV</a></p>',
        "html.parser",
    )
    p = soup.find("p")
    assert p is not None
    md = inline_to_markdown(p)
    assert "[BMV](https://mau.se/bmv)" in md
    assert "Link to the department:" in md


def test_inline_to_markdown_formatting():
    html = (
        "<p>We require <strong>PhD in Physics</strong> or "
        "<em>Chemistry</em> with <code>Python</code> skills.</p>"
    )
    soup = BeautifulSoup(html, "html.parser")
    p = soup.find("p")
    assert p is not None
    md = inline_to_markdown(p)
    assert "**PhD in Physics**" in md
    assert "*Chemistry*" in md
    assert "`Python`" in md


def test_inline_to_markdown_ignores_javascript_links():
    soup = BeautifulSoup(
        '<a href="javascript:void(0)">Click Here</a>',
        "html.parser",
    )
    a = soup.find("a")
    assert a is not None
    md = inline_to_markdown(a)
    assert md == "Click Here"
    assert "javascript" not in md


def test_html_to_markdown_full_document():
    raw_html = """
    <div>
        <h2>Research Environment</h2>
        <p>The lab is affiliated with <a href="https://example.org/center">BRCB Center</a>.</p>
        <ul>
            <li>Requirement 1: <strong>High impact</strong> research</li>
            <li>Requirement 2: See <a href="https://example.org/guide">Application Guide</a></li>
        </ul>
        <table>
            <tr><th>Field</th><th>Status</th></tr>
            <tr><td>Quantum</td><td><a href="https://example.org/quantum">Open</a></td></tr>
        </table>
    </div>
    """
    md = html_to_markdown(raw_html)
    assert "### Research Environment" in md
    assert "[BRCB Center](https://example.org/center)" in md
    assert "- Requirement 1: **High impact** research" in md
    assert "[Application Guide](https://example.org/guide)" in md
    assert "| Quantum | [Open](https://example.org/quantum) |" in md


def test_parse_dl_to_dict_preserves_links():
    soup = BeautifulSoup(
        """
        <dl>
            <dt>Organisation</dt><dd><a href="https://university.org">University of Science</a></dd>
            <dt>Deadline</dt><dd><time datetime="2026-12-31">31 Dec 2026</time></dd>
            <dt>Contact</dt><dd>info@university.org</dd>
        </dl>
        """,
        "html.parser",
    )
    dl = soup.find("dl")
    assert dl is not None
    data = parse_dl_to_dict(dl)
    assert data["Organisation"] == "https://university.org"
    assert data["Deadline"] == "2026-12-31"
    assert data["Contact"] == "info@university.org"


def test_normalize_markdown_separators():
    from core.utils.html_cleaner import normalize_markdown_separators

    text = (
        "French summary paragraph.\n\n"
        "----------------------------------------------------------------------------\n"
        "----------------------------------------------------------------------------\n\n"
        "English summary paragraph.\n\n"
        "============================================================================\n\n"
        "Final remarks."
    )
    normalized = normalize_markdown_separators(text)
    assert "--------------------------------" not in normalized
    assert "================================" not in normalized
    expected = (
        "French summary paragraph.\n\n"
        "---\n\n"
        "English summary paragraph.\n\n"
        "---\n\n"
        "Final remarks."
    )
    assert normalized == expected


def test_normalize_unicode_bullets_and_lists():
    from core.utils.html_cleaner import normalize_markdown_separators

    text = (
        "**You are good at:**\n\n\n"
        "•    Selling complex products\n\n\n"
        "•    Managing sales cycles\n\n\n"
        "▪    Working with product managers\n\n"
        "1. First step\n\n"
        "2. Second step"
    )
    normalized = normalize_markdown_separators(text)
    expected = (
        "**You are good at:**\n\n"
        "- Selling complex products\n"
        "- Managing sales cycles\n"
        "- Working with product managers\n\n"
        "1. First step\n"
        "2. Second step"
    )
    assert normalized == expected


def test_adjacent_asterisks_and_link_bold_normalization():
    from core.utils.html_cleaner import normalize_markdown_separators

    text = (
        "**Main missions****:**\n\n"
        "The [**SMIA**](https://chuv.ch) at CHUV is leading.\n\n"
        "**within Department of centers (**[**DCI**](https://chuv.ch)**)**\n\n"
        "-Master 2 in Physics\n\n"
        "See [reports](https://reports.org)tot and [data](https://data.org)2025"
    )
    normalized = normalize_markdown_separators(text)
    assert "**Main missions:**" in normalized
    assert "The [SMIA](https://chuv.ch) at CHUV" in normalized
    assert "- Master 2 in Physics" in normalized
    assert "[reports](https://reports.org) tot and [data](https://data.org) 2025" in normalized
    assert "****" not in normalized


def test_crlf_list_collapsing():
    from core.utils.html_cleaner import normalize_markdown_separators

    text = "- Item 1\r\n\r\n\r\n- Item 2\r\n\r\n- Item 3"
    normalized = normalize_markdown_separators(text)
    assert normalized == "- Item 1\n- Item 2\n- Item 3"


def test_alphabetical_and_parenthesized_list_collapsing():
    from core.utils.html_cleaner import normalize_markdown_separators

    text = (
        "a) Curriculum Vitae\n\n\n"
        "b) Faculty Application Form\n\n\n"
        "c) Research Statement\n\n"
        "(1) First step\n\n"
        "(2) Second step"
    )
    normalized = normalize_markdown_separators(text)
    expected = (
        "a) Curriculum Vitae\n"
        "b) Faculty Application Form\n"
        "c) Research Statement\n\n"
        "(1) First step\n"
        "(2) Second step"
    )
    assert normalized == expected


