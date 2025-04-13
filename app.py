from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import os
from supabase import create_client, Client
import datetime
from dotenv import load_dotenv
import base64
from model.inference import PD_Model

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

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

model = PD_Model()

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

@app.route('/add_assessment', methods=["POST"])
def add_assessment():
    date = request.args.get("date")
    assessment_type = request.args.get("type")
    path = request.args.get("path")
    baseline_path = request.args.get("baselinePath")

    try:
        data = {
            "date": date,
            "type": assessment_type,
            "path": path,
            "baselinePath": baseline_path
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

@app.route('/add_note/', methods=["POST"])
def add_note():
    patient_id = request.args.get("id")
    note = request.args.get("note")
    
    try:
        # Get current notes for the patient
        response = supabase.table("patients").select("notes").eq("id", patient_id).execute()
        
        if not response.data:
            return jsonify({"success": False, "error": "Patient not found"}), 404
            
        current_notes = response.data[0].get("notes", [])
        
        # Add new note to the array
        updated_notes = current_notes + [note] if current_notes else [note]
        
        # Update the patient's notes
        update_response = supabase.table("patients").update({"notes": updated_notes}).eq("id", patient_id).execute()
        return jsonify({"success": True, "data": update_response.data}), 200
        
    except Exception as e:
        app.logger.error(f"error updating patient notes: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
    

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/submit-assessment', methods=["POST"])
def submit_assessment():
    data = request.get_json()

    if not data or 'image' not in data or 'name' not in data:
        return jsonify({"success": False, "error": "Invalid data"}), 400

    trace_image = data['trace']
    template_image = data['template']
    age = data['age']

    # Remove the prefix (data:image/png;base64,) if it exists
    for image in [trace_image, template_image]:
        if image.startswith('data:image/png;base64,'):
            image = image.replace('data:image/png;base64,', '')
    
    # Decode the base64 strings
    try:
        trace_image = base64.b64decode(trace_image)
        template_image = base64.b64decode(template_image)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
    try:
        pd_prob = model.run_inference(trace_image, template_image, age)
    except Exception as e:
        return jsonify({"success": False, "error": "Error running model inference: str(e)"}), 500

    return jsonify({"success": True, "prob": pd_prob}), 201


if __name__ == '__main__':
    app.run(debug=True)
    