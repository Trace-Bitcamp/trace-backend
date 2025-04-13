import google.generativeai as genai
import os
from dotenv import load_dotenv
load_dotenv()
name = "John Doe"
age = 65
sex = "M"
phone_number = "+1234567890"
email = "john.d@gmail.com"
notes = [
    {"date": "2023-10-01", "note": "Patient shows mild tremors in the right hand."},
    {"date": "2023-09-15", "note": "Patient reports increased stiffness in the legs."},
    {"date": "2023-08-20", "note": "Patient's gait appears slightly shuffling."},
    {"date": "2023-07-10", "note": "Patient's medication regimen adjusted."},
    {"date": "2023-06-05", "note": "Patient reports improved sleep quality."}]
treatments = [
    {"date": "2023-10-01", "treatment": "Increased dosage of Levodopa.", "provider": "Dr. Smith"},
    {"date": "2023-09-01", "treatment": "Physical therapy sessions started.", "provider": "Dr. Jones"},
    {"date": "2023-08-15", "treatment": "Prescribed Amantadine for tremor control.", "provider": "Dr. Lee"},
    {"date": "2023-07-01", "treatment": "Initial diagnosis and treatment plan established.", "provider": "Dr. Brown"}]
assessments = [
    {"date": "2023-10-01", "DTW": 0.85, "model_confidence": 0.92, "mean_relative_tremor": 0.15},
    {"date": "2023-09-01", "DTW": 0.80, "model_confidence": 0.90, "mean_relative_tremor": 0.18},
    {"date": "2023-08-01", "DTW": 0.78, "model_confidence": 0.88, "mean_relative_tremor": 0.20},
    {"date": "2023-07-01", "DTW": 0.75, "model_confidence": 0.85, "mean_relative_tremor": 0.22}]

prompt = f"""
Generate a markdown report summarizing a Parkinson's disease patient's medical history and assessment data in a consistent, medically helpful format. The report must include the following sections in this exact order, using the provided data:

1. **Patient Information**: Display the patient's name, age, sex, phone number, email, and the current date (provided as input).
2. **Patient Summary**: A brief overview of the patient's condition based on the provided notes, treatments, and assessment trends.
3. **Past Notes**: A list of all past clinical notes, each including the date and the note content.
4. **Past Treatments**: A list of all past treatments, each including the date, the treatment details, and the treatment provider.
5. **Assessment Trends**: An analysis of trends over time forTambém the following metrics from each assessment:
   - Dynamic Time Warping (DTW)
   - Model confidence of Parkinson's diagnosis
   - Mean relative tremor
   Summarize how these metrics have changed, noting any patterns or significant fluctuations, and interpret their clinical relevance.
6. **Recommendations**: Provide brief, specific advice on next steps for the patient's care, tailored to the trends and data provided. Recommendations should be practical, medically sound, and relevant to Parkinson's disease management.

**Input Data**:  
- Patient Name: {name}
- Patient Age: {age}
- Patient Sex: {sex}
- Patient Phone: {phone_number}
- Patient Email: {email}   
- Past notes: {notes}
- Past treatments: {treatments}
- Assessments: {assessments}

**Output Format**:  
Return the response strictly in markdown with the following structure:

# Parkinson's Disease Patient Report

## Patient Information
- **Name**: [Patient name]
- **Age**: [Age]
- **Sex**: [Sex]
- **Phone Number**: [Phone number]
- **Email**: [Email]
- **Date**: [Current date]

## Patient Summary
[Brief overview of the patient's condition, integrating notes, treatments, and trends.]

## Past Notes
- **YYYY-MM-DD**: [Note content]
- **YYYY-MM-DD**: [Note content]
...

## Past Treatments
- **YYYY-MM-DD**: [Treatment details] (Provider: [Provider name])
- **YYYY-MM-DD**: [Treatment details] (Provider: [Provider name])
...

## Assessment Trends
[Summary of trends for DTW, model confidence, and mean relative tremor, with clinical interpretation.]

## Recommendations
[Specific, data-driven advice for next steps in patient care.]
"""


from google import genai

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

response = client.models.generate_content(
    model="gemini-2.0-flash", 
    contents=prompt
)
print(response.text)