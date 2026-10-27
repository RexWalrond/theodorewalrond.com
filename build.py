#!/usr/bin/env python3
"""Builds the static theodorewalrond.com site into ./docs (served by GitHub Pages).

Run:  python3 build.py            (preview build: noindex on every page)
      python3 build.py --live     (production build: indexable, adds CNAME)

Photos live in src/wp-content/uploads at the same paths the old WordPress site
used, so image URLs that Google already indexed keep working.
"""
import glob
import html as htmllib
import json
import os
import re
import shutil
import struct
import sys

LIVE = "--live" in sys.argv
BASE = "https://theodorewalrond.com"
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
OUT = os.path.join(HERE, "docs")
UP = "/wp-content/uploads/"
UPDATED = "2026-10-27"  # last site-wide change; used for sitemap lastmod and dateModified


def jpeg_size(path):
    """(width, height) of a JPEG, read from its SOF header."""
    with open(path, "rb") as f:
        d = f.read()
    i = 2
    while i + 9 < len(d):
        if d[i] != 0xFF:
            i += 1
            continue
        if d[i + 1] in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", d[i + 5:i + 9])
            return w, h
        i += 2 + struct.unpack(">H", d[i + 2:i + 4])[0]
    return None


def local_size(src):
    """Pixel size of a site image given its URL path (e.g. /wp-content/uploads/...)."""
    path = os.path.join(SRC, src.lstrip("/"))
    return jpeg_size(path) if os.path.exists(path) else None

NAV = [("Home", "/"), ("About", "/about/"), ("Blog", "/blog/"), ("Portfolio", "/portfolio/"),
       ("Resources", "/resources/"), ("Contact", "/contact/")]

HEADSHOT = UP + "2024/09/theodore-walrond-advocated-for-continuous-learning-and-development-1-819x1024.jpg"
PHOTOS = [  # (path, alt/caption)
    (HEADSHOT, "Theodore Walrond in a navy suit and blue tie"),
    (UP + "2024/09/theodore-walrond-aimed-for-a-professional-career-in-psychiatry-or-research-819x1024.jpg",
     "Theodore Walrond in a navy suit and white open-collar shirt"),
    (UP + "2024/09/theodore-walrond-aimed-to-blend-psychological-theories-with-physiological-insights-819x1024.jpg",
     "Theodore Walrond outdoors in a navy blazer"),
    (UP + "2024/09/theodore-walrond-analyzed-neurological-mechanisms-contributing-to-behavior-819x1024.jpg",
     "Theodore Walrond studio headshot with a blue tie"),
    (UP + "2024/09/theodore-walrond-applied-his-knowledge-of-physics-calculus-and-chemistry-at-university-819x1024.jpg",
     "Theodore Walrond studio headshot, open collar"),
    (UP + "2024/07/theodore-walrond-mastered-skills-such-as-equalization-techniques-in-scuba-diving.jpg",
     "Theodore Walrond hiking with a backpack in the mountains"),
]

# Theodore's other profiles. The old WordPress site linked to these; keeping the links preserves the
# support they give the profiles that rank for his name.
PROFILES = [
    ("LinkedIn", "Work history and education", "https://www.linkedin.com/in/theodore-rex-walrond/"),
    ("rexwalrond.com", "My main site, under the name Rex Walrond", "https://rexwalrond.com/"),
    ("Field notes", "Trip reports, gear and music", "https://rexwalrond.github.io/RexWalrond/"),
    ("Weebly", "Theodore Walrond on Weebly", "https://theodorewalrond.weebly.com/"),
    ("Issuu", "Biography, research summary, dive notes and the Rainier climb", "https://issuu.com/theodorewalrond"),
    ("Jimdo", "Theodore Walrond on Jimdo", "https://theodore-walrond.jimdosite.com/"),
    ("Webflow", "Theodore Walrond on Webflow", "https://theodore-walrond.webflow.io/"),
    ("Creator Spring", "Theodore Walrond's Spring page", "https://theodorewalrond.creator-spring.com/"),
    ("about.me", "Theodore Walrond on about.me", "https://about.me/theodorewalrond"),
    ("Muck Rack", "Theodore Walrond on Muck Rack", "https://muckrack.com/theodorewalrond"),
    ("Sessionize", "Speaker profile: research, diving and the mountains", "https://sessionize.com/theodorewalrond"),
    ("Crunchbase", "Theodore Walrond on Crunchbase", "https://www.crunchbase.com/person/theodore-walrond"),
    ("YouTube", "@theodorewalrond", "https://www.youtube.com/@theodorewalrond"),
    ("Strikingly", "Trip log: Rainier, the Tetons, Glacier and the High Sierra", "https://theodorewalrond.mystrikingly.com/"),
]


