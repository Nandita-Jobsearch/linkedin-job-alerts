"""What to search for. Everything here is safe to commit."""

import os

# Narrow queries beat one broad one: each stays well under LinkedIn's
# rate limit instead of paging deep enough to get blocked.
ROLES = [
    # B2B sales
    "sales development representative",
    "business development representative",
    "graduate sales",
    "sales intern",
    # Entry-level marketing in any industry, agencies included
    "graduate marketing",
    "marketing intern",
    "marketing executive",
    "marketing assistant",
    "junior marketing",
    "marketing coordinator",
    "digital marketing executive",
    # FMCG entry routes
    "brand assistant",
    "trade marketing",
    "commercial graduate",
    # Entry-level strategy
    "junior strategist",
    "strategy intern",
]

# Open to anywhere in Ireland, so search the country rather than a city list.
# One location keeps the query count low enough to add more boards.
LOCATIONS = ["Ireland"]

# Only boards that actually respond from a GitHub Actions runner.
# Glassdoor returns 403 on its location autocomplete and Google Jobs is
# disabled in the EU, so both were dropped after probing rather than left
# in to burn ~40s a run returning nothing. They need a proxy layer.
SITES = ["linkedin", "indeed"]

# gradireland has its own adapter rather than going through JobSpy.
USE_GRADIRELAND = True
# gradireland's search matches multi-word keys strictly, so "data engineer"
# returns almost nothing. The adapter walks the whole live catalogue instead
# and matches these against the title.
# Matched as plain substrings of the lowercased title, so avoid stems like
# "account" (it would also match "accountant").
GRADIRELAND_KEYWORDS = [
    "sales", "marketing", "business development", "commercial",
    "brand", "account executive", "customer success", "go-to-market",
    "growth", "communications", "advertising", "media",
    "strateg", "insight", "consumer", "category", "fmcg", "retail",
    "public relations", "digital marketing", "social media",
]
COUNTRY = "Ireland"

# Companies' own careers pages (see careers.py). Which companies, and which
# hiring system each uses, lives in careers-map.json; re-run the "Find company
# careers pages" workflow after editing companies.json.
USE_COMPANY_SITES = True
# Whole-word, case-insensitive matches against the job title. Company boards
# list every role they have, so these keep only sales and marketing ones.
CAREERS_KEYWORDS = [
    "sales", "marketing", "marketer", "business development", "sdr", "bdr",
    "brand", "demand generation", "lead generation",
    "growth marketing", "go-to-market", "gtm", "partnerships",
    "communications", "customer success", "social media", "campaign",
    "campaigns", "strategy", "strategist", "insights", "category",
    "public relations",
]
# Company boards list many Account Executive roles, which usually want 1-3
# years of closing experience. Dropped from company-site results only.
CAREERS_TITLE_EXCLUDE = ["account executive"]

# Firecrawl-backed boards. One page = one credit; the free plan gives 1,000 a
# month, seven searches a day costs roughly 220/month.
# Keep these single words: both sites use them as URL slugs.
FIRECRAWL_GLASSDOOR = ["sales", "marketing", "business-development",
                       "marketing-assistant", "graduate-marketing",
                       "marketing-intern", "junior-strategist"]
# jobs.ie is off. Its /jobs/<term> pages are SEO landing pages: the markup
# holds location facets and company logos but no linked job titles, so there
# is nothing stable to parse. Left wired up in case that changes.
FIRECRAWL_JOBS_IE = []

RESULTS_PER_QUERY = 40
HOURS_OLD = 26          # slight overlap with the daily cron; dedupe handles it
# 16 roles x 2 boards: a longer gap keeps LinkedIn from rate-limiting the run.
DELAY_BETWEEN_QUERIES = 9

# Drop anything whose title matches these before it reaches you.
# Matched as whole words (see scan._EXCLUDE_RX), so "lead" no longer rejects
# "Leadership". "architect" was dropped: Data Architect is often a mid-level
# title in Ireland and worth seeing.
TITLE_EXCLUDE = [
    "senior", "snr", "staff", "principal", "lead", "manager",
    "director", "head", "vp",
]

# Roles that need a language other than English, or cover a non-English
# market. Same whole-word matching as TITLE_EXCLUDE, applied to every source.
# "English speaking" roles are kept: only other languages are listed here.
LANGUAGE_EXCLUDE = [
    "german", "germany", "french", "france", "dutch", "netherlands", "flemish",
    "belgium", "italian", "italy", "spanish", "spain", "portuguese", "portugal",
    "brazil", "latam", "swedish", "danish", "norwegian", "finnish", "nordic",
    "nordics", "dach", "benelux", "iberia", "polish", "poland", "czech",
    "hungarian", "romanian", "greek", "turkish", "russian", "ukrainian",
    "arabic", "hebrew", "mandarin", "cantonese", "chinese", "japanese",
    "japan", "korean", "cee", "mena", "switzerland", "austria",
]

# Secrets come from the environment.
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
# Comma-separated. Everyone except SMTP_USER is Bcc'd (see notify.send_email).
DIGEST_TO = os.environ.get("DIGEST_TO", "")

WA_TOKEN = os.environ.get("WA_TOKEN", "")
WA_PHONE_ID = os.environ.get("WA_PHONE_ID", "")
WA_TO = os.environ.get("WA_TO", "")
WA_TEMPLATE = os.environ.get("WA_TEMPLATE", "job_digest")

# Fetch descriptions for the handful of jobs that survive dedupe, rather than
# the few hundred fetched. Also drops links that already 404.
ENRICH_SHORTLIST = True
