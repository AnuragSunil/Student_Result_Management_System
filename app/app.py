from flask import Flask, request, jsonify
import psycopg2
import psycopg2.extras
from flask_cors import CORS
import csv
from io import StringIO
from flask import send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

app = Flask(__name__)
CORS(app)  

# PostgreSQL Connection Setup
conn = psycopg2.connect(
    database="student_management",
    user="postgres",  # replace with your username
    password="a",  # replace with your password
    host="localhost",
    port="5432"
)
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

@app.route('/add_student', methods=['POST'])
def add_student():
    try:
        data = request.get_json()

        name = data['name']
        student_class = data['class']
        section = data['section']
        email = data['email']

        cur.execute("""
            INSERT INTO students (name, class, section, email)
            VALUES (%s, %s, %s, %s)
            RETURNING student_id;
        """, (name, student_class, section, email))

        student_id = cur.fetchone()[0]
        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Student added successfully",
            "student_id": student_id
        }), 201

    except Exception as e:
        conn.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
@app.route('/get_students', methods=['GET'])
def get_students():
    try:
        cur.execute("SELECT * FROM students;")
        rows = cur.fetchall()

        students_list = []
        for row in rows:
            student = {
                "student_id": row['student_id'],
                "name": row['name'],
                "class": row['class'],
                "section": row['section'],
                "email": row['email']
            }
            students_list.append(student)

        return jsonify({
            "status": "success",
            "students": students_list
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    
@app.route('/add_mark', methods=['POST'])
def add_mark():
    try:
        data = request.get_json()

        student_id = int(data['student_id'])
        subject = data['subject']
        score = int(data['score'])  # 🟢 Convert to int here

        # Validate score (between 0 and 100)
        if score < 0 or score > 100:
            return jsonify({
                "status": "error",
                "message": "Score must be between 0 and 100"
            }), 400

        # Check if student exists
        cur.execute("SELECT * FROM students WHERE student_id = %s;", (student_id,))
        student = cur.fetchone()

        if student is None:
            return jsonify({
                "status": "error",
                "message": "Student ID not found"
            }), 404

        # Insert mark
        cur.execute("""
            INSERT INTO marks (student_id, subject, score)
            VALUES (%s, %s, %s)
            RETURNING mark_id;
        """, (student_id, subject, score))

        mark_id = cur.fetchone()[0]
        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Mark added successfully",
            "mark_id": mark_id
        }), 201

    except Exception as e:
        conn.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

@app.route('/get_student_by_id/<int:student_id>', methods=['GET'])
def get_student_by_id(student_id):
    try:
        # Get student info
        cur.execute("SELECT * FROM students WHERE student_id = %s;", (student_id,))
        student = cur.fetchone()

        if student is None:
            return jsonify({
                "status": "error",
                "message": "Student ID not found"
            }), 404

        # Get marks for the student
        cur.execute("SELECT * FROM marks WHERE student_id = %s;", (student_id,))
        marks = cur.fetchall()

        marks_list = []
        for mark in marks:
            marks_list.append({
                "subject": mark['subject'],
                "score": mark['score']
            })

        # Return student info along with marks
        student_info = {
            "student_id": student['student_id'],
            "name": student['name'],
            "class": student['class'],
            "section": student['section'],
            "email": student['email'],
            "marks": marks_list
        }

        return jsonify({
            "status": "success",
            "student": student_info
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
@app.route('/update_student/<int:student_id>', methods=['PUT'])
def update_student(student_id):
    try:
        data = request.get_json()

        name = data.get('name')
        student_class = data.get('class')
        section = data.get('section')
        email = data.get('email')

        # Check if student exists
        cur.execute("SELECT * FROM students WHERE student_id = %s;", (student_id,))
        student = cur.fetchone()

        if student is None:
            return jsonify({
                "status": "error",
                "message": "Student ID not found"
            }), 404

        # Update student info
        cur.execute("""
            UPDATE students
            SET name = %s, class = %s, section = %s, email = %s
            WHERE student_id = %s;
        """, (name, student_class, section, email, student_id))

        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Student info updated successfully"
        }), 200

    except Exception as e:
        conn.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
@app.route('/delete_student/<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    try:
        # Check if student exists
        cur.execute("SELECT * FROM students WHERE student_id = %s;", (student_id,))
        student = cur.fetchone()

        if student is None:
            return jsonify({
                "status": "error",
                "message": "Student ID not found"
            }), 404

        # Delete marks associated with the student
        cur.execute("DELETE FROM marks WHERE student_id = %s;", (student_id,))

        # Delete student
        cur.execute("DELETE FROM students WHERE student_id = %s;", (student_id,))

        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Student and their marks deleted successfully"
        }), 200

    except Exception as e:
        conn.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
@app.route('/export_students_marks', methods=['GET'])
def export_students_marks():
    try:
        # Fetch all students
        cur.execute("SELECT * FROM students;")
        students = cur.fetchall()

        students_with_marks = []
        
        for student in students:
            student_data = {
                "student_id": student['student_id'],
                "name": student['name'],
                "class": student['class'],
                "section": student['section'],
                "email": student['email'],
                "marks": []
            }

            # Get marks for the student
            cur.execute("SELECT * FROM marks WHERE student_id = %s;", (student['student_id'],))
            marks = cur.fetchall()

            for mark in marks:
                student_data["marks"].append({
                    "subject": mark['subject'],
                    "score": mark['score']
                })

            students_with_marks.append(student_data)

        return jsonify({
            "status": "success",
            "students_with_marks": students_with_marks
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
@app.route('/generate_report_card/<int:student_id>', methods=['GET'])
def generate_report_card(student_id):
    try:
        # Fetch student data
        cur.execute("SELECT * FROM students WHERE student_id = %s;", (student_id,))
        student = cur.fetchone()

        if student is None:
            return jsonify({
                "status": "error",
                "message": "Student ID not found"
            }), 404

        # Fetch marks for the student
        cur.execute("SELECT * FROM marks WHERE student_id = %s;", (student_id,))
        marks = cur.fetchall()

        # Create PDF
        pdf_buffer = io.BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=letter)
        
        c.setFont("Helvetica", 12)

        # Title
        c.drawString(200, 750, f"Report Card for {student['name']}")
        c.drawString(200, 730, f"Class: {student['class']} | Section: {student['section']}")
        c.drawString(200, 710, f"Email: {student['email']}")

        # Draw subject and marks table
        y_position = 690
        c.drawString(50, y_position, "Subject")
        c.drawString(400, y_position, "Score")
        y_position -= 20

        for mark in marks:
            c.drawString(50, y_position, mark['subject'])
            c.drawString(400, y_position, str(mark['score']))
            y_position -= 20

        # Save PDF
        c.save()

        # Prepare PDF for sending to user
        pdf_buffer.seek(0)
        return send_file(pdf_buffer, as_attachment=True, download_name=f"report_card_{student['name']}.pdf", mimetype="application/pdf")

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

if __name__ == '__main__':
    app.run(debug=True)
