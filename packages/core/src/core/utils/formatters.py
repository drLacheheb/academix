import html


def format_profile_card(p: dict) -> str:
    name = html.escape(p.get("name") or "Candidate")
    email = html.escape(p.get("email") or "Not specified")
    degree = html.escape(p.get("highest_degree") or "Not specified")

    degree_fields_list = p.get("degree_fields") or []
    degree_fields_str = (
        html.escape(", ".join(degree_fields_list)) if degree_fields_list else "None extracted"
    )

    skills_list = p.get("skills") or []
    skills = ", ".join(skills_list[:25]) or "None extracted"
    if len(skills_list) > 25:
        skills += f" (+{len(skills_list) - 25} more)"

    interests_list = p.get("research_interests") or []
    interests = ", ".join(interests_list) or "None extracted"

    locations = ", ".join(p.get("preferred_locations") or []) or "Any location"

    langs = p.get("languages") or []
    lang_str = "Not specified"
    if langs:
        lang_items = []
        for lang in langs:
            if isinstance(lang, dict):
                lang_name = lang.get("language") or "Language"
                prof = lang.get("proficiency") or ""
                lang_items.append(f"{lang_name} ({prof})" if prof else lang_name)
            elif isinstance(lang, str):
                lang_items.append(lang)
        if lang_items:
            lang_str = ", ".join(lang_items)

    return (
        f"<b>Candidate Profile Summary</b>\n\n"
        f"<b>Name:</b> {name}\n"
        f"<b>Email:</b> {email}\n"
        f"<b>Highest Degree:</b> {degree}\n"
        f"<b>Degree Fields:</b> {degree_fields_str}\n\n"
        f"<b>Key Skills:</b>\n{html.escape(skills)}\n\n"
        f"<b>Research Domains:</b>\n{html.escape(interests)}\n\n"
        f"<b>Spoken Languages:</b>\n{html.escape(lang_str)}\n\n"
        f"<b>Preferred Locations:</b>\n{html.escape(locations)}\n\n"
        f"<i>Use /edit to modify any of these fields!</i>"
    )


def format_match_card(m: dict) -> str:
    score = m.get("score", 0.0)
    percentage = int(score * 100)
    title = html.escape(m.get("job_title", "Academic Position"))
    employer = html.escape(m.get("employer") or "Academic Institution")
    city = html.escape(m.get("city") or "")
    country = html.escape(m.get("country") or "")
    loc_parts = [p for p in [city, country] if p]
    location = ", ".join(loc_parts)
    deadline = html.escape(m.get("deadline") or "Not specified")
    explanation = html.escape(m.get("explanation") or "Matching requirements satisfied.")
    job_url = m.get("job_url", "")
    raw_degrees = m.get("job_degree_fields") or m.get("degree_fields") or []
    if isinstance(raw_degrees, str):
        try:
            import json

            parsed = json.loads(raw_degrees)
            degree_fields = parsed if isinstance(parsed, list) else [raw_degrees]
        except Exception:
            degree_fields = [raw_degrees]
    elif isinstance(raw_degrees, list):
        degree_fields = raw_degrees
    else:
        degree_fields = []

    degree_str = (
        f"\nDegree: {html.escape(', '.join(str(d) for d in degree_fields))}"
        if degree_fields
        else ""
    )
    location_str = f" ({location})" if location else ""

    return (
        f"<b>New Match Found! ({percentage}% Match)</b>\n\n"
        f"<b>{title}</b>\n"
        f"{employer}{location_str}\n"
        f"Deadline: {deadline}{degree_str}\n\n"
        f"<i>{explanation}</i>\n\n"
        f"<a href='{job_url}'>View Job Posting</a>"
    )
