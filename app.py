# --- Standard library ---
import logging
import os
import uuid
from decimal import Decimal, InvalidOperation
from datetime import date, datetime

# --- Third-party libraries ---
from flask import Flask, render_template, request, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# --- Local modules ---
from models.transaction import Transaction
from models.member import Member, Title
from models.transaction_type import TransactionType
from services.beverage_db import save_beverage_report
from services.logging_db import log_transaction_change, log_title_change, log_residency_change
from services.members_db import load_member_by_email, load_all_members
from services.reimbursements_db import save_reimbursement_items, update_bank_details
from services.report_sender import send_report_email
from services.settings_loader import (
    get_admin_email,
    get_monthly_payment_for_residents,
    get_monthly_payment_for_non_residents
)
from services.monthly_payments import get_missing_monthly_payment_transactions
from services.statistics import calculate_monthly_debt_trend, build_debt_chart
from services.transactions_db import (
    load_transactions_by_email,
    load_transaction_by_id,
    load_transactions_by_type
)
from services.beverage_loader import load_beverage_assortment

load_dotenv()

EMAIL_SENDER = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")
TEMPLATE_PATH = "config/emails/balance_report.html"

# Initialize the Flask application
app = Flask(__name__)

# Configure the uploads folder for saving receipts
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route('/', methods=['GET'])
def home():
    """
    Display the home page with the email login form.

    GET: Render the index login page.
    """
    return render_template("index.html")


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    """
    Display the member dashboard or redirect to "admin panel" if admin logs in.

    GET: Accept member email from query string (?email=...)
    POST: Accept member email from login form.
    """
    # Extract email from a form or query string
    email = request.form.get("email") if request.method == "POST" else request.args.get("email")
    if not email:
        return "[!] No email provided.", 400
    email = email.strip().lower()

    # Redirect admin user to "admin panel"
    if email == get_admin_email():
        return redirect(url_for("admin_panel"))

    # Load member by email
    try:
        member = load_member_by_email(email)
    except ValueError:
        return f"[!] No member found with this email: {email}", 404

    # Calculate balance and fetch transactions
    member.balance = member.get_balance()
    member.transactions = member.get_transactions()

    # Render the member dashboard
    return render_template("dashboard.html", member=member)


@app.route("/reimbursement-form/<email>")
def reimbursement_form(email):
    """
    Render the reimbursement submission form for a specific member.

    GET: Load member data by email and render a form pre-filled with name and date.
    """
    # Load the member from the database
    member = load_member_by_email(email)
    if not member:
        return "Mitglied nicht gefunden", 404

    # Render the reimbursement form, passing member data and current date
    return render_template(
        "reimbursement_form.html",
        member=member,
        current_date=date.today().strftime("%d.%m.%Y")
    )


@app.route("/submit-reimbursement", methods=["POST"])
def submit_reimbursement():
    """
    Handle the reimbursement form submission and store all valid entries.

    POST:
    - Parse form fields including description, date, amount, receipt
    - Save uploaded files to disk
    - Validate that all fields are present per row before saving
    - Optionally store updated bank data
    - Save valid reimbursement items to the database
    - Redirect to the member's dashboard
    """
    # Retrieve basic form fields
    email = request.form.get("email")
    refund_type = request.form.get("refund_type")
    bank_name = request.form.get("bank_name")
    iban = request.form.get("iban")

    # Collect all repeated row data from the form
    descriptions = request.form.getlist("description[]")
    dates = request.form.getlist("date[]")
    amounts = request.form.getlist("amount[]")
    files = request.files.getlist("receipt[]")

    # Process each row and save only fully filled ones
    entries = []
    for desc, dt, amt, file in zip(descriptions, dates, amounts, files):
        # Ensure all fields are filled and a file is uploaded
        if desc.strip() and dt.strip() and amt.strip() and file and file.filename:
            # Save the original file name and extension for later use
            original_name = secure_filename(file.filename)
            ext = os.path.splitext(original_name)[1]
            # Generate a new name: email_YYYYMMDD_desc_uuid.pdf
            short_desc = "_".join(desc.strip().lower().split())[:20]
            date_part = datetime.strptime(dt, "%d.%m.%Y").strftime("%Y%m%d")
            member = load_member_by_email(email)
            unique_id = uuid.uuid4().hex[:8]
            filename = f"{short_desc}_{date_part}_{member.last_name}_{unique_id}{ext}"
            # Save the file to the uploads folder with the new name
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            # Add a validated row-to-entries list
            entries.append({
                "description": desc,
                "date": dt,
                "amount": amt,
                "receipt_filename": filename
            })

    # Save all valid reimbursement rows to the database
    if entries:
        save_reimbursement_items(email, entries)

    # Optionally update bank details if "Bankkonto" is selected
    if refund_type == "bank" and bank_name.strip() and iban.strip():
        update_bank_details(email, bank_name, iban)

    # Redirect back to dashboard after successful submission
    return redirect(url_for("dashboard", email=email))


