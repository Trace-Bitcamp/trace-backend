from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from supabase import create_client, Client
import datetime

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

app = Flask(__name__)
CORS(app)

@app.route('/dashboard')
def hello_world():
    return 'Hello, World!'

@app.route('/add_patient', methods=["POST"])
def add_patient():
    fName : str = request.args.get("fName")
    lName : str = request.args.get("lName")
    birthDate = request.args.get("bDate")
    gender : str = request.args.get("gender")
    email : str = request.args.get("email")
    phoneNum : int = int(request.args.get("phoneNum"))
    address : str = request.args.get("address")
    contactName : str = request.args.get("contactName")
    contactPhone : str = request.args.get("contactPhone")
    diagnosis = request.args.get("diagnosis")
    severity : str = request.args.get("severity")
    medHist : str = request.args.get("medHist")
    medication : str = request.args.get("medication")
    assessment_ids = []

    try:
        # Calculate age from birth date
        birth_date = datetime.datetime.strptime(birthDate, "%Y-%m-%d")
        today = datetime.datetime.now()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

        data = {
            "first_name": fName,
            "last_name": lName,
            "birth_date": birthDate,
            "age": age,
            "gender": gender,
            "email": email,
            "phone_number": phoneNum,
            "address": address,
            "emergency_contact_name": contactName,
            "emergency_contact_phone": contactPhone,
            "diagnosis": diagnosis,
            "severity": severity,
            "medical_history": medHist,
            "medication": [medication],
            "assessment_ids": assessment_ids
        }
        
        response = supabase.table("patients").insert(data).execute()
        return jsonify({"success": True, "data": response.data}), 201

    except Exception as e:
        app.logger.error(f"error inserting patient data: {str(e)}")
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
    date = request.args.get("date")
    treatment = request.args.get("treatment")
    provider = request.args.get("provider")

    try: 

        data = {
            "date": date,
            "treatment": treatment,
            "provider": provider
        }

        response = supabase.table("treatments").insert(data).execute()
        return jsonify({"success": True, "data": response.data}), 201
    
    except Exception as e:
        app.logger.error(f"error inserting treatment data: {str(e)}")
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

if __name__ == '__main__':
    app.run(debug=True)
    