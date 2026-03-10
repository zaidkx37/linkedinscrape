<h1 align="center">linkedinscrape</h1>

<p align="center">
  <b>LinkedIn profile scraper SDK for Python</b><br>
  Extract comprehensive profile data via LinkedIn's Voyager API — as a library or from the command line.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/version-0.1.0-orange?style=flat-square" alt="Version">
</p>

---

## Features

- **Full profile extraction** — identity, headline, about, industry, location, profile picture, background image
- **Experience & education** — all positions and degrees with dates, descriptions, company/school logos
- **Skills, certifications, projects** — complete lists with metadata
- **Contact info** — email, phone, websites, Twitter handles, birthday
- **Network stats** — connections, followers, mutual connections, following state
- **Additional sections** — languages, volunteer, honors, publications, courses, patents, test scores, organizations
- **Cookie validation** — checks your session is alive before scraping, not mid-batch
- **Stealth by default** — auto-detected timezone, randomized User-Agent, jittered delays, display fingerprint rotation
- **Proxy rotation** — single proxy, proxy list, or proxy file with round-robin rotation
- **Multiple export formats** — JSON, CSV, formatted console summary
- **Batch scraping** — file-based username lists with progress logging
- **Offline parsing** — parse previously saved API response JSON files

---

## Installation

```bash
# Core SDK
pip install -e .

# With optional CLI (click + rich)
pip install -e ".[cli]"

# Development
pip install -e ".[dev]"
```

Requires **Python 3.10+**.

---

## Setup

You need two cookies from an authenticated LinkedIn browser session:

1. Open LinkedIn in your browser and log in
2. Open DevTools → **Application** → **Cookies** → `https://www.linkedin.com`
3. Copy the values of:
   - `li_at` → your session token
   - `JSESSIONID` → your CSRF token (**remove the surrounding quotes**)

Create a `.env` file in your project root:

```env
LI_AT=AQEDAUXCrYoED3MK...your_token_here...
CSRF_TOKEN=ajax:5191528851126725620
```

> **Tip:** The SDK auto-loads `.env` — no extra setup needed.

---

## Quick Start

```python
from linkedinscrape import LinkedIn

# Credentials are loaded automatically from .env
with LinkedIn() as li:
    profile = li.scrape("username")

    print(profile.full_name)        # "John Doe"
    print(profile.headline)         # "Software Engineer at Google"
    print(profile.current_company)  # "Google"
    print(profile.current_title)    # "Software Engineer"
    print(profile.to_dict())        # Full nested dictionary
```

> The SDK validates your cookies on startup. If they're expired, you get a clear `CookieExpiredError` immediately — not a cryptic failure 10 requests deep.

## Even Simpler
```python
from linkedinscrape import LinkedIn, Exporter

# pass a full proxy file or path to rotate proxies (recommended)
proxies='proxyfile.txt'

# you can pass validate=False to skip cookie validation
li = LinkedIn(proxy_file=proxies, validate=False)
profile = li.scrape("username")

exporter = Exporter('output_dir')
exporter.to_json(profile)
```

---

## SDK Usage

### Single Profile

```python
from linkedinscrape import LinkedIn

li = LinkedIn()
profile = li.scrape("satyanadella")

print(profile.full_name)
print(profile.about)
print(profile.industry_name)
print(profile.connection_info.total_connections)
print(profile.following_state.follower_count)

for pos in profile.positions:
    print(f"{pos.title} at {pos.company_name} ({'Current' if pos.is_current else pos.end_date})")

for edu in profile.educations:
    print(f"{edu.degree_name} - {edu.field_of_study} @ {edu.school_name}")

li.close()
```

### Batch Scraping

```python
from linkedinscrape import LinkedIn

with LinkedIn() as li:
    profiles = li.scrape_batch([
        "satyanadella",
        "williamhgates",
        "jeffweiner08",
    ])

    for p in profiles:
        print(f"{p.full_name} — {p.headline}")
```

Or from a file:

```python
from pathlib import Path
from linkedinscrape import LinkedIn

with LinkedIn() as li:
    usernames = Path("usernames.txt").read_text().splitlines()
    profiles = li.scrape_batch(usernames)
```

### Explicit Credentials

```python
# Override environment variables
li = LinkedIn(li_at="your_token", csrf_token="ajax:123456")
```

### Parse Saved JSON

```python
from linkedinscrape import LinkedIn

# No credentials needed — works offline
profile = LinkedIn.parse_local("saved_response.json")
print(profile.full_name)
```

