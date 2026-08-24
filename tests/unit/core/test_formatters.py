from core.utils.formatters import format_match_card, format_profile_card


def test_format_match_card_with_json_string_degrees():
    degrees_json = (
        '["Computer Science", "Software Engineering", "Information Technology"]'
    )
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
