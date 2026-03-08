# Quick Start Guide

Get your podcast conversation graphs online in 5 minutes.

## 🚀 Deploy to Cloudflare Pages (Recommended)

### Prerequisites
- GitHub account
- Cloudflare account (free)
- Domain in Cloudflare (optional, for custom domain)

### Step 1: Push to GitHub

```bash
cd /Volumes/juan_mac_mini_ssd/podcast-graphs-web

# create github repo (using gh cli)
gh repo create podcast-graphs-web --public --source=. --remote=origin
git push -u origin main

# or without gh cli:
# 1. go to https://github.com/new
# 2. create 'podcast-graphs-web' repo
# 3. run: git remote add origin https://github.com/YOUR_USERNAME/podcast-graphs-web.git
# 4. run: git push -u origin main
```

### Step 2: Connect to Cloudflare

1. Go to https://dash.cloudflare.com/
2. Click **Pages** → **Create a project**
3. Select **Connect to Git**
4. Authorize GitHub and select `podcast-graphs-web`
5. Settings:
   - Build command: (leave empty)
   - Build output: `/`
6. Click **Save and Deploy**

**Done!** Your site is live at `https://podcast-graphs-web.pages.dev`

### Step 3: Add Custom Domain (Optional)

1. In Cloudflare Pages, go to your project
2. Click **Custom domains** → **Set up a custom domain**
3. Enter: `graphs.yourdomain.com`
4. Cloudflare auto-configures DNS

**Live in 2-3 minutes** at your custom domain with HTTPS!

## 🧪 Test Locally First

```bash
cd /Volumes/juan_mac_mini_ssd/podcast-graphs-web

# using python
python -m http.server 8000

# or using node
npx serve .
```

Open http://localhost:8000

## 📊 Project Stats

- **218 files** ready to deploy
- **5.9 MB** total size
- **69 interactive graphs**
- **Search & filter** functionality included
- **$0 hosting cost** on Cloudflare

## 🔄 Update Process

When you generate new graphs:

```bash
# option 1: use the sync script
./sync-graphs.sh

# option 2: manual sync
cp /Volumes/juan_mac_mini_ssd/podcast-conversations/outputs/graphs/new_episode.html \
   graphs/podcast_name/

# update app.js with new episode
# then commit and push
git add .
git commit -m "add new episode"
git push  # auto-deploys to cloudflare
```

## 📖 Full Documentation

- **README.md** - Project overview
- **DEPLOYMENT.md** - Complete deployment guide
- **sync-graphs.sh** - Automation script

## 🆘 Need Help?

- Interactive graphs not working? Check that `lib/` folder is included
- 404 on episodes? Verify paths in `app.js` match actual files
- Domain issues? Wait 5-10 minutes for DNS propagation

## ✨ Features

- ✅ Interactive vis-network graphs
- ✅ Episode search
- ✅ Filter by type (summaries, normalized)
- ✅ Responsive design
- ✅ Auto-deploy on git push
- ✅ Free HTTPS
- ✅ Global CDN

That's it! Your podcast graphs are now online.
