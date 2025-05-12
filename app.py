import logging
import os

from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, jsonify
from decimal import Decimal, InvalidOperation
from datetime import date, datetime


from models.transaction import Transaction
from models.member import Member, Title
from models.transaction_type import TransactionType
from services.logging_db import log_transaction_change, log_title_change, log_residency_change
from services.members_db import load_member_by_email, load_all_members
from services.reimbursements_db import save_reimbursement_items, update_bank_details
from services.report_sender import send_report_email
from services.settings_loader import get_admin_email, get_monthly_payment_for_residents, \
    get_monthly_payment_for_non_residents
from services.monthly_payments import get_missing_monthly_payment_transactions
from services.transactions_db import load_transactions_by_email, load_transaction_by_id, load_transactions_by_type

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
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath) # Save uploaded file

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

    # Sort members by creation date (newest first)
    sorted_members = sorted(members, key=lambda member: member.created_at, reverse=True)

    # Render the admin member list
    return render_template("admin_members.html", members=sorted_members)


@app.route('/admin/add_member', methods=['GET', 'POST'])
def admin_add_member():
    """
    Allow admin to create a new member via form submission.

    GET: Render the "add member" form.
    POST: Validate and save the new member to the database.
    """
    if request.method == 'POST':
        email = request.form.get("email", "").strip()
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
        send_report_email(member)
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