# Issuu publications, linked one by one so each document gets a direct link.
PUBLICATIONS = [
    ('Biography of Theodore Walrond', 'Background, research, diving and the mountains', 'https://issuu.com/theodorewalrond/docs/biography_of_theodore_walrond'),
    ('Research Experience in Neuroscience and Drug Development', 'McKnight Brain Institute and Romark Laboratories', 'https://issuu.com/theodorewalrond/docs/the_journey_of_an_aspiring_scientist_from_classro'),
    ("A Divemaster's Notes on Florida Springs and Teaching Scuba", 'UF Scientific Diving Program, 2020-2023', 'https://issuu.com/theodorewalrond/docs/leadership_beneath_the_surface_how_scuba_diving_s'),
    ('Backcountry Log: Six Trips Above Treeline', 'From the Four Pass Loop to the High Sierra, 2019-2025', 'https://issuu.com/theodorewalrond/docs/exploring_the_wilderness_essential_tips_for_succe'),
    ('Climbing Mount Rainier', 'A guided summit with International Mountain Guides, 2020', 'https://issuu.com/theodorewalrond/docs/reaching_new_heights_the_adventure_of_mountain_cl'),
]


def profile_links(items):
    return "".join(f'<a href="{u}" rel="me"><b>{t}</b><span>{d}</span></a>' for t, d, u in items)


PERSON = {
    "@context": "https://schema.org",
    "@type": "Person",
    "name": "Theodore Walrond",
    "alternateName": ["Theodore Rex Walrond", "Rex Walrond"],
    "url": BASE + "/",
    "image": {"@type": "ImageObject", "url": BASE + HEADSHOT, "caption": "Theodore Walrond", "width": 819, "height": 1024},
    "alumniOf": [{"@type": "CollegeOrUniversity", "name": "University of Florida", "alternateName": "UF", "sameAs": "https://www.ufl.edu/"}],
    "homeLocation": {"@type": "Place", "name": "St. Petersburg, Florida",
                     "address": {"@type": "PostalAddress", "addressLocality": "St. Petersburg", "addressRegion": "FL", "addressCountry": "US"}},
    "knowsAbout": ["Cognitive neuroscience", "Scuba diving", "Mountaineering", "Consumer health"],
    "sameAs": [u for _, _, u in PROFILES],
}

T26 = UP + "2026/10/"
TRIP_PHOTOS = [  # (path, alt/caption, width, height) real trip photos, GPS stripped; sizes read from the files
    (src, alt) + local_size(src) for src, alt in [
        (T26 + "theodore-walrond-mount-rainier-snowfield.jpg", "Theodore Walrond on Mount Rainier, July 2020"),
        (T26 + "theodore-walrond-four-pass-loop-maroon-bells.jpg", "Theodore Walrond on the Four Pass Loop, Colorado, 2019"),
        (T26 + "theodore-walrond-teton-crest-trail.jpg", "Theodore Walrond on the Teton Crest Trail, Wyoming, 2022"),
        (T26 + "theodore-walrond-glacier-national-park-bowman-lake.jpg", "Theodore Walrond at Bowman Lake, Glacier National Park, 2023"),
        (T26 + "theodore-walrond-divemaster-florida-spring.jpg", "Theodore Walrond diving a Florida spring"),
        (T26 + "theodore-walrond-skiing-telluride.jpg", "Theodore Walrond skiing in Telluride, Colorado"),
    ]
]

with open(os.path.join(SRC, "posts.json"), encoding="utf-8") as f:
    POSTS = sorted(json.load(f), key=lambda p: p["date"], reverse=True)
POST_ALT = {"hiking-adventures-from-day-trips-to-extended-treks-in-stunning-locations": PHOTOS[5][1],
            "preparing-for-mount-rainier-tips-for-a-successful-summit": "Snow-covered mountain peak against a blue sky"}

# Old WordPress URLs -> where they live now. Near-duplicate posts are folded into one post per topic.
REDIRECTS = {
    "theodore-walrond-medical-researcher/": "/",
    "category/blogs/": "/blog/",
    "the-joys-of-hiking-discovering-nature-on-foot/": "/hiking-adventures-from-day-trips-to-extended-treks-in-stunning-locations/",
    "backpacking-key-tips-for-a-successful-outdoor-adventure/": "/exploring-the-wilderness-essential-tips-for-successful-backpacking-adventures/",
}
for s in ["embracing-the-thrill-and-challenge-of-mountain-climbing", "scaling-peaks-the-thrill-and-challenge-of-mountain-climbing",
          "mountain-climbing-for-beginners-tips-for-reaching-new-heights", "scaling-peaks-thrill-challenge-mountain-climbing",
          "reaching-new-heights-a-beginners-guide-to-mountain-climbing-2"]:
    REDIRECTS[s + "/"] = "/reaching-new-heights-a-beginners-guide-to-mountain-climbing/"
