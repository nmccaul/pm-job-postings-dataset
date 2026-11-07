# PM Job Postings Dataset

What do tech companies ask for in product manager job postings? This repo builds a dataset of 482 open PM postings from 54 tech companies, pulled from the public [Greenhouse Job Board API](https://developers.greenhouse.io/job-board.html) on November 6, 2026. Each posting is turned into one row with its seniority level, location, work mode, pay range, years of experience, and flags for AI, technical and soft skills.

I made this for STAT 386 at BYU. The blog post that walks through it is [here](https://nmccaul.github.io/tutorial_blog/posts/pm-job-postings.html).

## What's in the repo

| Path | What it is |
| --- | --- |
| `data/pm_postings.csv` | The final dataset (482 rows, 33 columns) |
| `data/companies.csv` | The 54 company boards I pulled, with an industry label I assigned |
| `scripts/collect.py` | Downloads each company's job board from the API and saves it to `data/raw/` |
| `scripts/clean.py` | Keeps PM postings and turns the description text into columns |
| `scripts/eda.py` | Prints summary tables and saves the figures |
| `figures/` | Figures used in the blog post |

`data/raw/` isn't in the repo. It holds the full posting text, which belongs to each company, so the CSV keeps a link to each posting instead.

## How to run it

You need [uv](https://docs.astral.sh/uv/). No API key is required.

```bash
uv sync
uv run scripts/collect.py   # about 1 minute, 1 request per second
uv run scripts/clean.py
uv run scripts/eda.py
```

Postings come down when jobs are filled, so running `collect.py` on a different day will give you a different set of postings.

## Columns

| Column | Type | Description |
| --- | --- | --- |
| `company` | text | Company name |
| `industry` | category | Industry label I assigned (Fintech, Data & AI, Consumer, Software & dev tools, Security & infrastructure, Gaming, Hardware & IoT, Logistics) |
| `job_id` | integer | Greenhouse job ID |
| `title` | text | Job title |
| `seniority` | category | Level from the title: Intern, Associate / Entry, Product Manager, Senior, Staff / Principal, Group / Manager, Director+ |
| `location` | text | Location as the company wrote it |
| `us_based` | yes/no | Location names a US place |
| `work_mode` | category | Remote, Hybrid, or Onsite / not stated |
| `department` | text | Department on the board |
| `first_published` | date | When the posting first went up |
| `req_section_found` | yes/no | Whether a requirements section (like "What you bring" or "Qualifications") was found. If not, keyword flags use the full text |
| `ai_in_requirements` | yes/no | AI, ML, LLMs, generative AI, etc. mentioned in the requirements |
| `ai_anywhere` | yes/no | Same terms anywhere in the posting, including the company blurb |
| `ai_tools_in_requirements` | yes/no | Requirements ask you to use AI tools yourself (e.g. "use AI tools in your workflow," ChatGPT, Claude, Cursor) |
| `tech_sql`, `tech_coding`, `tech_cs_degree`, `tech_technical_background`, `tech_apis`, `tech_data_analytics` | yes/no | Technical skill mentioned in the requirements |
| `soft_communication`, `soft_leadership`, `soft_collaboration`, `soft_stakeholders`, `soft_customer_focus` | yes/no | Soft skill mentioned in the requirements |
| `tech_count`, `soft_count` | integer | Number of technical (0-6) and soft (0-5) skills mentioned |
| `min_years_experience` | number | First "N+ years of experience" in the requirements (lower end of ranges like "3-5 years") |
| `pay_low`, `pay_high` | number | First USD pay range listed in the posting |
| `pay_period` | category | `year` or `hour` |
| `url` | text | Link to the posting |
| `board_open_jobs` | integer | Total open jobs of any kind on the company's board, a rough size measure |

## Things to know about the data

- Skill flags come from regular expressions, so they're approximate. I spot-checked postings by hand and fixed patterns that misfired, but some flags will still be wrong.
- Many companies list pay by location tier. `pay_low` and `pay_high` come from the first range listed, which could be any of the tiers.
- Pay is listed for 63% of postings. Pay transparency laws in states like California, New York, Washington and Colorado make US postings much more likely to have it.
- Titles don't mean the same thing at every company. Some companies (Anthropic, for example) title most roles just "Product Manager," so that level includes some very senior, highly paid roles.
- The data only covers companies that use Greenhouse and only the jobs open on one day.

## Ethics and scraping practice

The Greenhouse Job Board API is public, needs no key, and exists so job listings can be shown outside a company's careers page. The API's `robots.txt` only disallows `/embed/`. `collect.py` sends one request per second with an identifying User-Agent and saves each board so it's only pulled once. The dataset has no personal information. Recruiter names that appear in some descriptions are not kept, because the description text isn't saved in the CSV.
