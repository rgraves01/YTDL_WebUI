Download App with aria2c, yt-dlp, Web UI, and Google Drive Integration
This is a web application that allows you to download files using aria2c or yt-dlp through a web interface. It includes user authentication and the ability to upload downloaded files directly to your Google Drive. It's designed for easy deployment on Railway.app.
Features

Web UI: A user-friendly interface to input URLs, select download tools, and manage Google Drive uploads.
aria2c Integration: Supports general HTTP/FTP downloads with multi-connection capabilities.
yt-dlp Integration: Supports downloading videos from YouTube and many other sites.
User Authentication: Protects the web interface with a configurable username and password.
Google Drive Integration: Uploads downloaded files directly to a specified Google Drive folder.
Railway.app Ready: Includes a Dockerfile for easy deployment.

Technologies Used

Backend: Python (Flask)
Frontend: HTML, CSS (Tailwind CSS via CDN), JavaScript
Tools: aria2c, yt-dlp
Google API: google-api-python-client, google-auth-oauthlib
Deployment: Docker, Railway.app

Setup and Local Development

Clone the repository:
git clone https://github.com/your-username/your-download-app.git
cd your-download-app


Create a .env file:Copy the .env.example file and rename it to .env.
cp .env.example .env

Edit the .env file and set your desired APP_USERNAME, APP_PASSWORD, and SECRET_KEY. The SECRET_KEY should be a long, random string.
Crucially, you need to set up Google Drive API credentials:
Google Cloud Project Setup for Google Drive API

Go to Google Cloud Console: Visit console.cloud.google.com and log in with your Google account.
Create a new Project:
From the project dropdown at the top, select "New Project".
Give your project a name (e.g., "Download App Drive Uploader") and click "Create".


Enable Google Drive API:
Once the project is created, navigate to "APIs & Services" > "Enabled APIs & Services".
Click "+ Enable APIs and Services".
Search for "Google Drive API" and enable it.


Create OAuth Consent Screen:
Go to "APIs & Services" > "OAuth consent screen".
Choose "External" user type and click "Create".
Fill in the required fields: "App name" (e.g., "Download Uploader"), "User support email", and your email under "Developer contact information". Click "Save and Continue".
Scopes: Click "Add or Remove Scopes". Search for and select .../auth/drive.file (or .../auth/drive if you need broader access, but drive.file is recommended for security). Click "Update".
Test Users: Add your Google account as a "Test User". This is required until your app is "Verified" by Google (which is usually not necessary for personal projects).
Review and go back to Dashboard.


Create Credentials (OAuth 2.0 Client ID):
Go to "APIs & Services" > "Credentials".
Click "+ Create Credentials" > "OAuth client ID".
Select "Web application" as the Application type.
Give it a name (e.g., "Web client 1").
Authorized redirect URIs: This is very important. You need to add the URL where Google will redirect after authorization. For Railway.app, this will be your app's domain followed by /oauth2callback.
Example: https://your-app-domain.railway.app/oauth2callback
Note: You will get your your-app-domain.railway.app after deploying the app on Railway. For local testing, you can add http://127.0.0.1:5000/oauth2callback.


Click "Create".
You will now see your Client ID and Client Secret. Copy these values.


Create a Google Drive Folder:
Go to your Google Drive (drive.google.com).
Create a new folder where you want the downloaded files to be saved (e.g., "Downloaded Files from App").
Open the folder. The URL will look something like https://drive.google.com/drive/folders/THIS_IS_YOUR_FOLDER_ID. Copy the FOLDER_ID.



Now, update your .env file with these values:
APP_USERNAME=mysecureuser
APP_PASSWORD=myverystrongpassword123
SECRET_KEY=your_very_long_and_random_secret_key_here_for_flask_sessions

GOOGLE_CLIENT_ID=YOUR_COPIED_CLIENT_ID.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=YOUR_COPIED_CLIENT_SECRET
REDIRECT_URI=http://127.0.0.1:5000/oauth2callback # For local testing; change for Railway deployment
GOOGLE_DRIVE_FOLDER_ID=YOUR_COPIED_GOOGLE_DRIVE_FOLDER_ID


Install dependencies:
pip install -r requirements.txt


Run the application (for local testing):
python app.py

The app will typically run on http://127.0.0.1:5000.


Deployment on Railway.app

Create a new project on Railway.app:

Go to Railway.app and log in.
Click "New Project" -> "Deploy from GitHub Repo".
Connect your GitHub account and select the repository you've created/forked.


Configure Environment Variables:

Once your project is created, go to the "Variables" tab.
Add the following variables (matching what you set in your local .env file):
APP_USERNAME: Your desired username for the app.
APP_PASSWORD: Your desired password for the app.
SECRET_KEY: A long, random string for Flask session management.
GOOGLE_CLIENT_ID: Your Google Cloud Project's Client ID.
GOOGLE_CLIENT_SECRET: Your Google Cloud Project's Client Secret.
REDIRECT_URI: This must be your Railway.app's generated domain URL followed by /oauth2callback. For example: https://your-app-domain.railway.app/oauth2callback (replace your-app-domain.railway.app with your actual Railway domain).
GOOGLE_DRIVE_FOLDER_ID: The ID of the Google Drive folder where you want to save files.


Railway will automatically detect the Dockerfile and build your application.


Monitor Deployment:

Go to the "Deployments" tab to see the build and deployment progress.
Once the deployment is successful, Railway will provide a public domain URL for your application.



Important Notes

Google Drive Authentication Persistence: The Google Drive authentication tokens are currently stored in the Flask session. This means if the Railway.app container restarts (e.g., due to redeployment, scaling, or maintenance), you will need to re-authorize Google Drive. For a truly persistent solution, you would need to store these tokens in a database (like Firestore or another persistent storage solution).
Ephemeral Storage: While files are uploaded to Google Drive, the original downloaded files are still temporarily stored on Railway.app's ephemeral storage before being uploaded. They are deleted after the upload process is complete.
Security: Always keep your SECRET_KEY, APP_PASSWORD, GOOGLE_CLIENT_ID, and GOOGLE_CLIENT_SECRET confidential. Do not commit your actual .env file to GitHub. Use Railway's environment variables.
Resource Usage: Be mindful of Railway.app's free tier limits regarding CPU, RAM, and network egress. Large downloads and uploads can quickly consume resources.
Error Handling: The current error handling is basic. For a more robust application, you might want to implement more detailed logging and user feedback.
Real-time Progress: Displaying real-time download/upload progress would require more advanced techniques like WebSockets, which are not included in this basic example. The current setup shows the final output after the commands complete.
