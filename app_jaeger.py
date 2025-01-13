import json
import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

# Flask App Initialization
app = Flask(__name__)
app.secret_key = 'secret'
COURSE_FILE = 'course_catalog.json'

# Set up tracing
trace.set_tracer_provider(TracerProvider())

# Configure the Jaeger Exporter
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",  # Jaeger agent hostname
    agent_port=6831,             # Jaeger agent port
)

# Add the Jaeger exporter to the tracer provider
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(jaeger_exporter))
tracer = trace.get_tracer(__name__)

# Instrument Flask and Requests
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

# Set up logging
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
    logging.info(f"Existing courses: {courses}")  # Log current courses
    logging.info(f"Adding new course: {data}")  # Log the course being added
    courses.append(data)  # Append new course data
    with open(COURSE_FILE, 'w') as file:
        json.dump(courses, file, indent=4)  # Save the updated list back to the file

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/catalog')
def course_catalog():
    with tracer.start_as_current_span("Render Course Catalog") as span:
        courses = load_courses()
        span.set_attribute("courses.count", len(courses))
        return render_template('course_catalog.html', courses=courses)

@app.route('/course/<code>')
def course_details(code):
    with tracer.start_as_current_span("View Course Details") as span:
        courses = load_courses()
        course = next((course for course in courses if course['code'] == code), None)
        if not course:
            flash(f"No course found with code '{code}'.", "error")
            span.set_attribute("error", True)
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