@app.route("/admin", methods=["GET"])
def admin_panel():
    """
    Display the admin dashboard with a table of all members.

    GET: Render a sorted list of all members.
    """
    try:
        members = load_all_members()
    except Exception as e:
        return f"[!] Error loading members: {e}", 500

    # Sort members by: balance (default), name, email or created_at
    sort_by = request.args.get("sort_by", "balance")  # default: balance
    order = request.args.get("order", "asc")

    reverse = (order == "desc")

    def sort_key(m):
        if sort_by == "name":
            return m.last_name.lower()
        elif sort_by == "email":
            return m.email.lower()
        elif sort_by == "created_at":
            return m.created_at
        elif sort_by == "balance":
            return m.get_balance()
        return m.get_balance()  # fallback

    sorted_members = sorted(members, key=sort_key, reverse=reverse)

    # Render the admin member list
    return render_template("admin_members.html", members=sorted_members, sort_by=sort_by, order=order)


@app.route("/admin/statistics", methods=["GET"])
def admin_statistics():
    """
    Display the admin statistics page showing members with significant debts.

    GET: Load all members, compute balances and last credit date,
         and display those with debts greater than 100€.
    """
    # Parse the selected date from the query string (default = today)
    date_str = request.args.get("date", date.today().strftime("%d.%m.%Y"))
    try:
        reference_date = datetime.strptime(date_str, "%d.%m.%Y").date()
    except ValueError:
        logging.warning(f"[!] Invalid date format received: {date_str}, falling back to today")
        reference_date = date.today()

    # Attempt to load all members
    try:
        members = load_all_members()
    except Exception as e:
        logging.error(f"[!] Error loading members for statistics: {e}")
        members = []

    report_rows = []

    for member in members:
        current_balance = member.get_balance()
        if current_balance >= -100:
            continue

        balance_on_date = member.get_balance_at(reference_date)
        last_credit_date = member.get_last_credit_date()
        last_credit_str = last_credit_date.strftime("%d.%m.%Y") if last_credit_date else "–"

        report_rows.append({
            "name": f"{member.get_title()} {member.last_name}",
            "current_debt": round(current_balance, 2),
            "debt_on_date": round(balance_on_date, 2),
            "last_topup": last_credit_str
        })

    report_rows.sort(key=lambda r: r["current_debt"])

    # Build the debt chart (safely)
    try:
        labels, totals, deltas = calculate_monthly_debt_trend()
        chart_base64 = build_debt_chart(labels, totals, deltas)
    except Exception as e:
        logging.error(f"[!] Error generating debt chart: {e}")
        chart_base64 = None

    return render_template(
        "admin_statistics.html",
        rows=report_rows,
        selected_date=reference_date,
        chart_base64=chart_base64
    )


