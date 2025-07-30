import os
import subprocess
import tempfile
import shutil
from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from dotenv import load_dotenv

# Google Drive API အတွက် လိုအပ်သော Libraries များ
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# .env file ကနေ environment variables တွေကို load လုပ်မယ်။
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'a_very_secret_key_that_should_be_changed') # Session အတွက် လျှို့ဝှက်သော့

# သုံးစွဲသူအမည်နဲ့ စကားဝှက်ကို environment variables ကနေ ရယူမယ်။
# Railway.app မှာ Variables tab ထဲမှာ ထည့်သွင်းနိုင်ပါတယ်။
USERNAME = os.getenv('APP_USERNAME', 'admin')
PASSWORD = os.getenv('APP_PASSWORD', 'password')

# Google Drive API အတွက် Environment Variables
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID') # Upload လုပ်မယ့် Folder ID
SCOPES = ['https://www.googleapis.com/auth/drive.file'] # Drive.file က ဖန်တီးထားတဲ့ဖိုင်တွေကိုပဲ ဝင်ရောက်ခွင့်ပြုတယ်။
REDIRECT_URI = os.getenv('REDIRECT_URI') # Railway.app ရဲ့ domain URL + /oauth2callback (ဥပမာ: https://your-app-domain.railway.app/oauth2callback)

