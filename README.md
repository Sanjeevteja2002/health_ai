# Health Analytics Chatbot

A Flask-based web application that provides population-level health insights by querying a SQLite database containing health and lifestyle data. The chatbot uses Google's Gemini AI to intelligently generate SQL queries or Python code based on user questions.

## Features

- **Natural Language Querying**: Ask questions in plain English about health trends and patterns
- **Intelligent Query Generation**: Automatically determines whether to use SQL or Python for analysis
- **Population-Level Insights**: Provides data-driven insights based on dataset patterns
- **Responsible AI**: Refuses personal health predictions and redirects to dataset-based analysis
- **Chat History**: Maintains conversation context within sessions

## Tech Stack

- **Backend**: Flask (Python web framework)
- **Database**: SQLite
- **AI Model**: Google Gemini 2.5 Flash
- **Data Processing**: Pandas
- **Frontend**: HTML templates (Jinja2)

## Project Structure

```
.
├── app.py                    # Main Flask application
├── health.db                 # SQLite database
├── Health_dataset_1.csv      # Primary health data
├── Health_dataset_2.csv      # Lifestyle data
├── health_file.ipynb         # Analysis notebook
├── templates/
│   └── index.html           # Chat interface template
└── README.md
```

## Installation

### Prerequisites

- Python 3.8+
- pip package manager

### Setup

1. Clone the repository:
```bash
git clone <your-repo-url>
cd <repo-name>
```

2. Install dependencies:
```bash
pip install flask pandas google-genai
```

3. Set up your Google API key:
   - Get an API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Replace the API key in `app.py` (line 18) with your own key
   - **Important**: For production, use environment variables instead of hardcoding

4. Ensure CSV files are in the project directory:
   - `Health_dataset_1.csv`
   - `Health_dataset_2.csv`

## Usage

1. Start the Flask application:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://127.0.0.1:5000
```

3. Ask questions about health trends, such as:
   - "What is the average BMI by gender?"
   - "Is there a correlation between physical activity and BMI?"
   - "How many patients have high blood pressure?"
   - "What's the distribution of sleep hours?"

## How It Works

### Data Pipeline

1. **Data Loading**: CSV files are loaded into Pandas DataFrames
2. **Data Cleaning**: Column names are standardized (lowercase, underscores) and categorical values are normalized
3. **Database Creation**: Clean data is written to SQLite tables (`health` and `lifestyle`)

### Query Processing

1. **Scope Detection**: Checks if the question is personal or out-of-scope
2. **Query Generation**: LLM generates either:
   - SQL query (for standard data retrieval)
   - Python code + SQL query (for statistical analysis requiring correlation, etc.)
3. **Validation**: Ensures queries are read-only and code is safe
4. **Execution**: Runs the query/code against the database
5. **Insight Generation**: LLM converts results into user-friendly explanations

### Safety Features

- **Personal Question Filtering**: Redirects requests for personal health predictions
- **SQL Validation**: Blocks INSERT, UPDATE, DELETE, DROP, ALTER operations
- **Python Sandboxing**: Restricts imports and dangerous functions
- **Read-Only Access**: Database operations are strictly SELECT queries

## Database Schema

### Health Table
- `patient_number` (unique identifier)
- Health metrics (BMI, blood pressure, etc.)
- Patient demographics

### Lifestyle Table
- `patient_number` (links to health table)
- Lifestyle factors (activity level, sleep, etc.)

Tables are joined using `patient_number`.

## Configuration

### API Key Management

**For development:**
```python
client = genai.Client(api_key="YOUR_API_KEY")
```

**For production (recommended):**
```python
import os
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
```

Then set the environment variable:
```bash
export GOOGLE_API_KEY="your-api-key-here"
```

## Limitations

- Cannot provide personal health predictions or advice
- Limited to data present in the uploaded datasets
- Does not handle real-time data updates
- Requires internet connection for LLM API calls

## Security Considerations

⚠️ **Important**: 
- Never commit API keys to version control
- Use environment variables for sensitive credentials
- The current implementation has the API key hardcoded - replace this before deploying
- Consider implementing rate limiting for production use

## Future Enhancements

- [ ] Add data visualization (charts/graphs)
- [ ] Support for file uploads (custom datasets)
- [ ] User authentication and personalized chat history
- [ ] Export conversation history
- [ ] Enhanced error handling and logging
- [ ] Support for more complex statistical analyses

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Disclaimer

This application is for educational and informational purposes only. It does not provide medical advice, diagnosis, or treatment. Always consult with qualified healthcare professionals for medical decisions.

## Contact

sanjeevteja25021@gmail.com
