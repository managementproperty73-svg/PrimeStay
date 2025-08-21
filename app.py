
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, IntegerField, FloatField, TextAreaField, SubmitField, MultipleFileField, SelectField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {"png","jpg","jpeg","webp","gif"}

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "site.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET","dev-secret")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(os.path.join(BASE_DIR, UPLOAD_FOLDER), exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "admin_login"

# --------------- Models ---------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False, default="Admin")
    password_hash = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=True)

    def set_password(self, pw): self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(80), nullable=False)
    state = db.Column(db.String(40), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    for_rent = db.Column(db.Boolean, default=True)
    beds = db.Column(db.Integer, default=1)
    baths = db.Column(db.Float, default=1.0)
    sqft = db.Column(db.Integer, default=500)
    description = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    images = db.relationship("Image", backref="property", cascade="all,delete", lazy=True)

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    filename = db.Column(db.String(300), nullable=False)

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    move_in = db.Column(db.String(40), nullable=True)
    message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Inquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --------------- Forms ---------------
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign in")

class PropertyForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=150)])
    address = StringField("Address", validators=[DataRequired()])
    city = StringField("City", validators=[DataRequired()])
    state = StringField("State", validators=[DataRequired()])
    price = IntegerField("Price", validators=[DataRequired(), NumberRange(min=0)])
    mode = SelectField("Type", choices=[("rent","For Rent"),("sale","For Sale")])
    beds = IntegerField("Beds", validators=[Optional()])
    baths = FloatField("Baths", validators=[Optional()])
    sqft = IntegerField("Square Feet", validators=[Optional()])
    description = TextAreaField("Description", validators=[Optional(), Length(max=5000)])
    image_files = MultipleFileField("Upload Images (you can select multiple)")
    submit = SubmitField("Save")

# --------------- Auth helpers ---------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def seed_admin():
    if User.query.count() == 0:
        email = os.environ.get("ADMIN_EMAIL","admin@example.com")
        password = os.environ.get("ADMIN_PASSWORD","changeme123")
        u = User(email=email, name="Admin")
        u.set_password(password)
        db.session.add(u)
        db.session.commit()

def allowed_file(filename):
    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED_EXTENSIONS

def save_images(files, property_id):
    saved = []
    dest_dir = os.path.join(app.config["UPLOAD_FOLDER"], str(property_id))
    os.makedirs(dest_dir, exist_ok=True)
    for f in files:
        if not f or f.filename == "": 
            continue
        if allowed_file(f.filename):
            filename = secure_filename(f.filename)
            # ensure unique
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(os.path.join(dest_dir, filename)):
                filename = f"{base}_{counter}{ext}"
                counter += 1
            f.save(os.path.join(dest_dir, filename))
            img = Image(property_id=property_id, filename=os.path.join(str(property_id), filename))
            db.session.add(img)
            saved.append(filename)
    db.session.commit()
    return saved

# --------------- Public routes ---------------
@app.route("/")
def home():
    q = request.args.get("q","").strip()
    city = request.args.get("city","").strip()
    mode = request.args.get("mode","all")
    props = Property.query.order_by(Property.created_at.desc())
    if q:
        like = f"%{q}%"
        props = props.filter((Property.title.ilike(like)) | (Property.address.ilike(like)) | (Property.city.ilike(like)))
    if city:
        props = props.filter(Property.city.ilike(f"%{city}%"))
    if mode == "rent":
        props = props.filter(Property.for_rent == True)
    elif mode == "sale":
        props = props.filter(Property.for_rent == False)
    props = props.limit(6).all()
    return render_template("index.html", properties=props)

@app.route("/properties")
def properties():
    q = request.args.get("q","").strip()
    city = request.args.get("city","").strip()
    mode = request.args.get("mode","all")
    props = Property.query.order_by(Property.created_at.desc())
    if q:
        like = f"%{q}%"
        props = props.filter((Property.title.ilike(like)) | (Property.address.ilike(like)) | (Property.city.ilike(like)))
    if city:
        props = props.filter(Property.city.ilike(f"%{city}%"))
    if mode == "rent":
        props = props.filter(Property.for_rent == True)
    elif mode == "sale":
        props = props.filter(Property.for_rent == False)
    props = props.all()
    return render_template("properties.html", properties=props, mode=mode)

@app.route("/properties/<int:prop_id>")
def property_detail(prop_id):
    prop = Property.query.get_or_404(prop_id)
    return render_template("property_detail.html", prop=prop)

