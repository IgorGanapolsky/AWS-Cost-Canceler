# Nova Act SDK Integration Guide

This guide explains how to properly set up and use the Nova Act SDK in the AWS Cost Dashboard project.

## What is Nova Act SDK?

[Nova Act](https://github.com/aws/nova-act) is a browser automation tool from AWS that uses AI to navigate web interfaces. Unlike typical API-based SDKs, Nova Act controls a browser to perform actions on your behalf, such as:

- Navigating to AWS Console pages
- Finding and clicking elements
- Filling forms
- Extracting information from pages

## Installation

1. Install the Nova Act SDK via pip:

```bash
pip install AWS Cost Canceler
```

2. Add Nova Act to your project's requirements:

```bash
# Add to requirements.txt
AWS Cost Canceler==0.3.0  # Use the latest version
```

## Basic Usage

Nova Act is used to automate browser tasks with natural language commands:

```python
from nova_act import NovaAct

with NovaAct(starting_page="https://console.aws.amazon.com") as nova:
    # Log in to AWS Console (you'll need to handle auth separately)
    
    # Navigate to Cost Explorer
    nova.act("navigate to Cost Explorer")
    
    # Capture information or perform actions
    nova.act("click on the Reports button")
```

## Using Nova Act in the AWS Cost Dashboard

Our project now includes Nova Act integration for AWS console navigation. The implementation offers two approaches:

1. **URL Construction** (Default): Constructs direct console URLs without browser automation
2. **Browser Automation** (Advanced): Uses Nova Act to navigate the AWS Console interactively

### URL Construction Mode

This mode doesn't actually use the browser automation features of Nova Act, but follows the same pattern of determining correct console URLs:

```python
from nova_cost.utils.aws_resource_scanner import AWSResourceScanner

scanner = AWSResourceScanner()
# Get URL to Cost Explorer
url = scanner.get_console_url("AWS Cost Explorer")
```

### Browser Automation Mode (Future Enhancement)

For future interactive browser automation:

```python
scanner = AWSResourceScanner()
# This would launch a browser and navigate to Cost Explorer
scanner.run_nova_act_browser_session("AWS Cost Explorer")
```

## Environment Variables

Configure the following environment variables in your `.env` file:

```
# Optional: AWS credentials for boto3
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# For Nova Act browser automation
# NOVA_SDK_TOKEN is not needed for URL construction mode
NOVA_SDK_TOKEN=your_token  # If/when required for authentication
```

## Troubleshooting

Common issues:

1. **ImportError: No module named 'nova_act'**  
   Solution: Install the Nova Act SDK with `pip install nova-act`

2. **Browser automation not working**  
   Solution: Ensure you have Chrome installed and the `chromedriver` binary is available in your PATH

3. **Authentication failures**  
   Solution: For AWS Console navigation, you may need to handle authentication separately

## References

- [Nova Act GitHub Repository](https://github.com/aws/nova-act)
- [Sample Code](https://github.com/aws/nova-act/tree/main/src/nova_act/samples)