# Authentication လိုအပ်တဲ့ route တွေအတွက် decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            flash('Login လုပ်ရန်လိုအပ်ပါသည်။', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == USERNAME and password == PASSWORD:
            session['logged_in'] = True
            flash('Login အောင်မြင်ပါသည်။', 'success')
            return redirect(url_for('index'))
        else:
            flash('သုံးစွဲသူအမည် သို့မဟုတ် စကားဝှက် မှားယွင်းနေပါသည်။', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('google_credentials', None) # Google credentials တွေကိုပါ ရှင်းထုတ်မယ်။
    flash('Logout လုပ်ပြီးပါပြီ။', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    # Google Drive authorization status ကို UI မှာ ပြဖို့
    gdrive_authorized = 'google_credentials' in session and session['google_credentials'] is not None
    return render_template('index.html', gdrive_authorized=gdrive_authorized)

@app.route('/authorize_gdrive')
@login_required
def authorize_gdrive():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET or not REDIRECT_URI:
        flash('Google Drive API credentials များကို Railway.app Variables တွင် ထည့်သွင်းရန်လိုအပ်ပါသည်။', 'error')
        return redirect(url_for('index'))

    # OAuth 2.0 flow ကို စတင်မယ်။
    flow = Flow.from_client_secrets_file(
        'client_secrets.json', # client_secrets.json ကို ယာယီဖန်တီးမယ်။
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    # Railway.app မှာ client_secrets.json ကို တိုက်ရိုက်မထားနိုင်လို့ ဒီလိုလုပ်ရပါတယ်။
    # ပိုကောင်းတဲ့နည်းလမ်းက Google Cloud Secrets Manager ကိုသုံးတာ ဒါမှမဟုတ်
    # credentials တွေကို environment variables ကနေ တိုက်ရိုက်သုံးတာပါ။
    # ဒီမှာတော့ client_secrets.json ကို runtime မှာ ဖန်တီးပြီးသုံးပါမယ်။
    client_secrets_content = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "project_id": "your-project-id", # ဒါက dummy ပါ၊ အရေးမကြီးပါဘူး။
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uris": [REDIRECT_URI]
        }
    }
    with open('client_secrets.json', 'w') as f:
        import json
        json.dump(client_secrets_content, f)

    authorization_url, state = flow.authorization_url(
        access_type='offline', # Refresh token ရဖို့အတွက် offline access တောင်းရမယ်။
        include_granted_scopes='true'
    )
    session['google_oauth_state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
@login_required
def oauth2callback():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET or not REDIRECT_URI:
        flash('Google Drive API credentials များကို Railway.app Variables တွင် ထည့်သွင်းရန်လိုအပ်ပါသည်။', 'error')
        return redirect(url_for('index'))

    state = session.get('google_oauth_state')
    if not state or state != request.args.get('state'):
        flash('OAuth state မကိုက်ညီပါ။', 'error')
        return redirect(url_for('index'))

    flow = Flow.from_client_secrets_file(
        'client_secrets.json',
        scopes=SCOPES,
        state=state,
        redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    session['google_credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    flash('Google Drive ချိတ်ဆက်မှု အောင်မြင်ပါသည်။', 'success')
    return redirect(url_for('index'))

def get_drive_service():
    if 'google_credentials' not in session:
        return None

    creds_data = session['google_credentials']
    creds = Credentials(
        token=creds_data['token'],
        refresh_token=creds_data.get('refresh_token'),
        token_uri=creds_data['token_uri'],
        client_id=creds_data['client_id'],
        client_secret=creds_data['client_secret'],
        scopes=creds_data['scopes']
    )

    # Token သက်တမ်းကုန်သွားရင် refresh လုပ်မယ်။
    if not creds.valid:
        if creds.refresh_token:
            try:
                creds.refresh(Request())
                session['google_credentials'] = { # Refresh ဖြစ်ပြီးသား credentials တွေကို session မှာ ပြန်သိမ်းမယ်။
                    'token': creds.token,
                    'refresh_token': creds.refresh_token,
                    'token_uri': creds.token_uri,
                    'client_id': creds.client_id,
                    'client_secret': creds.client_secret,
                    'scopes': creds.scopes
                }
            except Exception as e:
                flash(f"Google Drive credentials refresh လုပ်ရာတွင် error ဖြစ်ပွားသည်: {e}. ကျေးဇူးပြု၍ ပြန်လည်ချိတ်ဆက်ပါ။", 'error')
                session.pop('google_credentials', None)
                return None
        else:
            flash("Google Drive credentials မမှန်ကန်ပါ သို့မဟုတ် refresh token မရှိပါ။ ကျေးဇူးပြု၍ ပြန်လည်ချိတ်ဆက်ပါ။", 'error')
            session.pop('google_credentials', None)
            return None

    return build('drive', 'v3', credentials=creds)

@app.route('/download', methods=['POST'])
@login_required
def download():
    url = request.form['url']
    tool = request.form['tool']
    upload_to_gdrive = 'upload_to_gdrive' in request.form # Checkbox ကနေ value ရယူမယ်။
    output = ""
    error = ""
    downloaded_files = [] # Download လုပ်ပြီးသား ဖိုင်တွေရဲ့ list

    if not url:
        flash('URL ထည့်သွင်းရန်လိုအပ်ပါသည်။', 'error')
        return redirect(url_for('index'))

    # Download လုပ်ဖို့အတွက် ယာယီ folder တစ်ခုဖန်တီးမယ်။
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        
        if tool == 'yt-dlp':
            # yt-dlp ကိုခေါ်ဆိုမယ်။ -o က output directory နဲ့ file name format ကို သတ်မှတ်တယ်။
            command = ['yt-dlp', url, '-o', os.path.join(temp_dir, '%(title)s.%(ext)s')]
        elif tool == 'aria2c':
            # aria2c ကိုခေါ်ဆိုမယ်။ -d က output directory ကို သတ်မှတ်တယ်။
            command = ['aria2c', '-x16', '-d', temp_dir, url]
        else:
            flash('မှန်ကန်သော tool ကိုရွေးချယ်ပါ။', 'error')
            return redirect(url_for('index'))

        flash(f"{tool} ဖြင့် download လုပ်နေပါသည်။ ခဏစောင့်ပါ။", 'info')
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=600) # 10 မိနစ် timeout
        output = result.stdout
        if result.stderr:
            error = result.stderr
            flash(f"Tool မှ error အချို့ထွက်ပေါ်လာသည်: {error}", 'warning')
        flash(f"{tool} ဖြင့် download လုပ်ခြင်း အောင်မြင်ပါသည်။", 'success')

        # Download လုပ်ပြီးသား ဖိုင်တွေကို ရှာမယ်။
        downloaded_files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]

        if upload_to_gdrive:
            drive_service = get_drive_service()
            if drive_service:
                if not GOOGLE_DRIVE_FOLDER_ID:
                    flash('Google Drive Folder ID ကို Railway.app Variables တွင် ထည့်သွင်းရန်လိုအပ်ပါသည်။', 'error')
                else:
                    flash('Google Drive သို့ upload လုပ်နေပါသည်။', 'info')
                    for file_path in downloaded_files:
                        file_name = os.path.basename(file_path)
                        try:
                            file_metadata = {
                                'name': file_name,
                                'parents': [GOOGLE_DRIVE_FOLDER_ID] # သတ်မှတ်ထားသော folder ထဲသို့ upload လုပ်ရန်
                            }
                            media = MediaFileUpload(file_path, resumable=True)
                            file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                            flash(f"'{file_name}' ကို Google Drive သို့ အောင်မြင်စွာ upload လုပ်ပြီးပါပြီ။ File ID: {file.get('id')}", 'success')
                        except Exception as e:
                            flash(f"'{file_name}' ကို Google Drive သို့ upload လုပ်ရာတွင် error ဖြစ်ပွားသည်: {str(e)}", 'error')
            else:
                flash('Google Drive သို့ upload လုပ်ရန်အတွက် Google Drive ကို ဦးစွာချိတ်ဆက်ပါ။', 'warning')

    except subprocess.CalledProcessError as e:
        error = f"Command failed with error: {e.stderr}"
        flash(f"Download လုပ်ခြင်း မအောင်မြင်ပါ: {error}", 'error')
    except FileNotFoundError:
        error = f"{tool} ကို ရှာမတွေ့ပါ။ Railway.app မှာ မှန်ကန်စွာ install လုပ်ထားကြောင်း သေချာပါစေ။"
        flash(f"Download လုပ်ခြင်း မအောင်မြင်ပါ: {error}", 'error')
    except Exception as e:
        error = f"မမျှော်လင့်ထားသော error တစ်ခုဖြစ်ပွားခဲ့သည်: {str(e)}"
        flash(f"Download လုပ်ခြင်း မအောင်မြင်ပါ: {error}", 'error')
    finally:
        # ယာယီ folder ကို ပြန်ဖျက်မယ်။
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            
    gdrive_authorized = 'google_credentials' in session and session['google_credentials'] is not None
    return render_template('index.html', output=output, error=error, gdrive_authorized=gdrive_authorized)

if __name__ == '__main__':
    # Railway.app က PORT environment variable ကို ပေးပါလိမ့်မယ်။
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)