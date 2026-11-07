"""Turn the saved Greenhouse boards into one table of product manager postings.

Reads data/raw/<slug>.json (made by collect.py) and data/companies.csv,
keeps PM postings, pulls skills, pay, experience and seniority out of the
description text, and writes data/pm_postings.csv.

The full description text is NOT saved in the output. Each row keeps the
posting URL instead.

Usage:
    uv run scripts/clean.py
"""

import html
import json
import re
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
OUT_PATH = ROOT / "data" / "pm_postings.csv"

PM_TITLE = re.compile(r"product manag|product owner|associate product manager", re.I)

# ---------------------------------------------------------------------------
# Finding the requirements section
# ---------------------------------------------------------------------------
# A short line that matches REQ_HEADING starts the requirements section, and
# the next short line that matches STOP_HEADING ends it.
REQ_HEADING = re.compile(
    r"qualifications|requirements|who you are|what you bring|what you'll bring|"
    r"what we look for|what we're looking for|you have|you may be a good fit|"
    r"about you|you might thrive|you'll thrive|experience:|skills|"
    r"what you need|we're excited about you|you are|bonus points|nice to have",
    re.I,
)
STOP_HEADING = re.compile(
    r"^about|benefits|compensation|pay range|pay transparency|salary|"
    r"equal opportunity|perks|why join|our commitment|what we offer|logistics|"
    r"location|the base|annual|how we|additional information|please note|"
    r"us applicants|accommodation|diversity|come work|like what you hear|"
    r"for roles performing|guidance on candidates|privacy",
    re.I,
)
MAX_HEADING_LEN = 70

# ---------------------------------------------------------------------------
# Keyword flags (searched in the requirements section)
# ---------------------------------------------------------------------------
AI_TERMS = (
    r"(?-i:\bAI\b|\bA\.I\.|\bML\b|\bLLMs?\b)|artificial intelligence|machine learning|"
    r"generative|\bgen ?AI\b|large language model|\bagentic\b|\bAI agents?\b"
)
AI_TOOLS = (
    r"AI tool|AI-native|AI-powered tools|AI coding|ChatGPT|Claude Code|(use|leverage)\w* Claude|\bCursor\b|"
    r"Copilot|prompt(ing)? |vibe cod|use(s|d)? AI|using AI|leverag\w* AI|"
    r"agentic coding|AI-enabled|coding (agents|tools)"
)

TECH_SKILLS = {
    "sql": r"\bSQL\b",
    "coding": r"\bpython\b|\bcoding\b|\bprogramming\b|write code|writing code|"
              r"\bjavascript\b|\bjava\b|software development experience",
    "cs_degree": r"computer science|(?-i:\bCS\b|\bSTEM\b)|technical degree|"
                 r"engineering degree|degree in engineering|related technical field",
    "technical_background": r"technical background|technical depth|technical acumen|"
                            r"engineering background|technical aptitude|"
                            r"technically (strong|fluent|minded|savvy)|strong technical",
    "apis": r"\bAPIs?\b|SDKs?\b|developer (platform|tools|products|experience)",
    "data_analytics": r"analytic|data-driven|data driven|A/B|experiment|metrics|"
                      r"quantitative",
}
SOFT_SKILLS = {
    "communication": r"communicat|storytell|written and verbal|verbal and written",
    "leadership": r"leadership|influenc|\bleading\b|\blead (teams|cross|without)",
    "collaboration": r"collaborat|cross-functional|cross functional|partner(ing)? with|"
                     r"teamwork",
    "stakeholders": r"stakeholder|executive|alignment|align ",
    "customer_focus": r"customer empathy|user empathy|customer-obsess|customer obsess|"
                      r"empathy|customer-centric|user-centric|customer needs|user needs",
}

YEARS = re.compile(r"(\d{1,2})\s*(?:\+|-\s*\d{1,2}|–\s*\d{1,2}|to\s*\d{1,2})?\s*\+?\s*"
                   r"years?", re.I)