@app.route('/admin/add_member', methods=['GET', 'POST'])
def admin_add_member():
    """
    Allow admin to create a new member via form submission.

    GET: Render the "add member" form.
    POST: Validate and save the new member to the database.
    """
    if request.method == 'POST':
        email = request.form.get("email", "").strip().lower()
        last_name = request.form.get("last_name", "").strip()
        first_name = request.form.get("first_name", "").strip()
        title = request.form.get("title", "F").strip()
        is_resident = request.form.get("is_resident", True) == "on"
        balance_str = request.form.get("start_balance", "0.00").strip()

        # Validate the email format
        if "@" not in email or "." not in email:
            return "Invalid email address.", 400

        # Convert balance string to Decimal
        try:
            start_balance = Decimal(balance_str.replace(",", "."))
        except InvalidOperation:
            return "[!] Invalid balance format", 400

        # Validate title value
        if title not in Title._value2member_map_:
            return "[!] Invalid title", 400

        # Check if the member already exists
        try:
            load_member_by_email(email)
            return f"[!] Member with email {email} already exists.", 400
        except ValueError:
            pass

        # Create a new Member
        member = Member(email=email,
                        last_name=last_name,
                        first_name=first_name,
                        title=title,
                        is_resident=is_resident,
                        start_balance=start_balance)

        # Save the new member to the database
        member.save_to_db()

        # Redirect to the admin panel
        return redirect(url_for("admin_panel"))

    # Render "add member" form
    return render_template("admin_add_member.html")


@app.route("/admin/check_monthly_payments")
def check_all_missing_monthly_payments():
    """
    Display the page for manually reviewing and adding missing monthly payments.

    GET: For each member (except AH), load both existing and missing monthly payments
         and render an editable table grouped by member.
    """
    members = load_all_members()

    result = []

    for member in members:
        if member.title == "AH":
            continue

        existing = load_transactions_by_type(member.email, TransactionType.MONTHLY_FEE.value)

        missing = get_missing_monthly_payment_transactions(member.email)

        existing_sorted = sorted(existing, key=lambda t: t.date)
        missing_sorted = sorted(missing, key=lambda t: t.date)

        result.append({
            "member": member,
            "existing": existing_sorted,
            "missing": missing_sorted
        })

    return render_template(
        "admin_missing_payments.html",
        members=result,
        resident_fee=get_monthly_payment_for_residents(),
        non_resident_fee=get_monthly_payment_for_non_residents()
    )


@app.route("/admin/save_missing_payments", methods=["POST"])
def save_missing_payments():
    """
    Save multiple missing monthly payments submitted from the UI.

    POST: Accept a list of transactions (email, date, amount) and create them as monthly fees.
    Returns JSON response with success status and number of saved transactions.
    """
    data = request.get_json()
    transactions = data.get("transactions", [])

    saved_count = 0

    for entry in transactions:
        try:
            email = entry["email"]
            date_str = entry["date"]
            amount = Decimal(entry["amount"])

            transaction_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            description = f"Aktivenbeitrag ({transaction_date.strftime('%B %Y')})"

            tx = Transaction(
                transaction_date=transaction_date,
                description=description,
                amount=-amount,
                member_email=email,
                transaction_type=TransactionType.MONTHLY_FEE
            )

            tx.save(changed_by=get_admin_email())
            saved_count += 1

        except Exception as e:
            print(f"[!] Fehler beim Speichern der Transaktion: {e}")
            continue

    return jsonify({"success": True, "saved": saved_count})


@app.route("/admin/beverage-report", methods=["GET", "POST"])
def beverage_report():
    """
    Render the beverage report input form for the admin.

    GET:
    - Load all members from the database
    - Load current beverage assortment from config
    - Render the report input form with dynamic table
    """
    members = load_all_members()
    beverages = load_beverage_assortment()
    return render_template("beverage_report.html", members=members, beverages=beverages)


