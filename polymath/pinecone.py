import os

import numpy as np
import pinecone
from library import EXPECTED_EMBEDDING_LENGTH, Bit, Library, vector_from_base64
from overrides import override

# TODO: Make this configurable
TOP_K = 100


class PineconeConfig:
    def __init__(self, config):
        self.namespace = config['namespace']
        self.index = config.get('index', 'polymath')
        self.environment = config.get('environment', 'us-west1-gcp')


class PineconeLibrary(Library):
    def __init__(self, config):
        self.config = PineconeConfig(config)
        super().__init__()

    @override
    def _produce_query_result(self, query_embedding, sort, sort_reversed, seed):
        self.omit = 'embedding'
        pinecone.init(
            api_key=os.getenv("PINECONE_API_KEY"),
            environment=self.config.environment)
        index = pinecone.Index(self.config.index)
        embedding = None
        if sort == 'similarity':
            embedding = vector_from_base64(query_embedding).tolist()
        else:
            embedding_length = EXPECTED_EMBEDDING_LENGTH[self.embedding_model]
            embedding = np.random.rand(embedding_length).tolist()
        result = index.query(
            namespace=self.config.namespace,
            top_k=100,
            include_metadata=True,
            vector=embedding
        )
        for item in result['matches']:
            bit = Bit(data={
                'id': item['id'],
                'text': item['metadata']['text'],
                'token_count': item['metadata'].get('token_count'),
                'access_tag': item['metadata'].get('access_tag'),
                'info': {
                    'url': item['metadata']['url'],
                    'image_url': item['metadata'].get('image_url'),
                    'title': item['metadata'].get('title'),
                    'description': item['metadata'].get('description'),
                }
            })
            self.insert_bit(bit)
