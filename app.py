from flask import Flask, render_template, request, redirect, url_for
from decimal import Decimal, InvalidOperation

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


@app.route('/add', methods=['POST'])
def add_member_from_form():
    """
    Create a new member from the submitted HTML form.

    Validates input fields, creates a new Member object, and saves it
    to the members database. Redirects to the homepage upon success.

    Returns:
        Response: Redirection to home or error message with HTTP status code.
    """
    # Extract form fields
    email = request.form.get("email", "").strip()
    last_name = request.form.get("last_name", "").strip()
    first_name = request.form.get("first_name", "").strip()
    title = request.form.get("title", "").strip()
    is_resident = request.form.get("is_resident") == "on"
    start_balance_str = request.form.get("start_balance", "0.00").strip()

    # Validate email format
    if "@" not in email or "." not in email:
        return "Invalid email address.", 400

    # Validate and convert start balance to Decimal
    try:
        start_balance = Decimal(start_balance_str.replace(",", "."))
    except InvalidOperation:
        return "Invalid format for starting balance.", 400

    # Validate title
    if title not in Title._value2member_map_:
        return "Invalid title.", 400

    # Load existing members and check for duplicates
    members = load_all_members()
    if email in members:
        return f"A member with email {email} already exists.", 400

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

    # Redirect back to homepage
    return redirect(url_for("home"))



if __name__ == '__main__':
    """
    Run the Flask development server when this script is executed directly.
    """
    app.run(debug=True)
