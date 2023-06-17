import numpy as np
from sentence_transformers import SentenceTransformer
embedder = SentenceTransformer('msmarco-MiniLM-L-6-v3')

np.random.seed(3407)
R = np.random.normal(0, 1, (25, 384))
print(R)



embeddings = embedder.encode(remove_song_anatomy_tags(song.lyrics), show_progress_bar=True)
embeddings_proj = np.dot(R, embeddings)



import boto3
import json

sagemaker_runtime = boto3.client('sagemaker-runtime')

# Specify the endpoint name
endpoint_name = 'your-endpoint-name'

# Specify the input data
input_data = {
    'instances': [
        # Your input data here
    ],
}

# Call the SageMaker endpoint
response = sagemaker_runtime.invoke_endpoint(
    EndpointName=endpoint_name,
    Body=json.dumps(input_data),
    ContentType='application/json',
)

# Parse the response
predictions = json.loads(response['Body'].read().decode())
