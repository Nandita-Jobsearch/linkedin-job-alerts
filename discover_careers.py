"""Find which hiring system (ATS) each company in companies.json uses.

Run from the Actions tab ("Find company careers pages"). It tries each
company's likely board names on every supported ATS, keeps the board that has
roles in Ireland, and writes:

  careers-map.json        what the daily run reads
  careers-discovery.md    a readable report, including companies not found

A company is only mapped when its board lists at least one role in Ireland.
That guards against a same-named account on a shared ATS, and a company with
no Irish roles has nothing to send anyway. Re-run it every month or two, or
after editing companies.json.
"""

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import careers
import config

PROVIDERS = ["greenhouse", "lever", "ashby", "smartrecruiters", "workable",
             "recruitee", "personio", "bamboohr"]


def slugs(company):
    if company.get("slugs"):
        return company["slugs"]
    base = re.sub(r"\(.*?\)", " ", company["company"].lower())
    words = re.sub(r"[^a-z0-9 ]", " ", base).split()
    out = ["".join(words), "-".join(words)]
    return list(dict.fromkeys(s for s in out if s))


def probe(company):
    tries = []
    if company.get("workday"):
        tries.append(("workday", company["workday"]))
    tries += [(ats, s) for s in slugs(company) for ats in PROVIDERS]

    best = None
    for ats, slug in tries:
        entry = {"company": company["company"], "ats": ats, "slug": slug}
        try:
            rows = careers.board_jobs(entry)
        except Exception as exc:
            if ats == "workday":
                print(f"workday {company['company']}: {type(exc).__name__}: {str(exc)[:200]}",
                      flush=True)
            continue
        if not rows:
            continue
        irish = [r for r, ok in rows if ok]
        matching = [r for r in irish
                    if careers.title_matches(r["title"], config.CAREERS_KEYWORDS)]
        hit = {**entry, "industry": company["industry"], "total": len(rows),
               "irish": len(irish), "matching": len(matching),
               "sample": [r["title"] for r in (matching or irish)[:3]]}
        if irish:
            return hit
        best = best or hit
    return best or {"company": company["company"], "industry": company["industry"],
                    "ats": None}


def main():
    companies = json.load(open("companies.json"))
    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(probe, companies))

    mapped = [r for r in results if r.get("ats") and r["irish"]]
    no_irish = [r for r in results if r.get("ats") and not r["irish"]]
    missing = [r for r in results if not r.get("ats")]

    json.dump([{k: r[k] for k in ("company", "industry", "ats", "slug")}
               for r in sorted(mapped, key=lambda r: r["company"].lower())],
              open("careers-map.json", "w"), indent=1, ensure_ascii=False)

    esc = lambda s: str(s).replace("|", "/")
    lines = [
        "# Company careers pages\n",
        f"Checked {len(results)} companies. **{len(mapped)}** have readable careers "
        f"pages with roles in Ireland and are now checked every day.\n",
        "## Checked daily\n",
        "| Company | Industry | System | Irish roles | Sales/marketing now | Examples |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in sorted(mapped, key=lambda r: (-r["matching"], r["company"].lower())):
        lines.append(f"| {esc(r['company'])} | {r['industry']} | {r['ats']} | {r['irish']} "
                     f"| {r['matching']} | {esc('; '.join(r['sample']))} |")
    lines += ["\n## Careers page found, but no roles in Ireland right now\n",
              "| Company | Industry | System |", "| --- | --- | --- |"]
    lines += [f"| {esc(r['company'])} | {r['industry']} | {r['ats']} |" for r in no_irish]
    lines += ["\n## Not readable automatically\n",
              "These use their own careers site. Their roles usually reach LinkedIn "
              "or Indeed anyway.\n",
              "| Company | Industry |", "| --- | --- |"]
    lines += [f"| {esc(r['company'])} | {r['industry']} |" for r in missing]
    open("careers-discovery.md", "w").write("\n".join(lines) + "\n")

    print(f"mapped {len(mapped)}, no Irish roles {len(no_irish)}, "
          f"not found {len(missing)} of {len(results)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
