import discover_careers as dc


def test_slugs_from_name_and_explicit_list():
    assert dc.slugs({"company": "Kitman Labs"}) == ["kitmanlabs", "kitman-labs"]
    assert dc.slugs({"company": "Core (marketing agency)"}) == ["core"]
    assert dc.slugs({"company": "X", "slugs": ["a", "b"]}) == ["a", "b"]


def test_probe_prefers_a_board_with_irish_roles(monkeypatch):
    def fake_board(entry):
        mk = lambda t: {"title": t}
        if entry["ats"] == "greenhouse":
            return [(mk("Sales Rep"), False)]                  # board, nothing Irish
        if entry["ats"] == "lever":
            return [(mk("Sales Intern"), True), (mk("Engineer"), True)]
        raise ValueError("no board")

    monkeypatch.setattr(dc.careers, "board_jobs", fake_board)
    hit = dc.probe({"company": "Acme", "industry": "Tech"})
    assert hit["ats"] == "lever"
    assert (hit["irish"], hit["matching"]) == (2, 1)
    assert hit["sample"] == ["Sales Intern"]


def test_probe_reports_board_without_irish_roles(monkeypatch):
    monkeypatch.setattr(dc.careers, "board_jobs",
                        lambda e: [({"title": "Sales"}, False)] if e["ats"] == "ashby" else [])
    hit = dc.probe({"company": "Acme", "industry": "Tech"})
    assert hit["ats"] == "ashby" and hit["irish"] == 0


def test_probe_not_found(monkeypatch):
    monkeypatch.setattr(dc.careers, "board_jobs", lambda e: [])
    assert dc.probe({"company": "Acme", "industry": "Tech"})["ats"] is None


def test_workday_is_tried_first_when_given(monkeypatch):
    seen = []

    def fake_board(entry):
        seen.append(entry["ats"])
        return [({"title": "Account Executive"}, True)]

    monkeypatch.setattr(dc.careers, "board_jobs", fake_board)
    hit = dc.probe({"company": "Big", "industry": "Tech",
                    "workday": "big.wd1.myworkdayjobs.com/big/Careers"})
    assert seen == ["workday"] and hit["ats"] == "workday"
