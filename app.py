from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = "technova_secret"
DATABASE = "placement.db"

UPLOAD_FOLDER = "static/resumes"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)



# =====================================================
# ADMIN LOGIN (SEPARATE PAGE)
# =====================================================
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM users
            WHERE role='admin' AND username=?
        """, (username,))

        admin = cursor.fetchone()

        if admin and check_password_hash(admin["password"], password):

            if admin["is_blacklisted"] == 1:
                conn.close()
                return render_template("admin_login.html",
                                       error="Admin Account Blacklisted")

            session["user_id"] = admin["id"]
            session["role"] = "admin"
            session["is_superuser"] = 1

            conn.close()
            return redirect(url_for("dashboard"))

        conn.close()
        return render_template("admin_login.html",
                               error="Invalid Admin Credentials")

    return render_template("admin_login.html")


# =====================================================
# DATABASE CONNECTION
# =====================================================
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# =====================================================
# DATABASE INIT
# =====================================================
def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT,
            username TEXT UNIQUE,
            password TEXT,
            is_superuser INTEGER DEFAULT 0,
            is_blacklisted INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            full_name TEXT,
            roll_no TEXT,
            email TEXT,
            phone TEXT,
            address TEXT,
            resume TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            company_name TEXT,
            company_id TEXT UNIQUE,
            email TEXT,
            contact_number TEXT,
            hr_email TEXT,
            company_website TEXT,
            approval_status TEXT DEFAULT 'Pending'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS placement_drives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            job_title TEXT,
            job_description TEXT,
            eligibility TEXT,
            deadline TEXT,
            drive_code TEXT,
            status TEXT DEFAULT 'Pending'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            drive_id INTEGER,
            application_date TEXT,
            status TEXT DEFAULT 'Applied',
            UNIQUE(student_id, drive_id)
        )
    """)
    # -----------------------------
    # ADD NEW COLUMNS IF NOT EXIST
    # -----------------------------
    try:
        cursor.execute("ALTER TABLE applications ADD COLUMN application_id TEXT")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE applications ADD COLUMN applied_date TEXT")
    except:
        pass

    

    cursor.execute("SELECT * FROM users WHERE role='admin'")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO users (role, username, password, is_superuser)
            VALUES (?, ?, ?, ?)
        """, ("admin", "admin",
              generate_password_hash("Admin@123"), 1))

    conn.commit()
    conn.close()


init_db()


# =====================================================
# LOGIN
# =====================================================
@app.route("/", methods=["GET", "POST"])
def login():

    selected_role = request.args.get("role", "student")
    open_modal = request.args.get("open")

    if request.method == "POST":

        role = request.form.get("role")
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM users
            WHERE role=? AND username=?
        """, (role, username))

        user = cursor.fetchone()

        if user and check_password_hash(user["password"], password):

            if user["is_blacklisted"] == 1:
                conn.close()
                return render_template(
                    "login.html",
                    role=role,
                    error="Account Blacklisted",
                    open_modal=open_modal
                )

            if role == "company":

                cursor.execute("""
                    SELECT approval_status
                    FROM companies
                    WHERE user_id=?
                """, (user["id"],))

                company = cursor.fetchone()

                # If company record not found
                if not company:
                    conn.close()
                    return render_template(
                        "login.html",
                        role=role,
                        error="Company profile not found",
                        open_modal=open_modal
                    )

                # Pending companies cannot login
                if company["approval_status"] == "Pending":
                    conn.close()
                    return render_template(
                        "login.html",
                        role=role,
                        error="Company Not Approved Yet",
                        open_modal=open_modal
                    )

            session["user_id"] = user["id"]
            session["role"] = role
            session["is_superuser"] = user["is_superuser"]

            conn.close()
            return redirect(url_for("dashboard"))

        conn.close()
        return render_template(
            "login.html",
            role=role,
            error="Invalid Credentials",
            open_modal=open_modal
        )

    return render_template(
        "login.html",
        role=selected_role,
        open_modal=open_modal
    )

