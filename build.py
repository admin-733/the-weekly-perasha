#!/usr/bin/env python3
"""
Build script for The Weekly Perasha.
Reads markdown files from content/, generates a complete static site in _site/.
"""

import os
import shutil
import re
from datetime import datetime
import markdown

# ─── Configuration ───────────────────────────────────────────────

SITE_NAME = "The Weekly Perasha"
SITE_TAGLINE = "Practical life lessons from the Torah"
SITE_URL = "https://theweeklyperasha.com"
AUTHOR = "Moshe Shasho"

# AdSense: replace with your publisher ID after approval
ADSENSE_ID = ""  # e.g., "ca-pub-1234567890"

# Formspree: replace with your form ID after signup
FORMSPREE_ID = ""  # e.g., "xyzabcde"

# Parshiyot in order, grouped by book
PARSHIYOT_BY_BOOK = {
    "Beresheet (Genesis)": [
        "Beresheet", "Noah", "Lech Lecha", "Vayera", "Haye Sarah",
        "Toldot", "Vayese", "Vayishlah", "Vayesheb", "Miqess",
        "Vayigash", "Vayehi"
    ],
    "Shemot (Exodus)": [
        "Shemot", "Vaera", "Bo", "Beshalah", "Yitro", "Mishpatim",
        "Terumah", "Tesave", "Ki Tisa", "Vayaqhel", "Pequde"
    ],
    "Vayiqra (Leviticus)": [
        "Vayiqra", "Sav", "Shemini", "Tazria", "Mesora",
        "Aharei Mot", "Qedoshim", "Aharei-Qedoshim", "Emor", "Behar", "Behuqotai",
        "Behar-Behuqotai"
    ],
    "Bemidbar (Numbers)": [
        "Bemidbar", "Naso", "Behaalotecha", "Shelah", "Qorah",
        "Huqat", "Balaq", "Huqat-Balaq", "Pinhas", "Matot", "Masei",
        "Matot-Masei"
    ],
    "Debarim (Deuteronomy)": [
        "Debarim", "Va'ethanan", "Eqeb", "Re'eh", "Shofetim",
        "Ki Tese", "Ki Tabo", "Nisabim", "Vayelech", "Ha'azinu",
        "Vezot Haberachah"
    ],
}

# Flat lookup: parsha name → book name
PARSHA_TO_BOOK = {}
PARSHA_ORDER = {}
order = 0
for book, parshiyot in PARSHIYOT_BY_BOOK.items():
    for p in parshiyot:
        PARSHA_TO_BOOK[p.lower()] = book
        PARSHA_ORDER[p.lower()] = order
        order += 1


# ─── Frontmatter & Markdown Parsing ─────────────────────────────

def parse_frontmatter(text):
    """Parse YAML-like frontmatter from markdown file."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = {}
    for line in parts[1].strip().split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, parts[2].strip()


def slugify(text):
    """Convert text to URL-friendly slug."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def read_articles(content_dir):
    """Read all markdown files and return sorted article list."""
    articles = []
    md = markdown.Markdown(extensions=["smarty"])

    for filename in os.listdir(content_dir):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(content_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        meta, body = parse_frontmatter(text)
        if not meta.get("title") or not meta.get("parsha"):
            print(f"  Skipping {filename}: missing title or parsha")
            continue

        md.reset()
        html_body = md.convert(body)

        # Build slug from filename (without .md)
        slug = filename[:-3]

        year = int(meta.get("year", datetime.now().year))
        date_str = meta.get("date", f"{year}-01-01")
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            date = datetime(year, 1, 1)

        articles.append({
            "title": meta["title"],
            "parsha": meta["parsha"],
            "author": meta.get("author", AUTHOR),
            "book": PARSHA_TO_BOOK.get(meta["parsha"].lower(), ""),
            "year": year,
            "date": date,
            "date_display": date.strftime("%B %d, %Y"),
            "summary": meta.get("summary", ""),
            "slug": slug,
            "url": f"/{slug}/",
            "html": html_body,
            "parsha_order": PARSHA_ORDER.get(meta["parsha"].lower(), 999),
        })

    # Sort newest first
    articles.sort(key=lambda a: a["date"], reverse=True)
    return articles


# ─── HTML Templates ──────────────────────────────────────────────

def head(title, description="", canonical=""):
    adsense_tag = f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_ID}" crossorigin="anonymous"></script>' if ADSENSE_ID else ""
    canonical_tag = f'<link rel="canonical" href="{SITE_URL}{canonical}">' if canonical else ""
    desc = description or SITE_TAGLINE
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | {SITE_NAME}</title>
    <meta name="description" content="{desc}">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{desc}">
    <meta property="og:type" content="article">
    <meta property="og:site_name" content="{SITE_NAME}">
    {canonical_tag}
    <link rel="alternate" type="application/rss+xml" title="{SITE_NAME}" href="{SITE_URL}/feed.xml">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700;1,400&family=Lora:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="/style.css">
    {adsense_tag}
