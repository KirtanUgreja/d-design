"""auth — session resolution and the fail-closed spine (v3, phase 16).

api never issues sessions (that is Better Auth in web); it resolves them
read-only so tenant-scoped work can run inside the as_user wrapper.
"""
