# Deploy to Render.com

## Quick Deploy Steps

1. **Push your code to GitHub** (if not already done):
   ```bash
   git add .
   git commit -m "Add Render deployment configuration"
   git push origin main
   ```

2. **Sign up for Render**: https://render.com/

3. **Create New Web Service**:
   - Click "New +" → "Web Service"
   - Connect your GitHub account
   - Select your `municipal-records-api` repository
   - Use these settings:
     - **Name**: municipal-records-api
     - **Environment**: Python
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `python main.py`

4. **Add Environment Variables** (in Render dashboard):
   ```
   STRIPE_SECRET_KEY=sk_live_51RcKLY...
   STRIPE_WEBHOOK_SECRET=(we'll create this after deploy)
   DATABASE_URL=(Render will provide this)
   REDIS_URL=(Render will provide this)
   ```

5. **Create Database**:
   - Go to "New +" → "PostgreSQL"
   - Name: municipal-records-db
   - Select free tier

6. **Create Redis**:
   - Go to "New +" → "Redis"
   - Name: municipal-records-redis
   - Select free tier

7. **Connect Services**:
   - In your web service settings
   - Add environment variable: DATABASE_URL → Internal Database URL from PostgreSQL
   - Add environment variable: REDIS_URL → Internal Redis URL

## After Deployment

1. **Your API URL will be**: `https://municipal-records-api.onrender.com`

2. **Create Stripe Webhook**:
   ```bash
   python scripts/create_webhook.py https://municipal-records-api.onrender.com
   ```

3. **Update your GitHub Pages site**:
   - Edit `municipal-records-website/order.js`
   - Change: `const API_BASE_URL = 'https://municipal-records-api.onrender.com';`
   - Commit and push

4. **Add webhook secret to Render**:
   - Copy the webhook secret from step 2
   - Add to Render environment variables: `STRIPE_WEBHOOK_SECRET=whsec_...`

## Free Tier Limitations

- **Spin down after 15 minutes of inactivity** (first request will be slow)
- **750 hours/month** (enough for 24/7 operation)
- **512 MB RAM**
- **0.1 CPU**

## Monitoring

- Check logs: Render Dashboard → Your Service → Logs
- Health check: `https://municipal-records-api.onrender.com/api/v1/health`

## Troubleshooting

If deployment fails:
1. Check build logs in Render dashboard
2. Ensure all dependencies are in requirements.txt
3. Verify environment variables are set correctly