</head>"""


def nav(active=""):
    def cls(name):
        return ' class="active"' if active == name else ""
    return f"""<nav>
    <div class="nav-inner">
        <div class="nav-left">
            <a href="/" class="site-name">{SITE_NAME}</a>
            <span id="heb-info" class="heb-info" style="display:none;">
                <span class="heb-sep">&#xB7;</span>
                <span id="heb-date"></span>
                <span class="heb-sep">&#xB7;</span>
                <span id="heb-parsha"></span>
            </span>
        </div>
        <div class="nav-links">
            <a href="/"{cls("home")}>Home</a>
            <a href="/archive/"{cls("archive")}>Archive</a>
            <a href="/about/"{cls("about")}>About</a>
            <a href="/feedback/"{cls("feedback")}>Feedback</a>
        </div>
        <button class="nav-toggle" aria-label="Menu" onclick="document.querySelector('.nav-links').classList.toggle('open')">&#9776;</button>
    </div>
</nav>"""


def footer():
    year = datetime.now().year
    return f"""<footer>
    <div class="footer-inner">
        <p>&copy; {year} {SITE_NAME}. All rights reserved.</p>
        <p class="footer-tagline">{SITE_TAGLINE}</p>
    </div>
</footer>
<script>
(function() {{
  var info = document.getElementById('heb-info');
  var dateEl = document.getElementById('heb-date');
  var parshaEl = document.getElementById('heb-parsha');
  if (!info) return;

  var now = new Date();
  var gy = now.getFullYear();
  var gm = now.getMonth() + 1;
  var gd = now.getDate();

  // Fetch Hebrew date
  fetch('https://www.hebcal.com/converter?cfg=json&g2h=1&gy=' + gy + '&gm=' + gm + '&gd=' + gd)
    .then(function(r) {{ return r.json(); }})
    .then(function(d) {{
      if (d.hebrew) {{
        dateEl.textContent = d.hebrew;
        info.style.display = '';
      }}
    }})
    .catch(function() {{}});

  // Sephardic transliteration map
  var seph = {{
    "Bereshit":"Beresheet","Noach":"Noah","Lech-Lecha":"Lech Lecha",
    "Chayei Sara":"Haye Sarah","Vayetzei":"Vayese","Vayishlach":"Vayishlah",
    "Vayeshev":"Vayesheb","Miketz":"Miqess","Vayechi":"Vayehi",
    "Sh'mot":"Shemot","Shemot":"Shemot","Va'eira":"Vaera","Va'era":"Vaera",
    "B'shalach":"Beshalah","Beshalach":"Beshalah",
    "Mishpatim":"Mishpatim","T'rumah":"Terumah",
    "Tetzaveh":"Tesave","T'tzaveh":"Tesave",
    "Vayak'hel":"Vayaqhel","Vayakhel":"Vayaqhel",
    "P'kudei":"Pequde","Pekudei":"Pequde",
    "Tzav":"Sav","Sh'mini":"Shemini","Shemini":"Shemini",
    "Tazria":"Tazria","Metzora":"Mesora","M'tzora":"Mesora",
    "Achrei Mot":"Aharei Mot","Acharei Mot":"Aharei Mot",
    "Kedoshim":"Qedoshim","K'doshim":"Qedoshim",
    "B'har":"Behar","Behar":"Behar",
    "Bechukotai":"Behuqotai","B'chukotai":"Behuqotai",
    "B'midbar":"Bemidbar","Bamidbar":"Bemidbar",
    "Nasso":"Naso","Beha'alotcha":"Behaalotecha","B'ha'alot'cha":"Behaalotecha",
    "Sh'lach":"Shelah","Shelach":"Shelah",
    "Korach":"Qorah","Chukat":"Huqat",
    "Balak":"Balaq","Pinchas":"Pinhas",
    "D'varim":"Debarim","Devarim":"Debarim",
    "Va'etchanan":"Va'ethanan","Vaetchanan":"Va'ethanan",
    "Eikev":"Eqeb","Ekev":"Eqeb",
    "Shoftim":"Shofetim",
    "Ki Teitzei":"Ki Tese","Ki Tetze":"Ki Tese",
    "Ki Tavo":"Ki Tabo",
    "Nitzavim":"Nisabim",
    "Vayeilech":"Vayelech","Ha'azinu":"Ha'azinu",
    "V'Zot HaB'rachah":"Vezot Haberachah","Vezot Haberachah":"Vezot Haberachah"
  }};

  // Fetch parsha + holidays (NYC geo)
  fetch('https://www.hebcal.com/shabbat?cfg=json&geonameid=5128581&M=on&b=18')
    .then(function(r) {{ return r.json(); }})
    .then(function(d) {{
      var parts = [];
      if (d.items) {{
        for (var i = 0; i < d.items.length; i++) {{
          var item = d.items[i];
          if (item.category === 'parashat') {{
            var name = item.title.replace('Parashat ', '');
            // Handle double parshiyot
            var segs = name.split('-');
            var mapped = [];
            for (var j = 0; j < segs.length; j++) {{
              var s = segs[j].trim();
              mapped.push(seph[s] || s);
            }}
            parts.push('Perashat ' + mapped.join('-'));
          }}
          if (item.category === 'holiday') {{
            parts.push(item.title);
          }}
        }}
      }}
      if (parts.length > 0) {{
        parshaEl.textContent = parts.join(' \\xB7 ');
        info.style.display = '';
      }}
    }})
    .catch(function() {{}});
}})();
</script>
</body>
</html>"""


def ad_slot(slot_type="in-article"):
    """Generate ad placeholder. Only renders if ADSENSE_ID is set."""
    if not ADSENSE_ID:
        return ""
    return f"""<div class="ad-container">
    <ins class="adsbygoogle"
         style="display:block; text-align:center;"
         data-ad-layout="in-article"
         data-ad-format="fluid"
         data-ad-client="{ADSENSE_ID}"
         data-ad-slot=""></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
