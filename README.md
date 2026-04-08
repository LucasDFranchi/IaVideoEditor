# IAVideoEditor

A Python-based application for video editing and manipulation.

## Features

- Video processing capabilities
- Modular architecture
- Comprehensive test suite
- Type hints support

## Requirements

- Python 3.8 or higher
- pip or conda for package management

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd IAVideoEditor
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. For development, also install dev dependencies:
```bash
pip install -r requirements-dev.txt
```

## Usage

Run the application:
```bash
python -m src.main
```

## Testing

Run tests with pytest:
```bash
pytest tests/
```

Run tests with coverage:
```bash
pytest tests/ --cov=src --cov-report=html
```

## Code Quality

Format code with Black:
```bash
black src/ tests/
```

Check code style with Flake8:
```bash
flake8 src/ tests/
```

Run linting with Pylint:
```bash
pylint src/
```

## Project Structure

```
IAVideoEditor/
├── src/                    # Main application source code
│   ├── __init__.py
│   └── main.py
├── tests/                  # Unit tests
│   ├── __init__.py
│   └── test_main.py
├── .github/
│   └── copilot-instructions.md
├── requirements.txt        # Project dependencies
├── requirements-dev.txt    # Development dependencies
├── setup.py               # Package setup configuration
├── pyproject.toml         # Project metadata and build configuration
├── .gitignore             # Git ignore rules
└── README.md              # This file
```

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support

For issues and questions, please open an issue on the repository.
