import streamlit as st
import boto3
import json

# Configure AWS credentials and region
# Make sure you have the necessary permissions to access Bedrock
boto3.setup_default_session(region_name='us-west-2')  # Replace with your region

# Create a Bedrock Runtime client
bedrock_runtime = boto3.client('bedrock-runtime')

# Streamlit app
st.title("Amazon Bedrock Model Streaming Demo")

# Model selection
model_id = st.selectbox(
    "Select Bedrock Model",
    ["anthropic.claude-3-sonnet-20240229-v1:0", "anthropic.claude-v2:1"]
)

# User input
user_input = st.text_area("Enter your prompt:", height=100)

if st.button("Generate Response"):
    if user_input:
        # Prepare the request
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": user_input
                }
            ]
        }

        try:
            # Invoke the model with streaming
            response = bedrock_runtime.invoke_model_with_response_stream(
                modelId=model_id,
                body=json.dumps(request_body)
            )

            # Initialize the response area
            response_area = st.empty()
            full_response = ""

            # Process the streaming response
            for event in response['body']:
                chunk = event.get('chunk')
                if chunk:
                    chunk_obj = json.loads(chunk.get('bytes').decode())
                    if "delta" in chunk_obj:
                        delta = chunk_obj['delta']
                        if "text" in delta:
                            text = delta['text']
                            full_response += text
                            response_area.markdown(full_response)

            # Display final response
            st.success("Response generated successfully!")

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
    else:
        st.warning("Please enter a prompt.")

# Add some information about the app
st.sidebar.header("About")
st.sidebar.info(
    "This Streamlit app demonstrates how to use Amazon Bedrock "
    "to generate streaming responses from AI models. "
    "Enter your prompt and watch the response generate in real-time!"
)
