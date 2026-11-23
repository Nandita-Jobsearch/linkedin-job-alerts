"""Jobs posted on companies' own careers pages.

Most companies don't build their careers page themselves: it is served by a
hiring system (an ATS) that publishes the open roles as public JSON or XML,
the same feed the careers page itself loads. Reading that feed is far more
reliable than scraping the page.

careers-map.json says which ATS and board name each company uses. It is
written by discover_careers.py (run by hand from the Actions tab), so the daily
run only makes one or two requests per company.

Every adapter returns rows in the shape the other sources use. Jobs are kept
only if they are in Ireland and the title matches config.CAREERS_KEYWORDS;
the shared TITLE_EXCLUDE filter and dedupe then run on them like any other.
"""

import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import requests

log = logging.getLogger(__name__)

SITE = "company_site"
MAP_PATH = Path("careers-map.json")
HEADERS = {
    "accept": "application/json, text/xml;q=0.9, */*;q=0.8",
    "user-agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0 Safari/537.36"),
}
TIMEOUT = 25

# A location counts as Irish if it names the country or one of these places.
# Northern Ireland is excluded: it needs UK right to work, not Irish.
_IRISH = re.compile(
    r"\b(?:ireland|dublin|cork|galway|limerick|waterford|kilkenny|athlone|"
    r"kildare|wicklow|meath|louth|drogheda|dundalk|sligo|shannon|swords|"
    r"maynooth|letterkenny|tralee|ennis|carlow|wexford|naas|leixlip)\b",
    re.I,
)
_NI = re.compile(r"\b(?:northern ireland|belfast|derry|londonderry)\b", re.I)
_IE_CODES = {"ie", "irl"}


def is_irish(*parts):
    """True if any location text or country code points at the Republic."""
    for part in parts:
        if part is None:
            continue
        text = str(part).strip()
        if not text:
            continue
        if text.lower() in _IE_CODES:
            return True
        if _NI.search(text):
            continue
        if _IRISH.search(text):
            return True
    return False


def title_matches(title, keywords):
    """Whole-word match, so "intern" does not match "International"."""
    return any(re.search(r"\b" + re.escape(k) + r"\b", title or "", re.I)
               for k in keywords)


def _date(value):
    """ISO date from an ISO string or a millisecond timestamp."""
    if value in (None, ""):
        return ""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).date().isoformat()
    return str(value)[:10]


def _get(url, **kw):
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, **kw)
    resp.raise_for_status()
    return resp


def _row(entry, native_id, title, location, url, posted=""):
    return {
        "site": SITE,
        "id": f"{entry['ats']}:{entry['slug']}:{native_id}",
        "title": title or "",
        "company": entry["company"],
        "location": location or "",
        "job_url": url,
        "date_posted": posted,
        "description": "",
    }


# ------------------------------------------------------------- adapters
# Each yields (row, is_irish) for every posting on the board, so discovery can
# count all of them and the daily run can keep only the Irish ones.

def greenhouse(entry):
    data = _get(f"https://boards-api.greenhouse.io/v1/boards/{entry['slug']}/jobs").json()
    for job in data.get("jobs") or []:
        loc = (job.get("location") or {}).get("name", "")
        offices = [o.get("name") or o.get("location") for o in job.get("offices") or []]
        yield (_row(entry, job.get("id"), job.get("title"), loc,
                    job.get("absolute_url"),
                    _date(job.get("first_published") or job.get("updated_at"))),
               is_irish(loc, *offices))


def lever(entry):
    data = _get(f"https://api.lever.co/v0/postings/{entry['slug']}?mode=json").json()
    for job in data if isinstance(data, list) else []:
        cats = job.get("categories") or {}
        locs = [cats.get("location"), *(cats.get("allLocations") or []), job.get("country")]
        yield (_row(entry, job.get("id"), job.get("text"),
                    cats.get("location") or "", job.get("hostedUrl"),
                    _date(job.get("createdAt"))),
               is_irish(*locs))


def ashby(entry):
    data = _get(f"https://api.ashbyhq.com/posting-api/job-board/{entry['slug']}").json()
    for job in data.get("jobs") or []:
        if job.get("isListed") is False:
            continue
        addr = ((job.get("address") or {}).get("postalAddress") or {})
        locs = [job.get("location"), addr.get("addressCountry"), addr.get("addressLocality"),
                *[s.get("location") for s in job.get("secondaryLocations") or []]]
        yield (_row(entry, job.get("id"), job.get("title"), job.get("location"),
                    job.get("jobUrl"), _date(job.get("publishedAt"))),
               is_irish(*locs))


def smartrecruiters(entry, max_pages=10):
    slug = entry["slug"]
    for page in range(max_pages):
        data = _get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
                    params={"limit": 100, "offset": page * 100}).json()
        content = data.get("content") or []
        for job in content:
            loc = job.get("location") or {}
            where = ", ".join(x for x in (loc.get("city"), loc.get("country")) if x)
            yield (_row(entry, job.get("id"), job.get("name"), where,
                        f"https://jobs.smartrecruiters.com/{slug}/{job.get('id')}",
                        _date(job.get("releasedDate"))),
                   is_irish(loc.get("country"), loc.get("city"), loc.get("fullLocation")))
        if len(content) < 100:
            return


