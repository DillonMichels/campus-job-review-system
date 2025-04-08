from flask import render_template, request, send_from_directory, redirect, flash, url_for, abort, jsonify
from flask_login import login_user, current_user, logout_user, login_required
from app.services.job_fetcher import fetch_job_listings
from app import app, db, bcrypt
from app.models import Meetings, Reviews, User, JobApplication, Recruiter_Postings, PostingApplications, JobExperience

from app.forms import RegistrationForm, LoginForm, ReviewForm, JobApplicationForm, PostingForm
from datetime import datetime
import json

import ollama
from ollama import chat
from ollama import ChatResponse

from pdfquery import PDFQuery
import base64
import PyPDF2
from io import BytesIO

## additions made 2/22
import os
from werkzeug.utils import secure_filename
from flask import Flask, flash, current_app
# added on 2/24
from flask import send_from_directory, current_app  # NEW
from werkzeug.utils import secure_filename  # NEW


def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    text = ""
    with open(pdf_path) as doc:
        for page in doc:
            text += page.get_text("text") + "\n"  # Extract text from each page
    return text if text.strip() else "No text found in the PDF."


app.config["SECRET_KEY"] = "5791628bb0b13ce0c676dfde280ba245"

@app.route("/")
@app.route("/home")
def home():
    """An API for the user to be able to access the homepage through the navbar"""
    entries = Reviews.query.all()
    return render_template("index.html", entries=entries)

# #####################################
# #####################################

## editing routes for tests to work Feb 25
UPLOAD_FOLDER = os.getcwd()+'/app/resumes'  # Create this folder in your project
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}  # Add other extensions as needed
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    user = current_user
    print("User's resume path (from database):", user.resume_path)  # Debugging: Print the path from the database.
    
    if request.method == 'POST':
        if 'resume' in request.files:  # Check if a file was uploaded
            file = request.files['resume']
            if file.filename == '':
                flash('No selected file', 'warning')
                return redirect(request.url)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)

                # Update the user's resume path in the database
                user.resume_path = filepath  # Or just filename if you prefer
                db.session.commit()
                flash('Resume uploaded successfully!', 'success')
                return redirect(url_for('account'))
            else:
                flash('Allowed file types are pdf, docx, txt', 'danger')
                return redirect(request.url)
        
    resume_path = user.resume_path if user.is_authenticated else None
    return render_template("account.html", title="Account", resume_path=resume_path)


@app.route('/resume/<path:path>')  # Serve the resume
@login_required
def serve_resume(path):
    user = current_user
    directory = app.config['UPLOAD_FOLDER']
    return send_from_directory(directory, path)

# #####################################
# #####################################

#@app.route("/register", methods=["GET"])
#def register():

