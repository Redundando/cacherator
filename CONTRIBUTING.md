# Contributing to Cacherator

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/Redundando/cacherator.git
cd cacherator
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

## Running Tests

```bash
pytest
```

## Building the Package

```bash
python -m build
```

## Publishing to PyPI

```bash
twine upload dist/*
```