---

## Exporting

```python
from linkedinscrape import LinkedIn, Exporter

with LinkedIn() as li:
    profile = li.scrape("username")

    exporter = Exporter("output")

    # JSON (single profile)
    exporter.to_json(profile)                     # output/username.json

    # JSON (batch)
    exporter.to_json_batch([profile])              # output/profiles.json

    # CSV (flat format for spreadsheets)
    exporter.to_csv([profile])                     # output/profiles.csv

    # Console summary
    exporter.print_summary(profile)
```

### Serialization

Every model has a `.to_dict()` method:

```python
import json

data = profile.to_dict()
print(json.dumps(data, indent=2))

# Flat dict for CSV/dataframes
flat = profile.to_flat_dict()
```

---

## Proxy Support

```python
from linkedinscrape import LinkedIn

# Single proxy
li = LinkedIn(proxy="http://user:pass@host:port")

# Multiple proxies (round-robin rotation)
li = LinkedIn(proxies=[
    "http://proxy1:8080",
    "http://proxy2:8080",
    "http://proxy3:8080",
])

# From a file (one URL per line, # comments supported)
li = LinkedIn(proxy_file="proxies.txt")
```

On rate limit (HTTP 429), the proxy automatically rotates to the next one.

> **Tip:** Residential proxies are strongly recommended over datacenter proxies for LinkedIn.

---

## Stealth

The SDK is designed to look like a real browser session:

| Technique | Description |
|-----------|-------------|
| **Timezone auto-detect** | `x-li-track` timezone matches your OS, not a hardcoded value |
| **UA rotation** | Random User-Agent picked from a pool of real Chrome versions per session |
| **Display fingerprint** | Random screen resolution and DPI from common profiles |
| **Jittered delays** | +-30% random variation on inter-request delay (humans aren't metronomes) |
| **Batch jitter** | +-40% variation between profiles in batch mode |
| **Cookie validation** | Catches expired sessions upfront instead of burning requests |
| **Proxy rotation** | Automatic round-robin on rate limit |
| **Decoration fallback** | Tries 3 API decoration versions (v93 → v91 → v35) |

---

## CLI

```bash
# Single profile
linkedinscrape username

# Batch from file
linkedinscrape --file usernames.txt

# Parse local JSON (offline)
linkedinscrape --local response.json

# Export formats
linkedinscrape username --format json          # default
linkedinscrape username --format csv
linkedinscrape username --format both

# Custom output directory
linkedinscrape username --output results/

# Proxy
linkedinscrape username --proxy http://host:port
linkedinscrape username --proxy-file proxies.txt

# Adjust delay (seconds)
linkedinscrape username --delay 3.0

# Skip cookie check on startup
linkedinscrape username --skip-check

# Verbose logging
linkedinscrape username -v

# Skip console summary
linkedinscrape username --no-summary
```

---

## Data Models

The full profile contains these sections:

| Section | Model | Fields |
|---------|-------|--------|
| Identity | `LinkedInProfile` | name, headline, about, industry, URLs, flags |
| Picture | `ProfilePicture` | artifacts with URL, dimensions, expiry |
| Location | `Location` | country, city, geo name |
| Contact | `ContactInfo` | email, phone, websites, twitter, birthday |
| Network | `ConnectionInfo`, `FollowingState`, `MutualConnection` | connections, followers, mutual |
| Experience | `Position` | title, company, dates, description, type |
| Education | `Education` | school, degree, field, grade, activities |
| Skills | `Skill` | name, endorsement count |
| Certifications | `Certification` | name, authority, license, URL, dates |
| Projects | `Project` | title, description, URL, members, dates |
| Languages | `Language` | name, proficiency |
| Volunteer | `VolunteerExperience` | role, organization, cause, dates |
| Honors | `HonorAward` | title, issuer, description, date |
| Publications | `Publication` | name, publisher, URL, date |
| Courses | `Course` | name, number |
| Patents | `Patent` | title, issuer, number, status, dates |
| Test Scores | `TestScore` | name, score, date |
| Organizations | `Organization` | name, position, dates |

---

## Error Handling

```
LinkedInError
├── AuthenticationError        # Cookies missing at startup
├── CookieExpiredError         # Cookies expired mid-use (401/403)
├── ProfileNotFoundError       # Profile doesn't exist
├── RateLimitError             # HTTP 429
├── RequestError               # Other HTTP errors
└── ParsingError               # Response structure changed
```

```python
from linkedinscrape import LinkedIn, CookieExpiredError, ProfileNotFoundError

with LinkedIn() as li:
    try:
        profile = li.scrape("username")
    except ProfileNotFoundError:
        print("Profile does not exist")
    except CookieExpiredError:
        print("Session expired — refresh your cookies")
```

---

## Testing

Since this SDK hits LinkedIn's live API, **do not run tests against real accounts casually** — it risks triggering rate limits or account restrictions.

### Safe testing with saved JSON (no network, no risk)

```python
from linkedinscrape import LinkedIn

# Parse a previously saved API response — no cookies or network needed
profile = LinkedIn.parse_local("output/zaidkx37.json")

print(profile.full_name)
print(profile.headline)
print(len(profile.positions), "positions")
print(len(profile.skills), "skills")
print(profile.to_dict())
```

You already have saved profiles in `output/` from previous runs. Use those:

```bash
ls output/
# misterdebugger.json
# muhammad-danyal-31677b33a.json
# salman0x01.json
# zaidkx37.json
```

### Quick smoke test (1 live request)

If you must test live, scrape a single profile with verbose logging:

```bash
linkedinscrape username -v --no-summary
```

Or in Python:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from linkedinscrape import LinkedIn

with LinkedIn() as li:
    profile = li.scrape("username")
    print(f"OK: {profile.full_name} ({len(profile.positions)} positions)")
```

### Cookie validation only (no profile scrape)

```python
from linkedinscrape import LinkedIn, CookieExpiredError

try:
    li = LinkedIn()  # validates cookies automatically
    print("Cookies are valid")
    li.close()
except CookieExpiredError as e:
    print(f"Expired: {e}")
```

### Export round-trip test

```python
from linkedinscrape import LinkedIn, Exporter

# Parse saved → export → verify file exists
profile = LinkedIn.parse_local("output/zaidkx37.json")

exporter = Exporter("test_output")
path = exporter.to_json(profile)
print(f"Exported to {path}")

csv_path = exporter.to_csv([profile])
print(f"CSV at {csv_path}")
```

---

## Project Structure

```
src/linkedinscrape/
├── __init__.py          # Public API exports
├── client.py            # LinkedIn class (main entry point)
├── models.py            # All data models (dataclasses)
├── exceptions.py        # Exception hierarchy
├── exporter.py          # JSON / CSV / console export
├── _http.py             # HTTP client with retry, proxy, rate limiting
├── _endpoints.py        # API URLs, headers, stealth config
├── _parsers.py          # Response parsing logic
└── cli/
    ├── __init__.py
    └── app.py           # Optional CLI (argparse)
```

---

## Disclaimer & Limitations

> **This project is for educational and research purposes only.**

This SDK uses LinkedIn's **undocumented internal Voyager API** — the same endpoints the LinkedIn web app uses in your browser. There is no official API support, no guarantee of stability, and no endorsement from LinkedIn.

### What you should know

- **No automated login.** You must manually log in to LinkedIn in your browser and copy two cookies (`li_at` and `JSESSIONID`). The SDK cannot and will not automate the login process.
- **Requires a real LinkedIn account.** There is no way to use this SDK without an authenticated session from a real account.
- **Cookies expire.** LinkedIn session cookies have a limited lifespan. When they expire, you'll need to copy fresh values from your browser. There is no refresh mechanism.
- **Your account is at risk.** Excessive or aggressive scraping can trigger LinkedIn's anti-abuse systems, leading to temporary restrictions, CAPTCHAs, or permanent account bans. The stealth measures in this SDK reduce — but do not eliminate — this risk.
- **API can break at any time.** LinkedIn can change their internal API structure, query IDs, or decoration versions without notice. This will cause the SDK to fail until updated.
- **Data accuracy is not guaranteed.** The API may return incomplete data, especially for profiles with privacy restrictions or profiles you're not connected to.
- **Rate limits apply.** LinkedIn enforces rate limits. Even with proxy rotation and jittered delays, scraping too many profiles too quickly will get you throttled (HTTP 429) or blocked.
- **No official support.** This is a community project. LinkedIn does not provide documentation or support for the Voyager API.

### Use responsibly

- Don't scrape profiles in bulk without a legitimate reason
- Respect people's privacy and LinkedIn's Terms of Service
- Use reasonable delays between requests (the default 1.5s is a minimum)
- Consider using proxies for any non-trivial workload
- Never share your `li_at` cookie — it grants full access to your LinkedIn account

---

## License

MIT — see [LICENSE](LICENSE) for details.