@app.route("/submit-beverage-report", methods=["POST"])
def submit_beverage_report():
    """
    Handle the submission of a beverage consumption report and create transactions.

    POST:
    - Parse form data with member drink consumption
    - Save the report and beverage prices to the database
    - Calculate total cost per member
    - Create and save a DRINKS transaction for each member
    - Redirect back to the beverage report page
    """
    form = request.form
    report_date_str = form.get("report_date")

    # Ensure a report date is provided
    if not report_date_str:
        logging.error("No report date provided")
        return redirect(url_for("beverage_report"))

    # Parse the date into a Python date object
    try:
        report_date = datetime.strptime(report_date_str.strip(), "%d.%m.%Y").date()
    except ValueError:
        logging.error("Invalid report date format")
        return redirect(url_for("beverage_report"))

    # Load beverage assortment and build a price map
    beverages = load_beverage_assortment()
    beverage_map = {b["name"]: Decimal(str(b["price"])) for b in beverages}

    # Save report and detailed consumption entries
    save_beverage_report(form, beverages, report_date)

    # Calculate the total amount per member
    member_totals = {}

    for key, values in form.items():
        if "_" not in key or key.startswith("event_"):
            continue

        email, bev = key.split("_", 1)
        if bev not in beverage_map:
            continue

        value_str = values.strip()
        if not value_str.isdigit():
            continue

        count = int(value_str)
        if count == 0:
            continue

        total = beverage_map[bev] * count
        member_totals[email] = member_totals.get(email, Decimal("0.00")) + total

    # Create one DRINKS transaction for each member
    changed_by = get_admin_email()

    for email, total in member_totals.items():
        tx = Transaction(
            transaction_date=report_date,
            description=f"Getränkeabrechnung vom {report_date.strftime('%d.%m.%Y')}",
            amount=-total,
            member_email=email,
            transaction_type=TransactionType.DRINKS
        )
        tx.save(changed_by=changed_by)

    return redirect(url_for("beverage_report"))


@app.route("/admin/fines", methods=["GET"])
def admin_fines():
    """
    Render the admin page for submitting fines to members.

    This page displays a form where admins can input multiple fines at once,
    including session date, protocol number, meeting type, semester, and fine entries.

    GET: Fetch all members and render the fine submission form.
    """
    members = load_all_members()
    current_year = datetime.now().year
    current_date = datetime.now().strftime("%d.%m.%Y")
    return render_template("admin_fines.html",
                           members=members, current_year=current_year,
                           current_date=current_date,
                           success=request.args.get("success") == "1")


@app.route("/admin/fines", methods=["POST"])
def submit_fines():
    """
    Render the admin page for submitting fines to members.

    This page displays a form where admins can input multiple fines at once,
    including session date, protocol number, meeting type, semester, and fine entries.

    GET: Fetch all members and render the fine submission form.
    """
    protocol_number = request.form.get("protocol_number", "").strip()
    meeting_type = request.form.get("meeting_type", "").strip()
    semester = request.form.get("semester", "").strip()
    session_date = request.form.get("session_date", "").strip()
    fines = request.form.to_dict(flat=False)

    # Validate protocol_number
    if not protocol_number.isdigit():
        return "[!] Ungültige Protokollnummer.", 400

    # Validate meeting_type
    if meeting_type not in ["AC", "CC", "FCC", "GCC"]:
        return "[!] Ungültiger Typ des Treffens.", 400

    # Validate that there is at least one fine entry
    if not any(key.startswith("fines[") for key in fines):
        return "[!] Es wurden keine Strafen eingetragen.", 400

    fines_list = []
    index = 0

    while f"fines[{index}][email]" in fines:
        email = fines[f"fines[{index}][email]"][0].strip()
        amount_str = fines[f"fines[{index}][amount]"][0].strip()
        reason = fines[f"fines[{index}][description]"][0].strip()

        if not email or not amount_str or not reason:
            return "[!] Alle Felder müssen ausgefüllt sein.", 400

        try:
            amount = Decimal(amount_str)
        except InvalidOperation:
            return f"[!] Ungültiger Betrag in Zeile {index + 1}.", 400

        try:
            transaction_date = datetime.strptime(session_date, "%d.%m.%Y").date()
        except ValueError:
            return "[!] Ungültiges Datum.", 400

        full_description = f"Strafe ({protocol_number}. {meeting_type} {semester}) vom {transaction_date.strftime('%d.%m.%Y')} [{reason}]"

        fines_list.append(Transaction(
            transaction_date=transaction_date,
            description=full_description,
            amount=-abs(amount),
            member_email=email,
            transaction_type=TransactionType.FINE
        ))

        index += 1

    for fine in fines_list:
        fine.save(changed_by=get_admin_email())

    return redirect(url_for("admin_fines", success=1))