# Pay like "$150,000 - $200,000", "$150K—$200K", "$54 — $56 USD"
MONEY = r"\$\s?(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s?([kK])?"
PAY_RANGE = re.compile(MONEY + r"\s*(?:USD)?\s*(?:-|–|—|to)\s*" + MONEY)
NON_USD = re.compile(r"CAD|C\$|AUD|A\$|SGD|NZD|HKD|MXN", re.I)

US_STATES = (
    "Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|"
    "Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|"
    "Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|"
    "Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|"
    "Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|"
    "Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming"
)
US_LOCATION = re.compile(
    rf"United States|\bUSA?\b|\bU\.S\.|{US_STATES}|"
    r",\s?(?:CA|NY|WA|TX|IL|MA|CO|GA|NC|OR|PA|UT|VA|DC|FL|AZ|NJ|MN|MI|OH)\b|"
    r"San Francisco|Seattle|NYC|Chicago|Austin|Boston|Denver|Los Angeles|"
    r"Mountain View|Palo Alto|San Mateo|Menlo Park|Bellevue|Atlanta|Oakland|Sunnyvale|"
    r"Santa Clara|San Jose|Pittsburgh|Portland|Lehi|Salt Lake|Miami|Washington,? DC",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def html_to_lines(content: str) -> list[str]:
    """Greenhouse sends HTML-escaped HTML. Return the non-empty text lines."""
    soup = BeautifulSoup(html.unescape(content or ""), "html.parser")
    for tag in soup.find_all(["li", "p", "h1", "h2", "h3", "h4", "div", "br"]):
        tag.insert_before("\n")
    text = soup.get_text(" ")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.split("\n")]
    return [line for line in lines if line]


def requirements_section(lines: list[str]) -> str | None:
    """Return the text under the requirements-style headings, or None if none found."""
    keep, inside = [], False
    for line in lines:
        is_heading = len(line) <= MAX_HEADING_LEN
        if is_heading and REQ_HEADING.search(line) and not STOP_HEADING.search(line):
            inside = True
            continue
        if inside and is_heading and STOP_HEADING.search(line):
            inside = False
            continue
        if inside:
            keep.append(line)
    return "\n".join(keep) if keep else None


def has(pattern: str, text: str) -> bool:
    """Case-insensitive search. Acronyms in the patterns use (?-i:...) to stay case-sensitive."""
    return re.search(pattern, text, re.I) is not None


def seniority(title: str) -> str:
    """Bucket a title into a seniority level. Order matters: check top levels first."""
    t = title.lower()
    if re.search(r"\bintern(ship)?\b", t):
        return "Intern"
    if re.search(r"\bdirector\b|\bvp\b|vice president|\bhead of\b|chief", t):
        return "Director+"
    if re.search(r"group product|\bmanager,? (of )?product management|"
                 r"senior manager|\bmanager, .*product|product management manager", t):
        return "Group / Manager"
    if re.search(r"\bstaff\b|principal|\blead\b", t):
        return "Staff / Principal"
    if re.search(r"\bsenior\b|\bsr\.?\b|\biii\b", t):
        return "Senior"
    if re.search(r"associate|\bapm\b|new grad|early career|\bjunior\b|"
                 r"product manager,? (i|1)\b", t):
        return "Associate / Entry"
    return "Product Manager"


def work_mode(location: str, text: str) -> str:
    loc = location.lower()
    if "hybrid" in loc:
        return "Hybrid"
    if "remote" in loc:
        return "Remote"
    if re.search(r"\bhybrid\b", text, re.I):
        return "Hybrid"
    if re.search(r"fully remote|remote-first|remote first|this role is remote|"
                 r"this is a remote", text, re.I):
        return "Remote"
    return "Onsite / not stated"


def to_number(amount: str, k: str | None) -> float:
    value = float(amount.replace(",", ""))
    return value * 1000 if k else value


