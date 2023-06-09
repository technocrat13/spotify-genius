from flask import Flask, render_template, request
import json
import boto3
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

app = Flask(__name__)

cid ='c73aee93e62c4b4aadb40c746b1abdc4'
secret ='14ce72b007bb4d24a40952c21f3b32e7'

client_credentials_manager = SpotifyClientCredentials(client_id=cid, client_secret=secret)
sp = spotipy.Spotify(client_credentials_manager = client_credentials_manager)


s3_client = boto3.client('s3', region_name='us-east-1')
lambda_client = boto3.client('lambda', region_name='us-east-1')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        playlist_url = request.form['playlist_url']
        # playlist_id = playlist_url.split('/')[-1]  # Extract playlist ID from URL
        results = sp.playlist_tracks(playlist_url)

        # Batch songs and send to Lambda function
        batch = []
        for item in results['items']:
            track = item['track']
            track_id = track['id']
            track_name = track['name']

            # Check if the song is already in the S3 bucket
            response = s3_client.list_objects_v2(Bucket='spotify-genius-featurestore', Prefix=f'processed-features/{track_id}')
            if 'Contents' in response:
                print(f"Track {track_name} is already in the S3 bucket.")
                continue

            batch.append({
                'id': track_id,
                'name': track_name,
                'artist': track['artists'][0]['name'],
                'popularity': track['popularity'],
                'explicit': int(track['explicit']),
            })
            if len(batch) == 25:
                lambda_client.invoke(
                    FunctionName='spotify-lyrcis-getter-3',
                    InvocationType='Event',
                    Payload=json.dumps(batch),
                )
                batch = []

        return 'Playlist submitted for processing.'
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)