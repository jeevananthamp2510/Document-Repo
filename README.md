A Secure Cloud-Based Document Management System

Technology
Python · Flask · SQLite · Amazon S3 · Boto3 · Werkzeug(Web Server Gateway Interface)
Server
AWS EC2 (Amazon Linux 2023) · Gunicorn · Nginx
Database
SQLite — stored locally on EC2 as docrepo.db
Auth
Session-based login with hashed passwords
Storage
Amazon S3 private bucket with pre-signed URLs
Port
5000 (Flask development) — upgrade to Gunicorn+Nginx for production

Abstract:
Document Repository is a secure, cloud-based web application designed to allow registered users to upload, store, and retrieve documents privately. Built using Python Flask as the web framework, the application leverages Amazon Web Services (AWS) for cloud infrastructure — specifically Amazon EC2 for server hosting and Amazon S3 for private file storage.
The system implements user authentication with session-based login and hashed password storage using the Werkzeug security library. All uploaded documents are stored in a private S3 bucket and accessed through time-limited pre-signed URLs, ensuring files are never publicly accessible. User account data and document metadata are persisted in a lightweight SQLite database stored directly on the EC2 instance, eliminating the need for a separate database server.
The application provides a clean, styled dashboard interface where users can view all their uploaded documents, download them via secure links, and delete them when no longer needed. This project demonstrates a practical implementation of cloud-based document management with a focus on security, simplicity, and cost-effectiveness.

Objective:
To build a secure, user-authenticated web application for private document storage.
To integrate Amazon S3 for scalable, private cloud file storage with time-limited access URLs.
To implement a lightweight SQLite database on EC2 to store user accounts and document metadata without requiring a separate database server.
To provide a clean, intuitive dashboard interface showing all uploaded documents with view and delete actions.
To enforce password security with hashing and validation rules (minimum 8 characters, one number, one special character).
To deploy the application on AWS EC2 with a production-ready server configuration.

Scope of the Project:
1. In scope
User registration with first name, last name, email, and validated password
User login and session management
File upload to private Amazon S3 bucket
Document listing dashboard showing filename, upload date, and file size
Secure file viewing via pre-signed S3 URLs (1-hour expiry)
File deletion from both S3 and the local database
SQLite database stored on EC2 for user and document records
Deployment on AWS EC2 with Gunicorn and Nginx
2. Out of scope:
File sharing between users
File versioning or revision history
Mobile application (web browser only)
Payment or subscription features
Advanced search or tagging of documents

Software and Hardware Requirements:
Programming Language:
1. Python
3.9+ (3.10 recommended)
2. Web Framework:
Flask
Latest stable
3. Cloud SDK:
Boto3
Latest stable — AWS SDK for Python
4. Password Security:
Werkzeug
Latest stable
5. Production Server:
Gunicorn
Latest stable
6. Reverse Proxy:
Nginx
Latest stable
7. Database:
SQLite
Built into Python — no install needed
8. Operating System:
Amazon Linux 2023
or Ubuntu 22.04 LTS
9. Browser:
Any modern browser
Chrome, Firefox, Edge, Safari

Hardware Requirements:
1. EC2 Instance
t2.micro (1 vCPU, 1GB RAM)
t2.small or t2.medium
3. Storage (EBS)
8 GB
20 GB
3. S3 Bucket
Any region
ap-south-1 (Mumbai) for India
4. Network
Public IPv4 required
Elastic IP for stable address
5. Internet
Required for S3 access
Stable broadband

System Development: 
1. Presentation
HTML Templates (Jinja2)
Login, Signup, Dashboard, Upload pages
2. Application
Flask (app.py)
Routes, authentication, session, business logic
3. Storage — Files
Amazon S3
Private file storage with pre-signed URL access
4. Storage — Data
SQLite (docrepo.db)
User accounts and document metadata on EC2
5. Security
Werkzeug + Flask Session
Password hashing, session cookies, login guard
6. Infrastructure
AWS EC2 + Gunicorn + Nginx
Server hosting and HTTP request handling

