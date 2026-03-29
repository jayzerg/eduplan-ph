# docs/DEPLOYMENT.md
# Deployment Guide for EduPlan PH

This guide walks you through deploying EduPlan PH to Streamlit Cloud.

## Prerequisites

1. A GitHub account
2. An OpenRouter API key (get one free at [openrouter.ai/keys](https://openrouter.ai/keys))
3. Your code pushed to a GitHub repository

## Step 1: Push Code to GitHub

```bash
# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit: EduPlan PH v1.0.0"

# Create repository on GitHub first, then:
git remote add origin https://github.com/YOUR_USERNAME/eduplan-ph.git
git push -u origin main
```

## Step 2: Deploy to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "Sign in" and authenticate with GitHub
3. Click "New app"
4. Select your GitHub repository and branch
5. Set the main file path to `app.py`
6. Click "Advanced settings"

## Step 3: Configure Secrets

In the Advanced settings panel, add your API key:

```toml
[secrets]
OPENROUTER_API_KEY = "your_openrouter_key_here"
```

Click "Deploy" and wait 2-3 minutes for the build to complete.

## Step 4: Verify Deployment

1. Test the live URL with your browser
2. Verify API key connection in the sidebar
3. Generate a test lesson plan
4. Test export functionality

## Local Development

For local development, create a `.env` file:

```bash
OPENROUTER_API_KEY=your_openrouter_key_here
```

Then run:
```bash
streamlit run app.py
```

## Troubleshooting

### Common Issues

1. **API Key Not Found**
   - Check that secrets are configured in Streamlit Cloud
   - Verify `.env` file exists locally (not committed to git)

2. **Generation Timeout**
   - Check your internet connection
   - Try a smaller model if available

3. **Export Fails**
   - Ensure all export dependencies are in requirements.txt
   - Check that the generated content is not empty