@app.route("/admin/add_transaction", methods=["GET", "POST"])
def admin_add_transaction():
    """
    Add a new transaction for a selected member.

    GET: Display the transaction form with a list of members.
    POST: Process the submitted transaction and insert into the database.
    """
    if request.method == "POST":
        try:
            email = request.form.get("email")
            date_str = request.form.get("date")
            description = request.form.get("description").strip()
            amount_str = request.form.get("amount", "0.00").strip().replace(",", ".")

            type_str = request.form.get("type", "1")
            try:
                transaction_type = TransactionType(int(type_str))
            except (ValueError, KeyError):
                return "[!] Ungültiger Transaktionstyp", 400

            try:
                transaction_date = date.fromisoformat(date_str)
            except ValueError:
                return "[!] Ungültiges Datum", 400

            try:
                amount = Decimal(amount_str)
            except InvalidOperation:
                return "[!] Ungültiger Betrag", 400

            # Create a new Transaction instance
            new_transaction = Transaction(
                transaction_date=transaction_date,
                description=description,
                amount=amount,
                member_email=email,
                transaction_type=transaction_type
            )

            # Save the transaction to the database
            new_transaction.save(changed_by=get_admin_email())

            logging.info(f"[✓] Transaction added: {new_transaction.description} for {email}")

            return redirect(url_for("admin_add_transaction", email=email))

        except Exception as e:
            logging.error(f"[!] Error adding transaction: {e}")
            return f"[!] Error adding transaction: {e}", 400

    # GET Request: Load data for the form
    members = load_all_members()
    selected_email = request.args.get("email")
    selected_member = None

    if selected_email:
        try:
            selected_member = load_member_by_email(selected_email)
        except Exception as e:
            logging.error(f"[!] Could not load selected member: {e}")

    return render_template(
        "admin_add_transaction.html",
        members=members,
        current_date=date.today().isoformat(),
        selected_member=selected_member,
        selected_email=selected_email
    )


@app.route('/delete_transaction/<email>/<int:transaction_id>', methods=['POST'])
def delete_transaction(email, transaction_id):
    """
    Handle the deletion of a specific transaction by its ID.

    This function:
    - Loads the transaction by its ID
    - Checks if it belongs to the correct member
    - Logs the deletion attempt
    - Attempts to delete the transaction from the database
    - Logs the deletion if successful

    Args:
        email (str): The email of the member requesting the deletion.
        transaction_id (int): The ID of the transaction to be deleted.

    Returns:
        str: An error message if there was a problem, or an empty response if successful.
    """
    try:
        # Load the transaction by its ID
        transaction = load_transaction_by_id(transaction_id)

        # Ensure the transaction belongs to the member requesting the deletion
        if transaction.member_email != email:
            return "[!] Email mismatch for transaction", 400

        # Delete transaction
        was_deleted = transaction.delete(changed_by=get_admin_email())

        if not was_deleted:
            return "[!] Deletion failed", 400

        # Log the transaction
        log_transaction_change(
            transaction_id=transaction.id,
            action="delete",
            changed_by=get_admin_email(),
            description=f"Deleted transaction: {transaction.description}"
        )

        logging.info(f"[✓] Deleted transaction {transaction.id} for {email}")
        return '', 204
    except Exception as e:
        # Log any errors that occur during the deletion process
        logging.error(f"[!] Error deleting transaction {transaction_id}: {e}")
        return f"[!] Error deleting transaction: {e}", 400


