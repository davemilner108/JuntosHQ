import json

meta_file = "corpus/founders_online_metadata.json"

with open(meta_file, encoding="utf-8") as f:
    data = json.load(f)

print(type(data))         # dict? list?
print(len(data))          # number of items
print(list(data[0].keys()))  # keys in first document
print(data[0])            # optional: see first doc
