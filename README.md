# AWS Nova Cost Dashboard

<div align="center">

![AWS Nova Cost Dashboard](https://img.shields.io/badge/AWS-Nova_Cost_Dashboard-orange?style=for-the-badge&logo=amazonaws)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Last Updated](https://img.shields.io/badge/last_updated-April_2025-lightgrey)](CHANGELOG.md)

</div>

A comprehensive dashboard for analyzing AWS costs, tracking service usage, and managing service cancellations. This tool helps you monitor AWS spending, identify high-cost services, and provides intelligent recommendations for cost optimization.

## 🌟 Features

- **Interactive Dashboard**: Visualize AWS costs with interactive charts and filtering
- **Service Cancellation Management**: Easily cancel unused services and track cancellation status
- **Pay-As-You-Go Service Management**: Special handling for services like Rekognition and Transcribe
- **Cost Trend Analysis**: Identify cost patterns and spikes with daily/monthly views
- **Service Relationship Mapping**: Understand service dependencies and connections
- **Intelligent AWS Console Navigation**: Uses Nova Act SDK for AI-powered console navigation

## 📊 Dashboard Preview

Experience our interactive AWS Cost Dashboard:

![Dashboard Overview](docs/images/Screenshot%202025-04-24%20at%202.42.18%20PM.png)
*AWS Cost Dashboard Overview*

### Key Features in Action

| Service Cancellation Management | Cost Explorer Information Modal |
|:------------------------------:|:------------------------------:|
| ![Service Cancellation](docs/images/Screenshot%202025-04-24%20at%202.42.24%20PM.png) | ![Cost Explorer Modal](docs/images/Screenshot%202025-04-24%20at%202.42.28%20PM.png) |
| *Service Cancellation Management* | *Cost Explorer Information Modal* |

| Daily Cost Trends Visualization | Service Cost Breakdown |
|:------------------------------:|:----------------------:|
| ![Daily Cost Trends](docs/images/Screenshot%202025-04-24%20at%202.42.32%20PM.png) | ![Service Breakdown](docs/images/Screenshot%202025-04-24%20at%202.42.51%20PM.png) |
| *Daily Cost Trends Visualization* | *Service Cost Breakdown* |

## 🏗️ Architecture

This project follows a **Hexagonal Architecture** (Ports and Adapters) pattern with two main components:

### Repository Structure

```
nova-act/
├── src/
│   ├── nova_act/            # Nova Act SDK integration (AI-powered browser automation)
│   │   ├── impl/            # SDK implementation classes
│   │   ├── artifacts/       # Browser extension artifacts
│   │   └── samples/         # Example usage scripts
│   ├── nova_cost/           # AWS Cost Dashboard (main application)
│   │   ├── adapters/        # Implementation adapters (AWS, HTML)
│   │   ├── domain/          # Core business logic and interfaces
│   │   ├── models/          # Data models for the domain
│   │   ├── templates/       # HTML report templates and static assets
│   │   └── utils/           # Utility functions and helpers
├── data/                    # Data storage
│   └── reports/             # Generated dashboard reports
├── tests/                   # Test suite
├── docs/                    # Documentation
└── run_report.py            # Main entry point script
```

### Why Two Components?

1. **nova_act**: This is the AI-powered browser automation SDK that provides intelligent navigation within the AWS console. It's a standalone component that can be used independently for browser automation tasks.

2. **nova_cost**: This is the main AWS Cost Dashboard application that utilizes the Nova Act SDK for enhanced functionality, particularly for navigating complex AWS console screens during service cancellation.

This separation follows the principle of single responsibility and allows each component to evolve independently.

> 📌 **Nova Act SDK Setup**: For detailed information on setting up and using the Nova Act SDK, see our [Nova Act SDK Integration Guide](docs/NOVA_ACT_SDK_SETUP.md).

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- AWS account with Cost Explorer access
- AWS credentials configured in your environment
- Chrome browser (for Nova Act SDK features)

### Installation

```bash
# Clone the repository
git clone https://github.com/aws/nova-act.git
cd AWS Cost Canceler

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (optional)
export AWS_PROFILE=your-profile
```

## 📈 Usage

The project has a single entry point for all functionality:

```bash
# Generate a cost dashboard report
python run_report.py --days=30 --output=./my-report.html

# Open the report automatically in your browser
python run_report.py --open

# Analyze costs without generating a report
python run_report.py --analyze --threshold=15.0
```

### Command-Line Options

- `--days`: Number of days to analyze (default: 30)
- `--output`: Custom path for generated report
- `--open`: Open report in browser after generation (default: true)
- `--analyze`: Analyze costs without generating a report
- `--threshold`: Cost threshold for analysis in USD (default: 10.0)

## 🧪 Testing Strategy

This project uses a focused testing approach that verifies dashboard features through static analysis.

### Running Tests

Run the dashboard tests using our simple test runner:

```bash
# Run dashboard feature tests
python3 run_features_tests.py
```

This verifies all core dashboard functionality including:
- Service cancellation features
- Cost Explorer modal
- UI components and interactions

No additional dependencies are required for testing.

## 🛠️ Recent Improvements

### Enhanced Pay-As-You-Go Service Handling

The dashboard now features specialized handling for pay-as-you-go services like Amazon Rekognition and Transcribe:

- **Service Status**: Clearly marked as "Pay-As-You-Go" instead of Active/Cancelled
- **Resource-Specific Guidance**: Detailed instructions for cleaning up persistent resources
- **Command Reference**: Includes specific AWS CLI commands to stop all charges

### Improved Documentation

- **Environment Setup**: Added `.env.example` template for proper configuration
- **Repository Structure**: Reorganized documentation into the `docs/` directory
- **GitHub Best Practices**: Added comprehensive `.gitignore` file

## 🔧 Setup and Installation

### Prerequisites

- Python 3.9 or higher
- AWS account with Cost Explorer enabled
- AWS credentials configured locally

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/AWS-Cost-Canceler.git
cd AWS-Cost-Canceler
```

2. Set up a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure your environment:
```bash
cp .env.example .env
# Edit .env with your AWS credentials and settings
```

### Running the Dashboard

```bash
# Generate a cost dashboard report
python run_report.py --days=30 --output=./my-report.html

# Open the report automatically in your browser
python run_report.py --open

# Analyze costs without generating a report
python run_report.py --analyze --threshold=15.0
```

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 📋 GitHub Repository Best Practices (2025)

This repository follows modern GitHub best practices:

1. **Comprehensive README**: Clear documentation of features, usage, and architecture
2. **Shields and Badges**: Visual indicators of project status and metadata
3. **Directory Structure**: Logical organization with clear separation of concerns
4. **CI/CD Integration**: Automated testing and deployment workflows
5. **Issue Templates**: Structured formats for bug reports and feature requests
6. **Semantic Versioning**: Clear versioning scheme (MAJOR.MINOR.PATCH)
7. **Documentation**: Separate docs directory with detailed guides
8. **Code of Conduct**: Clear community guidelines
9. **Security Policy**: Responsible disclosure process
10. **Contributing Guidelines**: How to contribute effectively

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Contact

Igor Ganapolsky - [@iganapolsky](https://twitter.com/iganapolsky)

Project Link: [https://github.com/aws/nova-act](https://github.com/aws/nova-act)