@app.route('/admin/edit_titles_and_residency')
def edit_titles_and_residency():
    """
   Renders the admin page for editing titles and residency status for all members.

   This page allows admins to view all members and modify their title and residency status.
   The titles are retrieved from the `Title` enum, and the members are fetched from the database.

   GET: Fetch all members and available titles, then render the edit page.
   """
    members = load_all_members()
    all_titles = list(Title)  # [Title.F, Title.CB, Title.iaCB, Title.AH]
    return render_template(
        'admin_edit_titles_and_residency.html',
        members=members,
        all_titles=all_titles
    )


@app.route('/admin/update_member_status', methods=['POST'])
def update_member_status():
    """
    Updates the title and residency status for a specific member.

    This function accepts a JSON payload with the email, new title, and new residency status.
    It checks if the title or residency status has changed, and if so, updates the values in the database.
    It also logs the changes to the respective logs.

    POST: Accepts JSON with email, new title, and residency status.
    Returns a success message or an error message if any field is missing or invalid.
    """
    data = request.get_json()
    email = data.get('email')
    new_title = data.get('title')
    new_resident = data.get('is_resident')
    changed_by = get_admin_email()

    if not email or new_title is None or new_resident is None:
        return jsonify({'error': 'Missing fields'}), 400

    try:
        member = load_member_by_email(email)

        if member.title != new_title:
            member.change_title(new_title, changed_by)
            log_title_change(email, new_title, changed_by)

        if member.is_resident != new_resident:
            member.change_residency(new_resident, changed_by)
            log_residency_change(email, new_resident, changed_by)

        return jsonify({'status': 'success'})

    except Exception as e:
        logging.error(f"[!] Failed to update member {email}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route("/send_report", methods=["POST"])
def send_report():
    """
    Send a transaction report email to a specific member.

    POST: Accepts a JSON body with member email, generates a personalized report,
          and sends it via email using the configured SMTP credentials.
    """
    data = request.get_json()
    email = data.get("email", "").strip().lower()

    # Validate that the email is provided
    if not email:
        return jsonify({"error": "Email fehlt"}), 400

    # Try to load the member from the database
    try:
        member = load_member_by_email(email)
    except ValueError:
        return jsonify({"error": "Mitglied nicht gefunden"}), 404

    # Generate and send the email report
    try:
        send_report_email(
            member,
            sender_email=EMAIL_SENDER,
            sender_password=EMAIL_PASSWORD,
            phone_number=PHONE_NUMBER,
            template_path=TEMPLATE_PATH
        )
        return jsonify({"success": True}), 200
    except Exception as e:
        logging.error(f"[!] Fehler beim Senden an {email}: {e}")
        return jsonify({"error": "Senden fehlgeschlagen"}), 500


@app.route("/admin/get_transactions")
def get_transactions():
    """
    Return all transactions for a specific member in JSON format.

    GET: Provide a list of transactions for dynamic table loading.
    """
    email = request.args.get("email", "").strip().lower()

    if not email:
        return jsonify({"error": "Missing email parameter."}), 400

    try:
        transaction_list = load_transactions_by_email(email)

        transactions = [
            {
                "id": t.id,
                "date": t.date.strftime("%d.%m.%Y"),
                "amount": str(t.amount),
                "description": t.description
            }
            for t in transaction_list
        ]

        return jsonify(transactions)

    except Exception as e:
        logging.error(f"[!] Error fetching transactions: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    """Run the Flask development server when this script is executed directly."""
    app.run(debug=True)