# =====================================================
# REGISTER
# =====================================================
@app.route("/register", methods=["POST"])
def register():

    role = request.form.get("role")
    password = generate_password_hash(request.form.get("password"))

    conn = get_db()
    cursor = conn.cursor()

    try:

        if role == "student":

            email = request.form.get("email")

            cursor.execute("""
                INSERT INTO users (role, username, password)
                VALUES (?, ?, ?)
            """, ("student", email, password))

            user_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO students
                (user_id, full_name, roll_no, email, phone, address)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                request.form.get("full_name"),
                request.form.get("roll_no"),
                email,
                request.form.get("phone"),
                request.form.get("address")
            ))

        elif role == "company":

            company_id = request.form.get("company_id")

            cursor.execute("""
                INSERT INTO users (role, username, password)
                VALUES (?, ?, ?)
            """, ("company", company_id, password))

            user_id = cursor.lastrowid

            hr_email = request.form.get("hr_email")
            company_website = request.form.get("company_website")

            cursor.execute("""
                INSERT INTO companies
                (user_id, company_name, company_id, email, contact_number, hr_email, company_website)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                request.form.get("company_name"),
                company_id,
                request.form.get("company_email"),
                request.form.get("contact_number"),
                hr_email,
                company_website
            ))

        conn.commit()

    except:
        conn.close()
        return render_template("login.html", error="User already exists")

    conn.close()
    return redirect(url_for("login"))
# =====================================================
# DASHBOARD ROUTER
# =====================================================
@app.route("/dashboard")
def dashboard():
    if "role" not in session:
        return redirect(url_for("login"))

    if session["role"] == "admin":
        return admin_dashboard()
    if session["role"] == "student":
        return student_dashboard()
    if session["role"] == "company":
        return company_dashboard()


# =====================================================
# ADMIN DASHBOARD + SEARCH + BLACKLIST
# =====================================================
def admin_dashboard():

    conn = get_db()
    cursor = conn.cursor()
   
    

    # -----------------------------
    # SEARCH INPUTS
    # -----------------------------
    search_student = request.args.get("search_student")
    search_company = request.args.get("search_company")
    search_application = request.args.get("search_application")

    students = []
    companies = []

    # -----------------------------
    # STUDENT SEARCH
    # -----------------------------
    if search_student:
        cursor.execute("""
            SELECT s.full_name, s.roll_no, u.id, u.is_blacklisted, s.resume
            FROM students s
            JOIN users u ON s.user_id = u.id
            WHERE s.full_name LIKE ?
            OR s.roll_no LIKE ?
        """, ('%' + search_student + '%',
              '%' + search_student + '%'))

        students = cursor.fetchall()

    # -----------------------------
    # COMPANY SEARCH
    # -----------------------------
    if search_company:
        cursor.execute("""
            SELECT company_name, company_id, approval_status
            FROM companies
            WHERE company_name LIKE ?
            OR company_id LIKE ?
        """, ('%' + search_company + '%',
              '%' + search_company + '%'))

        companies = cursor.fetchall()

    # -----------------------------
    # DASHBOARD COUNTS
    # -----------------------------
    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM companies")
    total_companies = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM placement_drives")
    total_drives = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM applications")
    total_applications = cursor.fetchone()[0]

    # -----------------------------
    # PLACEMENT ANALYTICS
    # -----------------------------
    # -----------------------------
# APPLICATIONS PER COMPANY GRAPH
# -----------------------------
    search_app = request.args.get("search_app")

    query = """
    SELECT a.application_id,
        s.full_name,
        s.roll_no,
        c.company_name,
        pd.drive_code,
        a.applied_date,
        s.resume,
        a.status
    FROM applications a
    JOIN students s ON a.student_id = s.id
    JOIN placement_drives pd ON a.drive_id = pd.id
    JOIN companies c ON pd.company_id = c.id
    """

    params = []

    if search_app:
        query += """
        WHERE s.full_name LIKE ?
        OR s.roll_no LIKE ?
        OR c.company_name LIKE ?
        OR pd.drive_code LIKE ?
        """
        value = "%" + search_app + "%"
        params = [value, value, value, value]

    cursor.execute(query, params)
    applications_per_company = cursor.fetchall()

    # -----------------------------
    # APPLICATIONS PER COMPANY TABLE
    # -----------------------------

    if search_application:
            cursor.execute("""
                SELECT 
                a.application_id,
                s.full_name,
                s.roll_no,
                c.company_name,
                pd.drive_code,
                a.applied_date,
                s.resume,
                a.status
                FROM applications a
                JOIN students s ON a.student_id = s.id
                JOIN placement_drives pd ON a.drive_id = pd.id
                JOIN companies c ON pd.company_id = c.id
                WHERE s.full_name LIKE ?
                OR s.roll_no LIKE ?
                OR c.company_name LIKE ?
                OR pd.drive_code LIKE ?
                OR a.status LIKE ?
                """, (
                '%' + search_application + '%',
                '%' + search_application + '%',
                '%' + search_application + '%',
                '%' + search_application + '%',
                '%' + search_application + '%'
            ))

    else:
        cursor.execute("""
            SELECT 
            a.application_id,
            s.full_name,
            s.roll_no,
            c.company_name,
            pd.drive_code,
            a.applied_date,
            s.resume,
            a.status
            FROM applications a
            JOIN students s ON a.student_id = s.id
            JOIN placement_drives pd ON a.drive_id = pd.id
            JOIN companies c ON pd.company_id = c.id
        """)

    applications_per_company = cursor.fetchall()

# -----------------------------
# PENDING COMPANY APPROVALS
# -----------------------------
    cursor.execute("""
    SELECT id, company_name, company_id, approval_status,
    contact_number, email, hr_email, company_website
    FROM companies
    WHERE approval_status='Pending'
    """)
    pending_companies = cursor.fetchall()


    # -----------------------------
    # COMPANY HISTORY
    # -----------------------------
    cursor.execute("""
        SELECT id, company_name, company_id, approval_status,
        contact_number, email, hr_email, company_website
        FROM companies
        WHERE approval_status != 'Pending'
        """)
    company_history = cursor.fetchall()

# -----------------------------
# PENDING DRIVE APPROVALS
# -----------------------------
    cursor.execute("""
    SELECT pd.id,
        pd.drive_code,
        c.company_name,
        pd.job_title,
        pd.job_description,
        pd.status
    FROM placement_drives pd
    JOIN companies c ON pd.company_id = c.id
    WHERE pd.status IN ('Pending','Approved','Closed')
    """)

    pending_drives = cursor.fetchall()

  
    # -----------------------------
    # ALL STUDENTS LIST
    # -----------------------------
    cursor.execute("""
        SELECT s.id, s.full_name, s.roll_no, s.email, s.resume, u.is_blacklisted, u.id
        FROM students s
        JOIN users u ON s.user_id = u.id
    """)

    all_students = cursor.fetchall()
      
    # Students placed
    cursor.execute("""
    SELECT COUNT(DISTINCT student_id)
    FROM applications
    WHERE status='Selected'
    """)
    placed_students = cursor.fetchone()[0]

    # Placement %
    placement_percentage = 0
    if total_students > 0:
        placement_percentage = round((placed_students / total_students) * 100, 2)

    # Top hiring companies
    cursor.execute("""
    SELECT c.company_name, COUNT(a.id)
    FROM applications a
    JOIN placement_drives pd ON a.drive_id = pd.id
    JOIN companies c ON pd.company_id = c.id
    WHERE a.status='Selected'
    GROUP BY c.company_name
    ORDER BY COUNT(a.id) DESC
    LIMIT 5
    """)
    top_companies = cursor.fetchall()

    # Applications per company (for graph)
    cursor.execute("""
    SELECT c.company_name, COUNT(a.id)
    FROM applications a
    JOIN placement_drives pd ON a.drive_id = pd.id
    JOIN companies c ON pd.company_id = c.id
    GROUP BY c.company_name
""")

    data = cursor.fetchall()

    company_names = [row[0] for row in data]
    application_counts = [row[1] for row in data]

    return render_template(
    "admin_dashboard.html",
    total_students=total_students,
    total_companies=total_companies,
    total_drives=total_drives,
    total_applications=total_applications,
    pending_companies=pending_companies,
    pending_drives=pending_drives,
    students=students,
    companies=companies,
    all_students=all_students,
    placed_students=placed_students,
    placement_percentage=placement_percentage,
    top_companies=top_companies,
    company_names=company_names,
    application_counts=application_counts,
    company_history=company_history,
    applications_per_company=applications_per_company
)
      

# =====================================================
# APPROVAL ROUTES
# =====================================================
@app.route("/approve_company/<int:id>")
def approve_company(id):
    conn = get_db()
    conn.execute("UPDATE companies SET approval_status='Approved' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route("/reject_company/<int:id>")
def reject_company(id):
    conn = get_db()
    conn.execute("UPDATE companies SET approval_status='Rejected' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route("/approve_drive/<int:id>")
def approve_drive(id):
    conn = get_db()
    conn.execute("UPDATE placement_drives SET status='Approved' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route("/reject_drive/<int:id>")
def reject_drive(id):
    conn = get_db()
    conn.execute("UPDATE placement_drives SET status='Rejected' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route("/blacklist_user/<int:user_id>")
def blacklist_user(user_id):
    conn = get_db()
    conn.execute("UPDATE users SET is_blacklisted=1 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))

@app.route("/activate_user/<int:user_id>")
def activate_user(user_id):
    conn = get_db()
    conn.execute("UPDATE users SET is_blacklisted=0 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))
@app.route("/blacklist_company/<int:id>")
def blacklist_company(id):
    conn = get_db()
    conn.execute(
        "UPDATE companies SET approval_status='Blacklisted' WHERE id=?",
        (id,)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route("/activate_company/<int:id>")
def activate_company(id):
    conn = get_db()
    conn.execute(
        "UPDATE companies SET approval_status='Approved' WHERE id=?",
        (id,)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


# =====================================================
# STUDENT DASHBOARD
# =====================================================
def student_dashboard():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, resume FROM students WHERE user_id=?",
                   (session["user_id"],))
    student = cursor.fetchone()

    if not student:
        conn.close()
        return redirect(url_for("logout"))

    student_id = student["id"]
    resume_link = student["resume"]

    # Approved and NOT Closed drives
    cursor.execute("""
    SELECT pd.id,
    pd.drive_code,
    c.company_id,
    pd.deadline,
    c.company_name,
    pd.eligibility,
    pd.job_title,
    pd.status,
    pd.job_description
    FROM placement_drives pd
    JOIN companies c ON pd.company_id = c.id
    WHERE pd.status IN ('Approved','Closed')
    """)
    approved_drives = cursor.fetchall()

    # Applications with drive id
    
    cursor.execute("""
        SELECT a.application_id,
            pd.id,
            pd.drive_code,
            c.company_name,
            pd.job_title,
            a.applied_date,
            a.status
        FROM applications a
        JOIN placement_drives pd ON a.drive_id = pd.id
        JOIN companies c ON pd.company_id = c.id
        WHERE a.student_id=?
        """, (student_id,))
        
    applied_drives = cursor.fetchall()
    applied_ids = [row[1] for row in applied_drives]

    conn.close()

    return render_template("student_dashboard.html",
                           approved_drives=approved_drives,
                           applied_drives=applied_drives,
                           resume_link=resume_link,
                            applied_ids=applied_ids)



# =====================================================
# EDIT STUDENT PROFILE
# =====================================================
# =====================================================
# EDIT STUDENT PROFILE (WITH FILE UPLOAD)
# =====================================================
@app.route("/edit-profile", methods=["GET", "POST"])
def edit_profile():

    if session.get("role") != "student":
        return redirect(url_for("dashboard"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT full_name, phone, address, resume
        FROM students
        WHERE user_id=?
    """, (session["user_id"],))

    student = cursor.fetchone()

    if request.method == "POST":

        resume_file = request.files.get("resume")

        filename = student["resume"]  # keep old file by default

        if resume_file and resume_file.filename != "":
            filename = secure_filename(resume_file.filename)
            resume_file.save(
                os.path.join(app.config["UPLOAD_FOLDER"], filename)
            )

        cursor.execute("""
            UPDATE students
            SET full_name=?, phone=?, address=?, resume=?
            WHERE user_id=?
        """, (
            request.form.get("full_name"),
            request.form.get("phone"),
            request.form.get("address"),
            filename,
            session["user_id"]
        ))

        conn.commit()
        conn.close()
        return redirect(url_for("dashboard"))

    conn.close()
    return render_template("edit_profile.html", student=student)