for s in ["adventurous-slopes-discovering-the-beauty-of-backcountry-skiing", "adventurous-slopes-discovering-the-beauty-of-backcountry-skiing-2",
          "fresh-tracks-unveiling-the-beauty-of-backcountry-skiing", "mastering-the-slopes-techniques-for-advanced-skiers",
          "advanced-skiing-techniques-for-expert-skiers"]:
    REDIRECTS[s + "/"] = "/top-ski-destinations-for-expert-skiers-conquer-telluride-to-alta/"
for s in ["scuba-diving-and-leadership-lessons-from-the-depths-on-effective-leadership",
          "leadership-underwater-lessons-from-scuba-diving-that-transformed-my-approach",
          "organizing-and-leading-dives-what-scuba-diving-taught-me-about-effective-leadership",
          "mastering-technical-scuba-plan-skill-respect-repeat"]:
    REDIRECTS[s + "/"] = "/beneath-the-surface-building-stronger-leaders-and-teams-through-scuba-diving/"
for n in range(2, 7):  # WordPress blog pagination
    REDIRECTS[f"blog/page/{n}/"] = "/blog/"
for s in ["the-journey-of-an-aspiring-scientist-from-classroom-to-research-lab", "the-unseen-impact-of-academic-research-on-society",
          "tackling-tough-stem-labs-tips-for-excelling", "charting-the-path-an-aspiring-scientists-journey-from-classroom-to-research-lab",
          "from-research-to-reality-how-academic-exploration-prepares-you-for-professional-success",
          "from-classroom-to-lab-the-journey-of-an-aspiring-scientist", "the-aspiring-scientists-path-from-classroom-theories",
          "from-calculus-to-neuroscience-navigating-the-complex-world-of-stem-education", "surviving-and-thriving-in-stem-strategies-for-success",
          "journey-an-aspiring-scientist-from-classroom-to-research-lab", "journey-of-an-aspiring-scientist-from-classroom-to-research-lab"]:
    REDIRECTS[s + "/"] = "/bridging-the-gap-how-academic-research-prepares-you-for-real-world-challenges/"
with open(os.path.join(SRC, "old_tags.txt")) as f:
    for tag in f.read().split():
        REDIRECTS[f"tag/{tag}/"] = "/blog/"

ARTICLES = {
    "Research and healthcare": [
        ("Theodore Rex Walrond Explores Subarachnoid Hemorrhages and Alzheimer's Research", "The American Reporter",
         "https://www.theamericanreporter.com/theodore-rex-walrond-explores-subarachnoid-hemorrhages-and-alzheimers-research/"),
        ("Theodore Rex Walrond: Inside the Internship at Romark and Its Role in Pharmaceutical Research", "Disrupt Magazine",
         "https://disruptmagazine.com/theodore-rex-walrond-inside-the-internship-at-romark-and-its-role-in-pharmaceutical-research/"),
        ("Cognitive Neuroscience: Theodore Walrond's Passion and Work", "Kivo Daily",
         "https://kivodaily.com/lifestyle/cognitive-neuroscience-theodore-walronds-passion-and-work/"),
        ("How Psychological Research Translates into Pharmaceutical Innovations", "MedicalResearch.com",
         "https://medicalresearch.com/how-psychological-research-translates-into-pharmaceutical-innovations/"),
        ("Theodore Rex Walrond Highlights the Connection between Cognitive Psychology and Healthcare", "Health Works Collective",
         "https://www.healthworkscollective.com/theodore-rex-walrond-highlights-the-connection-between-cognitive-psychology-and-healthcare/"),
        ("Theodore Rex Walrond Discusses How Data Analysis Powers Breakthroughs in Medical Research", "Let's Be Game Changers",
         "https://letsbegamechangers.com/blog/theodore-rex-walrond-discusses-how-data-analysis-powers-breakthroughs-in-medical-research/"),
        ("Theodore Rex Walrond: The Impact of Research Internships on Career Development in Science", "HHM Global",
         "https://www.hhmglobal.com/health-wellness/theodore-rex-walrond-the-impact-of-research-internships-on-career-development-in-science"),
        ("Theodore Rex Walrond: How Cognitive Neuroscience Explains Learning and Memory Formation", "MediTech Today",
         "https://meditechtoday.com/cognitive-neuroscience-learning-memory-formation/"),
    ],
    "The outdoors": [
        ("Exploring the Outdoors with Theodore Walrond: Hiking, Climbing, and More", "Travel Daily News",
         "https://www.traveldailynews.com/column/featured-articles/exploring-the-outdoors-with-theodore-walrond-hiking-climbing-and-more/"),
        ("Theodore Walrond's Guide to Safe and Enjoyable SCUBA Diving", "South Florida Reporter",
         "https://southfloridareporter.com/theodore-walronds-guide-to-safe-and-enjoyable-scuba-diving/"),
    ],
}


def esc(s):
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def jsonld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj) + "</script>\n"