Ec2 instance file path system:
your-project/
├── app.py
├── docrepo.db        ← auto-created on first run
└── templates/
    ├── base.html
    ├── login.html
    ├── signup.html
    ├── dashboard.html
    └── upload.html

Authentication Flow:
1.User submits email and password on login page
2.Flask looks up email in SQLite database
3.Werkzeug compares submitted password against stored hash
4.On success: user ID, name, email stored in encrypted Flask session cookie
5.All protected routes check session before serving content
6.Logout clears the session completely

File Upload Flow:
1.Logged-in user selects a file on the Upload page
2.Flask receives the file via POST request
3.A UUID is prepended to the filename to ensure uniqueness
4.File is uploaded to private S3 bucket using Boto3
5.Filename, S3 key, file size, and user ID saved to SQLite
6.User redirected to Dashboard with success message

File View Flow:
1.Dashboard page loads all documents for the logged-in user from SQLite
2.For each document, Flask calls generate_presigned_url() using the S3 key
3.Each URL is valid for 1 hour and signed with the EC2 IAM role credentials
4.User clicks View — browser opens the pre-signed URL directly
5.After 1 hour the URL expires — user reloads dashboard for a fresh link

Coding:
1. Generate Secret Key (Run First)
   python3 -c "import secrets; print(secrets.token_hex(32))"
   Copy the output and use this value as your SECRET_KEY in all configurations below
3. app.py file creation using touch or nano Linux command
4. Gunicorn systemd Service
   [Unit]
Description=Document Repository Flask App
After=network.target
[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/my-project
Environment=SECRET_KEY=YOUR_SECRET_KEY
Environment=AWS_DEFAULT_REGION=ap-south-1
ExecStart=/home/ec2-user/.local/bin/gunicorn \
        --workers 2 \
        --bind 127.0.0.1:8000 \
        app:app
Restart=always
[Install]
WantedBy=multi-user.target
#Replace YOUR_SECRET_KEY with the key generated
4.Nginx Configuration
server {
    listen 80;
    server_name YOUR_PUBLIC_IP;
    client_max_body_size 50M;
    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 60s;
    }
}
#Replace YOUR_PUBLIC_IP with your EC2 public IP
5. IAM Policy (S3 Permissions)
   {
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::my-photo-app-bucket-123/*"
    }
  ]
}

Result:
After successful deployment, the Document Repository application delivers the following working features:

1. Sign Up:
New users can register with first name, last name, email, and a validated password
2. Sign In
Registered users can log in securely — incorrect credentials are rejected
3. Dashboard
Logged-in users see a list of all their uploaded documents with name, date, and size
4. Upload
Users can upload any file type — it is stored privately in S3
5. View File
Each document has a View button that opens a secure 1-hour pre-signed URL
6. Delete File
Users can delete documents — removed from both S3 and the database
7. Session Security
Unauthenticated users are redirected to login for all protected pages
8. Password Hashing
Passwords are never stored in plain text — Werkzeug hashing is used
9. Private Storage
S3 bucket is fully private — no file is ever publicly accessible
10. SQLite DB
docrepo.db is auto-created on first run — no database setup required

Conclusion:
The Document Repository project successfully demonstrates the development and deployment of a secure, cloud-based document management system using modern Python web technologies and AWS cloud infrastructure. The application achieves its core objectives of providing private file storage, user authentication, and an intuitive document management interface.
The decision to use SQLite instead of a managed database service like Amazon RDS proved to be highly effective for this use case — it eliminates infrastructure costs, simplifies deployment, and performs reliably for personal or small-team usage. The combination of Amazon S3 for file storage with pre-signed URLs ensures that documents remain private while still being easily accessible to authorized users.
The use of Werkzeug for password hashing, Flask sessions for authentication state, and the login_required decorator for route protection provides a solid security foundation. The application can be further extended in future iterations with features such as file sharing between users, document search, file versioning, and HTTPS support through AWS Certificate Manager.
Overall, the project provides a practical, deployable solution that balances simplicity, security, and cost-effectiveness — making it suitable as both a learning exercise and a foundation for a production document management system.

Project Updates: 
App port from 80 to 5000 - Port 80 requires root/sudo privileges on Linux. Port 5000 works without special permissions for development.






