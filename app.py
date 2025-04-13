from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import os
from supabase import create_client, Client
import datetime
from dotenv import load_dotenv
from model.inference import PD_Model
import numpy as np
import cv2
import base64
from io import BytesIO
from PIL import Image
from google import genai

model = PD_Model()

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

model = PD_Model()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

app = Flask(__name__)
# Configure CORS to allow all origins and methods
CORS(app, resources={r"/*": {
    "origins": ["http://localhost:3000", "http://localhost:5173", "*"],  # Add your frontend URL
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization", "Accept"],
    "expose_headers": ["Content-Range", "X-Content-Range"],
    "supports_credentials": True
}})

@app.after_request
def after_request(response):
    app.logger.info(f"Response Headers: {dict(response.headers)}")
    return response

@app.route('/test')
def test():
    app.logger.info("Test endpoint hit")
    return jsonify({"status": "Server is running"}), 200

@app.route('/dashboard')
def hello_world():
    return 'Hello, World!'

@app.route('/patient')
def get_all_patients():
    try:
        response = supabase.table("patients").select("*").execute()
        
        if not response.data:
            return jsonify({"success": False, "error": "Patient not found"}), 404
        
        app.logger.info(response.data)
            
        return jsonify({"success": True, "data": response.data}), 200
        
    except Exception as e:
        app.logger.error(f"error fetching patient data: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/patient/<patient_id>')
def get_patient(patient_id):
    try:
        response = supabase.table("patients").select("*").eq("id", patient_id).execute()
        
        if not response.data:
            return jsonify({"success": False, "error": "Patient not found"}), 404
            
        return jsonify({"success": True, "data": response.data[0]}), 200
        
    except Exception as e:
        app.logger.error(f"error fetching patient data: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
    
@app.route('/assessments')
def get_all_assessments():
    try:
        response = supabase.table("assessments").select("*").execute()
        
        if not response.data:
            return jsonify({"success": False, "error": "No assessments found"}), 404
            
        return jsonify({"success": True, "data": response.data}), 200
        
    except Exception as e:
        app.logger.error(f"error fetching assessment data: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
    
@app.route('/assessments/<patient_id>')
def get_assessments(patient_id):
    try:
        response = supabase.table("assessments").select("*").eq("patientId", patient_id).execute()
        
        if not response.data:
            return jsonify({"success": False, "error": "No assessments found for this patient"}), 404
            
        return jsonify({"success": True, "data": response.data}), 200
        
    except Exception as e:
        app.logger.error(f"error fetching assessment data: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/add_patient', methods=["OPTIONS"])
def handle_options():
    app.logger.info("OPTIONS request received for /add_patient")
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    app.logger.info(f"Responding to OPTIONS with headers: {dict(response.headers)}")
    return response

@app.route('/add_patient', methods=["POST"])
def add_patient():
    try:
        # Log the incoming request
        app.logger.info("POST request received for /add_patient")
        app.logger.info(f"Request headers: {dict(request.headers)}")
        app.logger.info(f"Request method: {request.method}")
        app.logger.info(f"Request content type: {request.content_type}")
        
        # Get data from request body
        request_data = request.get_json(silent=True)
        if not request_data:
            app.logger.error("No JSON data received in request")
            app.logger.info(f"Request body: {request.get_data(as_text=True)}")
            return jsonify({"success": False, "error": "No data provided or invalid JSON"}), 400
            
        app.logger.info(f"Received data: {request_data}")
        
        # Extract data with validation
        fName = request_data.get("fName")
        lName = request_data.get("lName")
        birthDate = request_data.get("bDate")
        gender = request_data.get("gender")
        email = request_data.get("email")
        phoneNum = request_data.get("phoneNum")
        address = request_data.get("address")
        contactName = request_data.get("contactName")
        contactPhone = request_data.get("contactNum")
        diagnosis = request_data.get("diagnosis")
        severity = request_data.get("severity")
        medHist = request_data.get("medHist")
        medication = request_data.get("medication")
        assessment_ids = []

        # Validate required fields
        required_fields = ["fName", "lName", "bDate"]
        missing_fields = [field for field in required_fields if not request_data.get(field)]
        if missing_fields:
            app.logger.error(f"Missing required fields: {missing_fields}")
            return jsonify({"success": False, "error": f"Missing required fields: {missing_fields}"}), 400

        # Calculate age from birth date
        try:
            birth_date = datetime.datetime.strptime(birthDate, "%Y-%m-%d")
            today = datetime.datetime.now()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        except ValueError as e:
            app.logger.error(f"Invalid date format: {birthDate}")
            return jsonify({"success": False, "error": "Invalid date format. Use YYYY-MM-DD"}), 400

        data = {
            "fName": fName,
            "lName": lName,
            "birthDate": birthDate,
            "age": age,
            "gender": gender,
            "email": email,
            "phoneNum": phoneNum,
            "address": address,
            "contactName": contactName,
            "contactPhone": contactPhone,
            "diagnosis": diagnosis,
            "severity": severity,
            "medHist": medHist,
            "medication": [medication],
            "assessment_ids": assessment_ids,
            "notes": []
        }
        
        app.logger.info("Attempting to insert data into Supabase")
        response = supabase.table("patients").insert(data).execute()
        app.logger.info("Successfully inserted data")
        
        response = jsonify({"success": True, "data": response.data})
        return response, 201

    except Exception as e:
        app.logger.error(f"Error in add_patient: {str(e)}")
        app.logger.exception("Full traceback:")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/add-assessment', methods=["POST"])
def add_assessment():
    request_data = request.get_json(silent=True)

    date = request_data.get("date")
    assessment_type = request_data.get("type")
    patient_id = request_data.get("patientId")
    severity = request_data.get("severity")
    tremor = request_data.get("tremor")
    deviation = request_data.get("deviation")

    print("Received data:", date, assessment_type, patient_id, severity, tremor, deviation)

    try:
        data = {
            "date": date,
            "type": assessment_type,
            "patientId": int(patient_id),
            "severity": float(severity),
            "tremor": float(tremor),
            "deviation": float(deviation),
        }
        
        response = supabase.table("assessments").insert(data).execute()
        return jsonify({"success": True, "data": response.data}), 201

    except Exception as e:
        app.logger.error(f"error inserting assessment data: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
    
@app.route('/add_treatment', methods=["POST"])
def add_treatment():
    patient_id = request.args.get("id")
    date = request.args.get("date")
    t_desc = request.args.get("t_desc")
    provider = request.args.get("provider")
    treatment = {
        "date": date,
        "t_desc": t_desc,
        "provider": provider
    }
    
    try:
        # Get current treatments for the patient
        response = supabase.table("patients").select("medication").eq("id", patient_id).execute()
        
        if not response.data:
            return jsonify({"success": False, "error": "Patient not found"}), 404
            
        current_treatments = response.data[0].get("medication", [])
        
        # Add new treatment to the array
        updated_treatments = current_treatments + [treatment] if current_treatments else [treatment]
        
        # Update the patient's treatments
        update_response = supabase.table("patients").update({"medication": updated_treatments}).eq("id", patient_id).execute()
        return jsonify({"success": True, "data": update_response.data}), 200
        
    except Exception as e:
        app.logger.error(f"error updating patient treatments: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/add_note', methods=["POST"])
def add_note():
    patient_id = request.args.get("id")
    note = request.args.get("note")
    
    try:
        # Get current notes for the patient
        response = supabase.table("patients").select("notes").eq("id", patient_id).execute()
        
        if not response.data:
            return jsonify({"success": False, "error": "Patient not found"}), 404
            
        current_notes = response.data[0].get("notes", [])
        
        # Create new note object
        note_obj = {
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "note": note,
            "doctor": "Dr. Johnson"
        }
        
        # Add new note to the array
        updated_notes = current_notes + [note_obj] if current_notes else [note_obj]
        
        # Update the patient's notes
        update_response = supabase.table("patients").update({"notes": updated_notes}).eq("id", patient_id).execute()
        return jsonify({"success": True, "data": update_response.data}), 200
        
    except Exception as e:
        app.logger.error(f"error updating patient notes: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
    

@app.route('/submit-images', methods=["POST"])
def submit_images():
    data = request.get_json()

    if not data or 'trace' not in data or 'template' not in data or 'age' not in data:
        return jsonify({"success": False, "error": "Invalid request"}), 400

    trace_image = data['trace']
    template_image = data['template']
    age = data['age']

    # Remove the prefix (data:image/png;base64,) if it exists
    if trace_image.startswith('data:image/png;base64,'):
        trace_image = trace_image.replace('data:image/png;base64,', '')
    if template_image.startswith('data:image/png;base64,'):
        template_image = template_image.replace('data:image/png;base64,', '')

    try:
        severity_score, mean_tremor, dtw_distance = model.run_inference(trace_image, template_image, age)
        print("Severity Score:", severity_score, "Mean Tremor:", mean_tremor, "DTW Distance:", dtw_distance)
    except Exception as e:
        print(str(e))
        return jsonify({"success": False, "error": "Error running model inference:" +  str(e)}), 500
    
    return jsonify({"success": True, "data": {
        "severity_score": str(severity_score),
        "mean_tremor": str(mean_tremor),
        "dtw_distance": str(dtw_distance)
        }
    }), 201

@app.route('/gemini_treatment', methods=["POST"])
def gemini_treatment():
    data = request.get_json()

    if not data or 'date' not in data or 'description' not in data or 'provider' not in data:
        return jsonify({"success": False, "error": "Invalid request"}), 400

    date = data['date']
    description = data['description']
    provider = data['provider']

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=os.environ.get("TREATMENT_PROMPT")
    )

    return jsonify({"success": True, "response": str(response)}), 201

@app.route('/gemini_report', methods=["POST"])
def gemini_report():
    data = request.get_json()

    # if not data or 'date' not in data or 'description' not in data or 'provider' not in data:
    #     return jsonify({"success": False, "error": "Invalid request"}), 400

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

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    response = client.models.generate_content(
        model="gemini-2.0-flash", 
        contents=prompt
    )

    return jsonify({"success": True, "response": response.text}), 201

if __name__ == '__main__':
    app.run(debug=True)