def pay_range(text: str) -> tuple[float | None, float | None, str | None]:
    """Return (low, high, period) for the first USD pay range in the posting."""
    for match in PAY_RANGE.finditer(text):
        context = text[max(0, match.start() - 60): match.end() + 15]
        if NON_USD.search(context):
            continue
        low = to_number(match.group(1), match.group(2))
        high = to_number(match.group(3), match.group(4))
        if low > high:
            continue
        if high >= 20_000:
            return low, high, "year"
        if 10 <= low <= 200:
            return low, high, "hour"
    return None, None, None


def min_years(text: str) -> float | None:
    """First 'N+ years' mentioned with 'experience' nearby, as a number."""
    for match in YEARS.finditer(text):
        after = text[match.end(): match.end() + 60].lower()
        if "experience" in after or "of product" in after or "in product" in after:
            years = int(match.group(1))
            if 0 <= years <= 25:
                return years
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def parse_job(job: dict, slug: str) -> dict:
    lines = html_to_lines(job.get("content", ""))
    full_text = "\n".join(lines)
    req_text = requirements_section(lines)
    search_text = req_text or full_text
    location = (job.get("location") or {}).get("name", "").strip()

    row = {
        "job_id": job["id"],
        "slug": slug,
        "title": job["title"].strip(),
        "seniority": seniority(job["title"]),
        "location": location,
        "us_based": bool(US_LOCATION.search(location)),
        "work_mode": work_mode(location, full_text),
        "department": "; ".join(d["name"] for d in job.get("departments", [])),
        "first_published": (job.get("first_published") or job.get("updated_at") or "")[:10],
        "req_section_found": req_text is not None,
        "ai_in_requirements": has(AI_TERMS, search_text),
        "ai_anywhere": has(AI_TERMS, full_text),
        "ai_tools_in_requirements": has(AI_TOOLS, search_text),
    }
    for name, pattern in TECH_SKILLS.items():
        row[f"tech_{name}"] = has(pattern, search_text)
    for name, pattern in SOFT_SKILLS.items():
        row[f"soft_{name}"] = has(pattern, search_text)
    row["tech_count"] = sum(row[f"tech_{n}"] for n in TECH_SKILLS)
    row["soft_count"] = sum(row[f"soft_{n}"] for n in SOFT_SKILLS)
    years = min_years(search_text)
    row["min_years_experience"] = years if years is not None else min_years(full_text)
    row["pay_low"], row["pay_high"], row["pay_period"] = pay_range(full_text)
    row["word_count"] = len(full_text.split())
    row["url"] = job.get("absolute_url")
    return row


def main() -> None:
    companies = pd.read_csv(ROOT / "data" / "companies.csv")
    rows = []
    for slug in companies["slug"]:
        path = RAW_DIR / f"{slug}.json"
        if not path.exists():
            print(f"{slug}: no saved board, run collect.py first")
            continue
        board = json.loads(path.read_text())
        jobs = [j for j in board.get("jobs", []) if PM_TITLE.search(j["title"])]
        rows += [parse_job(job, slug) for job in jobs]

    df = pd.DataFrame(rows)

    # Size proxy: how many jobs of any kind the company had open on its board
    board_sizes = {
        slug: len(json.loads((RAW_DIR / f"{slug}.json").read_text()).get("jobs", []))
        for slug in companies["slug"] if (RAW_DIR / f"{slug}.json").exists()
    }
    df["board_open_jobs"] = df["slug"].map(board_sizes)
    df = companies.merge(df, on="slug", how="inner")

    # The same job is sometimes posted once per city. Keep one row per
    # company + title + description pay/skills combination.
    before = len(df)
    df = df.drop_duplicates(subset=["slug", "title", "pay_low", "pay_high",
                                    "min_years_experience", "word_count"])
    print(f"Dropped {before - len(df)} duplicate postings")

    df = df.drop(columns=["slug", "word_count"])
    df.to_csv(OUT_PATH, index=False)
    print(f"Saved {len(df)} postings from {df['company'].nunique()} companies "
          f"with {df.shape[1]} columns to {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
