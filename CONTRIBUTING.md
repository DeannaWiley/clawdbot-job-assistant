# 🤝 Contributing to ClawdBot

Want to contribute? Awesome! Here's how to get started.

## 🚀 Quick Contributing Guide

### 1. Fork & Clone

```bash
git clone https://github.com/YOUR_USERNAME/clawdbot-job-assistant.git
cd clawdbot-job-assistant
```

### 2. Set Up Development Environment

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Copy environment template
cp .env.example .env
# Edit .env with your API keys

# Set up Supabase database (see SETUP.md)
```

### 3. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 4. Make Your Changes

- Follow existing code style
- Add tests if applicable
- Update documentation

### 5. Test Your Changes

```bash
# Run tests
python skills/test_supabase_connection.py
python skills/test_resume_generation.py
python skills/job_queue_manager.py

# Test your specific feature
python skills/your_new_module.py
```

### 6. Commit & Push

```bash
git add .
git commit -m "feat: add your feature description"
git push origin feature/your-feature-name
```

### 7. Create Pull Request

- Go to GitHub
- Click "New Pull Request"
- Describe your changes
- Submit PR

---

## 📝 Development Guidelines

### Code Style

- Use Python 3.8+ syntax
- Follow PEP 8
- Add type hints where helpful
- Document functions with docstrings

### File Organization

```
skills/
├── core/           # Core functionality
├── integrations/   # External service integrations
├── utils/          # Utility functions
└── tests/          # Test files
```

### Adding New Features

1. **New Job Board Support**
   - Create `skills/job_[board].py`
   - Add to `skills/job_boards.py`
   - Update tests

2. **New LLM Provider**
   - Add to `skills/tailor_resume.py`
   - Add to `skills/write_cover_letter.py`
   - Update config.yaml

3. **New Database Feature**
   - Create migration in `db/migrations/`
   - Update `db/client.py`
   - Add tests

### Testing

Always test:
- Database connections
- LLM API calls
- Document generation
- Form automation

```python
# Example test structure
def test_new_feature():
    """Test new feature works correctly."""
    # Setup
    # Execute
    # Assert
    pass
```

---

## 🐛 Bug Reports

Found a bug? Please report:

1. **Check existing issues** first
2. **Create new issue** with:
   - Bug description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details
   - Screenshots if applicable

### Bug Report Template

```markdown
## Bug Description
Brief description of the bug

## Steps to Reproduce
1. Step one
2. Step two
3. Bug occurs

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g., Windows 11]
- Python: [e.g., 3.9]
- Browser: [e.g., Chrome 120]

## Additional Context
Any other relevant information
```

---

## 💡 Feature Requests

Have an idea? Great!

1. **Check existing issues**
2. **Create new issue** with:
   - Feature description
   - Use case
   - Implementation ideas (optional)

### Feature Request Template

```markdown
## Feature Description
What the feature should do

## Use Case
Why this feature is needed

## Implementation Ideas
How it could be implemented (optional)

## Alternatives Considered
Other approaches (optional)
```

---

## 📚 Documentation

Help improve docs:

- **README.md** - Project overview
- **SETUP.md** - Setup instructions
- **QUICK_START.md** - Quick start guide
- **Code comments** - Inline documentation

### Documentation Style

- Use clear, simple language
- Include code examples
- Add screenshots where helpful
- Keep it up-to-date

---

## 🎯 Areas That Need Help

### High Priority

- [ ] **More job board support** (Indeed, Glassdoor, etc.)
- [ ] **Better error handling** in automation
- [ ] **Unit tests** for core modules
- [ ] **Documentation** improvements

### Medium Priority

- [ ] **UI/UX improvements** for generated documents
- [ ] **Performance optimizations**
- [ ] **More LLM provider options**
- [ ] **Mobile responsiveness** for documents

### Low Priority

- [ ] **Docker containerization**
- [ ] **CI/CD pipeline**
- [ ] **Internationalization**
- [ ] **Plugin system**

---

## 🏆 Recognition

Contributors get:
- 🌟 GitHub contributor status
- 📝 Credit in README
- 🏅 Special badge in Discord
- 💝 Eternal gratitude

---

## 📞 Get Help

- **Discord**: [Join our community]
- **Email**: deannawiley.careers@gmail.com
- **Issues**: GitHub Issues

---

## 📄 License

By contributing, you agree your code will be under the MIT License.

---

**Thank you for contributing to ClawdBot! 🎉**
