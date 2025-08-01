# Release Guide - VETTING Python Package

This guide explains how to publish new versions of the vetting-python package to PyPI using automated workflows.

## 🎯 Current Status

✅ **Package Published**: [vetting-python v0.1.0](https://pypi.org/project/vetting-python/0.1.0/)  
✅ **GitHub Actions Workflow**: Created  
⏳ **Trusted Publisher**: Needs to be configured (see Step 1 below)

## 📋 Setup Guide (One-time)

### Step 1: Configure Trusted Publisher on PyPI

1. **Go to PyPI**: https://pypi.org/manage/account/publishing/
2. **Add a new pending publisher** with these details:
   ```
   PyPI Project Name: vetting-python
   Owner: hichipli
   Repository name: vetting-python
   Workflow name: publish.yml
   Environment name: pypi
   ```

3. **Create Environment in GitHub**:
   - Go to: https://github.com/hichipli/vetting-python/settings/environments
   - Click "New environment"
   - Name: `pypi`
   - Add protection rules (recommended):
     - ✅ Required reviewers: Add yourself
     - ✅ Wait timer: 0 minutes
     - ✅ Deployment branches: Selected branches only → `main`

### Step 2: Verify Workflow Permissions

The workflow already has the correct permissions:
```yaml
permissions:
  id-token: write  # Required for trusted publishing
  contents: read
```

## 🚀 Release Methods

### Method 1: GitHub Releases (Recommended)

1. **Create a new release** on GitHub:
   - Go to: https://github.com/hichipli/vetting-python/releases/new
   - Tag: `v1.0.1` (example)
   - Title: `Release v1.0.1`
   - Description: Release notes
   - Click "Publish release"

2. **Automatic Publishing**: The workflow will automatically:
   - Build the package
   - Publish to PyPI
   - No manual intervention needed!

### Method 2: Manual Workflow Trigger

1. **Go to Actions**: https://github.com/hichipli/vetting-python/actions/workflows/publish.yml
2. **Click "Run workflow"**
3. **Enter version** (e.g., `1.0.1`) or leave empty for current version
4. **Click "Run workflow"**

### Method 3: Version Management Scripts

Use the provided scripts for version management:

```bash
# Show current version
make version

# Bump version automatically
make bump-patch    # 1.0.0 -> 1.0.1
make bump-minor    # 1.0.0 -> 1.1.0  
make bump-major    # 1.0.0 -> 2.0.0

# Create complete release
make release VERSION=1.0.1
```

## 📝 Version Update Process

### Automatic (Using Scripts)

```bash
# Bump patch version and create release
make bump-patch
git push && git push --tags

# Or specify exact version
make release VERSION=1.2.3
git push && git push --tags
```

### Manual Version Updates

Update these files manually:
1. `pyproject.toml` - version field
2. `vetting_python/__init__.py` - __version__ variable
3. `CHANGELOG.md` - add new entry

## 🔄 Complete Release Workflow

### For Regular Updates (Patch/Minor)

```bash
# 1. Update code and commit changes
git add .
git commit -m "Add new feature"

# 2. Bump version (this updates files and creates tag)
make bump-minor

# 3. Push everything
git push && git push --tags

# 4. GitHub Actions will automatically publish to PyPI
```

### For Major Releases

```bash
# 1. Update README, CHANGELOG, documentation
git add .
git commit -m "Prepare for major release"

# 2. Create major version bump
make bump-major

# 3. Push and create GitHub Release
git push && git push --tags

# 4. Go to GitHub and create a detailed release
```

## 🛡️ Trusted Publisher Benefits

Once configured, you get:
- ✅ **No API tokens needed** - Automatic authentication
- ✅ **Secure publishing** - Only from your GitHub repo
- ✅ **Audit trail** - Full transparency in GitHub Actions
- ✅ **Environment protection** - Only authorized releases
- ✅ **No credential management** - GitHub handles everything

## 📊 Monitoring

### Check Release Status

```bash
# Check if package was published
pip search vetting-python

# Install specific version
pip install vetting-python==1.0.1

# Check package info
pip show vetting-python
```

### GitHub Actions Logs

Monitor releases at: https://github.com/hichipli/vetting-python/actions

## 🐛 Troubleshooting

### Common Issues

1. **"No such environment: pypi"**
   - Create the environment in GitHub repository settings

2. **"Trusted publisher not configured"**
   - Add the pending publisher on PyPI as described in Step 1

3. **"Permission denied"**
   - Check workflow permissions include `id-token: write`

4. **"Version already exists"**
   - Bump version number before publishing

### Debug Commands

```bash
# Test build locally
make build

# Check built packages
python -m twine check dist/*

# Test installation from local build
pip install dist/vetting_python-*.whl
```

## 📚 Resources

- **PyPI Project**: https://pypi.org/project/vetting-python/
- **GitHub Repository**: https://github.com/hichipli/vetting-python
- **Trusted Publishers Guide**: https://docs.pypi.org/trusted-publishers/
- **GitHub Actions**: https://docs.github.com/en/actions

## 🎉 Quick Start for Next Release

```bash
# Update your code...
git add . && git commit -m "Your changes"

# Release new version  
make bump-patch && git push --follow-tags

# Done! Check GitHub Actions for automatic PyPI publishing
```

---

**Note**: After setting up the Trusted Publisher (Step 1), all future releases will be completely automated through GitHub Actions! 🚀