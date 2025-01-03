from flask import Flask, request, render_template, jsonify
import pyotp
import hashlib
import base64
import os
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas
from io import BytesIO
import pyzipper
import datetime
import pytz
import dotenv
import json
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from azure.identity import ClientSecretCredential

# Load environment variables
dotenv.load_dotenv()

client_id=os.getenv("client_id")
tenant_id=os.getenv("tenant_id")
client_secret=os.getenv("client_secret")
vault_url = os.getenv("kv_fileShare_URL")

connection_string = "fileShareConnectionString"
container_name = "fileShareContainerName"
main_email = "fileShareEmail"
brevo_api = "fileShareBrevoAPI"

# Create a credential for Azure Key Vault
credential = ClientSecretCredential(
    client_id = client_id, 
    client_secret= client_secret,
    tenant_id= tenant_id
)
client = SecretClient(vault_url=vault_url, credential=credential)

# Retrieve secrets from Azure Key Vault
received_connection_string = client.get_secret(connection_string)
received_container_name = client.get_secret(container_name)
received_main_email = client.get_secret(main_email)
received_brevo_api = client.get_secret(brevo_api)

app = Flask(__name__)

totp = pyotp.TOTP(pyotp.random_base32())
MAIN_EMAIL = received_main_email.value
generated_otp = None
attempts = 0

# Azure Blob Storage configuration
AZURE_STORAGE_CONNECTION_STRING = received_connection_string.value
CONTAINER_NAME = received_container_name.value

# BREVO configuration
BREVO_API_KEY = received_brevo_api.value

blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)

# Configure BREVO API
configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = BREVO_API_KEY
api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

def numeric_to_alphanumeric(numeric_otp):
    hash_object = hashlib.sha256(numeric_otp.encode())
    binary_digest = hash_object.digest()
    base64_encoded = base64.urlsafe_b64encode(binary_digest).decode('utf-8')
    base64_filtered = base64_encoded.replace('_', '').replace('-', '')
    alphanumeric_otp = base64_filtered[:5]
    return alphanumeric_otp

def send_OTP_mail(otp_code, mail_email, from_email):
    html_content = f"""
    <html>
        <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background: radial-gradient(#222, #101010); color: #ffffff;">
            <table cellpadding="0" cellspacing="0" border="0" width="100%" style="max-width: 600px; margin: 0 auto; padding: 2rem; border: 5px solid #cfff04; background-color: #000000;">
                <tr>
                    <td align="center" style="padding-bottom: 2rem;">
                        <h1 style="color: #cfff04; font-size: 24px; margin: 0;">Complete your fileShare Transfer</h1>
                    </td>
                </tr>
                <tr>
                    <td align="center" style="padding-bottom: 2rem;">
                        <p style="font-size: 16px; line-height: 1.5; margin: 0;">
                            Thank you for using fileShare, use this OTP to start the file transfer
                        </p>
                    </td>
                </tr>
                <tr>
                    <td align="center" style="padding-bottom: 2rem;">
                        <table cellpadding="0" cellspacing="0" border="0" style="border: 2px solid #cfff04; border-radius: 8px; background-color: rgba(207, 255, 4, 0.1); padding: 1rem;">
                            <tr>
                                <td align="center" style="padding: 1.5rem;">
                                    <span style="font-size: 32px; font-weight: bold; letter-spacing: 0.25em; color: #cfff04;">{otp_code}</span>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
                <tr>
                    <td align="center" style="padding-bottom: 2rem;">
                        <p style="font-size: 14px; color: #ffffff; margin: 0;">
                            If you did not request this code, please ignore this email
                        </p>
                    </td>
                </tr>
                <tr>
                    <td align="center" style="border-top: 5px solid #cfff04; padding-top: 1rem;">
                        <p style="font-size: 14px; color: #ffffff; margin: 0;">
                            Best regards,<br>
                            Mohammed Furqaan<br>
                            <span style="color: #cfff04;">fileShare Team</span>
                        </p>
                    </td>
                </tr>
            </table>
        </body>
    </html>
    """

    try:
        # Send OTP email using Brevo API
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": from_email}], 
            html_content=html_content, 
            sender={"name": "fileShare", "email": mail_email}, 
            subject="Verify your email"
        )
        
        api_response = api_instance.send_transac_email(send_smtp_email)
        return 201
    except ApiException as e:
        return 400

