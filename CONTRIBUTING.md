# Contributing to MediMatch

Thank you for your interest in contributing to MediMatch! This document provides guidelines and instructions for
contributing.

## 🤝 How to Contribute

### Reporting Bugs

1. **Check existing issues** to see if the bug has already been reported
2. **Create a new issue** with:
    - Clear title describing the bug
    - Steps to reproduce
    - Expected behavior
    - Actual behavior
    - Screenshots (if applicable)
    - Environment details (OS, Python version, browser)

### Suggesting Features

1. **Check existing feature requests** to avoid duplicates
2. **Create a new issue** with:
    - Clear description of the feature
    - Use case and benefits
    - Possible implementation approach
    - Any relevant examples or mockups

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**
4. **Test thoroughly**
5. **Commit with clear messages**:
   ```bash
   git commit -m "Add: Brief description of changes"
   ```
6. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Open a Pull Request** with:
    - Description of changes
    - Link to related issues
    - Screenshots (for UI changes)

## 📋 Development Guidelines

### Code Style

- Follow **PEP 8** for Python code
- Use **meaningful variable names**
- Add **docstrings** to all functions and classes
- Keep functions **small and focused**
- Use **type hints** where appropriate

Example:

```python
def calculate_similarity(smiles1: str, smiles2: str) -> float:
    """
    Calculate Tanimoto similarity between two SMILES strings.
    
    Args:
        smiles1: SMILES string for first molecule
        smiles2: SMILES string for second molecule
    
    Returns:
        float: Similarity score between 0 and 1
    
    Raises:
        ValueError: If SMILES strings are invalid
    """
    # Implementation here
    pass
```

### Commit Messages

Use conventional commit format:

- `Add:` New feature
- `Fix:` Bug fix
- `Update:` Modify existing feature
- `Remove:` Delete code/feature
- `Docs:` Documentation changes
- `Style:` Code style changes (formatting, etc.)
- `Refactor:` Code restructuring
- `Test:` Add or update tests
- `Chore:` Maintenance tasks

Examples:

```
Add: Drug interaction checker endpoint
Fix: Handle missing SMILES in comparison
Update: Improve OCR accuracy with preprocessing
Docs: Add API endpoint documentation
```

### Testing

Before submitting a PR:

1. **Test all endpoints**:
   ```bash
   # Test drug search
   curl http://localhost:5000/api/search_drug?query=aspirin
   
   # Test comparison
   curl http://localhost:5000/api/compare_drugs?drug1=aspirin&drug2=ibuprofen
   ```

2. **Test UI features**:
    - Drug visualization
    - Drug comparison
    - OCR upload
    - Knowledge graph
    - AI Copilot chat

3. **Check for errors** in:
    - Browser console
    - Flask logs
    - Terminal output

### Documentation

Update documentation when:

- Adding new features
- Changing API endpoints
- Modifying configuration
- Adding dependencies

Update these files as needed:

- `README.md` - Main documentation
- `CONTRIBUTING.md` - This file
- Inline code comments
- Docstrings

## 🏗️ Development Setup

### 1. Clone and Install

```bash
git clone https://github.com/yourusername/medimatch.git
cd medimatch
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Set Up Environment

```bash
cp .env.example .env
# Edit .env and add your API keys
```

### 3. Run in Development Mode

```bash
export FLASK_ENV=development  # or set FLASK_ENV=development on Windows
export DEBUG=True
python app.py
```

### 4. Make Changes

- Edit code
- Test changes
- Commit with clear messages
- Push to your fork
- Open PR

## 🎯 Priority Areas for Contribution

We're especially looking for help in these areas:

### High Priority

- [ ] Expand drug database with common OTC drugs
- [ ] Improve OCR accuracy for handwritten prescriptions
- [ ] Add comprehensive drug-drug interaction database
- [ ] Implement unit tests for core functions
- [ ] Add ADMET property prediction

### Medium Priority

- [ ] Mobile-responsive UI improvements
- [ ] Add more visualization options (2D structure editor)
- [ ] Integrate additional knowledge graphs (DrugBank, KEGG)
- [ ] Add batch processing for multiple molecules
- [ ] Implement user authentication

### Low Priority (Nice to Have)

- [ ] Dark mode toggle
- [ ] Export reports as PDF
- [ ] Molecule structure drawing tool
- [ ] Advanced filtering in drug search
- [ ] Internationalization (i18n)

## 🐛 Bug Bounty

We don't have a formal bug bounty program, but we appreciate all bug reports! Major bug fixes will be acknowledged in
release notes.

## 📝 Code Review Process

1. **Initial Review**: Maintainers will review your PR within 1-3 days
2. **Feedback**: We may request changes or ask questions
3. **Iteration**: Make requested changes and push updates
4. **Approval**: Once approved, we'll merge your PR
5. **Recognition**: Your contribution will be acknowledged in release notes

## 🚫 What We Don't Accept

- Code without proper documentation
- Changes that break existing functionality
- Large PRs without prior discussion
- Plagiarized or copyrighted code
- Code that doesn't follow our style guide

## 💬 Communication

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Pull Request Comments**: For code-specific discussions

## 📚 Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [RDKit Documentation](https://www.rdkit.org/docs/)
- [PEP 8 Style Guide](https://pep8.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)

## 🙏 Thank You!

Every contribution, no matter how small, helps make MediMatch better. We appreciate your time and effort!

---

**Questions?** Feel free to open an issue or reach out to the maintainers.
