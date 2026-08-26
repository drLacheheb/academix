from core.utils.formatters import format_match_card, format_profile_card


def test_format_match_card_with_json_string_degrees():
    degrees_json = '["Computer Science", "Software Engineering", "Information Technology"]'
    match_dict = {
        "score": 0.7873,
        "job_title": "Software Engineer Open Source",
        "employer": "Delft University of Technology",
        "city": "Delft",
        "country": "Netherlands",
        "deadline": "2026-09-06",
        "job_degree_fields": degrees_json,
        "explanation": "Strong Python and Linux fit.",
        "job_url": "https://example.com/job/123",
    }
    card = format_match_card(match_dict)
    assert "78% Match" in card
    assert "Software Engineer Open Source" in card
    assert "Delft University of Technology (Delft, Netherlands)" in card
    assert "Degree: Computer Science, Software Engineering, Information Technology" in card
    assert "Strong Python and Linux fit." in card
    assert "https://example.com/job/123" in card


def test_format_match_card_with_list_degrees():
    match_dict = {
        "score": 0.85,
        "job_title": "Postdoc in AI",
        "employer": "University of Twente",
        "deadline": "2026-10-01",
        "job_degree_fields": ["Artificial Intelligence", "Data Science"],
        "explanation": "High research alignment.",
        "job_url": "https://example.com/job/456",
    }
    card = format_match_card(match_dict)
    assert "85% Match" in card
    assert "Degree: Artificial Intelligence, Data Science" in card


def test_format_match_card_with_no_degrees():
    match_dict = {
        "score": 0.70,
        "job_title": "Research Assistant",
        "employer": "Leiden University",
        "deadline": "2026-11-01",
        "job_degree_fields": None,
        "explanation": "Basic requirements met.",
        "job_url": "https://example.com/job/789",
    }
    card = format_match_card(match_dict)
    assert "70% Match" in card
    assert "Degree:" not in card


def test_format_profile_card():
    profile = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "highest_degree": "Master",
        "degree_fields": ["Computer Science", "Informatics"],
        "skills": ["Python", "FastAPI", "Docker"],
        "research_interests": ["Machine Learning", "Cloud Systems"],
        "languages": [{"language": "English", "proficiency": "Native"}],
        "preferred_locations": ["Netherlands", "Germany"],
    }
    card = format_profile_card(profile)
    assert "Jane Doe" in card
    assert "Master" in card
    assert "Computer Science, Informatics" in card
    assert "Python, FastAPI, Docker" in card
    assert "Machine Learning, Cloud Systems" in card


def test_format_status_bar():
    from core.utils.formatters import format_status_bar

    res_ingest = format_status_bar("INGESTING")
    assert "10%" in res_ingest
    assert "Ingesting Document" in res_ingest

    res_refine = format_status_bar("REFINEMENT_CLAIMED")
    assert "70%" in res_refine
    assert "Extracting Skills and Research" in res_refine

    res_complete = format_status_bar("COMPLETED")
    assert "100%" in res_complete
    assert "Ready and Matched" in res_complete


def test_format_single_match_card():
    from core.utils.formatters import format_single_match_card

    match_dict = {
        "score": 0.88,
        "job_title": "Tenure Track Assistant Professor in AI",
        "employer": "Eindhoven University of Technology",
        "city": "Eindhoven",
        "country": "Netherlands",
        "deadline": "2026-12-01",
        "job_degree_fields": ["Computer Science", "AI"],
        "explanation": "Exceptional fit with candidate machine learning background.",
        "job_url": "https://example.com/job/999",
    }
    card = format_single_match_card(match_dict, current_idx=1, total=5)
    assert "Match 1 of 5 (88% Match)" in card
    assert "Tenure Track Assistant Professor in AI" in card
    assert "Eindhoven University of Technology (Eindhoven, Netherlands)" in card
    assert "Computer Science, AI" in card
    assert "Exceptional fit with candidate machine learning background." in card