WEBSITE = {"@context": "https://schema.org", "@type": "WebSite", "name": "Theodore Walrond", "alternateName": "theodorewalrond.com", "url": BASE + "/"}
PROFILE_PAGE = {"@context": "https://schema.org", "@type": "ProfilePage", "url": BASE + "/about/", "dateModified": UPDATED,
                "mainEntity": {k: v for k, v in PERSON.items() if k != "@context"}}


def crumbs(*items):
    """BreadcrumbList JSON-LD; items are (name, path) pairs after Home."""
    trail = [("Home", "")] + list(items)
    return jsonld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": BASE + "/" + p} for i, (n, p) in enumerate(trail)]})


def finish_imgs(body):
    """Give every <img> its real width/height (no layout shift), load the first image eagerly with high
    priority (it's the largest above-the-fold image) and lazy-load the rest."""
    seen = [False]

    def fix(m):
        tag = m.group(0)
        if "width=" not in tag:
            size = local_size(re.search(r'src="([^"]+)"', tag).group(1))
            if size:
                tag = tag[:-1] + f' width="{size[0]}" height="{size[1]}">'
        if not seen[0]:
            seen[0] = True
            if "loading=" not in tag:
                tag = tag[:-1] + ' fetchpriority="high">'
        elif "loading=" not in tag:
            tag = tag[:-1] + ' loading="lazy">'
        if "decoding=" not in tag:
            tag = tag[:-1] + ' decoding="async">'
        return tag
    return re.sub(r"<img\b[^>]*>", fix, body)


def write(path, html):
    dest = os.path.join(OUT, path, "index.html") if path.endswith("/") or path == "" else os.path.join(OUT, path)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(html)


def page(path, title, description, body, current=None, extra_head="", image=HEADSHOT):
    t, d = htmllib.unescape(title), htmllib.unescape(description)
    if path not in ("404.html", "privacy-policy/") and not (30 <= len(t) <= 65 and 120 <= len(d) <= 160):
        print(f"  ! check lengths on /{path}: title {len(t)}, description {len(d)}")
    body = finish_imgs(body)
    nav ="".join(f'<a href="{href}"{" aria-current=page" if label == current else ""}>{label}</a>' for label, href in NAV)
    robots = "" if LIVE else '<meta name="robots" content="noindex,nofollow">\n'
    canonical = BASE + "/" + path
    write(path, f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{esc(description)}">
{robots}<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Theodore Walrond">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{BASE}{image}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='10' fill='%232e5b4a'/%3E%3Ctext x='32' y='44' font-family='Georgia,serif' font-size='34' fill='%23fbfaf6' text-anchor='middle'%3ETW%3C/text%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Manrope:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/style.css">
{extra_head}</head>
<body>
<header class="site-head"><div class="wrap"><a class="brand" href="/">Theodore Walrond</a><nav class="nav">{nav}</nav></div></header>
<main>
{body}
</main>
<footer class="site-foot"><div class="wrap"><span>&copy; 2026 Theodore Walrond</span><span><a href="https://www.linkedin.com/in/theodore-rex-walrond/">LinkedIn</a> &middot; <a href="https://rexwalrond.com/">rexwalrond.com</a> &middot; <a href="https://rexwalrond.github.io/RexWalrond/">Field notes</a></span></div></footer>
</body>
</html>
""")


def redirect(path, target):
    write(path, f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Moved</title>
<link rel="canonical" href="{BASE}{target}">
<meta http-equiv="refresh" content="0; url={target}">
</head><body><p>This page has moved: <a href="{target}">{BASE}{target}</a></p></body></html>
""")


def display_variant(rel):
    """Prefer WordPress's 1024px rendition of a featured image if it exists."""
    stem = rel[:-4]
    for pat in ("-1024x*.jpg", "-768x*.jpg"):
        hits = sorted(glob.glob(os.path.join(SRC, stem + pat)))
        if hits:
            return "/" + os.path.relpath(hits[0], SRC).replace(os.sep, "/")
    return "/" + rel


def row(p):
    from datetime import date
    d = date.fromisoformat(p["date"]).strftime("%b %Y")
    return f'<a href="/{p["slug"]}/"><time datetime="{p["date"]}">{d}</time><b>{p["title"]}</b><span class="tag">{p["tag"]}</span></a>'


