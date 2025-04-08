# Welcome to *Campus Job Review System* Contributing Guide

Thank you for taking the time to contribute to our [project](https://github.com/SEFall24-Team61/campus-job-review-system)! This guide will help you understand our contribution process, from opening an issue to creating and merging pull requests.

Please start by reviewing our [Code of Conduct](https://github.com/SEFall24-Team61/campus-job-review-system/blob/main/CODE_OF_CONDUCT.md) to help keep our community respectful and inclusive.

----

## Table of Contents
1. [How Can I Contribute?](#how-can-i-contribute)
2. [Reporting Issues](#reporting-issues)
3. [Submitting a Pull Request](#submitting-a-pull-request)
4. [Coding Standards](#coding-standards)

---

## How Can I Contribute?

#### 1. Discuss Changes
- Before making any changes, discuss your idea with the project owners. Start by creating a [new issue](https://github.com/SEFall24-Team61/campus-job-review-system/issues), emailing, or reaching out to repository maintainers via any other appropriate means listed in the [README](https://github.com/SEFall24-Team61/campus-job-review-system/blob/main/README.md).

#### 2. Creating Issues
- Before opening a new issue, check the [existing issue list](https://github.com/SEFall24-Team61/campus-job-review-system/issues) to avoid duplicating reports.
- When reporting a bug, please complete the provided bug report template. Include detailed information to help us reproduce and address the issue quickly.

#### 3. Reporting Unacceptable Behavior
- If you encounter any behavior that violates our Code of Conduct, please report it to the project owners. You can find contact details in the [README](https://github.com/SEFall24-Team61/campus-job-review-system/blob/main/README.md).

---

## Submitting a Pull Request

1. **Fork the Repository**: Start by forking the repository and cloning it to your local machine.
2. **Create a New Branch**: Name your branch descriptively, e.g., `feature-new-functionality` or `bugfix-issue-123`.
3. **Make Changes**: Make your changes, following the coding standards outlined below.
4. **Add Tests**: If you’re adding new functionality or fixing a bug, add relevant tests.
5. **Run Local Tests**: Ensure all tests pass locally before creating a pull request.
6. **Submit a Pull Request (PR)**: When you’re ready, push your changes and create a PR with a clear title and description. Complete the provided PR template to help maintainers review your contribution.

---

## Coding Standards

To maintain code quality, please follow these coding standards:

- **Code Formatting**: We use `autopep8` and `black` for automatic formatting. Run these tools before submitting your code to ensure consistent style:
```bash
autopep8 --in-place --recursive .
black .
```

- **Linting**: We use `pylint` to enforce code quality. Run pylint locally and resolve any reported issues:
```bash
pylint your_code_file.py
```

- **Linting and Complexity Checks with Flake8**: `Flake8` is also used to catch syntax errors, undefined names, and complexity issues in the CI workflow:
```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
```
These checks run automatically in our CI pipeline but should also be run locally before submitting a PR.