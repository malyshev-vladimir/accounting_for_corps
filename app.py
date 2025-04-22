from flask import Flask, render_template, request, redirect, url_for, jsonify
from decimal import Decimal, InvalidOperation
from datetime import date, datetime

from db import get_cursor
from services.settings_loader import get_admin_email
from services.members_db import load_member, save_member, load_all_members
from services.monthly_payments import add_missing_monthly_payments
from models.member import Member, Title

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
        member = load_member(email)
    except ValueError:
        return f"No member found with this email: {email}", 404

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
        return f"Error loading members: {e}", 500

    # Sort members by creation date (newest first)
    sorted_members = dict(
        sorted(members.items(), key=lambda item: item[1].created_at, reverse=True)
    )

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
        title = request.form.get("title", "").strip()
        is_resident = request.form.get("is_resident") == "on"
        balance_str = request.form.get("start_balance", "0.00").strip()

        # Validate the email format
        if "@" not in email or "." not in email:
            return "Invalid email address.", 400

        # Convert balance string to Decimal
        try:
            start_balance = Decimal(balance_str.replace(",", "."))
        except InvalidOperation:
            return "Invalid balance format", 400

        # Validate title value
        if title not in Title._value2member_map_:
            return "Invalid title", 400

        # Check if member already exists
        try:
            load_member(email)
            return f"Member with email {email} already exists.", 400
        except ValueError:
            pass

        # Create a new Member instance
        member = Member(email=email, last_name=last_name, start_balance=start_balance)
        member.first_name = first_name
        member.title = title
        member.is_resident = is_resident
        member.title_history = {member.created_at: title}
        member.resident_history = {member.created_at: is_resident}

        # Save the new member to the database
        save_member(member)

        # Redirect to the admin panel
        return redirect(url_for("admin_panel"))

    # Render the add member form
    return render_template("admin_add_member.html")


@app.route("/admin/check_monthly_payments")
def check_monthly_payments():
    """
    Check and add any missing monthly contributions for all members.

    GET: Update payment records for each member and redirect to admin panel.
    """
    today = datetime.today()

    # Fetch all member email addresses from the database
    with get_cursor() as cur:
        cur.execute("SELECT email FROM members ORDER BY last_name, first_name")
        emails = [row[0] for row in cur.fetchall()]

    # Load, update, and save each member individually
    for email in emails:
        try:
            member = load_member(email)
            add_missing_monthly_payments(member, today)
            save_member(member)
        except Exception as e:
            print(f"[!] Error processing {email}: {e}")

    # Redirect back to the admin panel
    return redirect(url_for("admin_panel"))


@app.route("/admin/add_transaction", methods=["GET", "POST"])
def admin_add_transaction():
    """
    Add a new transaction for a selected member.

    GET: Display the transaction form with a list of members.
    POST: Process submitted transaction and update the selected member.
    """
    # Load list of email addresses
    with get_cursor() as cur:
        cur.execute("SELECT email FROM members ORDER BY last_name, first_name")
        emails = [row[0] for row in cur.fetchall()]

    # Load full member objects
    members = {}
    for email in emails:
        try:
            member = load_member(email)
            member.current_title = member.get_title_at(date.today().isoformat())
            members[email] = member
        except Exception as e:
            print(f"[!] Failed to load member {email}: {e}")

    # Save transaction (POST)
    if request.method == "POST":
        email = request.form.get("email")
        amount = float(request.form.get("amount"))
        date_str = request.form.get("date")
        description = request.form.get("description")

        try:
            member = load_member(email)
            member.add_transaction(date_str, description, amount)
            save_member(member)
        except Exception as e:
            return f"Error adding transaction: {e}", 400

        return redirect(url_for("admin_add_transaction", email=email))

    # Load selected member (GET)
    selected_email = request.args.get("email")
    selected_member = None
    if selected_email:
        try:
            selected_member = load_member(selected_email)
        except Exception as e:
            print(f"[!] Could not load selected member: {e}")

    # Render template
    return render_template(
        "admin_add_transaction.html",
        members=members.values(),
        current_date=date.today().isoformat(),
        selected_member=selected_member
    )


@app.route('/delete_transaction/<email>/<int:transaction_id>', methods=['POST'])
def delete_transaction(email, transaction_id):
    """
    Delete a specific transaction from a member by its index.

    POST: Remove the transaction and save the updated member.
    """
    try:
        member = load_member(email)
    except ValueError:
        return "Member not found", 404

    if not (0 <= transaction_id < len(member.transactions)):
        return "Transaction not found", 404

    # Delete the transaction by index and save it
    del member.transactions[transaction_id]
    save_member(member)
    return '', 204


@app.route('/admin/change_title')
def admin_change_title():
    """
    Display the form for editing member titles.

    GET: Show table of all members with dropdown to update their title.
    """
    today_str = date.today().isoformat()

    # Load all members and prepare simplified data for template rendering
    members = load_all_members()
    member_data = [
        {
            'email': m.email,
            'last_name': m.last_name,
            'current_title': m.get_title_at(today_str)
        }
        for m in members.values()
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
        return jsonify({"success": False}), 400

    today = date.today().isoformat()
    updated = 0  # Counter to track how many updates were successful

    # Iterate through all submitted updates
    for update in updates:
        email = update.get("email")
        new_title = update.get("new_title")

        # Validate input fields
        if not email or not new_title:
            continue
        if new_title not in Title._value2member_map_:
            continue

        try:
            member = load_member(email)
            member.title_history[today] = new_title
            save_member(member)
            updated += 1

        except Exception as e:
            print(f"[!] Failed to update {email}: {e}")

    return jsonify({"success": True, "updated": updated})


@app.route("/admin/get_transactions")
def get_transactions():
    """
    Return all transactions for a given member.

    GET: Accept member email as a query parameter and return transactions as JSON.
    """
    # Get the email parameter from the query string
    email = request.args.get("email")

    # Try to load the member from the database
    try:
        member = load_member(email)
    except ValueError:
        return jsonify([])

    # Return the transactions in reverse order with their real index
    return jsonify([
        {
            "id": i,  # real index in the original list
            "date": tx["date"],
            "amount": tx["amount"],
            "description": tx["description"]
        }
        for i, tx in reversed(list(enumerate(member.transactions)))
    ])


if __name__ == '__main__':
    """Run the Flask development server when this script is executed directly."""
    app.run(debug=True)
