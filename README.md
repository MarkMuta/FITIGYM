FITIGYM - Gym Management System 
FITIGYM is a web-based gym membership management system built with Python (Flask) and MySQL. It provides user-friendly tools for gym members and administrators, supporting membership plans, self check-in, attendance tracking, BMI calculations, and payment integration through the M-Pesa API.
Features
Member / User Side
•	Registration & login
•	Membership plan selection
•	 Self check‑in and attendance logging
•	 View membership status and history
•	 BMI calculator and fitness tools
•	 Responsive UI across devices
Admin / Manager Side
•	Manage members & memberships
•	 Approve or reject new sign-ups
•	 Track attendance & usage reports
•	 Manage fitness plans and pricing
•	 Configure gym details
•	 Role-based access control
M-Pesa Integration
FITIGYM integrates with the M-Pesa Daraja API for secure mobile payments. Members can pay for their plans directly through M-Pesa, and transactions are logged in the system for transparency and ease of reconciliation.
Tech Stack
•	Backend: Python (Flask)
•	Frontend: HTML, CSS, JavaScript
•	 Database: MySQL
•	 Payment Integration: M-Pesa Daraja API
•	Deployment: Docker (optional)
Project Structure
FITIGYM/
│── app.py                # Main Flask app
│── db_config.py          # Database configuration
│── mpesa_api.py          # M-Pesa integration
│── schema.sql            # Database schema
│── setup_membership_plans.py
│── setup_test_data.py
│── static/               # CSS, JS, Images
│── templates/            # HTML templates
│── .env                  # Environment variables
│── README.md

Installation & Setup
1. Clone the repository:
   git clone https://github.com/MarkMuta/FITIGYM.git
   cd FITIGYM

2. Install dependencies:
   pip install -r requirements.txt

3. Configure environment variables in `.env` and set up the database using schema.sql

4. (Optional) Run setup scripts:
   python setup_membership_plans.py
   python setup_test_data.py

5. Run the application:
   flask run

Future Enhancements
- Advanced analytics dashboards
- AI-powered fitness recommendations
- Mobile app integration
- Enhanced multi-language support
- Expanded M-Pesa features (recurring billing, refunds, receipts)
Contributing
Contributions, issues, and feature requests are welcome! Fork the repo and open a pull request.
License
This project is licensed under the MIT License.
Author
Developed by Mark Muta