def workable(entry):
    data = _get(f"https://apply.workable.com/api/v1/widget/accounts/{entry['slug']}").json()
    for job in data.get("jobs") or []:
        where = ", ".join(x for x in (job.get("city"), job.get("country")) if x)
        locs = [job.get("country"), job.get("city"),
                *[(l or {}).get("country") for l in job.get("locations") or []],
                *[(l or {}).get("countryCode") for l in job.get("locations") or []]]
        yield (_row(entry, job.get("shortcode"), job.get("title"), where,
                    job.get("url") or job.get("application_url"),
                    _date(job.get("published_on") or job.get("created_at"))),
               is_irish(*locs))


def recruitee(entry):
    data = _get(f"https://{entry['slug']}.recruitee.com/api/offers/").json()
    for job in data.get("offers") or []:
        yield (_row(entry, job.get("id"), job.get("title"), job.get("location"),
                    job.get("careers_url"), _date(job.get("published_at"))),
               is_irish(job.get("country_code"), job.get("country"), job.get("location"),
                        job.get("city")))


def personio(entry):
    slug = entry["slug"]
    root = ET.fromstring(_get(f"https://{slug}.jobs.personio.de/xml").content)
    for pos in root.iter("position"):
        get = lambda tag: (pos.findtext(tag) or "").strip()
        offices = [get("office"), *[(o.text or "") for o in pos.iter("additionalOffice")]]
        yield (_row(entry, get("id"), get("name"), get("office"),
                    f"https://{slug}.jobs.personio.de/job/{get('id')}",
                    _date(get("createdAt"))),
               is_irish(*offices))


def bamboohr(entry):
    slug = entry["slug"]
    data = _get(f"https://{slug}.bamboohr.com/careers/list").json()
    for job in data.get("result") or []:
        loc = job.get("location") or {}
        ats_loc = job.get("atsLocation") or {}
        where = ", ".join(x for x in (loc.get("city"), loc.get("state")) if x)
        yield (_row(entry, job.get("id"), job.get("jobOpeningName"), where,
                    f"https://{slug}.bamboohr.com/careers/{job.get('id')}"),
               is_irish(loc.get("city"), loc.get("state"), loc.get("country"),
                        ats_loc.get("country"), ats_loc.get("city")))


def _workday_post(api, body, tries=4):
    """Workday answers 429 when read quickly from shared CI addresses."""
    for attempt in range(tries):
        resp = requests.post(api, headers={**HEADERS, "content-type": "application/json"},
                             json=body, timeout=TIMEOUT)
        if resp.status_code != 429 or attempt == tries - 1:
            resp.raise_for_status()
            return resp.json()
        time.sleep(5 * (attempt + 1))


def workday_irish_facets(facets):
    """Workday's own location filter for Ireland, as appliedFacets.

    Prefers a country facet; falls back to every Irish city/location value.
    Tenants nest facet groups differently, so the tree is walked.
    """
    found = {}

    def walk(groups):
        for group in groups or []:
            param = group.get("facetParameter") or ""
            for value in group.get("values") or []:
                if value.get("values"):
                    walk([value])
                elif value.get("id") and is_irish(value.get("descriptor")):
                    found.setdefault(param, []).append(value["id"])

    walk(facets)
    country = {p: ids for p, ids in found.items() if "country" in p.lower()}
    return country or found


def workday(entry, max_pages=25):
    """Workday careers sites have a search API rather than a full feed.

    `slug` is "<host>/<tenant>/<site>", e.g.
    "salesforce.wd12.myworkdayjobs.com/salesforce/External_Career_Site".
    The search is narrowed with the site's own Ireland filter, so every job
    returned is Irish even when it only says "2 Locations".
    """
    host, tenant, site = entry["slug"].split("/")
    api = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
    first = _workday_post(api, {"appliedFacets": {}, "limit": 1, "offset": 0,
                                "searchText": ""})
    facets = workday_irish_facets(first.get("facets"))
    body = ({"appliedFacets": facets, "searchText": ""} if facets
            else {"appliedFacets": {}, "searchText": "Ireland"})

    seen = set()
    for page in range(max_pages):
        time.sleep(1)
        postings = _workday_post(api, {**body, "limit": 20, "offset": page * 20}
                                 ).get("jobPostings") or []
        for job in postings:
            path = job.get("externalPath") or ""
            if not path or path in seen:
                continue
            seen.add(path)
            yield (_row(entry, path.rsplit("_", 1)[-1], job.get("title"),
                        job.get("locationsText"), f"https://{host}/en-US/{site}{path}"),
                   bool(facets) or is_irish(job.get("locationsText"), path))
        if len(postings) < 20:
            break


ADAPTERS = {
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
    "smartrecruiters": smartrecruiters,
    "workable": workable,
    "recruitee": recruitee,
    "personio": personio,
    "bamboohr": bamboohr,
    "workday": workday,
}


def board_jobs(entry):
    """All postings on one company's board as (row, is_irish) pairs."""
    return list(ADAPTERS[entry["ats"]](entry))


def load_map(path=MAP_PATH):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        return []


def fetch(keywords, entries=None):
    """Irish, role-matching jobs from every mapped company.

    Returns (jobs, failures). One broken board never stops the others.
    """
    entries = load_map() if entries is None else entries
    jobs, failures = [], []
    for entry in entries:
        try:
            kept = [row for row, irish in board_jobs(entry)
                    if irish and title_matches(row["title"], keywords)]
            jobs.extend(kept)
            log.info("company site %s (%s) -> %d", entry["company"], entry["ats"], len(kept))
        except Exception as exc:
            failures.append(f"{SITE}:{entry['company']}: {type(exc).__name__}")
            log.warning("company site %s failed: %s", entry["company"], exc)
        time.sleep(0.3)
    return jobs, failures
