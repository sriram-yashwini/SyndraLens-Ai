# SyndraLens AI

A Lightweight Clinical Text Analysis and Regional Health Surveillance Using a Small Language Model (SLM)

## Overview

SyndraLens AI is a domain-specific AI prototype designed to extract structured clinical symptoms and related information from text reports. It combines a fine-tuned Small Language Model (SLM), rule-based extraction, syndrome-pattern analysis, and an interactive dashboard to explore synthetic health reports.

The project aims to make clinical-style text easier to analyze by converting unstructured descriptions into structured information and visualizing potential regional symptom patterns.

**Note:** This project uses synthetic data for development and demonstration. It is not a clinically validated diagnostic tool.

## Key Features

- **Clinical Text Extraction:** Extracts symptoms and related attributes from text.
- **SLM-Based Analysis:** Uses a Qwen2.5-0.5B-Instruct model with a LoRA adapter.
- **Rule-Based Fallback:** Supports extraction and structured output when model predictions need additional handling.
- **Symptom and Syndrome Analysis:** Identifies potential patterns using structured symptom information and deterministic rules.
- **Regional Visualization:** Displays synthetic reports and potential symptom patterns through an interactive dashboard.
- **Data Analysis:** Supports exploring report attributes and potential trends.
- **Evaluation:** Includes evaluation scripts for examining extraction quality and output validity.

## Technology Stack

- Python
- Small Language Models (SLMs)
- Qwen2.5-0.5B-Instruct
- LoRA fine-tuning
- Natural Language Processing (NLP)
- Streamlit
- Pandas
- Data visualization
- Rule-based information extraction

## Project Structure

```text
Synthetic clinical application/
├── configs/
│   └── config.yaml
├── data/
│   └── processed/
├── models/
│   └── syndralens-lora-small/
├── scripts/
│   └── analyse_complaints.py
├── syndralens/
│   ├── challenge.py
│   ├── inference.py
│   ├── ontology.py
│   ├── rule_extractor.py
│   ├── schema.py
│   ├── spatiotemporal.py
│   └── syndrome_engine.py
├── training/
│   ├── __init__.py
│   ├── _boot.py
│   ├── train.py
│   └── evaluate.py
├── dashboard.py
├── requirements.txt
├── .gitignore
└── README.md
```

*This is an illustrative structure. Keep only the folders and files that actually exist in your repository.*

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Sriram-Yashwini/SyndraLens-AI.git
cd SyndraLens-AI
```


### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Check configuration and model files

Ensure that the configuration file, required synthetic data, and trained LoRA adapter are available at the paths expected by the application.

The base model may need to be downloaded from Hugging Face when running the application for the first time.

## Running the Application

Start the Streamlit dashboard from the project root:

```bash
python -m streamlit run dashboard.py
```

Streamlit will provide a local URL in the terminal. Open that URL in your browser to use the dashboard.

## Model Training and Evaluation

Training and evaluation scripts are provided for development and experimentation.

Run training only when the required datasets, configuration, dependencies, and base model are available:

```bash
python training/train.py
```

Run evaluation using the commands supported by the project's evaluation script and configuration.

## Future Improvements

- Expand and improve the diversity of synthetic training examples.
- Improve symptom extraction and experiencer attribution.
- Evaluate performance on carefully governed, representative datasets.
- Improve model robustness and error handling.
- Enhance dashboard usability and regional data visualization.
## Responsible Use and Limitations

- The project uses synthetic clinical-style data for development and demonstration.
- Model predictions and rule-based extraction may contain errors or omit important information.
- Detected symptom patterns should be treated as exploratory signals, not confirmed disease outbreaks.
- The system is not a medical diagnostic tool and must not be used to make treatment decisions.
- Further testing and validation are required before considering real-world healthcare applications.