def send_file_link(file_url, recipients, from_email, message, zip_password):
    html_content = f"""
    <html>
        <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background: radial-gradient(#222, #101010); color: #ffffff;">
            <table cellpadding="0" cellspacing="0" border="0" width="100%" style="max-width: 600px; margin: 0 auto; padding: 2rem; border: 5px solid #cfff04; background-color: #000000;">
                <tr>
                    <td align="center" style="padding-bottom: 2rem;">
                        <h1 style="color: #cfff04; font-size: 24px; margin: 0;">File Shared with You</h1>
                    </td>
                </tr>
                <tr>
                    <td style="padding-bottom: 1rem;">
                        <p style="font-size: 16px; line-height: 1.5; margin: 0;">
                            <span style="color: #0000FF;">{from_email}</span> has shared a file with you using fileShare
                        </p>
                    </td>
                </tr>
                <tr>
                    <td style="padding-bottom: 1rem;">
                        <p style="font-size: 16px; line-height: 1.5; margin: 0;">
                            <strong style="color: #cfff04;">Message:</strong> {message}
                        </p>
                    </td>
                </tr>
                <tr>
                    <td align="center" style="padding-bottom: 1rem;">
                        <table cellpadding="0" cellspacing="0" border="0">
                            <tr>
                                <td align="center" style="background-color: #cfff04; border-radius: 4px; padding: 10px 20px;">
                                    <a href="{file_url}" style="color: #000000; text-decoration: none; font-weight: bold; font-size: 16px;">Download File</a>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
                <tr>
                    <td style="padding-bottom: 1rem;">
                        <p style="font-size: 16px; line-height: 1.5; margin: 0;">
                            This ZIP file is protected, use the password below to extract the files
                        </p>
                    </td>
                </tr>
                <tr>
                    <td align="center" style="padding-bottom: 1rem;">
                        <table cellpadding="0" cellspacing="0" border="0" style="border: 2px solid #cfff04; border-radius: 4px; background-color: rgba(207, 255, 4, 0.1);">
                            <tr>
                                <td align="center" style="padding: 10px 20px;">
                                    <span style="font-size: 18px; font-weight: bold; letter-spacing: 0.1em; color: #cfff04;">{zip_password}</span>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
                <tr>
                    <td align="center" style="padding-bottom: 2rem;">
                        <p style="font-size: 14px; color: #ff0000; margin: 0;">
                            <strong>Important:</strong> The download link will expire in 6 hours
                        </p>
                    </td>
                </tr>
                <tr>
                    <td align="center" style="border-top: 5px solid #cfff04; padding-top: 1rem;">
                        <p style="font-size: 14px; color: #ffffff; margin: 0;">
                            Best regards,<br>
                            Mohammed Furqaan<br>
                            <span style="color: #cfff04;">fileShare Team</span>
                        </p>
                    </td>
                </tr>
            </table>
        </body>
    </html>
    """

    try:
        # Send file link email using Brevo API
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": recipient} for recipient in recipients],
            html_content=html_content, 
            sender={"name": "fileShare", "email": MAIN_EMAIL}, 
            subject="You received files via fileShare"
        )
        
        api_response = api_instance.send_transac_email(send_smtp_email)
        return 201
    except ApiException as e:
        return 400

@app.route('/')
def index():
    return render_template('index.html')
    
@app.route('/privacy_page')
def privacy_page():
    return render_template('privacy.html')

@app.route('/send_otp', methods=['POST'])
def send_otp():
    global generated_otp
    data = request.json
    from_email = data.get('from')
    
    if not from_email:
        return jsonify({"message": "Missing 'from' email address."}), 400
    
    # Generate and send OTP
    numeric_otp = totp.now()
    generated_otp = numeric_to_alphanumeric(numeric_otp)
    status = send_OTP_mail(generated_otp, MAIN_EMAIL, from_email)
    
    if status == 201:
        return jsonify({"message": "OTP sent successfully!"})
    else:
        return jsonify({"message": "Failed to send OTP"}), 400

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    global attempts
    data = request.json
    otp = data.get('otp')
    
    # Verify OTP
    if otp == generated_otp:
        attempts = 0
        return jsonify({"message": "Verification successful!", "success": True})
    else:
        attempts += 1
        if attempts >= 3:
            attempts = 0
            return jsonify({"message": "Verification failed. File transfer won't happen.", "success": False, "reload": True})
        return jsonify({"message": f"Invalid OTP. Please enter the correct OTP. Attempts left: {3 - attempts}", "success": False})

def create_zip_generator(files, zip_password):
    """Generate ZIP file content in chunks"""
    zip_buffer = BytesIO()
    
    with pyzipper.AESZipFile(zip_buffer, "w", compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zip_file:
        zip_file.setpassword(zip_password.encode("utf-8"))
        for file in files:
            zip_file.writestr(file.filename, file.stream.read())
    
    zip_buffer.seek(0)
    while True:
        chunk = zip_buffer.read(4 * 1024 * 1024)  # 4MB chunks
        if not chunk:
            break
        yield chunk

@app.route("/upload", methods=["POST"])
def upload():
    try:
        files = request.files.getlist("files")
        from_email = request.form.get("from")
        message = request.form.get("message")
        recipients = json.loads(request.form.get("recipients"))

        if not files:
            return jsonify({"error": "No files provided."}), 400

        # Generate ZIP password
        zip_password = numeric_to_alphanumeric(pyotp.TOTP(pyotp.random_base32()).now())

        # Create timestamp in IST
        now_utc = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
        ist_timezone = pytz.timezone('Asia/Kolkata')
        now_ist = now_utc.astimezone(ist_timezone)
        timestamp = now_ist.strftime("%I.%M.%S.%p_%d-%m-%Y")
        zip_filename = f"fileShare-{timestamp}-{totp.now()}.zip"

        # Get blob client
        blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=zip_filename)

        # Start block upload
        block_list = []
        block_number = 0

        # Upload ZIP file in chunks
        for chunk in create_zip_generator(files, zip_password):
            block_id = base64.b64encode(str(block_number).zfill(10).encode()).decode()
            blob_client.stage_block(block_id, chunk)
            block_list.append(block_id)
            block_number += 1

        # Commit the blocks
        blob_client.commit_block_list(block_list)

        # Generate SAS Token with IST expiry
        expiry_time = now_ist + datetime.timedelta(minutes=30)
        sas_token = generate_blob_sas(
            account_name=blob_client.account_name,
            container_name=CONTAINER_NAME,
            blob_name=zip_filename,
            account_key=blob_service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=expiry_time
        )

        file_url = f"{blob_client.url}?{sas_token}"

        # Send email with file link to recipients
        send_status = send_file_link(file_url, recipients, from_email, message, zip_password)

        if send_status == 201:
            return jsonify({"message": "Files uploaded and shared successfully."})
        else:
            return jsonify({"error": "Failed to send email with file link."}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)