# ML Vulnerability Detection Model

This directory contains the pre-trained PyTorch model (`model.pt`) for vulnerability detection.

## Model Integration

The ML model is automatically integrated into the `VulnerabilityScanner` class. When scanning targets, the system will:

1. **First attempt**: Use the ML model to predict vulnerabilities based on scan data
2. **Fallback**: If ML model is unavailable or fails, use rule-based detection

## Usage

The model is automatically loaded when the `VulnerabilityScanner` is initialized. No additional configuration is needed.

### Testing the Model

To test if the model loads correctly, run:

```bash
cd art-ai/backend
python test_ml_model.py
```

### Model Input

The model expects:
- **Target**: Hostname or IP address
- **Open Ports**: List of dictionaries with `port` and `service` fields
- **Services**: Optional list of service information

### Model Output

The model returns a list of vulnerabilities with:
- `name`: Vulnerability name
- `severity`: critical, high, medium, or low
- `description`: Description of the vulnerability
- `affected_service`: Service affected
- `affected_port`: Port number
- `confidence`: ML model confidence score (0-1)
- `detection_method`: "ML Model"
- `exploit_available`: Boolean
- `remediation`: Remediation suggestion

## Requirements

Make sure PyTorch and NumPy are installed:

```bash
pip install torch numpy
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

## Model Architecture

The model wrapper automatically detects the model architecture and handles:
- Feedforward neural networks
- LSTM/RNN models
- Custom architectures

If the model architecture cannot be automatically detected, a fallback architecture is used.

## Troubleshooting

If the model fails to load:
1. Check that `model.pt` exists in the `models/` directory
2. Verify PyTorch is installed: `python -c "import torch; print(torch.__version__)"`
3. Check the console output for specific error messages
4. The system will automatically fall back to rule-based detection if ML fails

