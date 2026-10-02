from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


# =========================
# APP CONFIGURATION
# =========================

app = Flask(__name__)

app.config['SECRET_KEY'] = "asset-management-secret-key"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)


# =========================
# LOGIN CONFIGURATION
# =========================

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "login"


@login_manager.unauthorized_handler
def unauthorized():

    return redirect('/login')



# =========================
# USER MODEL
# RBAC
# =========================

class User(db.Model, UserMixin):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(200),
        nullable=False
    )

    role = db.Column(
        db.String(50),
        default="Employee"
    )



@login_manager.user_loader
def load_user(user_id):

    return db.session.get(
        User,
        int(user_id)
    )



# =========================
# ASSET MODEL
# =========================

class Asset(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    category = db.Column(
        db.String(50)
    )

    location = db.Column(
        db.String(100)
    )

    status = db.Column(
        db.String(50)
    )

# =========================
# MAINTENANCE MODEL
# =========================

class Maintenance(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )


    asset_id = db.Column(
        db.Integer,
        db.ForeignKey('asset.id')
    )


    issue = db.Column(
        db.String(200),
        nullable=False
    )


    date = db.Column(
        db.Date,
        nullable=False
    )


    cost = db.Column(
        db.Float,
        default=0
    )


    status = db.Column(
        db.String(50),
        default="Pending"
    )


    asset = db.relationship(
        'Asset',
        backref='maintenance'
    )
    # =========================
# REGISTER USER
# =========================

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']

        existing_user = User.query.filter_by(
            username=username
        ).first()


        if existing_user:
            return "Username already exists"


        password = generate_password_hash(
            request.form['password']
        )

        role = request.form['role']


        user = User(
            username=username,
            password=password,
            role=role
        )


        db.session.add(user)
        db.session.commit()


        return redirect('/login')


    return render_template(
        'register.html'
    )
# =========================
# LOGIN
# =========================

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(
            username=username
        ).first()

        if user and check_password_hash(
            user.password,
            password
        ):

            login_user(user)

            if user.role == "Admin":
                return redirect('/admin_dashboard')

            elif user.role == "Engineer":
                return redirect('/engineer_dashboard')

            else:
                return redirect('/employee_dashboard')

        else:
            return "Invalid Username or Password"

    return render_template('login.html')






# =========================
# LOGOUT
# =========================

@app.route('/logout')
@login_required
def logout():

    logout_user()

    return redirect('/login')



# =========================
# DASHBOARD
# =========================

@app.route('/dashboard')
@login_required
def index():

    search = request.args.get('search')


    if search:

        assets = Asset.query.filter(
            Asset.name.contains(search)
        ).all()

    else:

        assets = Asset.query.all()



    total_assets = Asset.query.count()


    active_assets = Asset.query.filter_by(
        status="Active"
    ).count()


    maintenance_assets = Asset.query.filter_by(
        status="Under Maintenance"
    ).count()


    inactive_assets = Asset.query.filter_by(
        status="Inactive"
    ).count()



    return render_template(
        'index.html',
        assets=assets,
        total_assets=total_assets,
        active_assets=active_assets,
        maintenance_assets=maintenance_assets,
        inactive_assets=inactive_assets
    )



# =========================
# ADD ASSET
# ADMIN ONLY
# =========================

@app.route('/add', methods=['GET','POST'])
@login_required
def add_asset():


    if current_user.role != "Admin":

        return "Access Denied"



    if request.method == 'POST':


        asset = Asset(

            name=request.form['name'],

            category=request.form['category'],

            location=request.form['location'],

            status=request.form['status']

        )


        db.session.add(asset)

        db.session.commit()


        return redirect('/admin_dashboard')



    return render_template(
        'add_asset.html'
    )



# =========================
# EDIT ASSET
# ADMIN ONLY
# =========================

@app.route('/edit/<int:id>', methods=['GET','POST'])
@login_required
def edit_asset(id):


    if current_user.role != "Admin":

        return "Access Denied"



    asset = Asset.query.get_or_404(id)



    if request.method == 'POST':


        asset.name = request.form['name']

        asset.category = request.form['category']

        asset.location = request.form['location']

        asset.status = request.form['status']


        db.session.commit()


        return redirect('/admin_dashboard')



    return render_template(
        'edit_asset.html',
        asset=asset
    )



# =========================
# DELETE ASSET
# ADMIN ONLY
# =========================

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_asset(id):


    if current_user.role != "Admin":

        return "Access Denied"



    asset = Asset.query.get_or_404(id)


    db.session.delete(asset)

    db.session.commit()


    return redirect('/admin_dashboard')



# =========================
# ADD MAINTENANCE
# ENGINEER + ADMIN
# =========================

@app.route('/maintenance/<int:asset_id>', methods=['GET','POST'])
@login_required
def add_maintenance(asset_id):


    if current_user.role not in ["Admin","Engineer"]:

        return "Access Denied"



    asset = Asset.query.get_or_404(
        asset_id
    )



    if request.method == 'POST':


        maintenance = Maintenance(

            asset_id=asset.id,

            issue=request.form['issue'],

            date=datetime.strptime(
                request.form['date'],
                '%Y-%m-%d'
            ).date(),


            cost=float(
                request.form['cost']
            ),


            status=request.form['status']

        )



        db.session.add(maintenance)

        db.session.commit()



        return redirect(
            '/maintenance_history'
        )



    return render_template(
        'maintenance.html',
        asset=asset
    )
# =========================
# HOME PAGE
# =========================

@app.route('/')
def home():
    return render_template('home.html')

# =========================
# MAINTENANCE HISTORY
# =========================

@app.route('/maintenance_history')
@login_required
def maintenance_history():

    records = Maintenance.query.all()


    return render_template(
        'maintenance_history.html',
        records=records
    )


@app.route('/admin_dashboard')
@login_required
def admin_dashboard():

    if current_user.role != "Admin":
        return "Access Denied"

    search = request.args.get('search')

    if search:

        assets = Asset.query.filter(
            Asset.name.contains(search)
        ).all()

    else:

        assets = Asset.query.all()

    total_assets = Asset.query.count()

    active_assets = Asset.query.filter_by(
        status="Active"
    ).count()

    maintenance_assets = Asset.query.filter_by(
        status="Under Maintenance"
    ).count()

    inactive_assets = Asset.query.filter_by(
        status="Inactive"
    ).count()

    return render_template(
        'admin_dashboard.html',
        assets=assets,
        total_assets=total_assets,
        active_assets=active_assets,
        maintenance_assets=maintenance_assets,
        inactive_assets=inactive_assets
    )
    # =========================
# ENGINEER DASHBOARD
# =========================

@app.route('/engineer_dashboard')
@login_required
def engineer_dashboard():

    if current_user.role != "Engineer":
        return "Access Denied"

    records = Maintenance.query.all()

    return render_template(
        'engineer_dashboard.html',
        records=records
    )
    # =========================
# EMPLOYEE DASHBOARD
# =========================

@app.route('/employee_dashboard')
@login_required
def employee_dashboard():

    if current_user.role != "Employee":
        return "Access Denied"

    assets = Asset.query.all()

    return render_template(
        'employee_dashboard.html',
        assets=assets
    )
# =========================
# CREATE DATABASE
# RUN APP
# =========================

if __name__ == '__main__':


    with app.app_context():

        db.create_all()


    app.run(
        debug=True
    )