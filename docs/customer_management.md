# Customer Management Guide

This guide explains how to manage customer access to the Cerebrum repository, including adding new customers, managing their access, and handling repository synchronization.

## For Repository Owners

### Initial Setup

1. **Configure Repository Secrets**:
   - Go to your repository Settings > Secrets and variables > Actions
   - Add a new repository secret named `ADMIN_TOKEN`
   - Generate a GitHub Personal Access Token with these permissions:
     - `repo` (Full control of private repositories)
     - `admin:org` (Full control of orgs and teams)
     - `delete_repo` (Delete repositories)
   - Save this token as the `ADMIN_TOKEN` secret

### Managing Customers

#### Adding a New Customer

1. Go to the "Actions" tab in your repository
2. Click on "Manage Customer Access" workflow
3. Click "Run workflow"
4. Fill in the details:
   - Action: `add`
   - Username: Customer's GitHub username
   - Email: Customer's email address
   - Plan: Select plan level (basic/premium/enterprise)
5. Click "Run workflow"

The workflow will:
- Add the customer as a repository collaborator
- Record their information in the customer database
- Grant them pull access to the repository

#### Removing a Customer

1. Go to the "Actions" tab in your repository
2. Click on "Manage Customer Access" workflow
3. Click "Run workflow"
4. Fill in the details:
   - Action: `remove`
   - Username: Customer's GitHub username
5. Click "Run workflow"

The workflow will:
- Remove their repository collaborator access
- Mark them as inactive in the customer database
- Record the removal date

#### Listing Customers

1. Go to the "Actions" tab in your repository
2. Click on "Manage Customer Access" workflow
3. Click "Run workflow"
4. Select:
   - Action: `list`
5. Click "Run workflow"

This will show:
- All active customers with their plans and add dates
- All inactive (removed) customers with their removal dates

### Monitoring Customer Activity

- Check the Actions tab for sync workflow runs
- Review pull requests created by the sync workflow
- Monitor customer forks through GitHub's fork list

## For Customers

### Initial Setup

1. **Fork the Repository**:
   - Visit the Cerebrum repository
   - Click the "Fork" button
   - Wait for the fork to complete

2. **Configure Fork Access**:
   - Go to your forked repository's Settings > Secrets and variables > Actions
   - Add a new repository secret named `SYNC_TOKEN`
   - Generate a GitHub Personal Access Token with these permissions:
     - `repo` (Full control of private repositories)
   - Save this token as the `SYNC_TOKEN` secret

### Syncing with Base Repository

#### Automatic Daily Sync

Your fork will automatically sync with the base repository every day at midnight. When changes are detected:
1. A pull request will be created in your fork
2. Review the changes in the pull request
3. Merge if the changes look good
4. Test your application after merging

#### Manual Sync

To manually sync with the base repository:
1. Go to the "Actions" tab in your fork
2. Click on "Sync with Base Repository" workflow
3. Click "Run workflow"
4. Click "Run workflow" again to confirm

If there are changes to sync:
- A pull request will be created automatically
- Review and merge the changes
- Test your application after merging

### Handling Conflicts

If the sync process encounters conflicts:
1. A special pull request titled "Manual Sync Required" will be created
2. The PR description will contain instructions
3. Resolve conflicts manually:
   ```bash
   git checkout -b sync-resolution
   git fetch base
   git merge base/main
   # Resolve conflicts in your editor
   git add .
   git commit -m "chore: resolve sync conflicts"
   git push origin sync-resolution
   ```
4. Create a pull request from your `sync-resolution` branch

### Best Practices

1. **Keep Clean History**:
   - Don't modify files that don't need customization
   - Document your customizations
   - Keep a separate branch for custom changes

2. **Regular Testing**:
   - Test your application after each sync
   - Maintain a test suite for your customizations
   - Report any issues with base repository changes

3. **Customization Management**:
   - Create a `custom/` directory for your modifications
   - Document all customizations in `CUSTOMIZATIONS.md`
   - Use feature flags for major changes

## Troubleshooting

### Common Issues

1. **Sync Failure**:
   - Verify your `SYNC_TOKEN` is valid
   - Check if you have active subscription
   - Ensure no local changes block the sync

2. **Access Denied**:
   - Confirm your subscription is active
   - Verify your GitHub username is correct
   - Contact repository owners if needed

3. **Conflict Resolution**:
   - Back up your changes before resolving
   - Create a separate branch for resolution
   - Test thoroughly after resolving

### Getting Help

- Open an issue in the base repository
- Contact support with your customer ID
- Include error messages and workflow run links

## Security Notes

1. **Token Security**:
   - Never share your access tokens
   - Rotate tokens periodically
   - Use tokens with minimal required permissions

2. **Access Control**:
   - Don't add other collaborators to your fork
   - Keep your fork private
   - Don't expose sensitive customizations

3. **Data Protection**:
   - Don't commit sensitive data
   - Use environment variables for secrets
   - Regular security audits of your fork 