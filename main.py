import streamlit as st
import boto3
import json
import time
import os
from datetime import datetime
from datetime import datetime


def format_json_as_log(json_data):
    try:
        log_output = ""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        def process_item(item, prefix=""):
            nonlocal log_output
            if isinstance(item, dict):
                for key, value in item.items():
                    log_output += f"[{current_time}] - {key}:\n"
                    if isinstance(value, (list, str)):
                        if isinstance(value, list):
                            # Add color styling to the detection results
                            colored_results = '<span style="color: #00ff00;">[' + \
                                            ', '.join(str(v) for v in value) + \
                                            ']</span>\n'
                            log_output += colored_results
                        else:
                            log_output += f'<span style="color: #00ff00;">[{value}]</span>\n'
                    else:
                        log_output += f'<span style="color: #00ff00;">[{str(value)}]</span>\n'
            elif isinstance(item, list):
                log_output += f'<span style="color: #00ff00;">[{", ".join(str(v) for v in item)}]</span>\n'
            else:
                log_output += f'<span style="color: #00ff00;">[{str(item)}]</span>\n'
            
        # Handle both list and dictionary JSON formats
        if isinstance(json_data, list):
            for item in json_data:
                process_item(item)
        else:
            process_item(json_data)
            
        return log_output
    except Exception as e:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return f"[{current_time}] - Error formatting log: {str(e)}\n"

# Set page config for a wider layout and custom title
st.set_page_config(
    page_title="Video Uploader",
    page_icon="🎥",
    layout="wide",
)

# Custom CSS for a stunning look
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(to right, #1a1a1a, #2d2d2d);
        color: white;
    }
    .upload-header {
        text-align: center;
        padding: 2rem;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .json-content {
        background: rgba(255, 255, 255, 0.05);
        padding: 1rem;
        border-radius: 8px;
        margin-top: 1rem;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        padding: 15px 32px;
        border: none;
        border-radius: 4px;
        font-size: 16px;
    }
    </style>
""", unsafe_allow_html=True)

def get_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )

def upload_to_s3(file_obj, filename):
    try:
        s3_client = get_s3_client()
        bucket_name = "input-data-stream-nht"
        
        # Upload to S3
        s3_client.upload_fileobj(file_obj, bucket_name, filename)
        return True
        
    except Exception as e:
        st.error(f"Error uploading: {str(e)}")
        return False

def get_json_content(filename):
    try:
        s3_client = get_s3_client()
        json_bucket = "final-output-nht"
        
        # Extract base name without extension
        base_name = filename.rsplit('.', 1)[0]
        # Construct the JSON path: basename/basename.json
        json_key = f"{base_name}/{base_name}.json"
        
        try:
            response = s3_client.get_object(
                Bucket=json_bucket,
                Key=json_key
            )
            content = response['Body'].read().decode('utf-8')
            return json.loads(content)
        except s3_client.exceptions.NoSuchKey:
            st.info(f"Waiting for logs...")
            return None
        except s3_client.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                st.info(f"Waiting for logs...")
                return None
            else:
                st.error(f"Access Error: {str(e)}")
                return None
        
    except Exception as e:
        st.error(f"Error reading JSON: {str(e)}")
        return None

def main():
    # Header with animation
    st.markdown("<div class='upload-header'>", unsafe_allow_html=True)
    st.title("🎥 Video Uploader")
    st.subheader("Upload your video and view processing results")
    st.markdown("</div>", unsafe_allow_html=True)

    # Center the upload section
    col1, col2 = st.columns([2, 2])
    
    with col1:
        # File uploader with drag and drop
        uploaded_file = st.file_uploader(
            "Choose a video file", 
            type=['mp4', 'avi', 'mov'],
            help="Drag and drop or click to upload"
        )

        if uploaded_file:
            # Show video details
            file_details = {
                "Filename": uploaded_file.name,
                "File size": f"{uploaded_file.size / (1024*1024):.2f} MB"
            }
            st.json(file_details)

            # Upload button
            if st.button("Process Video", type="primary"):
                with st.spinner("Uploading ..."):
                    if upload_to_s3(uploaded_file, uploaded_file.name):
                        st.success("✅ Video Processing!")
                        # Store the filename in session state
                        st.session_state['current_file'] = uploaded_file.name
                    else:
                        st.error("❌ Failed to process video")
        else:
            # Placeholder message
            st.markdown("""
                ### 📤 Upload your video file
                Supported formats: MP4, AVI, MOV
            """)

    with col2:
        # Only show JSON content section if we have a file uploaded
        if 'current_file' in st.session_state:
            st.markdown("### Processing Log")
            
            # Create a placeholder for the JSON content
            log_placeholder = st.empty()
            
            # Add auto-refresh checkbox
            auto_refresh = st.checkbox('Auto-refresh logs', value=True)
            
            def update_log_content():
                json_content = get_json_content(st.session_state['current_file'])
                if json_content:
                    # Style for log display
                    # In the update_log_content function, update the style:
                    st.markdown("""
                        <style>
                        .log-container {
                            background-color: #1e1e1e;
                            color: #ffffff;  /* Changed to white for the timestamp and frame numbers */
                            font-family: 'Courier New', monospace;
                            padding: 15px;
                            border-radius: 5px;
                            height: 400px;
                            overflow-y: auto;
                            white-space: pre-wrap;
                            word-wrap: break-word;
                        }
                        </style>
                    """, unsafe_allow_html=True)
                    
                    log_text = format_json_as_log(json_content)
                    log_placeholder.markdown(
                        f"""<div class="log-container">{log_text}</div>""", 
                        unsafe_allow_html=True
                    )
                    return True
                else:
                    log_placeholder.info("Waiting for processing logs...")
                    return False

            # Initial update
            log_found = update_log_content()

            # Auto-refresh loop
            if auto_refresh:
                max_attempts = 10  # 5 minutes total
                attempt = 0
                
                while attempt < max_attempts:
                    time.sleep(10)  # Check every 5 seconds
                    attempt += 1
                    st.rerun()

if __name__ == "__main__":
    main()
