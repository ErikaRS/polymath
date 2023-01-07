import argparse
import json
import os

import openai
import urllib3
from dotenv import load_dotenv

from ask_embeddings import (base64_from_vector, get_completion_with_context,
                            get_embedding, Library, get_context_for_library,
                            get_chunk_infos_for_library, CURRENT_VERSION,
                            EMBEDDINGS_MODEL_ID)

# TODO: Make this computed from the number of servers.
CONTEXT_TOKEN_COUNT = 1500


def query_server(query_embedding, random, server):
    http = urllib3.PoolManager()
    fields = {
        "version": CURRENT_VERSION,
        "query_embedding_model": EMBEDDINGS_MODEL_ID,
        "count": CONTEXT_TOKEN_COUNT
    }
    if random:
        fields["sort"] = "random"
    else:
        fields["query_embedding"] = query_embedding
    response = http.request(
        'POST', server, fields=fields).data
    obj = json.loads(response)
    if 'error' in obj:
        error = obj['error']
        raise Exception(f"Server returned an error: {error}")
    return Library(data=obj)


parser = argparse.ArgumentParser()
parser.add_argument("query", help="The question to ask",
                    default="Tell me about 3P")
parser.add_argument("--server", help="A server to use for querying",
                    action="append", required=True),
parser.add_argument("--completion", help="Request completion based on the query and context",
                    action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--random", help="Ask for a random set of chunks",
                    action=argparse.BooleanOptionalAction, default=False)
parser.add_argument("--verbose", help="Print out context and sources and other useful intermediate data",
                    action=argparse.BooleanOptionalAction, default=False)
args = parser.parse_args()

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

query = args.query
server_list = args.server

if args.verbose:
    if args.random:
        print("Getting random chunks ...")
    else:
        print(f"Getting embedding for \"{query}\" ...")

query_vector = None if args.random else base64_from_vector(
    get_embedding(query))

context = []
sources = []
for server in server_list:
    print(f"Querying {server} ...") if args.verbose else None
    # for now, just combine contexts
    library = query_server(query_vector, args.random, server)
    context.extend(get_context_for_library(library))
    sources.extend([chunk["url"]
                   for chunk in get_chunk_infos_for_library(library)])

sources = "\n  ".join(sources)

if args.verbose:
    context_str = "\n\n".join(context)
    print(f"Context:\n{context_str}")
    print(f"\nSources:\n  {sources}")

if args.completion:
    print("Getting completion ...") if args.verbose else None
    print(f"\nAnswer:\n{get_completion_with_context(query, context)}")
    print(f"\nSources:\n  {sources}")
