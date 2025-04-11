from flask import Flask, render_template, request, redirect, url_for, session, abort
from decimal import Decimal, InvalidOperation
from datetime import date, datetime

from services.settings_loader import load_settings
from services.members_io import load_all_members, save_all_members
from models.member import Member, Title

# Initialize the Flask application
app = Flask(__name__)


@app.route('/', methods=['GET'])
def home():
    """
    Display the home page with the email login form.

    Returns:
        str: Rendered HTML content of the login page.
    """
    return render_template("index.html")


@app.route('/dashboard', methods=['POST'])
def dashboard():
    """
    Display the member dashboard or redirect to admin panel if admin logs in.

    Returns:
        Response: Redirect to admin panel or render member dashboard.
    """
    # Get the submitted email address from the login form
    email = request.form.get("email", "").strip()

    # Check if user is admin
    if email == load_settings().get("email_address"):
        return redirect(url_for("admin_panel"))

    # Check if user is a regular member
    members = load_all_members()
    if email not in members:
        return f"No member found with this email: {email}", 404

    member = members[email]
    return render_template("dashboard.html", member=member)


@app.route("/admin", methods=["GET"])
def admin_panel():
    """
    Admin dashboard with table of all members.
    """
    members = load_all_members()

    # Sort by created_at
    sorted_members = dict(
        sorted(members.items(), key=lambda item: item[1].created_at, reverse=True)
    )
    return render_template("admin_members.html", members=sorted_members)


@app.route('/admin/add_member', methods=['GET', 'POST'])
def admin_add_member():
    """
    Admin view: create a new member via form submission.
    GET: show the form.
    POST: process and save new member to members.json.
    """
    # Extract form fields
    if request.method == 'POST':
        email = request.form.get("email", "").strip()
        last_name = request.form.get("last_name", "").strip()
        first_name = request.form.get("first_name", "").strip()
        title = request.form.get("title", "").strip()
        is_resident = request.form.get("is_resident") == "on"
        balance_str = request.form.get("start_balance", "0.00").strip()

        # Validate email format
        if "@" not in email or "." not in email:
            return "Invalid email address.", 400

        # Validate and convert start balance to Decimal
        try:
            start_balance = Decimal(balance_str.replace(",", "."))
        except InvalidOperation:
            return "Invalid balance format", 400

        # Validate title
        if title not in Title._value2member_map_:
            return "Invalid title", 400

        # Load existing members and check for duplicates
        members = load_all_members()
        if email in members:
            return f"Member with email {email} already exists.", 400

        # Create new Member instance
        member = Member(email=email, last_name=last_name, start_balance=start_balance)

        # Set optional fields
        member.first_name = first_name
        member.title = title
        member.is_resident = is_resident

        # Initialize history fields
        member.title_history = {member.created_at: title}
        member.resident_history = {member.created_at: is_resident}

        # Save the new member to storage
        members[email] = member
        save_all_members(members)

        # Redirect back to admin-panel
        return redirect(url_for("admin_panel"))

    return render_template("admin_add_member.html")


@app.route("/admin/add_transaction", methods=["GET", "POST"])
def admin_add_transaction():
    """
    Admin view: create a new transaction via form submission.
    GET: show the transaction form.
    POST: process and save the transaction to the selected member.
    """
    # Load all members from storage
    members = load_all_members()

    # Assign current title to each member for display in the dropdown
    for m in members.values():
        m.current_title = m.get_title_at(date.today().isoformat())

    if request.method == "POST":
        # Extract form data
        email = request.form.get("email")
        amount = float(request.form.get("amount"))
        date_str = request.form.get("date")
        description = request.form.get("description")


        # Find the selected member
        member = members.get(email)
        if member:
            # Append the transaction
            member.transactions.append({
                "date": date_str,
                "description": description,
                "amount": amount
            })

            # Save updated data
            save_all_members(members)

        # Redirect to admin panel
        return redirect(url_for("admin_add_transaction"))

    # Render the form
    return render_template(
        "admin_add_transaction.html",
        members=members.values(),
        current_date=date.today().isoformat()
    )


if __name__ == '__main__':
    """
    Run the Flask development server when this script is executed directly.
    """
    app.run(debug=True)
