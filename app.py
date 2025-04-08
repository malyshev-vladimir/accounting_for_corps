"""
Flask web interface for the CC accounting system.

Features:
- Login via email address
- Load member data from members.json
- Display balance and transaction history in a styled HTML dashboard
- Uses Bootstrap 5 for basic layout and visual polish

Templates:
- index.html: login form
- dashboard.html: personalized user view
"""

from flask import Flask, render_template, request
from services.members_io import load_all_members

# Initialize Flask application
app = Flask(__name__)


# Route: homepage with email login form
@app.route('/', methods=['GET'])
def home():
    return render_template("index.html")


# Route: dashboard showing balance and transactions for a valid member
@app.route('/dashboard', methods=['POST'])
def dashboard():
    email = request.form.get("email").strip()
    members = load_all_members()

    # Validate email input
    if email not in members:
        return f"Kein Mitglied mit dieser E-Mail: {email}", 404
    member = members[email]

    # Pass member data to the dashboard template
    return render_template("dashboard.html", member=member)


# Run development server when executed directly
if __name__ == '__main__':
    app.run(debug=True)
