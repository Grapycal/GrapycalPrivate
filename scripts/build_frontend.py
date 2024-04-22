import os

# check frontend is changed from last build (hash.txt)

included = [
    "frontend/src",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/tsconfig.json",
    "frontend/webpack.config.standalone.js",
    "submodules/topicsync-client/src",
    "submodules/topicsync-client/package.json",
    "submodules/topicsync-client/package-lock.json",
    "submodules/objectsync-client/src",
    "submodules/objectsync-client/package.json",
    "submodules/objectsync-client/package-lock.json",
]


def hash_files() -> str:
    import hashlib

    h = hashlib.sha256()
    for path in included:
        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                for file in files:
                    with open(os.path.join(root, file), "rb") as f:
                        h.update(f.read())
        else:
            with open(path, "rb") as f:
                h.update(f.read())
    return h.hexdigest()


def read_hash() -> str:
    try:
        with open("frontend/last_build_hash.txt") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def write_hash(hash: str):
    with open("frontend/last_build_hash.txt", "w") as f:
        f.write(hash)


hash_result = hash_files()
if hash_result == read_hash():
    print("No changes in frontend. Skipping build.")
    exit(0)


if os.system("cd frontend && npm run build:standalone && cd .."):
    print("Failed to build frontend")
    exit(1)

write_hash(hash_result)
print("Frontend build successful")
