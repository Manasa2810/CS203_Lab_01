import json
import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash

# Flask App Initialization
app = Flask(__name__)
app.secret_key = 'secret'
COURSE_FILE = 'course_catalog.json'

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')


# Utility Functions
def load_courses():
    """Load courses from the JSON file."""
    if not os.path.exists(COURSE_FILE):
        return []  # Return an empty list if the file doesn't exist
    with open(COURSE_FILE, 'r') as file:
        return json.load(file)


def save_courses(data):
    """Save new course data to the JSON file."""
    courses = load_courses()  # Load existing courses
    courses.append(data)  # Append the new course
    with open(COURSE_FILE, 'w') as file:
        json.dump(courses, file, indent=4)


# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/catalog')
def course_catalog():
    courses = load_courses()
    return render_template('course_catalog.html', courses=courses)


@app.route('/course/<code>')
def course_details(code):
    courses = load_courses()
    course = next((course for course in courses if course['code'] == code), None)
    if not course:
        flash(f"No course found with code '{code}'.", "error")
        return redirect(url_for('course_catalog'))
    return render_template('course_details.html', course=course)


@app.route('/add_course', methods=['GET', 'POST'])
def add_course():
    if request.method == 'POST':
        # Retrieve form data
        course_name = request.form.get('name')
        instructor = request.form.get('instructor')
        semester = request.form.get('semester')
        course_code = request.form.get('code')

        # Check if any required field is missing
        missing_fields = []
        if not course_name:
            missing_fields.append("Course Name")
        if not instructor:
            missing_fields.append("Instructor")
        if not semester:
            missing_fields.append("Semester")
        if not course_code:
            missing_fields.append("Course Code")

        # If any field is missing, display an error message
        if missing_fields:
            logging.error(f"Failed to add course: Missing fields - {', '.join(missing_fields)}.")
            flash(f"Error: The following fields are required: {', '.join(missing_fields)}.", "error")
            return redirect(url_for('add_course'))

        # Add the new course to the catalog
        save_courses({
            'name': course_name,
            'instructor': instructor,
            'semester': semester,
            'code': course_code
        })

        flash(f"Course '{course_name}' added successfully!", "success")
        return redirect(url_for('course_catalog'))
    
    return render_template('add_course.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
