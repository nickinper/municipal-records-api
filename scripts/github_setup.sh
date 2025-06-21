#!/bin/bash

echo "🚀 GitHub Setup for Municipal Records API"
echo "========================================"
echo ""
echo "This script will help you push the project to GitHub."
echo ""

# Check if git remote exists
if git remote | grep -q origin; then
    echo "⚠️  Git remote 'origin' already exists"
    echo "Current remote: $(git remote get-url origin)"
    read -p "Do you want to update it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your GitHub repository URL (e.g., https://github.com/username/repo.git): " REPO_URL
        git remote set-url origin "$REPO_URL"
    fi
else
    echo "📝 Please create a new repository on GitHub first:"
    echo "   1. Go to https://github.com/new"
    echo "   2. Name it: municipal-records-api"
    echo "   3. Make it PRIVATE (contains business logic)"
    echo "   4. Don't initialize with README"
    echo ""
    read -p "Enter your GitHub repository URL (e.g., https://github.com/username/repo.git): " REPO_URL
    git remote add origin "$REPO_URL"
fi

echo ""
echo "📤 Pushing to GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Successfully pushed to GitHub!"
    echo ""
    echo "🔒 Important Security Steps:"
    echo "   1. Ensure your repository is PRIVATE"
    echo "   2. Add collaborators carefully"
    echo "   3. Never commit real .env files"
    echo "   4. Consider using GitHub Secrets for deployment"
    echo ""
    echo "📊 Next Steps:"
    echo "   1. Set up GitHub Actions for CI/CD"
    echo "   2. Configure branch protection rules"
    echo "   3. Add issue templates for bug tracking"
    echo "   4. Create a project board for feature tracking"
    echo ""
    echo "🚀 Ready to deploy? Check out:"
    echo "   - Railway: https://railway.app"
    echo "   - Render: https://render.com"
    echo "   - DigitalOcean App Platform"
else
    echo ""
    echo "❌ Failed to push to GitHub"
    echo ""
    echo "Common issues:"
    echo "1. Authentication: You may need to use a Personal Access Token"
    echo "   - Go to GitHub Settings > Developer settings > Personal access tokens"
    echo "   - Generate a token with 'repo' scope"
    echo "   - Use the token as your password"
    echo ""
    echo "2. Repository doesn't exist: Create it on GitHub first"
    echo ""
    echo "3. Permission denied: Check your GitHub credentials"
fi

echo ""
echo "💡 Pro tip: Set up GitHub Actions for automated testing and deployment!"
echo ""