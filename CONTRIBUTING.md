# Contributing to Rupture

Thank you for your interest in contributing!

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Contribute

### Reporting Bugs

- Check if the issue already exists
- Include steps to reproduce
- Include expected vs actual behavior
- Include your environment details

### Suggesting Features

- Open a GitHub Discussion first
- Explain the use case
- Consider backward compatibility

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Commit with clear messages
6. Push and open a Pull Request

### Rule Contributions (Bounty Program)

Contributing new deprecation rules? See the rule bounty program:

- Rules must include test fixtures
- Rules are MIT licensed
- Contributors receive Audit credits (not cash, pre-revenue)

## Development Setup

```bash
git clone https://github.com/ntoledo319/Rupture.git
cd Rupture
pip install -e kits/lambda-lifeline
pip install -e kits/al2023-gate
pip install -e kits/python-pivot
pytest
```

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
