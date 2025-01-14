import json
import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from pythonjsonlogger import jsonlogger
import time

# Flask App Initialization
app = Flask(__name__)
app.secret_key = 'secret'
COURSE_FILE = 'course_catalog.json'

# Configure Tracing
trace.set_tracer_provider(TracerProvider())
jaeger_exporter = JaegerExporter(
    agent_host_name='localhost',
    agent_port=6831,
)
span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)
FlaskInstrumentor().instrument_app(app)

# Configure Structured Logging
log_handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(message)s')
log_handler.setFormatter(formatter)
logging.root.addHandler(log_handler)
logging.root.setLevel(logging.INFO)

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
    with trace.get_tracer(__name__).start_as_current_span("index_page"):
        logging.info("Rendering index page")
        return render_template('index.html')


@app.route('/catalog')
def course_catalog():
    with trace.get_tracer(__name__).start_as_current_span("course_catalog"):
        start_time = time.time()
        courses = load_courses()
        logging.info("Accessed course catalog", extra={"route": "/catalog", "requests": 1})
        return render_template('course_catalog.html', courses=courses, processing_time=time.time() - start_time)


@app.route('/course/<code>')
def course_details(code):
    with trace.get_tracer(__name__).start_as_current_span("course_details"):
        start_time = time.time()
        courses = load_courses()
        course = next((course for course in courses if course['code'] == code), None)
        if not course:
            logging.error(f"No course found with code '{code}'", extra={"route": f"/course/{code}", "error": "not_found"})
            flash(f"No course found with code '{code}'.", "error")
            return redirect(url_for('course_catalog'))
        logging.info(f"Course details accessed for {code}", extra={"route": f"/course/{code}", "requests": 1, "processing_time": time.time() - start_time})
        return render_template('course_details.html', course=course)


@app.route('/add_course', methods=['GET', 'POST'])
def add_course():
    with trace.get_tracer(__name__).start_as_current_span("add_course"):
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
                logging.error(f"Failed to add course: Missing fields - {', '.join(missing_fields)}.", extra={"route": "/add_course", "error": "missing_fields"})
                flash(f"Error: The following fields are required: {', '.join(missing_fields)}.", "error")
                return redirect(url_for('add_course'))

            # Add the new course to the catalog
            save_courses({
                'name': course_name,
                'instructor': instructor,
                'semester': semester,
                'code': course_code
            })

            logging.info(f"Course '{course_name}' added successfully!", extra={"route": "/add_course", "requests": 1})
            flash(f"Course '{course_name}' added successfully!", "success")
            return redirect(url_for('course_catalog'))
        
        return render_template('add_course.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