@app.route("/apply/<int:prop_id>", methods=["GET","POST"])
def apply(prop_id):
    prop = Property.query.get_or_404(prop_id)
    if request.method == "POST":
        full_name = request.form.get("full_name","").strip()
        email = request.form.get("email","").strip()
        phone = request.form.get("phone","").strip()
        move_in = request.form.get("move_in","").strip()
        message = request.form.get("message","").strip()
        if not (full_name and email and phone):
            flash("Please complete all required fields.", "danger")
        else:
            app_entry = Application(property_id=prop.id, full_name=full_name, email=email, phone=phone, move_in=move_in, message=message)
            db.session.add(app_entry)
            db.session.commit()
            flash("Application submitted. We'll be in touch shortly.", "success")
            return redirect(url_for("property_detail", prop_id=prop.id))
    return render_template("apply.html", prop=prop)

@app.route("/contact", methods=["GET","POST"])
def contact():
    if request.method == "POST":
        full_name = request.form.get("full_name","").strip()
        email = request.form.get("email","").strip()
        phone = request.form.get("phone","").strip()
        subject = request.form.get("subject","").strip()
        message = request.form.get("message","").strip()
        if not (full_name and email and subject and message):
            flash("Please complete all required fields.", "danger")
        else:
            db.session.add(Inquiry(full_name=full_name, email=email, phone=phone, subject=subject, message=message))
            db.session.commit()
            flash("Thanks! We'll reply shortly.", "success")
            return redirect(url_for("contact"))
    return render_template("contact.html")

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# --------------- Admin routes ---------------
@app.route("/admin/login", methods=["GET","POST"])
def admin_login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data) and user.active:
            login_user(user)
            return redirect(url_for("admin_dashboard"))
        flash("Invalid credentials.", "danger")
    return render_template("admin/login.html", form=form)

@app.route("/admin/logout")
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for("admin_login"))

@app.route("/admin")
@login_required
def admin_dashboard():
    props = Property.query.order_by(Property.created_at.desc()).all()
    return render_template("admin/dashboard.html", properties=props)

@app.route("/admin/new", methods=["GET","POST"])
@login_required
def admin_new():
    form = PropertyForm()
    if form.validate_on_submit():
        p = Property(
            title=form.title.data.strip(),
            address=form.address.data.strip(),
            city=form.city.data.strip(),
            state=form.state.data.strip(),
            price=form.price.data,
            for_rent=True if form.mode.data=="rent" else False,
            beds=form.beds.data or 1,
            baths=form.baths.data or 1.0,
            sqft=form.sqft.data or 500,
            description=form.description.data or ""
        )
        db.session.add(p)
        db.session.commit()
        save_images(form.image_files.data, p.id)
        flash("Property created.", "success")
        return redirect(url_for("admin_dashboard"))
    return render_template("admin/new.html", form=form)

@app.route("/admin/<int:prop_id>/edit", methods=["GET","POST"])
@login_required
def admin_edit(prop_id):
    prop = Property.query.get_or_404(prop_id)
    form = PropertyForm(
        title=prop.title, address=prop.address, city=prop.city, state=prop.state, price=prop.price,
        mode="rent" if prop.for_rent else "sale", beds=prop.beds, baths=prop.baths, sqft=prop.sqft, description=prop.description
    )
    if form.validate_on_submit():
        prop.title = form.title.data.strip()
        prop.address = form.address.data.strip()
        prop.city = form.city.data.strip()
        prop.state = form.state.data.strip()
        prop.price = form.price.data
        prop.for_rent = True if form.mode.data=="rent" else False
        prop.beds = form.beds.data or 1
        prop.baths = form.baths.data or 1.0
        prop.sqft = form.sqft.data or 500
        prop.description = form.description.data or ""
        db.session.commit()
        save_images(form.image_files.data, prop.id)
        flash("Property updated.", "success")
        return redirect(url_for("admin_dashboard"))
    return render_template("admin/edit.html", form=form, prop=prop)

@app.route("/admin/<int:prop_id>/delete", methods=["POST"])
@login_required
def admin_delete(prop_id):
    prop = Property.query.get_or_404(prop_id)
    db.session.delete(prop)
    db.session.commit()
    flash("Property deleted.", "success")
    return redirect(url_for("admin_dashboard"))

# --------------- Bootstrap DB ---------------
with app.app_context():
    db.create_all()
    seed_admin()
    if Property.query.count() == 0:
        sample = Property(title="Modern Downtown Loft", address="123 Market St, Unit 504", city="Los Angeles", state="CA",
                          price=2950, for_rent=True, beds=1, baths=1.0, sqft=740,
                          description="Sunny loft with floor-to-ceiling windows, polished concrete floors, and in-unit laundry.")
        db.session.add(sample); db.session.commit()

if __name__ == "__main__":
    app.run(debug=True)
