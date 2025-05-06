import logging

from flask import Flask, render_template, request, redirect, url_for, jsonify
from decimal import Decimal, InvalidOperation
from datetime import date, datetime

from models.transaction import Transaction
from models.member import Member, Title
from models.transaction_type import TransactionType
from services.logging_db import log_transaction_change
from services.members_db import load_member_by_email, load_all_members
from services.report_sender import send_report_email
from services.settings_loader import get_admin_email, get_monthly_payment_for_residents, \
    get_monthly_payment_for_non_residents
from services.monthly_payments import get_missing_monthly_payment_transactions
from services.transactions_db import load_transactions_by_email, load_transaction_by_id, load_transactions_by_type

# Initialize the Flask application
app = Flask(__name__)


@app.route('/', methods=['GET'])
def home():
    """
    Display the home page with the email login form.

    GET: Render the index login page.
    """
    return render_template("index.html")


@app.route('/dashboard', methods=['POST'])
def dashboard():
    """
    Display the member dashboard or redirect to admin panel if admin logs in.

    POST: Accept member email from login form and redirect accordingly.
    """
    email = request.form.get("email", "").strip().lower()

    # Redirect admin users to the admin panel
    if email == get_admin_email():
        return redirect(url_for("admin_panel"))

    # Load the member from the database
    try:
        member = load_member_by_email(email)
    except ValueError:
        return f"[!] No member found with this email: {email}", 404

    # Render the dashboard for the member
    return render_template("dashboard.html", member=member)


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

    GET: Render the add member form.
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

        # Check if member already exists
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

    # Render the add member form
    return render_template("admin_add_member.html")


@app.route("/admin/check_monthly_payments")
def check_all_missing_monthly_payments():
    """
    Display the page for manually reviewing and adding missing monthly payments.

    GET: For each member (except AH), load both existing and missing monthly payments,
         and render an editable table grouped by member.
    """
    members = load_all_members()

    result = []

    for member in members:
        if member.title == "AH":
            continue

        # Загружаем существующие ежемесячные транзакции
        existing = load_transactions_by_type(member.email, TransactionType.MONTHLY_FEE.value)

        # Загружаем недостающие
        missing = get_missing_monthly_payment_transactions(member.email)

        # Сортируем обе группы по дате
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


@app.route('/admin/change_title')
def admin_change_title():
    """
    Display the form for editing member titles.

    GET: Show table of all members with dropdown to update their title.
    """
    # Load all members and prepare simplified data for template rendering
    members = load_all_members()

    # Prepare data for template
    member_data = [
        {
            'email': m.email,
            'last_name': m.last_name,
            'current_title': m.title
        }
        for m in members
    ]

    # Mapping of title codes to human-readable descriptions
    title_labels = {
        "F": "Fuchs",
        "CB": "Corpsbursch",
        "iaCB": "inaktiver Corpsbursch",
        "AH": "Alter Herr"
    }

    # Render the page with member list and dropdown options
    return render_template(
        'admin_change_title.html',
        members=member_data,
        possible_titles=[t.value for t in Title],
        title_labels=title_labels
    )


@app.route('/update_titles_bulk', methods=['POST'])
def update_titles_bulk():
    """
    Bulk update titles for multiple members.

    POST: Accept a JSON array of updates, apply title changes, and return a summary.
    """
    # Parse request body as JSON
    data = request.get_json()
    updates = data.get("updates", [])

    # Validate format
    if not isinstance(updates, list):
        return jsonify({"success": False, "error": "Invalid format"}), 400

    updated = 0  # Counter to track how many updates were successful

    # Iterate through all submitted updates
    for update in updates:
        email = update.get("email")
        new_title = update.get("new_title")

        if not email or not new_title:
            continue

        try:
            member = load_member_by_email(email)
            member.change_title_to(new_title, changed_by=get_admin_email())
            updated += 1
        except Exception as e:
            logging.error(f"[!] Error updating title for {email}: {e}")
            continue

    return jsonify({"success": True, "updated": updated})


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