def build():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    shutil.copy(os.path.join(SRC, "style.css"), OUT)
    shutil.copytree(os.path.join(SRC, "wp-content"), os.path.join(OUT, "wp-content"))

    # ---------------- Home
    press = "".join(f'<a href="{u}" rel="noopener"><b>{t}</b><span>{pub}</span></a>' for t, pub, u in ARTICLES["Research and healthcare"][:3] + ARTICLES["The outdoors"][:1])
    home = f"""
<section class="hero">
  <div class="wrap hero-grid">
    <div class="frame"><img src="{HEADSHOT}" alt="{PHOTOS[0][1]}" width="819" height="1024"></div>
    <div>
      <div class="kicker">Neuroscience &#183; Diving &#183; Mountains</div>
      <h1>Theodore Walrond</h1>
      <p class="aka">Most people call me Rex.</p>
      <p class="lede">I trained in behavioral and cognitive neuroscience at the University of Florida, spent my spare time teaching people to breathe underwater, and save my time off for high mountain passes. These days I live in St. Petersburg, Florida, on Tampa Bay, where I'm building an early-stage company in consumer health.</p>
      <div class="cta"><a class="btn btn-solid" href="/about/">About me</a><a class="btn btn-line" href="/portfolio/">Photos</a></div>
    </div>
  </div>
</section>

<section class="band">
  <div class="wrap">
    <div class="kicker">What I care about</div>
    <h2 class="sec-title">Three things I keep coming back to</h2>
    <div class="threads">
      <div class="thread"><div class="num">01</div><h3>The brain</h3><p>Two research roles shaped how I think. At UF's McKnight Brain Institute (2022&#8211;2023) I worked through more than 300 studies on whether bleeding around the brain raises the risk of Alzheimer's later in life. In the summer of 2021, at Romark Laboratories, I tracked more than two dozen COVID-19 drug candidates as their trials unfolded.</p></div>
      <div class="thread"><div class="num">02</div><h3>The water</h3><p>I'm an SDI Divemaster. From 2020 to 2023 I was a teaching assistant for the University of Florida's Scientific Diving Program, helping students work from Open Water up through Master Diver. My favorite Florida dive is Paradise Springs. My favorite anywhere is the kelp forest off Catalina Island.</p></div>
      <div class="thread"><div class="num">03</div><h3>The mountains</h3><p>I summited Mount Rainier on a guided climb with International Mountain Guides, and I've backpacked the John Muir Trail, the Teton Crest Trail and the backcountry of Glacier National Park. The thinner the air, the better the trip.</p></div>
    </div>
  </div>
</section>

<section class="now">
  <div class="wrap">
    <div class="kicker">These days</div>
    <h2>Putting a science background to work in consumer health</h2>
    <p>After completing graduate coursework in finance at the University of Notre Dame, I turned my attention to building. I'm now working on an early-stage consumer health venture, drawing on what I learned reading clinical research and what I learned about how companies get financed.</p>
    <p>I also spent a year as an Impact Partner with the American Parkinson Disease Association, leading a monthly support group.</p>
  </div>
</section>

<section class="sec">
  <div class="wrap">
    <div class="kicker">Writing</div>
    <h2 class="sec-title">Recent posts</h2>
    <div class="rows">{"".join(row(p) for p in POSTS[:4])}</div>
    <div class="cta"><a class="btn btn-line" href="/blog/">All posts</a></div>
  </div>
</section>

<section class="sec" style="padding-top:0">
  <div class="wrap"><div class="narrow" style="max-width:740px">
    <div class="kicker">In the press</div>
    <h2 class="sec-title">Articles about my work</h2>
    <div class="press">{press}</div>
    <div class="cta"><a class="btn btn-line" href="/resources/">More articles</a></div>
  </div></div>
</section>

<section class="sec" style="padding-top:0">
  <div class="wrap">
    <div class="kicker">Elsewhere online</div>
    <h2 class="sec-title">Find Theodore Walrond elsewhere</h2>
    <div class="elsewhere">{profile_links(PROFILES)}</div>
  </div>
</section>

<section class="sec" style="padding-top:0">
  <div class="wrap"><div class="close"><h2>Want to compare notes on a trip, a dive or a study?</h2><div class="cta" style="margin-top:0"><a class="btn btn-solid" href="/contact/">Get in touch</a><a class="btn btn-line" href="https://www.linkedin.com/in/theodore-rex-walrond/">LinkedIn</a></div></div></div>
</section>
"""
    page("", "Theodore Walrond | Neuroscience, Diving &amp; Mountains, Tampa Bay",
         "Theodore Walrond (Rex): University of Florida neuroscience graduate, SDI Divemaster and mountaineer in Tampa Bay, now starting a consumer health company.",
         home, "Home", jsonld(PERSON) + jsonld(WEBSITE))

    # ---------------- About
    about = f"""
<div class="wrap narrow">
  <div class="page-head"><div class="kicker">About</div><h1>About Theodore Walrond</h1>
  <p>I'm Theodore Rex Walrond. I answer to Rex, which is why you'll also find me as Rex Walrond, including on my other site, <a href="https://rexwalrond.com/">rexwalrond.com</a>.</p></div>
  <div class="prose">
    <figure class="side-photo"><img src="{PHOTOS[1][0]}" alt="{PHOTOS[1][1]}" width="819" height="1024"></figure>
    <div class="facts">
      <div><b>Education</b>B.S. in Psychology (Behavioral and Cognitive Neuroscience), University of Florida, cum laude</div>
      <div><b>Graduate study</b>Completed graduate coursework in finance, University of Notre Dame</div>
      <div><b>Based in</b>St. Petersburg, Florida, on Tampa Bay</div>
      <div><b>Diving</b>SDI Divemaster, Master Scuba Diver, Rescue Diver, Nitrox</div>
      <div><b>Highest summit</b>Mount Rainier, 14,411 ft</div>
    </div>
    <h2>How I got into research</h2>
    <p>I chose behavioral and cognitive neuroscience because I wanted to understand behavior from the physical side: how chemistry and wiring in the brain show up in learning, mood and movement. That curiosity turned into two research roles.</p>
    <p>From 2022 to 2023 I worked at the University of Florida's McKnight Brain Institute on a single hard question: can a subarachnoid hemorrhage, a bleed into the space around the brain, leave someone more vulnerable to Alzheimer's disease later on? My job was to read and analyze the evidence, more than 300 studies, and turn it into a framework of the variables that seemed to connect vascular injury to neurodegeneration. The team used it to decide which experiments to run next, and I presented the findings to faculty across three departments.</p>
    <p>Earlier, in the summer of 2021, I worked as a research assistant at Romark Laboratories. I built dashboards that tracked more than 25 COVID-19 drug candidates by trial phase, mechanism and early efficacy, and reviewed over 400 articles on the antiviral potential of niclosamide.</p>
    <h2>Teaching underwater</h2>
    <p>From 2020 to 2023 I was a divemaster and teaching assistant for UF's Scientific Diving Program. I helped run courses from Open Water through Master Diver: in-water skill sessions, dry-land drills and classroom lectures on dive planning, dive physics and physiology, for more than 30 students. My own certifications are through SDI: Open Water, Advanced, Nitrox, Rescue, Master Scuba Diver and Divemaster.</p>
    <p>Most of my diving has been in Florida's freshwater springs, and Paradise Springs is the one I'd go back to tomorrow. The best dive I've done anywhere was the kelp forest off Catalina Island.</p>
    <h2>Time above treeline</h2>
    <p>The trip people ask about is Mount Rainier, which I climbed on a guided expedition with International Mountain Guides in 2020. The rest of my list is mostly long backpacking routes: the Four Pass Loop near Maroon Bells (2019), the John Muir Trail through Yosemite with side trips up Half Dome and Clouds Rest (2021), the Teton Crest Trail (2022), Boulder Pass in Glacier National Park (2023), and fifty miles of High Sierra from Onion Valley to Whitney Portal (2025). I keep shorter trip notes in my <a href="https://rexwalrond.github.io/RexWalrond/trips.html">field notes</a>.</p>
    <h2>Giving back</h2>
    <p>In 2025 and 2026 I volunteered as an Impact Partner with the American Parkinson Disease Association, leading a monthly support group of 15 to 20 people. I wrote about <a href="https://rexwalrond.weebly.com/blog/what-leading-a-parkinsons-support-group-taught-me">what that year taught me</a>.</p>
    <h2>What I'm doing now</h2>
    <p>I'm building an early-stage venture in consumer health, where my research background and my finance coursework both get used every week.</p>
    <h2>Off the clock</h2>
    <p>Golf, acoustic guitar, more sleep and training data than anyone needs, and strong opinions about Zach Bryan's catalog.</p>
    <p><a href="/contact/">Contact me</a> &#183; <a href="https://www.linkedin.com/in/theodore-rex-walrond/">LinkedIn</a></p>
  </div>
</div>
<div style="height:72px"></div>
"""
    page("about/", "About Theodore Walrond | UF Neuroscience, Diving &amp; Mountaineering",
         "About Theodore Walrond: St. Petersburg, FL neuroscience graduate (UF), former McKnight Brain Institute researcher, SDI Divemaster and Mount Rainier climber.",
         about, "About", jsonld(PROFILE_PAGE) + crumbs(("About", "about/")), image=PHOTOS[1][0])

    # ---------------- Portfolio (photos)
    figs = "".join(f'<figure><img src="{src}" alt="{alt}" loading="lazy" width="819" height="1024"><figcaption>{alt}.</figcaption></figure>' for src, alt in PHOTOS)
    figs += "".join(f'<figure><img src="{src}" alt="{alt}" loading="lazy" width="{w}" height="{h}"><figcaption>{alt}.</figcaption></figure>' for src, alt, w, h in TRIP_PHOTOS)
    gallery_ld = {"@context": "https://schema.org", "@type": "ImageGallery", "name": "Photos of Theodore Walrond",
                  "about": {"@type": "Person", "name": "Theodore Walrond"},
                  "image": [{"@type": "ImageObject", "contentUrl": BASE + src, "caption": alt} for src, alt in PHOTOS]
                           + [{"@type": "ImageObject", "contentUrl": BASE + src, "caption": alt} for src, alt, _, _ in TRIP_PHOTOS]}
    portfolio = f"""
<div class="wrap">
  <div class="page-head narrow"><div class="kicker">Portfolio</div><h1>Photos of Theodore Walrond</h1><p>Recent headshots and photos from the trail and the water. For my research and service work, see <a href="https://rexwalrond.com/portfolio/">rexwalrond.com</a>; for trip reports, see my <a href="https://rexwalrond.github.io/RexWalrond/trips.html">field notes</a>.</p></div>
  <div class="gallery">{figs}</div>
</div>
<div style="height:88px"></div>
"""
    page("portfolio/", "Photos of Theodore Walrond: Headshots, Trails and Diving",
         "Photos of Theodore Walrond: recent headshots, plus Mount Rainier, the Four Pass Loop, the Teton Crest Trail, Glacier National Park and a Florida spring.",
         portfolio, "Portfolio", jsonld(gallery_ld) + crumbs(("Portfolio", "portfolio/")))

    # ---------------- Blog index + posts
    blog_intro = ("<p>Trip reports, dive notes and research. Each trip post covers one route I've actually done, from the guided "
                  "Mount Rainier climb in 2020 to Glacier National Park in 2023, with the mileage, the hard parts and what I'd do "
                  "differently. The dive post is about three years with UF's Scientific Diving Program, and the research posts are "
                  'plain-language takes on the questions I worked on. Shorter notes are in my <a href="https://rexwalrond.github.io/RexWalrond/trips.html">field notes</a>.</p>')
    page("blog/", "Theodore Walrond's Blog: Trip Reports, Dives and Research",
         "Trip reports and notes by Theodore Walrond: Mount Rainier, the Teton Crest Trail, Glacier National Park, Florida springs diving and research.",
         f'<div class="wrap narrow"><div class="page-head"><div class="kicker">Blog</div><h1>Writing</h1>{blog_intro}</div><div class="rows">{"".join(row(p) for p in POSTS)}</div></div><div style="height:88px"></div>',
         "Blog", crumbs(("Blog", "blog/")))
    for p in POSTS:
        img = display_variant(p["image"]) if p["image"] else None
        alt = p.get("alt") or POST_ALT.get(p["slug"], p["title"])
        cap = f'<figcaption>{p["caption"]}</figcaption>' if p.get("caption") else ""
        fig = f'<figure><img src="{img}" alt="{alt}">{cap}</figure>' if img else ""
        art = {"@context": "https://schema.org", "@type": "BlogPosting", "headline": p["title"], "datePublished": p["date"],
               "author": {"@type": "Person", "name": "Theodore Walrond", "url": BASE + "/"}, "mainEntityOfPage": f"{BASE}/{p['slug']}/"}
        if p.get("modified"):
            art["dateModified"] = p["modified"]
        if img:
            art["image"] = {"@type": "ImageObject", "url": BASE + img, "caption": alt}
            if local_size(img):
                art["image"]["width"], art["image"]["height"] = local_size(img)
        from datetime import date
        d = date.fromisoformat(p["date"]).strftime("%B %-d, %Y")
        body = (f'<div class="wrap narrow"><div class="page-head"><div class="kicker">{p["tag"]} &#183; {d}</div><h1>{p["title"]}</h1>'
                f'<p>By Theodore Walrond</p></div><article class="prose">{fig}{p["html"]}</article>'
                f'<p style="margin-top:40px"><a href="/blog/">&#8592; All posts</a></p></div><div style="height:72px"></div>')
        title = p["seo_title"] or p["title"]
        desc = p["description"] or p["title"]
        if len(desc) > 160:
            desc = desc[:157].rsplit(" ", 1)[0] + "..."
        page(p["slug"] + "/", f"{esc(title)} | Theodore Walrond", desc, body, "Blog",
             jsonld(art) + crumbs(("Blog", "blog/"), (p["title"], p["slug"] + "/")), image=img or HEADSHOT)

    # ---------------- Resources
    groups = "".join(
        f'<h2 style="font-size:28px;margin:36px 0 8px">{g}</h2><div class="press">'
        + "".join(f'<a href="{u}" rel="noopener"><b>{t}</b><span>{pub}</span></a>' for t, pub, u in items) + "</div>"
        for g, items in ARTICLES.items())
    prof = profile_links(PROFILES)
    resources = f"""
<div class="wrap narrow">
  <div class="page-head"><div class="kicker">Resources</div><h1>Theodore Walrond in the press</h1><p>Articles that have featured my research and time outdoors, plus the other places I keep things online.</p></div>
  {groups}
  <h2 style="font-size:28px;margin:44px 0 8px">Publications on Issuu</h2>
  <div class="press">{profile_links(PUBLICATIONS)}</div>
  <h2 style="font-size:28px;margin:44px 0 8px">Elsewhere online</h2>
  <div class="press">{prof}</div>
</div>
<div style="height:88px"></div>
"""
    page("resources/", "Theodore Walrond in the Press: Articles and Profiles",
         "Articles featuring Theodore Walrond's research and outdoor pursuits, his Issuu publications, and links to his other sites and profiles online.",
         resources, "Resources", crumbs(("Resources", "resources/")))

    # ---------------- Contact, privacy, 404
    page("contact/", "Contact Theodore Walrond | Tampa Bay, Florida",
         "How to reach Theodore Walrond (Rex), a University of Florida neuroscience graduate and SDI Divemaster in St. Petersburg, Florida: email or LinkedIn.",
         '<div class="wrap narrow"><div class="page-head"><div class="kicker">Contact</div><h1>Contact Theodore Walrond</h1><p>Email is the fastest way to reach me. LinkedIn works too.</p>'
         '<p>Write if you are planning one of the routes I have written about, want a Florida spring recommendation, or are working on brain health research or Parkinson&#8217;s support. I live in St. Petersburg, on Tampa Bay.</p></div>'
         '<div class="cta"><a class="btn btn-solid" href="mailto:rexwalrond@gmail.com">Email me</a><a class="btn btn-line" href="https://www.linkedin.com/in/theodore-rex-walrond/">LinkedIn</a></div>'
         f'<h2 style="font-size:28px;margin:44px 0 8px">Elsewhere</h2><div class="press">{profile_links(PROFILES[:6])}</div></div><div style="height:88px"></div>',
         "Contact", crumbs(("Contact", "contact/")))
    page("privacy-policy/", "Privacy Policy | Theodore Walrond", "Privacy policy for theodorewalrond.com.",
         '<div class="wrap narrow"><div class="page-head"><div class="kicker">Privacy</div><h1>Privacy policy</h1></div><div class="prose"><p>This site has no forms, accounts, analytics or advertising, and it does not set cookies. Pages load fonts from Google Fonts, which receives standard request information such as your IP address. If you email me, I use your message only to reply.</p></div></div><div style="height:120px"></div>')
    page("404.html", "Page not found | Theodore Walrond", "This page doesn't exist.",
         '<div class="wrap narrow"><div class="page-head"><div class="kicker">404</div><h1>Page not found</h1><p>That page has moved or no longer exists.</p></div><div class="cta"><a class="btn btn-solid" href="/">Home</a><a class="btn btn-line" href="/blog/">Blog</a></div></div><div style="height:120px"></div>')

    # ---------------- Redirects for retired WordPress URLs
    for old, new in REDIRECTS.items():
        redirect(old, new)

    # ---------------- robots, sitemap, CNAME
    urls = ["", "about/", "blog/", "portfolio/", "resources/", "contact/"] + [p["slug"] + "/" for p in POSTS]
    # NetReputation's old WordPress sitemap index is still registered in Search Console and lists ~40 retired
    # URLs. Serving our sitemap at that address stops the "Page with redirect" warnings for sitemap URLs.
    with open(os.path.join(OUT, "sitemap_index.xml"), "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                f"  <sitemap><loc>{BASE}/sitemap.xml</loc><lastmod>{UPDATED}</lastmod></sitemap>\n</sitemapindex>\n")
    with open(os.path.join(OUT, "sitemap.xml"), "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n')
        for u in urls:
            imgs = "".join(f"<image:image><image:loc>{BASE}{src}</image:loc></image:image>" for src, *_ in PHOTOS + TRIP_PHOTOS) if u == "portfolio/" else ""
            post = next((p for p in POSTS if p["slug"] + "/" == u), None)
            if post and post["image"]:
                imgs += "".join(f"<image:image><image:loc>{BASE}/{s}</image:loc></image:image>" for s in [post["image"]] + re.findall(r'src="/(wp-content/[^"]+)"', post["html"]))
            mod = UPDATED
            f.write(f"  <url><loc>{BASE}/{u}</loc><lastmod>{mod}</lastmod>{imgs}</url>\n")
        f.write("</urlset>\n")
    with open(os.path.join(OUT, "robots.txt"), "w") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n" if LIVE else "User-agent: *\nDisallow: /\n")
    if LIVE:
        with open(os.path.join(OUT, "CNAME"), "w") as f:
            f.write("theodorewalrond.com\n")
        # Google Search Console ownership file (keep it, or the property loses verification).
        with open(os.path.join(OUT, "google489e379d499b3d8e.html"), "w") as f:
            f.write("google-site-verification: google489e379d499b3d8e.html")
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    print("built", "LIVE" if LIVE else "PREVIEW", "->", OUT, f"({len(POSTS)} posts, {len(REDIRECTS)} redirects)")


if __name__ == "__main__":
    build()