# =====================================================
# COMPANY DASHBOARD
# =====================================================
def company_dashboard():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM companies WHERE user_id=?", (session["user_id"],))
    company = cursor.fetchone()

    if not company:
        conn.close()
        return redirect(url_for("dashboard"))

    company_id = company["id"]

    # Company drives with applicant count
    cursor.execute("""
        SELECT pd.id, pd.drive_code, pd.job_title, pd.status,
            COUNT(a.id)
        FROM placement_drives pd
        LEFT JOIN applications a ON pd.id = a.drive_id
        WHERE pd.company_id=?
        GROUP BY pd.id
    """, (company_id,))
    drives = cursor.fetchall()

    # Student applications + resume
    cursor.execute("""
    SELECT 
        a.id,
        a.application_id,
        s.full_name,
        s.roll_no,
        pd.drive_code,
        pd.job_title,
        a.applied_date,
        a.status,
        s.resume
    FROM applications a
    JOIN students s ON a.student_id = s.id
    JOIN placement_drives pd ON a.drive_id = pd.id
    WHERE pd.company_id=?
""", (company_id,))
    
    applications = cursor.fetchall()

    total_drives = len(drives)
    total_applicants = len(applications)

    conn.close()

    return render_template(
        "company_dashboard.html",
        company=company,
        drives=drives,
        applications=applications,
        total_drives=total_drives,
        total_applicants=total_applicants
    )


