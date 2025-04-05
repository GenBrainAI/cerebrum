# Development Commands

## Linting
- Run basic syntax check: `flake8 --count --select=E9,F63,F7,F82 --show-source`
- Run full linting: `flake8`
- Format code: `black .`
- Sort imports: `isort .`

To run all linting and formatting:
```bash
black . && isort . && flake8
```