@app.route("/register", methods=["POST", "GET"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode(
            "utf-8"
        )
        user = User(
            username=form.username.data, email=form.email.data, password=hashed_password, is_recruiter=form.signup_as_recruiter.data
        )
        db.session.add(user)
        db.session.commit()
        flash(
            "Account created successfully! Please log in with your credentials.",
            "success",
        )
        return redirect(url_for("login"))
    return render_template("register.html", title="Register", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get("next")
            return redirect(next_page) if next_page else redirect(url_for("home"))
        else:
            flash(
                "Login Unsuccessful. Please enter correct email and password.", "danger"
            )
    return render_template("login.html", title="Login", form=form)


# @app.route("/logout")
# def logout():
#     logout_user()
#     flash("Logged out successfully!", "success")
#     return redirect(url_for("home"))
@app.route("/logout")
def logout():
    if not current_user.is_authenticated:
        flash("You need to be logged in", "warning")
        return redirect(url_for("login"))

    logout_user()
    flash("You have been logged out", "success")
    return redirect(url_for("home"))


@app.route("/review/all")
def view_reviews():
    """An API for the user to view all the reviews entered with pagination"""
    page = request.args.get("page", 1, type=int)
    per_page = 5
    entries = Reviews.query.paginate(page=page, per_page=per_page)
    return render_template("view_reviews.html", entries=entries)


@app.route("/resume_parser", methods=['GET','POST'])
def resume_parser():
    """
    LLM Integration that gives resume advice
    """
    available_models = ollama.list()
    print('available models', available_models)

    model_name = 'deepseek-r1:1.5b'
    model_exists = any(model.model == model_name for model in available_models['models'])

    

    if request.method == 'POST':
        # if 'file' not in request.files:
        #     return render_template("resume_parser.html", llmresponse = "no file added...")
        # file = request.files['file']
        text = ''
        if request.files:
            file_storage = request.files['file']  # Extract the FileStorage object

            # Read the file content
            file_content = file_storage.read()  # This returns the file content as bytes

            # If you need to save the file
            #file_storage.save('Resume-Srinivas_Vasudevan.pdf')
            try:
                pdf_reader = PyPDF2.PdfReader(BytesIO(file_content))
                for page in pdf_reader.pages:
                    text += page.extract_text()

                print(model_exists, len(text) > 0, text)
            
                if model_exists and len(text) > 0:
                    response: ChatResponse = chat(model='deepseek-r1:1.5b', messages=[{'role': 'user','content': f'give improvement suggestions for this resume: {text}'}])
                    print(response.message.content)
                    return jsonify({'status': 'Task complete', 'result': response.message.content })
                else:
                    return jsonify({'status': 'Task Failed', 'result': 'Possibly no model' })
            except Exception as e:
                print(f'{e}')
                return jsonify({'status': 'Task failed', 'result': 'Possibly wrong file type' })
        else:
            return jsonify({'status': 'Failed', 'result': 'No file sent' })
    
    else:
        if model_exists:
            #response: ChatResponse = chat(model='deepseek-r1:1.5b', messages=[{'role': 'user','content': 'Why is the sky blue?'}])
            #print(response.message.content)
            return render_template("resume_parser.html", llmresponse = 'llm ready buddy..')
        else:
            return render_template("resume_parser.html", llmresponse = "model is not ready yet....")

@app.route("/resume_parser_we", methods=['POST'])
def resume_parser_we():
    """
    LLM Integration that gives resume advice
    """
    available_models = ollama.list()
    print('available models', available_models)

    model_name = 'deepseek-r1:1.5b'
    model_exists = any(model.model == model_name for model in available_models['models'])

    if request.method == 'POST':
        # if 'file' not in request.files:
        #     return render_template("resume_parser.html", llmresponse = "no file added...")
        # file = request.files['file']
        text = ''
        if request.files:
            file_storage = request.files['file']  # Extract the FileStorage object


            # Read the file content
            file_content = file_storage.read()  # This returns the file content as bytes

            try:

            # If you need to save the file
            #file_storage.save('Resume-Srinivas_Vasudevan.pdf')

                pdf_reader = PyPDF2.PdfReader(BytesIO(file_content))
                for page in pdf_reader.pages:
                    text += page.extract_text()
                    text+= "\n"

            
                if model_exists and len(text) > 0:
                    response: ChatResponse = chat(model='deepseek-r1:1.5b', messages=[{'role': 'user','content': 
                                        f'''categorize the work experience you see in the following resume into following categories: 
                                            job_title, 
                                            company_name,
                                            location,
                                            duration,
                                            description,
                                            skills, 
                                            give that output in a json formatt.
                                            This work experience should only be extracted from the experience section of the resume. Do not parse the whole resume and give incorrect results.
                                            You should essentially return an array of json objects each holding the work experience categorized correctly based on my requirements.   
                                            Make sure that the answer you give me just has a json so that I dont run into parsing issues in my python script.  
                                            a sample output would be: [{{"job_title":"",
                                            "company_name":"",
                                            "location":"",
                                            "duration":"",
                                            "description":"",
                                            "skills":""}},
                                            {{"job_title":"",
                                            "company_name":"",
                                            "location":"",
                                            "duration":"",
                                            "description":"",
                                            "skills":""}}]      
                                            see how it is an array of json objects and it only uses the work experience/professional experience section and nothing else. 
                                            , the resume is : 
                                            : {text}'''}])
                    print(response.message.content)
                    print(response.message.content[response.message.content.find('['):response.message.content.rfind(']')+1])
                    we_json = json.loads(response.message.content[response.message.content.find('['):response.message.content.rfind(']')+1])
                    for we in we_json:
                        print(we)
                        job_title = we["job_title"]
                        company_name = we["company_name"]
                        location =we["location"]
                        duration = we["duration"]
                        description =we["description"]
                        skills = ','.join(we["skills"])

                        new_job = JobExperience(
                            job_title=job_title,
                            company_name=company_name,
                            location=location,
                            duration=duration,
                            description=description,
                            skills=skills,
                            username=current_user.username
                        )
                        db.session.add(new_job)
                        db.session.commit()
                    return jsonify({'status': 'Task complete', 'result': response.message.content[response.message.content.find('['):response.message.content.rfind(']')+1] })
                else:
                    return jsonify({'status': 'Task Failed', 'result': 'Possibly no model' })
            except Exception as e:
                print(f'{e}')
                return jsonify({'status': 'Task Failed', 'result': 'Possibly wrong file type'})
        else:
            return jsonify({'status': 'Failed', 'result': 'No file sent' })
    
    else:
        if model_exists:
            #response: ChatResponse = chat(model='deepseek-r1:1.5b', messages=[{'role': 'user','content': 'Why is the sky blue?'}])
            #print(response.message.content)
            return render_template("resume_parser.html", llmresponse = 'llm ready buddy..')
        else:
            return render_template("resume_parser.html", llmresponse = "model is not ready yet....")
        


@app.route("/review/new", methods=["GET", "POST"])
@login_required
def new_review():
    form = ReviewForm()
    if form.validate_on_submit():
        print("Checkbox value:", form.is_anonymous.data) #DBG
        review = Reviews(
            job_title=form.job_title.data,
            job_description=form.job_description.data,
            department=form.department.data,
            locations=form.locations.data,
            hourly_pay=form.hourly_pay.data,
            benefits=form.benefits.data,
            review=form.review.data,
            rating=form.rating.data,
            recommendation=form.recommendation.data,
            is_anonymous=form.is_anonymous.data,
            author=current_user,
        )
        db.session.add(review)
        db.session.commit()
        flash("Review submitted successfully!", "success")
        return redirect(url_for("view_reviews"))
    
    return render_template(
        "create_review.html", title="New Review", form=form, legend="Add your Review"
    )


@app.route("/review/<int:review_id>")
def review(review_id):
    review = Reviews.query.get_or_404(review_id)
    return render_template("review.html", review=review)


@app.route("/review/<int:review_id>/update", methods=["GET", "POST"])
@login_required
def update_review(review_id):
    review = Reviews.query.get_or_404(review_id)
    if review.author != current_user:
        abort(403)
    form = ReviewForm()
    if form.validate_on_submit():
        review.job_title = form.job_title.data
        review.job_description = form.job_description.data
        review.department = form.department.data
        review.locations = form.locations.data
        review.hourly_pay = form.hourly_pay.data
        review.benefits = form.benefits.data
        review.review = form.review.data
        review.rating = form.rating.data
        review.recommendation = form.recommendation.data
        db.session.commit()
        flash("Your review has been updated!", "success")
        return redirect(url_for("view_reviews"))
    elif request.method == "GET":
        form.job_title.data = review.job_title
        form.job_description.data = review.job_description
        form.department.data = review.department
        form.locations.data = review.locations
        form.hourly_pay.data = review.hourly_pay
        form.benefits.data = review.benefits
        form.review.data = review.review
        form.rating.data = review.rating
        form.recommendation.data = review.recommendation
    return render_template(
        "create_review.html", title="Update Review", form=form, legend="Update Review"
    )


@app.route('/upvote/<int:review_id>', methods=['POST'])
@login_required
def upvote_review(review_id):
    review = Reviews.query.get_or_404(review_id)
    if review.upvotes is None:
        review.upvotes = 0  # Set to 0 if None
    review.upvotes += 1
    db.session.commit()
    flash('You upvoted the review!', 'success')
    return redirect(request.referrer or url_for('page_content_post'))


@app.route('/downvote/<int:review_id>', methods=['POST'])
@login_required
def downvote_review(review_id):
    review = Reviews.query.get_or_404(review_id)
    if review.upvotes is None:
        review.upvotes = 0  # Set to 0 if None
    if review.upvotes > 0:
        review.upvotes -= 1  # Decrement upvote count only if greater than 0
        db.session.commit()
        flash('You downvoted the review!', 'warning')
    return redirect(request.referrer or url_for('page_content_post'))


@app.route("/review/<int:review_id>/delete", methods=["POST"])
@login_required
def delete_review(review_id):
    review = Reviews.query.get_or_404(review_id)
    if review.author != current_user:
        abort(403)
    db.session.delete(review)
    db.session.commit()
    flash("Your review has been deleted!", "success")
    return redirect(url_for("view_reviews"))


@app.route("/dashboard")
@login_required
def getVacantJobs():
    """
    An API for the users to see all the available vacancies and their details
    """
    postings = Recruiter_Postings.query.all()
    return render_template("dashboard.html", postings=postings)

@app.route("/apply/<int:posting_id>", methods=["POST"])
@login_required
def applyForJob(posting_id):
    postings = Recruiter_Postings.query.all()
    recruiter_id = request.form.get('recruiter_id')
    applicant_id = current_user.id
    resume_filename = None

    # Check if the applicant has already applied
    existing_application = PostingApplications.query.filter_by(
        postingId=posting_id,
        recruiterId=recruiter_id,
        applicantId=applicant_id
    ).first()

    if existing_application:
        flash("You have already applied for this job.", "warning")
        return render_template("dashboard.html", postings=postings)

    # Handle Resume Upload
    if 'resume' in request.files:
        file = request.files['resume']
        if file.filename != '' and allowed_file(file.filename):  # Validate file type
            resume_filename = secure_filename(file.filename)
            resume_path = os.path.join(UPLOAD_FOLDER, resume_filename)
            file.save(resume_path)  # Save resume to 'static/resumes/'
        else:
            flash("Invalid resume file. Only PDF, DOC, or DOCX allowed.", "danger")
            return redirect(request.referrer)

    # Create a new job application
    new_application = PostingApplications(
        postingId=posting_id,
        recruiterId=recruiter_id,
        applicantId=applicant_id
    )

    db.session.add(new_application)
    db.session.commit()

    # Store resume in JobApplication model
    job_application = JobApplication(
        job_link=str(posting_id),  # Assuming posting_id is used as job reference
        applied_on=datetime.utcnow().date(),
        last_update_on=datetime.utcnow().date(),
        status="applied",
        user_id=applicant_id,
        resume_path=f"static/resumes/{resume_filename}" if resume_filename else None
    )

    db.session.add(job_application)
    db.session.commit()

    flash("Application successfully submitted with resume!", "success")
    return render_template("dashboard.html", postings=postings)

# @app.route("/apply/<int:posting_id>", methods=["POST"])
# @login_required
# def applyForJob(posting_id):
#     postings = Recruiter_Postings.query.all()
#     recruiter_id = request.form.get('recruiter_id')
#     applicant_id = current_user.id
#     existing_application = PostingApplications.query.filter_by(
#         postingId=posting_id,
#         recruiterId=recruiter_id,
#         applicantId=applicant_id
#     ).first()

#     if existing_application:
#         # If application exists, redirect or show a message
#         flash("You have already applied for this job.", "warning")
#         return render_template("dashboard.html", postings=postings)
    
#     new_application = PostingApplications(
#         postingId = posting_id,
#         recruiterId = recruiter_id,
#         applicantId = applicant_id
#     )

#     db.session.add(new_application)
#     db.session.commit()

#     flash("Application successfully submitted to the recruiter!", "success")
#     return render_template("dashboard.html", postings=postings)


@app.route("/add_jobs", methods=['GET', 'POST'])
@login_required
def add_jobs():
    if not current_user.is_recruiter:
        flash("Unauthorized: You must be a recruiter to post jobs.", "danger")
        return redirect(url_for("home"))
    
    form = PostingForm()
    if form.validate_on_submit():
        posting = Recruiter_Postings(
            postingId = form.jobPostingID.data,
            recruiterId = current_user.id,
            jobTitle = form.jobTitle.data,
            jobLink = form.jobLink.data,
            jobDescription = form.jobDescription.data,
            jobLocation = form.jobLocation.data,
            jobPayRate = form.jobPayRate.data,
            maxHoursAllowed = form.maxHoursAllowed.data
        )
        print("Adding posting: ", posting)
        db.session.add(posting)
        db.session.commit()
        flash("Job Posting added successfully!", "success")
        return redirect(url_for("recruiter_postings"))
    return render_template(
        "add_jobs.html", title="Job Posting", form=form, legend="Add new posting"
    )

@app.route("/recruiter_postings")
@login_required
def recruiter_postings():
    if not current_user.is_recruiter:
        flash("Unauthorized: You must be a recruiter to post jobs.", "danger")
        return redirect(url_for("home"))
    
    postings = Recruiter_Postings.query.filter(Recruiter_Postings.recruiterId == current_user.id).all()
    return render_template(
        "recruiter_postings.html",
        postings=postings
    )

@app.route("/recruiter/postings/delete/<int:posting_id>", methods=["POST"])
def delete_posting(posting_id):
    if not current_user.is_recruiter:
        flash("Unauthorized: You must be a recruiter to post jobs.", "danger")
        return redirect(url_for("home"))
    
    # Fetch the posting by its ID
    posting = Recruiter_Postings.query.filter_by(postingId=posting_id, recruiterId=current_user.id).first()
    applicants_for_posting = PostingApplications.query.filter_by(postingId=posting_id, recruiterId=current_user.id).all()

    if applicants_for_posting:
        for application in applicants_for_posting:
            db.session.delete(application)
        db.session.commit()
    
    if posting:
        if posting.recruiterId == current_user.id:
            db.session.delete(posting)
            db.session.commit()
            flash("Job Posting deleted successfully!", "success")
        else:
            flash("You are not authorized to delete this posting", "danger")
    
    return redirect(url_for('recruiter_postings'))

@app.route("/recruiter/<int:posting_id>/applications", methods=["GET"])
@login_required
def get_applications(posting_id):
    """
    Display all applications for a specific job posting by the recruiter.
    """
    # Ensure the recruiter owns the posting
    posting = Recruiter_Postings.query.filter_by(
        postingId=posting_id, recruiterId=current_user.id
    ).first_or_404()

    # Fetch all applications for this posting
    applications = PostingApplications.query.filter_by(postingId=posting_id).all()

    # Create a list of user profiles associated with the applications
    application_user_profiles = []
    for application in applications:
        applicant = User.query.filter_by(id=application.applicantId).first()
        if applicant:
            application_user_profiles.append(applicant)

    # Pass the posting and the applicants to the template
    return render_template(
        "posting_applicants.html",
        posting=posting,
        application_user_profiles=application_user_profiles,
    )

@app.route("/applicant_profile/<string:applicant_username>", methods=["GET"])
@login_required
def get_applicant(applicant_username):
    job_experiences = JobExperience.query.filter_by(username=applicant_username).all()
    applicant_details = User.query.filter_by(username=applicant_username).first()

    print("Queried for: ", applicant_username)
    print(applicant_details.username)
    print("Job exp", job_experiences)

    return render_template(
        "applicant_profile.html",
        applicant_details=applicant_details,
        job_experiences=job_experiences
    )

@app.route("/pageContentPost", methods=["POST", "GET"])
def page_content_post():
    """An API for the user to view specific reviews depending on the job title, location, and rating range with pagination."""
    page = request.args.get("page", 1, type=int)
    per_page = 5  # Set items per page as desired

    # Retrieve form data
    search_title = request.form.get("search_title", "")
    search_location = request.form.get("search_location", "")
    min_rating = request.form.get("min_rating", type=int, default=1)
    max_rating = request.form.get("max_rating", type=int, default=5)

    # Initial query for reviews
    query = Reviews.query

    # Apply filters if search fields are filled
    if search_title.strip():
        query = query.filter(Reviews.job_title.ilike(f"%{search_title}%"))
    if search_location.strip():
        query = query.filter(Reviews.locations.ilike(f"%{search_location}%"))
    if min_rating is not None and max_rating is not None:
        query = query.filter(Reviews.rating.between(min_rating, max_rating))

    # Paginate the results
    entries = query.paginate(page=page, per_page=per_page)

    # Pass search terms back to the template to preserve state across pagination
    return render_template(
        "view_reviews.html",
        entries=entries,
        search_title=search_title,
        search_location=search_location,
        min_rating=min_rating,
        max_rating=max_rating,
    )


# @app.route("/account", methods=['GET', 'POST'])
# @login_required
# def account():
#     user = current_user
#     resume_path = user.resume_path if user.is_authenticated else None # Get resume path from user object
#     return render_template("account.html", title="Account", resume_path=resume_path)


@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    job_listings = fetch_job_listings()
    return jsonify(job_listings)

@app.route("/job_application/new", methods=["GET", "POST"])
@login_required
def new_job_application():
    form = JobApplicationForm()  # Form class should include fields for job_link, applied_on, last_update_on, and status
    if form.validate_on_submit():
        # Create a new job application instance
        application = JobApplication(
            job_link=form.job_link.data,
            applied_on=form.applied_on.data,
            last_update_on=form.last_update_on.data,
            status=form.status.data,
            user_id=current_user.id  # Associate with the current logged-in user
        )
        db.session.add(application)
        db.session.commit()
        flash("Job application added successfully!", "success")
        return redirect(url_for("view_job_applications"))
    return render_template(
        "create_job_application.html",
        title="New Job Application",
        form=form,
        legend="Add Job Application"
    )

@app.route("/application_tracker")
@login_required
def application_tracker():
    # Query all job applications for the logged-in user
    job_applications = JobApplication.query.filter_by(user_id=current_user.id).all()
    return render_template(
        "job_applications.html",
        title="Application Tracker",
        job_applications=job_applications,
    )

@app.route("/add_job_application", methods=["POST"])
@login_required
def add_job_application():
    job_link = request.form.get('job_link')
    applied_on = request.form.get('applied_on')
    last_update_on = request.form.get('last_update_on')
    status = request.form.get('status')

    new_application = JobApplication(
        job_link=job_link,
        applied_on=datetime.strptime(applied_on, '%Y-%m-%d').date(),
        last_update_on=datetime.strptime(last_update_on, '%Y-%m-%d').date(),
        status=status,
        user_id=current_user.id
    )

    db.session.add(new_application)
    db.session.commit()

    flash("Job application added successfully!", "success")
    return redirect(url_for('application_tracker'))

@app.route("/update_status/<int:application_id>", methods=["POST"])
@login_required
def update_status(application_id):
    application = JobApplication.query.get_or_404(application_id)

    if application.user_id != current_user.id:
        flash("You cannot update this application.", "danger")
        return redirect(url_for('application_tracker'))

    status = request.form.get('status')
    application.status = status
    db.session.commit()

    flash("Application status updated successfully!", "success")
    return redirect(url_for('application_tracker'))

@app.route("/update_last_update/<int:application_id>", methods=["POST"])
@login_required
def update_last_update(application_id):
    application = JobApplication.query.get_or_404(application_id)

    if application.user_id != current_user.id:
        flash("You cannot update this application.", "danger")
        return redirect(url_for('application_tracker'))

    last_update_on = request.form.get('last_update_on')
    application.last_update_on = datetime.strptime(last_update_on, '%Y-%m-%d').date()
    db.session.commit()

    flash("Application last update date updated successfully!", "success")
    return redirect(url_for('application_tracker'))

@app.route("/delete_job_application/<int:application_id>", methods=["POST"])
@login_required
def delete_job_application(application_id):
    application = JobApplication.query.get_or_404(application_id)

    if application.user_id != current_user.id:
        flash("You cannot delete this application.", "danger")
        return redirect(url_for('application_tracker'))

    db.session.delete(application)
    db.session.commit()
    flash("Job application deleted successfully!", "success")
    return redirect(url_for('application_tracker'))

@app.route('/job_profile', methods=['GET', 'POST'])
@login_required
def job_profile():
    if request.method == 'POST':
        # Handle job experience form submission
        job_title = request.form.get('job_title')
        company_name = request.form.get('company_name')
        location = request.form.get('location')
        duration = request.form.get('duration')
        description = request.form.get('description')
        skills = request.form.get('skills') 

        new_job = JobExperience(
            job_title=job_title,
            company_name=company_name,
            location=location,
            duration=duration,
            description=description,
            skills=skills,
            username=current_user.username
        )
        db.session.add(new_job)
        db.session.commit()
        flash('Job experience added successfully!', 'success')
        return redirect(url_for('job_profile'))

    # Fetch job experiences for the current user
    job_experiences = JobExperience.query.filter_by(username=current_user.username).all()
    return render_template('job_profile.html', job_experiences=job_experiences)

@app.route('/schedule_meeting/<string:applicant_username>', methods=['POST'])
@login_required
def schedule_meeting(applicant_username):
    meeting_time_str = request.form.get('meeting_time')  # Get the meeting time
    posting_id = request.form.get('posting_id')  # Get the posting ID

    try:
        # Convert the meeting time string to a datetime object
        meeting_time = datetime.strptime(meeting_time_str, "%Y-%m-%dT%H:%M")
    except ValueError:
        flash("Invalid date format. Please use the provided date-time picker.", "danger")
        return redirect(request.referrer)

    # Validate posting ID
    if not posting_id:
        flash("No job posting associated with this meeting.", "danger")
        return redirect(request.referrer)

    # Fetch the applicant from the database
    applicant = User.query.filter_by(username=applicant_username).first()
    if not applicant:
        flash("Applicant not found.", "danger")
        return redirect(request.referrer)

    # Validate the job posting exists
    job_posting = Recruiter_Postings.query.filter_by(postingId=posting_id, recruiterId=current_user.id).first()
    if not job_posting:
        flash("Job posting not found or you are not authorized to schedule a meeting for this posting.", "danger")
        return redirect(request.referrer)

    # Create and save the meeting
    new_meeting = Meetings(
        recruiter_id=current_user.id,
        applicant_id=applicant.id,
        meeting_time=meeting_time,
        posting_id=posting_id  # Associate the meeting with the job posting
    )

    db.session.add(new_meeting)
    db.session.commit()

    flash(f"Meeting scheduled with {applicant_username} on {meeting_time} for job posting '{job_posting.jobTitle}'.", "success")
    return redirect(request.referrer)

@app.route('/recruiter/meetings', methods=['GET'])
@login_required
def recruiter_meetings():
    meetings = Meetings.query.filter_by(recruiter_id=current_user.id).all()
    return render_template("recruiter_meetings.html", meetings=meetings)

@app.route('/applicant/meetings', methods=['GET'])
@login_required
def applicant_meetings():
    meetings = Meetings.query.filter_by(applicant_id=current_user.id).all()
    return render_template("applicant_meetings.html", meetings=meetings)
@app.route('/shortlisted/<int:posting_id>', methods=['GET'])
@login_required
def view_shortlisted_for_posting(posting_id):
    """
    Fetch and display all shortlisted applicants for a specific job posting.
    """
    # Ensure the current user is the recruiter for this posting
    posting = Recruiter_Postings.query.filter_by(postingId=posting_id, recruiterId=current_user.id).first_or_404()

    # Fetch all shortlisted applicants for the job posting
    shortlisted_applicants = PostingApplications.query.filter_by(
        postingId=posting_id,
        recruiterId=current_user.id,
        shortlisted=True
    ).all()

    return render_template("shortlisted_applicants.html", posting=posting, applicants=shortlisted_applicants)


@app.route('/shortlisted', methods=['GET'])
@login_required
def view_all_shortlisted():
    """
    Fetch and display all shortlisted applicants for all job postings of the recruiter.
    """
    if not current_user.is_recruiter:
        flash("Unauthorized access! Only recruiters can view this page.", "danger")
        return redirect(url_for('home'))

    # Fetch all job postings for the current recruiter
    job_postings = Recruiter_Postings.query.filter_by(recruiterId=current_user.id).all()

    # Create a dictionary to group shortlisted applicants by job postings
    shortlisted_by_posting = {}
    for posting in job_postings:
        shortlisted_by_posting[posting] = PostingApplications.query.filter_by(
            postingId=posting.postingId,
            recruiterId=current_user.id,
            shortlisted=True
        ).all()

    return render_template(
        "shortlisted_applicants.html",
        shortlisted_by_posting=shortlisted_by_posting
    )


@app.route('/shortlist/<int:posting_id>/<int:applicant_id>', methods=['POST'])
@login_required
def toggle_shortlist(posting_id, applicant_id):
    """
    Toggle the shortlisted status of an applicant for a specific job posting.
    """
    application = PostingApplications.query.filter_by(
        postingId=posting_id,
        recruiterId=current_user.id,
        applicantId=applicant_id
    ).first_or_404()

    # Toggle shortlist status
    application.shortlisted = not application.shortlisted
    db.session.commit()

    # Add a flash message for feedback
    flash(
        f"Applicant {'shortlisted' if application.shortlisted else 'unshortlisted'} successfully!",
        "success"
    )

    # Redirect back to the referring page
    return redirect(request.referrer)

@app.route('/search_candidates', methods=['GET', 'POST'])
@login_required
def search_candidates():
    if not current_user.is_recruiter:
        flash("Unauthorized access! Only recruiters can access this page.", "danger")
        return redirect(url_for('home'))

    job_experiences = []
    if request.method == 'POST':
        # Get search type (role or skills) and search query
        search_type = request.form.get('search_type')
        search_query = request.form.get('search_query', '').strip()

        # Base query: Fetch job experiences with related user information
        query = db.session.query(JobExperience, User).join(User).filter(User.is_recruiter == False)

        # Apply filters based on the search type
        if search_query:
            if search_type == 'role':
                query = query.filter(JobExperience.job_title.ilike(f"%{search_query}%"))
            elif search_type == 'skills':
                query = query.filter(JobExperience.skills.ilike(f"%{search_query}%"))

        # Execute query
        job_experiences = query.all()

    return render_template('search_candidates.html', job_experiences=job_experiences)

@app.route("/download_resume/<int:user_id>", methods=["GET"])
@login_required
def download_resume(user_id):
    """Allow users to download their uploaded resume."""
    user = User.query.get_or_404(user_id)
    
    if not user.resume_path:
        flash("Resume not found for this user.", "danger")
        return redirect(url_for("account"))

    return send_from_directory(
        directory=os.path.dirname(user.resume_path),
        path=os.path.basename(user.resume_path),
        as_attachment=True,
    )
@app.route("/upload_resume", methods=["POST"])
@login_required
def upload_resume():
    if 'resume' not in request.files:
        flash("No file part", "danger")
        return redirect(url_for("account"))

    file = request.files['resume']
    if file.filename == '':
        flash("No selected file", "danger")
        return redirect(url_for("account"))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        current_user.resume_path = filepath
        db.session.commit()

        flash("Resume uploaded successfully!", "success")
        return redirect(url_for("account"))

    flash("Invalid file type!", "danger")
    return redirect(url_for("account"))

@app.route("/profile", methods=["POST"])
@login_required
def profile():
    username = request.form.get("username")

    if len(username) < 2:
        flash("Username must be at least 2 characters long", "danger")
        return render_template("profile.html"), 400  

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        flash("Username already taken", "danger")
        return render_template("profile.html"), 409  

    if ";" in username or "DROP" in username:
        flash("Invalid characters in username", "danger")
        return render_template("profile.html"), 400  

    current_user.username = username
    db.session.commit()

    flash("Profile updated successfully!", "success")
    return redirect(url_for("profile"))
