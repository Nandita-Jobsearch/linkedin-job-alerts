import careers


class FakeResp:
    def __init__(self, data=None, content=b""):
        self._data, self.content = data, content

    def json(self):
        return self._data

    def raise_for_status(self):
        pass


def patch_get(monkeypatch, data=None, content=b""):
    calls = []

    def fake(url, **kw):
        calls.append((url, kw))
        return FakeResp(data, content)

    monkeypatch.setattr(careers, "_get", fake)
    return calls


def entry(ats, slug="acme", company="Acme"):
    return {"company": company, "ats": ats, "slug": slug}


KW = ["sales", "marketing", "business development", "sdr", "intern"]


# ------------------------------------------------------------ filters

def test_irish_locations():
    assert careers.is_irish("Dublin, Ireland")
    assert careers.is_irish("IE")
    assert careers.is_irish("Remote", "Cork")
    assert not careers.is_irish("London, UK")
    assert not careers.is_irish("Belfast, Northern Ireland")
    assert not careers.is_irish(None, "")


def test_title_keywords_are_whole_words():
    assert careers.title_matches("Sales Development Representative", KW)
    assert careers.title_matches("Marketing Intern", KW)
    assert not careers.title_matches("International Tax Associate", KW)
    assert not careers.title_matches("Software Engineer", KW)


# ------------------------------------------------------------ adapters

def test_greenhouse(monkeypatch):
    patch_get(monkeypatch, {"jobs": [
        {"id": 1, "title": "SDR", "location": {"name": "Dublin, Ireland"},
         "absolute_url": "https://x/1", "first_published": "2026-11-20T09:00:00Z"},
        {"id": 2, "title": "SDR", "location": {"name": "Paris"},
         "absolute_url": "https://x/2"},
    ]})
    rows = careers.board_jobs(entry("greenhouse"))
    assert [irish for _, irish in rows] == [True, False]
    row = rows[0][0]
    assert row["site"] == "company_site"
    assert row["id"] == "greenhouse:acme:1"
    assert row["company"] == "Acme"
    assert row["job_url"] == "https://x/1"
    assert row["date_posted"] == "2026-11-20"


def test_lever_uses_all_locations(monkeypatch):
    patch_get(monkeypatch, [
        {"id": "a", "text": "Marketing Executive", "hostedUrl": "https://l/a",
         "createdAt": 1763600000000,
         "categories": {"location": "Remote", "allLocations": ["Remote", "Dublin"]}},
    ])
    (row, irish), = careers.board_jobs(entry("lever"))
    assert irish and row["title"] == "Marketing Executive"
    assert row["date_posted"].startswith("2025") or row["date_posted"].startswith("2026")


def test_ashby_skips_unlisted_and_reads_secondary_locations(monkeypatch):
    patch_get(monkeypatch, {"jobs": [
        {"id": "1", "title": "BDR", "location": "London",
         "secondaryLocations": [{"location": "Dublin"}], "jobUrl": "https://a/1"},
        {"id": "2", "title": "BDR", "location": "Dublin", "isListed": False},
    ]})
    rows = careers.board_jobs(entry("ashby"))
    assert len(rows) == 1 and rows[0][1]


def test_smartrecruiters_pages_until_short_page(monkeypatch):
    calls = patch_get(monkeypatch, {"content": [
        {"id": "9", "name": "Sales Intern", "location": {"city": "Dublin", "country": "ie"}}]})
    (row, irish), = careers.board_jobs(entry("smartrecruiters"))
    assert irish and row["job_url"] == "https://jobs.smartrecruiters.com/acme/9"
    assert len(calls) == 1


def test_workable(monkeypatch):
    patch_get(monkeypatch, {"name": "Acme", "jobs": [
        {"shortcode": "AB1", "title": "Marketing Assistant", "country": "Ireland",
         "city": "Galway", "url": "https://w/AB1", "published_on": "2026-11-01"}]})
    (row, irish), = careers.board_jobs(entry("workable"))
    assert irish and row["location"] == "Galway, Ireland"


def test_recruitee(monkeypatch):
    patch_get(monkeypatch, {"offers": [
        {"id": 5, "title": "SDR", "country_code": "IE", "location": "Dublin",
         "careers_url": "https://r/5"}]})
    (row, irish), = careers.board_jobs(entry("recruitee"))
    assert irish and row["job_url"] == "https://r/5"