</div>"""


# ─── Page Generators ─────────────────────────────────────────────

def build_article_page(article):
    prev_next = ""  # Could add prev/next navigation here
    return f"""{head(f"Perashat {article['parsha']}: {article['title']}", article['summary'], article['url'])}
<body>
{nav()}
<main>
    <article class="article-page">
        <header class="article-header">
            <span class="article-parsha">Perashat {article['parsha']}</span>
            <h1>{article['title']}</h1>
            <div class="article-meta">
                <span class="article-author">By {article['author']}</span>
                <time datetime="{article['date'].strftime('%Y-%m-%d')}">{article['date_display']}</time>
            </div>
        </header>
        <div class="article-body">
            {article['html']}
        </div>
        {ad_slot()}
        <div class="article-footer">
            <a href="/archive/">&#8592; Browse all Divrei Torah</a>
        </div>
    </article>
</main>
{footer()}"""


def build_home_page(articles):
    # This week's article — rendered in full right on the homepage
    this_week = ""
    if articles:
        a = articles[0]
        this_week = f"""<section class="this-week">
        <div class="this-week-label">This Week's Perasha</div>
        <article class="home-article">
            <header class="home-article-header">
                <span class="home-parsha-name">Perashat {a['parsha']}</span>
                <h2><a href="{a['url']}">{a['title']}</a></h2>
                <div class="article-meta">
                    <span class="article-author">By {a['author']}</span>
                    <time datetime="{a['date'].strftime('%Y-%m-%d')}">{a['date_display']}</time>
                </div>
            </header>
            <div class="home-article-body">
                {a['html']}
            </div>
            <div class="home-article-share">
                <a href="{a['url']}">Permalink</a>
            </div>
        </article>
    </section>"""

    # Previous divrei torah — compact list
    prev_items = ""
    for a in articles[1:8]:
        prev_items += f"""<li>
            <a href="{a['url']}">
                <span class="prev-parsha">Perashat {a['parsha']}</span>
                <span class="prev-title">{a['title']}</span>
                <time>{a['date_display']}</time>
            </a>
        </li>\n"""

    previous = ""
    if prev_items:
        previous = f"""<section class="previous">
        <h3>Previous Divrei Torah</h3>
        <ul>{prev_items}</ul>
        <a href="/archive/" class="browse-link">Browse the full archive &#8594;</a>
    </section>"""

    return f"""{head("Home", SITE_TAGLINE, "/")}
