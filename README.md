# Podcast Conversation Graphs - Static Site

This directory contains the deployable static website for podcast conversation graph visualizations.

## Structure

```
site/
├── index.html                  # landing page with episode browser
├── graphs/                     # interactive graph visualizations
│   ├── a_bit_fruity_with_matt_bernstein/  # 68 episode graphs
│   └── summaries/              # summary graphs
├── lib/                        # JavaScript dependencies
│   ├── bindings/utils.js      # required for interactivity
│   ├── tom-select/
│   └── vis-9.1.2/
└── README.md                   # this file
```

## Local Testing

To test locally, run a simple HTTP server:

```bash
# python 3
python -m http.server 8000

# or with node.js
npx serve .

# then visit http://localhost:8000
```

## Deployment

See [DEPLOYMENT.md](../DEPLOYMENT.md) in the project root for full deployment instructions.

**Quick deploy to Cloudflare Pages:**

```bash
# option 1: via git
git init
git add .
git commit -m "initial site"
git remote add origin <your-github-repo>
git push -u origin main
# then connect to cloudflare pages via dashboard

# option 2: direct deploy
npx wrangler pages deploy . --project-name=podcast-graphs
```

## Updating

When new graphs are generated, rebuild the site:

```bash
cd ..
uv run python scripts/build_site.py
cd site/
git add .
git commit -m "update graphs"
git push  # or npx wrangler pages deploy .
```

## Site Features

- **Interactive graphs**: vis-network powered visualizations
- **Search**: filter episodes by title
- **Responsive**: works on desktop and mobile
- **Fast**: served from Cloudflare CDN
- **Free hosting**: no cost on Cloudflare Pages

## Graph Files

Each podcast episode has three file formats:
- `.html` - interactive visualization (what's displayed on the site)
- `.csv` - tabular data export
- `.json` - raw structured data

Currently only HTML files are linked from the index page.