@app.route("/create-drive", methods=["GET", "POST"])
def create_drive():

    if session.get("role") != "company":
        return redirect(url_for("dashboard"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, approval_status, company_name
        FROM companies
        WHERE user_id=?
    """, (session["user_id"],))

    company = cursor.fetchone()

    if not company:
        conn.close()
        return redirect(url_for("dashboard"))

    if company["approval_status"] == "Blacklisted":
        conn.close()
        return render_template(
            "company_dashboard.html",
            error="Your company is blacklisted"
        )

    company_id = company["id"]
    company_name = company["company_name"]

    if request.method == "POST":

        job_title = request.form.get("job_title")
        job_description = request.form.get("job_description")
        eligibility = request.form.get("eligibility")
        deadline = request.form.get("deadline")

        # -----------------------------
        # GENERATE DRIVE ID
        # -----------------------------

        prefix = company_name[:2].upper()

        today = datetime.now().strftime("%d%m%Y")

        cursor.execute("""
        SELECT COUNT(*)
        FROM placement_drives
        WHERE company_id=?
        """, (company_id,))

        count = cursor.fetchone()[0] + 1

        serial = str(count).zfill(2)

        drive_code = f"{prefix}{today}-{serial}"

        # -----------------------------
        # INSERT DRIVE
        # -----------------------------

        cursor.execute("""
        INSERT INTO placement_drives
        (company_id, job_title, job_description, eligibility, deadline, drive_code)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            company_id,
            job_title,
            job_description,
            eligibility,
            deadline,
            drive_code
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    conn.close()
    return render_template("create_drive.html")

# =====================================================
# UPDATE APPLICATION STATUS (COMPANY ACTION)
# =====================================================
@app.route("/update-application/<int:id>/<status>")
def update_application(id, status):

    if session.get("role") != "company":
        return redirect(url_for("dashboard"))

    conn = get_db()
    conn.execute(
        "UPDATE applications SET status=? WHERE id=?",
        (status, id)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))


# =====================================================
# EDIT DRIVE
# =====================================================
@app.route("/edit-drive/<int:drive_id>", methods=["GET", "POST"])
def edit_drive(drive_id):
    if session["role"] != "company":
        return redirect(url_for("dashboard"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM placement_drives WHERE id=?", (drive_id,))
    drive = cursor.fetchone()

    if request.method == "POST":
        cursor.execute("""
            UPDATE placement_drives
            SET job_title=?, job_description=?, eligibility=?, deadline=?
            WHERE id=?
        """, (
            request.form.get("job_title"),
            request.form.get("job_description"),
            request.form.get("eligibility"),
            request.form.get("deadline"),
            drive_id
        ))
        conn.commit()
        conn.close()
        return redirect(url_for("dashboard"))

    conn.close()
    return render_template("edit_drive.html", drive=drive)






# =====================================================
# CLOSE DRIVE
# =====================================================
@app.route("/close-drive/<int:drive_id>")
def close_drive(drive_id):
    if session["role"] != "company":
        return redirect(url_for("dashboard"))

    conn = get_db()
    conn.execute("UPDATE placement_drives SET status='Closed' WHERE id=?",
                 (drive_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))

# =====================================================
# APPLY DRIVE
# =====================================================
@app.route("/apply/<int:drive_id>")
def apply_drive(drive_id):

    if session.get("role") != "student":
        return redirect(url_for("dashboard"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM students WHERE user_id=?",
                   (session["user_id"],))
    student = cursor.fetchone()

    if not student:
        conn.close()
        return redirect(url_for("dashboard"))

    student_id = student["id"]

    # get student roll number
    cursor.execute("SELECT roll_no FROM students WHERE id=?", (student_id,))
    roll = cursor.fetchone()
    roll_no = roll["roll_no"]

    # get drive code
    cursor.execute("SELECT drive_code FROM placement_drives WHERE id=?", (drive_id,))
    drive = cursor.fetchone()
    drive_code = drive["drive_code"]

    # generate application id
    application_id = f"{roll_no}-{drive_code}"

    # applied date
    applied_date = datetime.now().strftime("%Y-%m-%d")

    try:
        cursor.execute("""
            INSERT INTO applications
            (student_id, drive_id, application_id, applied_date,status)
            VALUES (?, ?, ?, ?, ?)
        """,(student_id, drive_id, application_id, applied_date, "Registered"))

        conn.commit()
    except:
        pass

    conn.close()
    return redirect(url_for("dashboard"))
# =====================================================
# hr details button in company dashboard
# =====================================================

@app.route("/hr-details", methods=["GET","POST"])
def hr_details():

    user_id = session["user_id"]

    conn = get_db()
    cursor = conn.cursor()

    # When HR email is edited
    if request.method == "POST":

        hr_email = request.form.get("hr_email")

        cursor.execute("""
        UPDATE companies SET hr_email=? WHERE user_id=?
        """,(hr_email, user_id))

        conn.commit()

    # Get current HR email
    cursor.execute("""
        SELECT company_name, company_id, hr_email
        FROM companies
        WHERE user_id=?
        """,(user_id,))

    company = cursor.fetchone()

    conn.close()

    return render_template("hr_details.html", company=company)

# =====================================================
# LOGOUT
# =====================================================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)