<body>
{nav("home")}
<main class="home">
    <header class="home-header">
        <h1>{SITE_NAME}</h1>
        <p>{SITE_TAGLINE}</p>
    </header>
    {this_week}
    {ad_slot()}
    {previous}
</main>
{footer()}"""


def build_archive_page(articles):
    # Group by book → parsha
    by_parsha = {}
    for a in articles:
        key = a["parsha"]
        if key not in by_parsha:
            by_parsha[key] = []
        by_parsha[key].append(a)

    # Group by year
    by_year = {}
    for a in articles:
        if a["year"] not in by_year:
            by_year[a["year"]] = []
        by_year[a["year"]].append(a)

    # Build parsha section (organized by book)
    parsha_html = ""
    for book, parshiyot in PARSHIYOT_BY_BOOK.items():
        entries = ""
        for p in parshiyot:
            if p in by_parsha:
                links = ", ".join(
                    f'<a href="{a["url"]}">{a["year"]}</a>'
                    for a in sorted(by_parsha[p], key=lambda x: x["year"])
                )
                entries += f'<li><span class="parsha-name">{p}</span> {links}</li>\n'
        if entries:
            parsha_html += f"""<div class="archive-book">
                <h3>{book}</h3>
                <ul>{entries}</ul>
            </div>\n"""

    # Build year section
    year_html = ""
    for year in sorted(by_year.keys(), reverse=True):
        items = ""
        for a in sorted(by_year[year], key=lambda x: x["parsha_order"]):
            items += f'<li><a href="{a["url"]}"><strong>Perashat {a["parsha"]}</strong>: {a["title"]}</a> <time>{a["date_display"]}</time></li>\n'
        year_html += f"""<div class="archive-year">
            <h3>{year}</h3>
            <ul>{items}</ul>
        </div>\n"""

    return f"""{head("Archive", "Browse all Divrei Torah by parsha or year", "/archive/")}
<body>
{nav("archive")}
<main>
    <div class="page-content">
        <h1>Archive</h1>
        <p class="page-subtitle">Browse all Divrei Torah by parsha or by year.</p>

        <div class="archive-tabs">
            <button class="tab active" onclick="showTab('parsha')">By Parsha</button>
            <button class="tab" onclick="showTab('year')">By Year</button>
        </div>

        <div id="tab-parsha" class="tab-content active">
            {parsha_html}
        </div>

        <div id="tab-year" class="tab-content">
            {year_html}
        </div>
    </div>
</main>
<script>
function showTab(name) {{
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
    document.getElementById('tab-' + name).classList.add('active');
    event.target.classList.add('active');
}}
</script>
{footer()}"""


def build_about_page():
    return f"""{head("About", f"About {AUTHOR} and {SITE_NAME}", "/about/")}
<body>
{nav("about")}
<main>
    <div class="page-content">
        <h1>About</h1>
        <div class="about-body">
            <p>
                Thanks for visiting. My name is Moshe. I've been a baal koreh for over
                30 years. Reading the Torah week after week has taught me to slow down
                with the text and catch what I'd otherwise miss. A repeated word, an
                unusual phrase, a detail that doesn't seem to fit until it does. That's
                where most of my articles start.
            </p>
            <p>
                I grew up in a Sephardic home and I write the way I learned: perasha by
                perasha, with the commentators I grew up on and the questions real life
                puts in front of you. I've been writing these articles weekly for about
                three years now. If one idea stays with you during your week, it did its job.
            </p>
            <p>
                I also run <a href="https://ms-teach.com">MS-Teach</a>, my AI consulting
                company, where I help people and businesses get practical with AI and
                Microsoft tools.
            </p>
            <p>
                Have a question or comment on an article?
                <a href="/feedback/">I'd like to hear it.</a>
            </p>
        </div>
    </div>
