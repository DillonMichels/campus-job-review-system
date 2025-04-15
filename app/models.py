from app import db, login_manager
from flask_login import UserMixin
import pyotp  # For OTP secret generation

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Reviews(db.Model):
    """Model which stores the information of the reviews submitted"""

    id = db.Column(db.Integer, primary_key=True)
    department = db.Column(db.String(64), index=True, nullable=False)
    locations = db.Column(db.String(120), index=True, nullable=False)
    job_title = db.Column(db.String(64), index=True, nullable=False)
    job_description = db.Column(db.String(120), index=True, nullable=False)
    hourly_pay = db.Column(db.String(10), nullable=False)
    benefits = db.Column(db.String(120), index=True, nullable=False)
    review = db.Column(db.String(120), index=True, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    recommendation = db.Column(db.Integer, nullable=False)
    upvotes = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    is_anonymous = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Review {self.id} - {self.job_title}>"


class Vacancies(db.Model):
    """Model which stores the information of the reviews submitted"""

    vacancyId = db.Column(db.Integer, primary_key=True)
    jobTitle = db.Column(db.String(500), index=True, nullable=False)
    jobDescription = db.Column(db.String(1000), index=True, nullable=False)
    jobLocation = db.Column(db.String(500), index=True, nullable=False)
    jobPayRate = db.Column(db.String(120), index=True, nullable=False)
    maxHoursAllowed = db.Column(db.Integer, nullable=False)

    def __init__(self, jobTitle, jobDescription, jobLocation, jobPayRate, maxHoursAllowed):
        self.jobTitle = jobTitle
        self.jobDescription = jobDescription
        self.jobLocation = jobLocation
        self.jobPayRate = jobPayRate
        self.maxHoursAllowed = maxHoursAllowed

    def __repr__(self):
        return f"<Vacancy {self.vacancyId} - {self.jobTitle}>"


class User(db.Model, UserMixin):
    """Model to store user information"""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default="default.jpg")
    password = db.Column(db.String(60), nullable=False)
    is_recruiter = db.Column(db.Boolean, default=False)
    resume_path = db.Column(db.String(255), nullable=True)

    # New fields for two-factor authentication
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(16))

    # Relationships
    reviews = db.relationship("Reviews", backref="author", lazy=True)

    def generate_otp_secret(self):
        """
        Generates a new OTP secret using pyotp and assigns it to the user.
        Returns the generated secret.
        """
        self.two_factor_secret = pyotp.random_base32()
        return self.two_factor_secret

    def get_totp_uri(self):
        """
        Generates a TOTP URI for use with Google Authenticator.
        """
        app_name = "CampusJobReview"  
        return f'otpauth://totp/{app_name}:{self.username}?secret={self.two_factor_secret}&issuer={app_name}'

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"


class JobApplication(db.Model):
    """Model to store information about job applications"""

    id = db.Column(db.Integer, primary_key=True)
    job_link = db.Column(db.String(255), nullable=False)
    applied_on = db.Column(db.Date, nullable=False)
    last_update_on = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    resume_path = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<JobApplication {self.id} - {self.status}>"


class Recruiter_Postings(db.Model):
    """Model which stores the information of the postings added by recruiter"""

    __tablename__ = "recruiter_postings"
    postingId = db.Column(db.Integer, primary_key=True)
    recruiterId = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    jobTitle = db.Column(db.String(500), index=True, nullable=False)
    jobDescription = db.Column(db.String(1000), index=True, nullable=False)
    jobLink = db.Column(db.String(1000), index=True, nullable=False)
    jobLocation = db.Column(db.String(500), index=True, nullable=False)
    jobPayRate = db.Column(db.String(120), index=True, nullable=False)
    maxHoursAllowed = db.Column(db.Integer, nullable=False)

    # Relationships
    recruiter = db.relationship("User", backref="recruiter_postings")

    def __repr__(self):
        return f"<RecruiterPosting {self.postingId} - {self.jobTitle}>"


class PostingApplications(db.Model):
    """Model which stores the information of all applications for each recruiter posting."""
    
    __tablename__ = "posting_applications"
    postingId = db.Column(db.Integer, db.ForeignKey("recruiter_postings.postingId"), primary_key=True)
    recruiterId = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
    applicantId = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
    shortlisted = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships
    recruiter = db.relationship("User", foreign_keys=[recruiterId], backref="reviewed_applications")
    applicant = db.relationship("User", foreign_keys=[applicantId], backref="applied_applications")
    job_posting = db.relationship("Recruiter_Postings", foreign_keys=[postingId], backref="applications")

    def __repr__(self):
        return (
            f"<PostingApplication Posting ID: {self.postingId}, "
            f"Recruiter ID: {self.recruiterId}, Applicant ID: {self.applicantId}, "
            f"Shortlisted: {self.shortlisted}>"
        )


class JobExperience(db.Model):
    """Model to store job experiences for users"""

    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String(120), nullable=False)
    company_name = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120), nullable=False)
    duration = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    skills = db.Column(db.Text, nullable=True)
    username = db.Column(db.String(20), db.ForeignKey("user.username"), nullable=False)

    def __repr__(self):
        return f"<JobExperience {self.job_title} at {self.company_name} | Skills: {self.skills}>"


class Meetings(db.Model):
    """Model to store meeting information"""

    id = db.Column(db.Integer, primary_key=True)
    recruiter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    applicant_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    meeting_time = db.Column(db.DateTime, nullable=False)
    posting_id = db.Column(db.Integer, db.ForeignKey("recruiter_postings.postingId"), nullable=True)

    # Relationships
    recruiter = db.relationship("User", foreign_keys=[recruiter_id], backref="recruiter_meetings")
    applicant = db.relationship("User", foreign_keys=[applicant_id], backref="applicant_meetings")
    job_posting = db.relationship("Recruiter_Postings", backref="meetings")

    def __repr__(self):
        return f"<Meeting {self.id} | Time: {self.meeting_time}>"
