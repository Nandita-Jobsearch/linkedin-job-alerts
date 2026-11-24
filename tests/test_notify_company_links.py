import notify


def test_direct_website_and_linkedin_page_both_shown():
    job = {"company": "Acme", "company_url_direct": "https://acme.ie",
           "company_url": "https://ie.linkedin.com/company/acme"}
    assert notify.company_links(job) == [
        ("website", "https://acme.ie"),
        ("LinkedIn", "https://ie.linkedin.com/company/acme"),
    ]


def test_indeed_company_page_is_not_labelled_linkedin():
    job = {"company": "Acme", "company_url": "https://ie.indeed.com/cmp/acme"}
    label, url = notify.company_links(job)[0]
    assert label == "find website"
    assert "acme" in url.lower()


def test_falls_back_to_a_search_when_board_gives_nothing():
    links = notify.company_links({"company": "Salt & Pepper Ltd"})
    assert links[0][0] == "find website"
    assert links[0][1].startswith("https://www.google.com/search?q=")
    assert "&" not in links[0][1].split("q=", 1)[1]   # name is URL-encoded


def test_no_company_name_means_no_links():
    assert notify.company_links({"company": ""}) == []


def test_company_cell_escapes_names_and_urls():
    cell = notify._company_cell({"company": "A&B <Co>",
                                 "company_url_direct": "https://ab.ie/?a=1&b='x'"})
    assert "A&amp;B &lt;Co&gt;" in cell
    assert "'x'" not in cell


def test_email_row_carries_the_company_link():
    job = {"title": "SDR", "company": "Acme", "job_url": "https://j/1",
           "company_url_direct": "https://acme.ie", "site": "indeed"}
    assert "https://acme.ie" in notify._html([job], [], False, {})
    assert "company website: https://acme.ie" in notify._plain([job])


def test_nan_fields_from_pandas_do_not_crash():
    """Regression: a float NaN in company_url_direct crashed the 24 Nov run."""
    nan = float("nan")
    job = {"title": "SDR", "company": "Acme", "job_url": "https://j/1",
           "company_url_direct": nan, "company_url": nan, "site": "linkedin"}
    assert notify.company_links(job)[0][0] == "find website"
    assert "Acme" in notify._plain([job])