</main>
{footer()}"""


def build_feedback_page():
    if FORMSPREE_ID:
        form = f"""<form action="https://formspree.io/f/{FORMSPREE_ID}" method="POST" class="feedback-form">
            <label for="name">Name (optional)</label>
            <input type="text" id="name" name="name" placeholder="Your name">
            <label for="email">Email (optional)</label>
            <input type="email" id="email" name="email" placeholder="your@email.com">
            <label for="message">Your feedback</label>
            <textarea id="message" name="message" rows="6" placeholder="What did you think? Any parsha you'd like covered?" required></textarea>
            <button type="submit">Send Feedback</button>
        </form>"""
    else:
        form = """<div class="feedback-placeholder">
            <p>Feedback form coming soon. In the meantime, feel free to reach out directly.</p>
        </div>"""

    return f"""{head("Feedback", "Share your thoughts and feedback", "/feedback/")}
<body>
{nav("feedback")}
<main>
    <div class="page-content">
        <h1>Feedback</h1>
        <p class="page-subtitle">
            Enjoyed a Dvar Torah? Have a question? Want to suggest a topic?
            I'd love to hear from you.
        </p>
        {form}
    </div>
</main>
{footer()}"""


def build_rss_feed(articles):
    items = ""
    for a in articles[:20]:
        pub_date = a["date"].strftime("%a, %d %b %Y 00:00:00 +0000")
        summary = a["summary"] or a["title"]
        items += f"""    <item>
      <title>Perashat {a['parsha']}: {a['title']}</title>
      <link>{SITE_URL}{a['url']}</link>
      <guid>{SITE_URL}{a['url']}</guid>
      <pubDate>{pub_date}</pubDate>
      <description>{summary}</description>
    </item>\n"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{SITE_NAME}</title>
    <link>{SITE_URL}</link>
    <description>{SITE_TAGLINE}</description>
    <atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>
{items}  </channel>
</rss>"""


def build_sitemap(articles):
    urls = ["/", "/archive/", "/about/", "/feedback/"]
    entries = ""
    for url in urls:
        entries += f"  <url><loc>{SITE_URL}{url}</loc></url>\n"
    for a in articles:
        entries += f"  <url><loc>{SITE_URL}{a['url']}</loc><lastmod>{a['date'].strftime('%Y-%m-%d')}</lastmod></url>\n"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{entries}</urlset>"""


def build_404_page():
    return f"""{head("Page Not Found")}
<body>
{nav()}
<main>
    <div class="page-content" style="text-align:center; padding: 4rem 1rem;">
        <h1>Page Not Found</h1>
        <p>The page you're looking for doesn't exist.</p>
        <p><a href="/">Go back home</a> or <a href="/archive/">browse the archive</a>.</p>
    </div>
</main>
{footer()}"""


# ─── Build ───────────────────────────────────────────────────────

def build():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    content_dir = os.path.join(base_dir, "content")
    static_dir = os.path.join(base_dir, "static")
    output_dir = os.path.join(base_dir, "_site")

    print(f"Building {SITE_NAME}...")

    # Clean output
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    # Read articles
    articles = read_articles(content_dir)
    print(f"  Found {len(articles)} articles")

    # Generate article pages
    for a in articles:
        article_dir = os.path.join(output_dir, a["slug"])
        os.makedirs(article_dir, exist_ok=True)
        with open(os.path.join(article_dir, "index.html"), "w") as f:
            f.write(build_article_page(a))
        print(f"  Built: {a['slug']}/")

    # Generate main pages
    pages = {
        "index.html": build_home_page(articles),
        "archive/index.html": build_archive_page(articles),
        "about/index.html": build_about_page(),
        "feedback/index.html": build_feedback_page(),
        "404.html": build_404_page(),
        "feed.xml": build_rss_feed(articles),
        "sitemap.xml": build_sitemap(articles),
    }

    for path, content in pages.items():
        full_path = os.path.join(output_dir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
        print(f"  Built: {path}")

    # Copy static files
    if os.path.exists(static_dir):
        for item in os.listdir(static_dir):
            src = os.path.join(static_dir, item)
            dst = os.path.join(output_dir, item)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
            else:
                shutil.copytree(src, dst)
        print("  Copied static files")

    print(f"Done! Site built in _site/ ({len(articles)} articles)")


if __name__ == "__main__":
    build()
