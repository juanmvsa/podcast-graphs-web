# Deployment Guide: Cloudflare Pages

This guide covers deploying your podcast conversation graphs to Cloudflare Pages with a custom domain.

## Prerequisites

- Cloudflare account (free tier works fine)
- Your domain configured in Cloudflare DNS
- Git installed
- GitHub account

## Quick Start: GitHub Integration

This is the recommended approach for automatic deployments on every commit.

### Step 1: Create GitHub Repository

```bash
cd /Volumes/juan_mac_mini_ssd/podcast-graphs-web

# initialize git
git init

# stage all files
git add .

# create initial commit
git commit -m "initial commit: podcast conversation graphs"

# create github repo (using gh cli)
gh repo create podcast-graphs-web --public --source=. --remote=origin

# push to github
git push -u origin main
```

Or create the repository manually:
1. Go to https://github.com/new
2. Name: `podcast-graphs-web`
3. Visibility: **Public**
4. Don't initialize with README
5. Create repository
6. Follow GitHub's instructions to push existing repository

### Step 2: Connect to Cloudflare Pages

1. **Login to Cloudflare**:
   - Go to https://dash.cloudflare.com/
   - Navigate to **Pages** in the left sidebar

2. **Create Project**:
   - Click **Create a project**
   - Select **Connect to Git**

3. **Authorize GitHub**:
   - Click **Connect GitHub**
   - Authorize Cloudflare Pages
   - Select your repository: `podcast-graphs-web`

4. **Configure Build Settings**:
   - **Project name**: `podcast-graphs-web` (or your preference)
   - **Production branch**: `main`
   - **Build command**: Leave empty (static site)
   - **Build output directory**: `/` (root directory)
   - **Root directory**: Leave empty
   - **Environment variables**: None needed

5. **Deploy**:
   - Click **Save and Deploy**
   - Wait 2-3 minutes for initial deployment
   - You'll get a URL like: `https://podcast-graphs-web.pages.dev`

### Step 3: Add Custom Domain

1. **In Cloudflare Pages Dashboard**:
   - Go to your project: `podcast-graphs-web`
   - Click **Custom domains** tab
   - Click **Set up a custom domain**

2. **Configure Domain**:
   - Enter your domain: `graphs.yourdomain.com` (or `www.yourdomain.com`)
   - Cloudflare will automatically create DNS records
   - SSL certificate is provisioned automatically

3. **Wait for DNS Propagation**:
   - Usually takes 1-5 minutes
   - Your site will be live at your custom domain with HTTPS

## Alternative: Direct Deploy with Wrangler

For one-off deployments or if you prefer CLI:

### Step 1: Install Wrangler

```bash
npm install -g wrangler
```

### Step 2: Authenticate

```bash
wrangler login
```

This opens a browser window for Cloudflare authentication.

### Step 3: Deploy

```bash
cd /Volumes/juan_mac_mini_ssd/podcast-graphs-web
npx wrangler pages deploy . --project-name=podcast-graphs
```

First deployment creates the project. Subsequent runs update it.

### Step 4: Configure Custom Domain

Via Wrangler:
```bash
npx wrangler pages domain add podcast-graphs graphs.yourdomain.com
```

Or use the Cloudflare dashboard as described above.

## Updating Your Site

### With GitHub Integration (Automatic)

Simply commit and push changes:

```bash
git add .
git commit -m "update: add new episodes"
git push
```

Cloudflare automatically rebuilds and deploys within 2-3 minutes.

### With Wrangler (Manual)

```bash
npx wrangler pages deploy .
```

## Adding New Episodes

1. **Generate graphs** in your analysis project:
   ```bash
   cd /Volumes/juan_mac_mini_ssd/podcast-conversations
   # run your analysis scripts
   ```

2. **Copy new graphs** to web project:
   ```bash
   cp outputs/graphs/podcast_name/new_episode_graph.html \
      /Volumes/juan_mac_mini_ssd/podcast-graphs-web/graphs/podcast_name/
   ```

3. **Update app.js**:
   ```javascript
   // add to episodes array in app.js
   {
       title: "New Episode Title",
       url: "graphs/podcast_name/new_episode_graph.html",
       type: "episode",
       podcast: "fruity"
   }
   ```

