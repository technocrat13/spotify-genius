# import sys
# sys.path.append('/mnt/efs/')
import json

import boto3
import lyricsgenius as lg
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from requests import exceptions

import re


cid ='c73aee93e62c4b4aadb40c746b1abdc4'
secret ='14ce72b007bb4d24a40952c21f3b32e7'

client_credentials_manager = SpotifyClientCredentials(client_id=cid, client_secret=secret)
sp = spotipy.Spotify(client_credentials_manager = client_credentials_manager)

# l = ['7eX5SypK35V8Y9d9pS6rWy',
#         '4fPBB44eDH71YohayI4eKV',
#         #'2M7UdnD0fEaryh8TnCvqFX',
#         #'6LqZFfv4fUP7va14Y6VW9a',
# ]

# print(sp.audio_features(tracks=l))


token = '0GGXQLMawu2kxxYNqTGFT79I0wq8McYb8jbOz0HGOQc-sCAmu0HuYKo_C71dsRg-'
genius = lg.Genius(token, retries=3)
genius.verbose = True
# Remove section headers (e.g. [Chorus]) from lyrics when searching
genius.remove_section_headers = True

# Include hits thought to be non-songs (e.g. track lists)
genius.skip_non_songs = True

# Exclude songs with these words in their title
genius.excluded_terms = ["(Remix)", "(Live)"]

# import numpy as np
# np.random.seed(3407)
# R = np.random.normal(0, 1, (25, 384))

# import random
# import math

# # Set the random seed
# random.seed(3407)

# # Generate the random matrix R
# R = [[random.gauss(0, 1) for _ in range(384)] for _ in range(25)]

# # Define a function for matrix multiplication
# def matmul(A, B):
#     return [[sum(a*b for a, b in zip(A_row, B_col)) for B_col in zip(*B)] for A_row in A]


# from sentence_transformers import SentenceTransformer
# embedder = SentenceTransformer('msmarco-MiniLM-L-6-v3')

embed_remover = re.compile(r'\D*')

s3 = boto3.client('s3')
bucket_name = 'spotify-genius-featurestore'
folder_name = 'processed-features'

key = f'{folder_name}'

def remove_song_anatomy_tags(l):
    l = l.split('\n')
    l = l[1::]
    edited = []

    last_line = l[-1]
    last_line = last_line.split(' ')
    last_line[-1] = re.findall(embed_remover, last_line[-1])[0]
    l[-1] = ' '.join(last_line)

    for i in l:
        if i == '':
            continue

        if i == ' ':
            continue

        edited.append(i)

    return ' '.join(edited)


def get_song_lyrics_and_features(track_id, track_name, artist_name, popularity=50, explicit=0):
    feature_list = []
    track_features = sp.audio_features(tracks = [track_id])[0]

    feature_names = ['danceability', 'energy', 'key', 'loudness', 'mode', 'speechiness', 'acousticness', 'instrumentalness', 'liveness', 'valence', 'tempo', 'time_signature', 'duration_ms']

    for feature in feature_names:
        feature_list.append(track_features[feature])
        
    feature_list.append(popularity)
    feature_list.append(explicit)
    print(feature_list)

    
    max_tries = 4

    for i in range(max_tries):

        try:
            song = genius.search_song(track_name, artist_name)
            break
        except exceptions.Timeout:
            print(f'{track_name} pooped itself: {i} tries')
            if i == max_tries - 1:
                song = 'ERR_blank'
                # raise

    
    lyrics = remove_song_anatomy_tags(song.lyrics)
    print(lyrics)
    # embeddings = embedder.encode(lyrics, show_progress_bar=True)
    # embeddings_proj = np.dot(R, embeddings)
    # embeddings_proj = matmul(R, embeddings)

    # feature_list.extend(embeddings_proj)
    print(feature_list)
    return feature_list, lyrics


def lambda_handler(event, context):
    # TODO implement
    

    print(event)
    for song in event:
        track_id = song['id']
        track_name = song['name']
        artist_name = song['artist']
        popularity = song['popularity']
        explicit = song['explicit']
        
        features, full_lyrics = get_song_lyrics_and_features(track_id, track_name, artist_name, popularity, explicit)
        
        data = {
            'name': track_name,
            'artist': artist_name,
            'features': features,
            'lyrics': full_lyrics,
        }
        
        s3.put_object(Body=json.dumps(data), Bucket=bucket_name, Key=f'{key}/{track_id}.json')
        print('succes for {track_name}')
        
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }

