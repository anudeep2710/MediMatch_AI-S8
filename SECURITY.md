# Security Policy

## 🔒 Reporting Security Vulnerabilities

If you discover a security vulnerability in MediMatch, please report it responsibly:

1. **DO NOT** open a public GitHub issue
2. **Email** the maintainers directly at: security@medimatch.example.com
3. **Provide** detailed information about the vulnerability
4. **Wait** for acknowledgment and further instructions

We take security seriously and will respond within 48 hours.

## 🛡️ Security Best Practices

### API Key Management

⚠️ **CRITICAL**: Never commit API keys to Git!

#### Setup

1. Copy `.env.example` to `.env`
2. Add your real API keys to `.env`
3. Verify `.env` is in `.gitignore`
4. Never share `.env` file publicly

#### If Keys Are Exposed

If you accidentally commit API keys:

1. **Immediately rotate** all exposed keys
2. **Revoke** the old keys from provider dashboards
3. **Remove** keys from Git history:
   ```bash
   git filter-branch --force --index-filter \
   "git rm --cached --ignore-unmatch .env" \
   --prune-empty --tag-name-filter cat -- --all
   ```
4. **Force push** to update remote:
   ```bash
   git push origin --force --all
   ```

### Dependency Management

#### Regular Updates

```bash
# Check for outdated packages
pip list --outdated

# Update all packages (test thoroughly after!)
pip install --upgrade -r requirements.txt
```

#### Known Vulnerabilities

```bash
# Check for known security issues
pip install safety
safety check
```

### API Rate Limiting

To prevent abuse:

- Implement rate limiting in production
- Use API keys with proper scopes
- Monitor API usage regularly

Example with Flask-Limiter:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)

@app.route('/api/search_drug')
@limiter.limit("30 per minute")
def search_drug():
    # Your code here
    pass
```

### Input Validation

Always validate user inputs:

- Sanitize SMILES strings
- Validate file uploads (type, size)
- Escape HTML in user-generated content
- Use parameterized queries

### HTTPS in Production

Always use HTTPS in production:

```python
# Force HTTPS redirects
@app.before_request
def before_request():
    if not request.is_secure and app.env == "production":
        url = request.url.replace("http://", "https://", 1)
        return redirect(url, code=301)
```

## 🔐 Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | ✅ Active support  |
| < 1.0   | ❌ Not supported   |

## 📋 Security Checklist for Production

- [ ] All API keys in environment variables
- [ ] `.env` file not committed to Git
- [ ] HTTPS enabled (SSL certificate)
- [ ] Rate limiting implemented
- [ ] Input validation on all endpoints
- [ ] CORS properly configured
- [ ] File upload size limits set
- [ ] Error messages don't expose sensitive info
- [ ] Dependencies regularly updated
- [ ] Security headers configured:
  ```python
  @app.after_request
  def set_security_headers(response):
      response.headers['X-Content-Type-Options'] = 'nosniff'
      response.headers['X-Frame-Options'] = 'DENY'
      response.headers['X-XSS-Protection'] = '1; mode=block'
      response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
      return response
  ```

## 🚨 Known Security Considerations

### 1. API Keys in Environment

- **Risk**: API keys in `.env` file
- **Mitigation**: Use secret management service (AWS Secrets Manager, Azure Key Vault, etc.) in production

### 2. File Uploads

- **Risk**: Malicious file uploads
- **Mitigation**:
    - Validate file types
    - Scan uploads with antivirus
    - Store in isolated directory
    - Limit file sizes

### 3. External API Calls

- **Risk**: SSRF vulnerabilities
- **Mitigation**:
    - Whitelist allowed domains
    - Set timeouts
    - Validate responses

### 4. SQL Injection (N/A)

- **Status**: No SQL database used (CSV files)
- **Future**: If adding SQL, use parameterized queries

### 5. XSS (Cross-Site Scripting)

- **Risk**: User-generated content
- **Mitigation**:
    - Flask auto-escapes templates
    - Sanitize all outputs
    - Use Content Security Policy

## 🔍 Security Audits

Last audit: Not yet conducted  
Next audit: TBD

## 📚 References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/latest/security/)
- [Python Security](https://python.readthedocs.io/en/stable/library/security_warnings.html)

## 📧 Contact

For security concerns: security@medimatch.example.com  
For general inquiries: contact@medimatch.example.com

---

**Remember**: Security is everyone's responsibility! 🛡️