def test_personio(monkeypatch):
    xml = b"""<workzag-jobs><position><id>77</id><office>Dublin</office>
              <name>Sales Development Rep</name><createdAt>2026-11-02T10:00:00+00:00</createdAt>
              </position></workzag-jobs>"""
    patch_get(monkeypatch, content=xml)
    (row, irish), = careers.board_jobs(entry("personio"))
    assert irish and row["job_url"] == "https://acme.jobs.personio.de/job/77"


def test_bamboohr(monkeypatch):
    patch_get(monkeypatch, {"result": [
        {"id": "3", "jobOpeningName": "Marketing Intern",
         "location": {"city": "Dublin", "state": "County Dublin"}}]})
    (row, irish), = careers.board_jobs(entry("bamboohr"))
    assert irish and row["job_url"] == "https://acme.bamboohr.com/careers/3"


FACETS = [
    {"facetParameter": "locationCountry", "values": [
        {"descriptor": "United States of America", "id": "us1"},
        {"descriptor": "Ireland", "id": "ie1"}]},
    {"facetParameter": "locationMainGroup", "values": [
        {"facetParameter": "locations", "values": [
            {"descriptor": "Dublin, Ireland", "id": "dub1"},
            {"descriptor": "Belfast, Northern Ireland", "id": "bel1"}]}]},
]


def test_workday_prefers_country_facet():
    assert careers.workday_irish_facets(FACETS) == {"locationCountry": ["ie1"]}


def test_workday_falls_back_to_irish_locations():
    assert careers.workday_irish_facets(FACETS[1:]) == {"locations": ["dub1"]}


class WDResp(FakeResp):
    def __init__(self, data, status=200):
        super().__init__(data)
        self.status_code = status


def test_workday_filters_to_ireland_and_retries_when_busy(monkeypatch):
    posting = {"title": "Account Executive", "locationsText": "2 Locations",
               "externalPath": "/job/Dublin/Account-Executive_JR1"}
    bodies, replies = [], iter([
        WDResp({}, 429),                                  # busy, retried
        WDResp({"facets": FACETS, "jobPostings": []}),
        WDResp({"jobPostings": [posting]}),
    ])

    def fake_post(url, json=None, **kw):
        bodies.append(json)
        return next(replies)

    monkeypatch.setattr(careers.requests, "post", fake_post)
    monkeypatch.setattr(careers.time, "sleep", lambda s: None)
    e = entry("workday", slug="acme.wd1.myworkdayjobs.com/acme/External")
    (row, irish), = careers.board_jobs(e)
    assert irish                       # facet-filtered, despite "2 Locations"
    assert bodies[-1]["appliedFacets"] == {"locationCountry": ["ie1"]}
    assert row["job_url"] == ("https://acme.wd1.myworkdayjobs.com/en-US/External"
                              "/job/Dublin/Account-Executive_JR1")


# ------------------------------------------------------------ fetch

def test_fetch_keeps_irish_matching_roles_and_isolates_failures(monkeypatch):
    good = entry("greenhouse", company="Good")
    bad = entry("lever", company="Bad")

    def fake_board(e):
        if e is bad:
            raise ValueError("boom")
        mk = lambda t: careers._row(e, t, t, "Dublin", "https://x/" + t)
        return [(mk("Sales Intern"), True), (mk("Sales Manager Paris"), False),
                (mk("Software Engineer"), True)]

    monkeypatch.setattr(careers, "board_jobs", fake_board)
    monkeypatch.setattr(careers.time, "sleep", lambda s: None)
    jobs, failures = careers.fetch(KW, [good, bad])
    assert [j["title"] for j in jobs] == ["Sales Intern"]
    assert failures == ["company_site:Bad: ValueError"]


def test_missing_map_means_no_companies(tmp_path):
    assert careers.load_map(tmp_path / "nope.json") == []


def test_fetch_drops_excluded_titles(monkeypatch):
    e = entry("greenhouse")
    mk = lambda t: careers._row(e, t, t, "Dublin", "https://x/" + t)
    monkeypatch.setattr(careers, "board_jobs", lambda _: [
        (mk("Sales Development Representative"), True),
        (mk("Commercial Account Executive"), True)])
    monkeypatch.setattr(careers.time, "sleep", lambda s: None)
    jobs, _ = careers.fetch(["sales", "account executive"], [e],
                            exclude=["account executive"])
    assert [j["title"] for j in jobs] == ["Sales Development Representative"]