4. **Deploy**:
   ```bash
   cd /Volumes/juan_mac_mini_ssd/podcast-graphs-web
   git add .
   git commit -m "add: new episode visualization"
   git push  # automatic deployment
   ```

## Automation Script

Create a script to sync new graphs automatically:

```bash
#!/bin/bash
# sync-graphs.sh

SOURCE="/Volumes/juan_mac_mini_ssd/podcast-conversations/outputs/graphs"
DEST="/Volumes/juan_mac_mini_ssd/podcast-graphs-web/graphs"

# sync graphs
rsync -av --delete "$SOURCE/" "$DEST/"

echo "Graphs synced successfully!"
```

Then:
```bash
chmod +x sync-graphs.sh
./sync-graphs.sh

# commit and push
cd /Volumes/juan_mac_mini_ssd/podcast-graphs-web
git add graphs/
git commit -m "sync: update graphs"
git push
```

## Environment Configuration

### Production

- **URL**: Your custom domain (e.g., `https://graphs.yourdomain.com`)
- **Branch**: `main`
- **Auto-deploy**: Enabled on push

### Preview Deployments

Cloudflare automatically creates preview deployments for:
- Pull requests
- Non-production branches

Each gets a unique URL like: `https://<branch>.podcast-graphs-web.pages.dev`

## Performance Optimization

### Current Performance

- **Total size**: 5.5 MB
- **Graphs**: 69 HTML files
- **Load time**: < 2s on fast connections
- **CDN**: Global Cloudflare network

### Optimization Tips

1. **Exclude unused files**:
   ```bash
   # only deploy HTML, not CSV/JSON
   rm graphs/**/*.csv graphs/**/*.json
   ```

2. **Enable caching**:
   - Cloudflare Pages automatically caches static assets
   - HTML: 4 hours
   - JS/CSS: 1 year (with versioning)

3. **Image optimization**:
   - If you add images, use WebP format
   - Cloudflare automatically optimizes images

## Monitoring

### Analytics

Enable Cloudflare Web Analytics (free):
1. Go to your Pages project
2. Click **Analytics** tab
3. Enable **Web Analytics**
4. Add tracking code to `index.html` (optional)

### Build Logs

View deployment logs:
1. Go to your Pages project
2. Click **Deployments** tab
3. Click any deployment to see logs

## Troubleshooting

### Issue: Graphs not loading

**Problem**: HTML files load but graphs don't render.

**Solution**: Ensure `lib/` directory is present with:
- `lib/bindings/utils.js`
- `lib/vis-9.1.2/vis-network.min.js`
- `lib/vis-9.1.2/vis-network.css`

### Issue: 404 on episode links

**Problem**: Clicking episodes returns 404.

**Solution**: Check file paths in `app.js` match actual file locations.

### Issue: Deployment fails

**Problem**: Build fails or times out.

**Solution**:
- Ensure repository size < 25 MB
- Check build logs for errors
- Verify no `.gitignore` is excluding necessary files

### Issue: Custom domain not working

**Problem**: Domain shows "Not found" error.

**Solution**:
1. Verify DNS records in Cloudflare
2. Wait for DNS propagation (up to 24 hours)
3. Check SSL certificate status
4. Try accessing via `https://` not `http://`

## Security

- **HTTPS**: Automatic SSL/TLS encryption
- **DDoS Protection**: Cloudflare's network
- **No secrets**: Static site, no backend
- **Public data**: Visualizations are meant to be shared

## Cost

**Cloudflare Pages Free Tier**:
- 500 builds per month
- Unlimited requests
- Unlimited bandwidth
- 100 GB-seconds compute
- 1 concurrent build

Your site stays within free tier limits comfortably.

## Backup

Your site is backed up in three places:
1. **Local**: `/Volumes/juan_mac_mini_ssd/podcast-graphs-web/`
2. **GitHub**: Remote repository
3. **Cloudflare**: Deployment history (last 100 deployments)

## Next Steps

1. ✅ Deploy site
2. ✅ Configure custom domain
3. Add analytics (optional)
4. Set up automated graph syncing
5. Add more podcast series as data becomes available

## Resources

- [Cloudflare Pages Docs](https://developers.cloudflare.com/pages/)
- [Wrangler CLI Docs](https://developers.cloudflare.com/workers/wrangler/)
- [vis-network Docs](https://visjs.github.io/vis-network/docs/network/)
